#!/usr/bin/env python3
"""
Production Card Identification System - Shop Ready
Integrates: DINOv2 visual, ORB geometric, foil detection, card number extraction

Ready for deployment with document camera at card shop.

Usage:
    python production_card_identifier.py <image_path> [--tcg one-piece]

Author: Senior Principal Engineer
"""
import sys
import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import numpy as np
    import faiss
    import torch
    import cv2
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel

    # Import our custom modules
    from universal_card_extractor import UniversalCardExtractor, TCG
    from foil_detector import FoilDetector
    from variant_classifier import VariantClassifier
    from polished_card_detector import PolishedCardDetector
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("  pip install numpy opencv-python pillow torch transformers faiss-cpu easyocr")
    sys.exit(1)

# Configuration
ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "faiss"
IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"

MODEL_NAME = "facebook/dinov2-small"
DEFAULT_GAME = "one-piece"

# Scoring weights (base weights, dynamically adjusted per-candidate)
WEIGHT_VISUAL_BASE = 0.70
WEIGHT_GEOMETRIC_BASE = 0.30

# Thresholds (tuned for shop operations - balanced accuracy and throughput)
# Updated 2025-10-21: Lowered thresholds based on real-world shop testing
# Analysis showed original thresholds (0.75/0.62) were too strict for:
# - Cards in sleeves (glare reduces score by 0.05-0.10)
# - Real photos vs database images (inherent 0.05-0.08 gap)
# - Text-heavy event cards (geometric matching weaker)
THRESHOLD_HIGH = 0.70       # High confidence - auto-accept (was 0.75)
THRESHOLD_MODERATE = 0.55   # Moderate confidence - review recommended (was 0.62)
THRESHOLD_MARGIN = 0.08     # Margin for confidence boost (was 0.10, tightened slightly)


class ProductionCardIdentifier:
    """
    Production-ready card identification system.

    Features:
    - Universal TCG support (MTG, Yu-Gi-Oh, Pokémon, One Piece, etc.)
    - Foil detection
    - Card number extraction
    - Variant-aware scoring
    - Robust error handling
    """

    def __init__(self, game: str = DEFAULT_GAME, verbose: bool = True, enable_variant_classifier: bool = True):
        """
        Initialize production identifier.

        Args:
            game: Game to identify (default: one-piece)
            verbose: Print status messages
            enable_variant_classifier: Enable variant classification (default: True)
        """
        self.game = game
        self.verbose = verbose
        self.enable_variant_classifier = enable_variant_classifier

        if self.verbose:
            print("="*70)
            print("PRODUCTION CARD IDENTIFICATION SYSTEM")
            print("="*70)
            print(f"Initializing for game: {game}")
            if enable_variant_classifier:
                print(f"Variant classification: ENABLED")

        # Load DINOv2 model
        if self.verbose:
            print("\n[1/6] Loading DINOv2 vision model...")
        start = time.time()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        if self.verbose:
            print(f"  [OK] Model loaded on {self.device} ({time.time()-start:.1f}s)")

        # Load FAISS index
        if self.verbose:
            print(f"\n[2/6] Loading FAISS index for {game}...")
        start = time.time()

        index_file = FAISS_DIR / f"{game}-dinov2" / "index.faiss"
        ids_file = FAISS_DIR / f"{game}-dinov2" / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_file}\n"
                f"Please run the embedder and indexer scripts first."
            )

        self.index = faiss.read_index(str(index_file))

        with open(ids_file, 'r', encoding='utf-8') as f:
            self.card_ids = json.load(f)

        if self.verbose:
            print(f"  [OK] Loaded {self.index.ntotal} cards ({time.time()-start:.1f}s)")

        # Load metadata
        if self.verbose:
            print(f"\n[3/6] Loading card metadata...")
        start = time.time()

        metadata_file = ARTIFACTS_DIR / "embeddings" / f"{game}-dinov2" / "metadata.jsonl"
        self.metadata = {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    self.metadata[meta['id']] = meta

        if self.verbose:
            print(f"  [OK] Metadata loaded ({time.time()-start:.1f}s)")

        # Initialize geometric matchers with SIFT→ORB→AKAZE cascade
        if self.verbose:
            print(f"\n[4/6] Initializing geometric matchers (SIFT + ORB + AKAZE)...")

        # SIFT: Best accuracy (most discriminative features)
        # Patent expired 2020 - now free to use
        self.sift = cv2.SIFT_create(
            nfeatures=1000,
            contrastThreshold=0.04,  # Lower = more features detected
            edgeThreshold=10,        # Lower = detect features on edges
            sigma=1.6                # Gaussian blur for scale space
        )

        # ORB: Fast and good for most cases
        # Increased from 500 to 1000 features for more robust matching
        # Higher nfeatures = more keypoints = better matching on complex card art
        self.orb = cv2.ORB_create(
            nfeatures=1000,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=15,  # Lower threshold = detect features closer to edges
            firstLevel=0,
            WTA_K=2,
            patchSize=31
        )

        # AKAZE: Best for compressed/low-res images
        self.akaze = cv2.AKAZE_create()

        if self.verbose:
            print(f"  [OK] SIFT + ORB + AKAZE initialized (triple cascade matching)")

        # Load pre-computed keypoints if available (for geometric optimization)
        KEYPOINTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "keypoints"
        keypoints_path = KEYPOINTS_DIR / game / "orb_keypoints.npz"
        if keypoints_path.exists():
            if self.verbose:
                print(f"\n  Loading pre-computed keypoints...")
            self.precomputed_keypoints = np.load(keypoints_path, allow_pickle=True)
            if self.verbose:
                file_size_mb = keypoints_path.stat().st_size / 1024 / 1024
                print(f"  [OK] Loaded {len(self.precomputed_keypoints.files)} card keypoints ({file_size_mb:.1f} MB)")
        else:
            self.precomputed_keypoints = None
            if self.verbose:
                print(f"\n  [INFO] Pre-computed keypoints not found (will compute on-the-fly)")

        # Initialize universal extractors
        if self.verbose:
            print(f"\n[5/7] Initializing universal extractors...")
        start = time.time()

        self.card_extractor = UniversalCardExtractor(ocr_backend='easy')
        self.foil_detector = FoilDetector()
        self.card_detector = PolishedCardDetector(verbose=False)

        if self.verbose:
            print(f"  [OK] Extractors ready (including card detector) ({time.time()-start:.1f}s)")

        # Initialize variant classifier (if enabled)
        self.variant_classifier = None
        if self.enable_variant_classifier:
            if self.verbose:
                print(f"\n[6/7] Initializing variant classifier...")
            start = time.time()

            self.variant_classifier = VariantClassifier(verbose=False)

            if self.verbose:
                print(f"  [OK] Variant classifier ready ({time.time()-start:.1f}s)")

        if self.verbose:
            print("\n" + "="*70)
            print("SYSTEM READY")
            print("="*70 + "\n")

    def _check_image_quality(self, image_path: str) -> Dict:
        """
        Check image quality to detect blurry or low-quality captures.

        Returns:
            {
                'is_acceptable': bool,
                'sharpness_score': float,
                'brightness': float,
                'warnings': list
            }
        """
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {
                'is_acceptable': False,
                'sharpness_score': 0.0,
                'brightness': 0.0,
                'warnings': ['Image could not be loaded']
            }

        warnings = []

        # Check image size (too small = poor quality)
        if min(img.shape) < 200:
            warnings.append(f'Image too small ({img.shape[1]}x{img.shape[0]})')

        # Check sharpness using Laplacian variance
        # Higher variance = sharper image
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        sharpness_score = laplacian.var()

        if sharpness_score < 50:
            warnings.append(f'Image may be blurry (sharpness: {sharpness_score:.1f})')

        # Check brightness
        brightness = np.mean(img)

        if brightness < 50:
            warnings.append(f'Image too dark (brightness: {brightness:.1f})')
        elif brightness > 220:
            warnings.append(f'Image overexposed (brightness: {brightness:.1f})')

        # Acceptable if no critical issues
        is_acceptable = sharpness_score >= 30 and 30 <= brightness <= 240

        return {
            'is_acceptable': is_acceptable,
            'sharpness_score': float(sharpness_score),
            'brightness': float(brightness),
            'warnings': warnings
        }

    def identify(
        self,
        image_path: str,
        top_k: int = 50,  # Increased from 30 to 50 for better recall
        use_geometric: bool = True,
        tcg_hint: Optional[str] = None
    ) -> Dict:
        """
        Identify card with full analysis.

        Args:
            image_path: Path to card image
            top_k: Number of visual candidates (default: 50, optimized for accuracy)
            use_geometric: Enable geometric verification (default: True)
            tcg_hint: TCG hint for card number extraction (e.g., 'one-piece', 'pokemon')

        Returns:
            Complete identification result with confidence scoring
        """
        start_time = time.time()

        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        result = {
            'image_path': image_path,
            'matches': [],
            'best_match': None,
            'scores': {},
            'time_ms': 0,
            'confidence': 'UNKNOWN',
            'foil_detected': False,
            'card_number_extracted': None,
            'quality_check': {},
        }

        # Stage 0a: Image quality check
        if self.verbose:
            print(f"Analyzing: {Path(image_path).name}")
            print("-" * 70)
            print("[Stage 0a] Image quality check...")

        quality = self._check_image_quality(image_path)
        result['quality_check'] = quality

        if self.verbose:
            status = "[OK]" if quality['is_acceptable'] else "[WARN]"
            print(f"  {status} Sharpness: {quality['sharpness_score']:.1f}, Brightness: {quality['brightness']:.1f}")
            for warning in quality['warnings']:
                print(f"  [WARN] {warning}")

        # Continue even if quality is poor (but flag it)

        # Stage 0b: Foil detection and card number extraction (parallel)
        if self.verbose:
            print(f"\n[Stage 0b] Feature extraction...")

        stage0_start = time.time()

        # Foil detection
        foil_result = self.foil_detector.detect_foil(image_path)
        result['foil_detected'] = foil_result.is_foil
        result['foil_type'] = foil_result.foil_type.value
        result['foil_confidence'] = foil_result.confidence

        if self.verbose:
            foil_status = f"[YES] Foil" if foil_result.is_foil else "[NO] Foil"
            print(f"  {foil_status}: {foil_result.foil_type.value} (conf: {foil_result.confidence:.3f})")

        # Card number extraction
        tcg_enum = None
        if tcg_hint:
            tcg_map = {
                'mtg': TCG.MTG, 'magic': TCG.MTG,
                'yugioh': TCG.YUGIOH, 'ygo': TCG.YUGIOH,
                'pokemon': TCG.POKEMON, 'ptcg': TCG.POKEMON,
                'one-piece': TCG.ONE_PIECE, 'optcg': TCG.ONE_PIECE,
                'digimon': TCG.DIGIMON,
                'gundam': TCG.GUNDAM,
                'lorcana': TCG.LORCANA,
            }
            tcg_enum = tcg_map.get(tcg_hint.lower())

        card_num_result = self.card_extractor.extract_card_number(image_path, tcg_hint=tcg_enum)
        if card_num_result:
            result['card_number_extracted'] = card_num_result.card_number
            result['tcg_detected'] = card_num_result.tcg.value
            result['card_number_confidence'] = card_num_result.confidence

            if self.verbose:
                print(f"  [OK] Card Number: {card_num_result.card_number} ({card_num_result.tcg.value}, conf: {card_num_result.confidence:.3f})")
        else:
            if self.verbose:
                print(f"  [--] Card Number: Not detected")

        stage0_time = time.time() - stage0_start

        # Stage 1: Visual retrieval
        if self.verbose:
            print(f"\n[Stage 1] Visual retrieval (DINOv2, top {top_k})...")
        stage1_start = time.time()

        embedding = self._get_image_embedding(image_path)
        embedding_2d = np.array([embedding])

        distances, indices = self.index.search(embedding_2d, top_k)

        # Build candidates
        candidates = []
        for idx, (dist, index) in enumerate(zip(distances[0], indices[0])):
            card_id = self.card_ids[int(index)]
            meta = self.metadata.get(card_id, {})

            candidates.append({
                'rank': idx + 1,
                'card_id': card_id,
                'product_id': meta.get('productId'),
                'name': meta.get('name', 'Unknown'),
                'number': meta.get('number', ''),
                'set': meta.get('set'),
                'rarity': meta.get('rarity'),
                'imageUrl': meta.get('imageUrl'),
                'prices': meta.get('prices', {}),
                'url': meta.get('url', ''),
                'visual_score': float(dist),
                'geometric_score': 0.0,
                'card_number_match': 0.0,
                'foil_match': 0.0,
                'final_score': 0.0,
            })

        stage1_time = time.time() - stage1_start
        if self.verbose:
            print(f"  [OK] Found {len(candidates)} candidates ({stage1_time*1000:.0f}ms)")

        # Stage 2: Card number filtering (if extracted)
        if card_num_result:
            if self.verbose:
                print(f"\n[Stage 2] Card number clustering...")
            stage2_start = time.time()

            # Boost candidates with matching card numbers
            extracted_num = card_num_result.card_number
            for candidate in candidates:
                candidate_name = candidate['name']
                candidate_number = candidate['number']

                # Check if extracted number appears in candidate
                if extracted_num in candidate_name or extracted_num == candidate_number:
                    candidate['card_number_match'] = 1.0
                    if self.verbose:
                        print(f"  [OK] Match: {candidate['name']}")

            # Sort by card number match (matching cards first)
            candidates.sort(key=lambda x: x['card_number_match'], reverse=True)

            stage2_time = time.time() - stage2_start
            matches = sum(1 for c in candidates if c['card_number_match'] > 0)
            if self.verbose:
                print(f"  [OK] Clustered: {matches} matching variants ({stage2_time*1000:.0f}ms)")

            # NEW: OCR Hard Filter - If OCR confidence is high, narrow down to matching cards only
            # This dramatically speeds up identification when card number is read successfully
            # Expected impact: -300-400ms on 60-70% of identifications
            if card_num_result.confidence > 0.80 and matches >= 3:
                # Filter to only matching cards
                candidates = [c for c in candidates if c['card_number_match'] > 0]
                if self.verbose:
                    print(f"  [OCR FILTER] High confidence OCR ({card_num_result.confidence:.2f}) - narrowed to {len(candidates)} matching variants")
                    print(f"               Skipping {top_k - len(candidates)} non-matching candidates")

        # Stage 3: Geometric verification (OPTIMIZED for speed)
        # OPTIMIZATION: Reduced to top 10 (was 20) for -40% geometric time
        # Early stopping when strong match found (score > 0.8)
        if use_geometric:
            if self.verbose:
                print(f"\n[Stage 3] Geometric verification (Hybrid SIFT+ORB+AKAZE, top 10)...")
            stage3_start = time.time()

            # SPEED OPTIMIZATION: Only verify top 10 candidates (was 20)
            # Impact: -600ms to -1000ms (roughly -40% geometric time)
            top_candidates = candidates[:10]
            verified = 0
            early_stopped = False

            for idx, candidate in enumerate(top_candidates):
                card_id = candidate['card_id']

                # Find candidate image
                candidate_image = None
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    candidate_path = IMAGES_DIR / self.game / f"{card_id}{ext}"
                    if candidate_path.exists():
                        candidate_image = str(candidate_path)
                        break

                if candidate_image:
                    # Use triple cascade SIFT → ORB → AKAZE matching
                    geom_score = self._compute_geometric_similarity_hybrid(image_path, candidate_image)
                    candidate['geometric_score'] = geom_score
                    if geom_score > 0.05:  # Count anything above 0.05 as verified
                        verified += 1

                    # EARLY STOP: If we found a very strong geometric match, stop verification
                    # Visual > 0.85 + Geometric > 0.8 = very likely correct
                    if candidate['visual_score'] > 0.85 and geom_score > 0.8:
                        early_stopped = True
                        if self.verbose:
                            print(f"  [EARLY STOP] Strong match found at rank {idx+1} (V:{candidate['visual_score']:.3f} G:{geom_score:.3f})")
                        break

            stage3_time = time.time() - stage3_start
            if self.verbose:
                verified_count = len(top_candidates) if not early_stopped else idx + 1
                print(f"  [OK] Verified {verified}/{verified_count} candidates ({stage3_time*1000:.0f}ms)")
                if early_stopped:
                    print(f"  [SPEED] Stopped early, saved {(10 - idx - 1)} unnecessary verifications")

        # Stage 4: Foil-aware scoring
        if foil_result.is_foil:
            if self.verbose:
                print(f"\n[Stage 4] Foil-aware scoring...")

            for candidate in candidates:
                # Check if candidate is foil/parallel variant
                name_lower = candidate['name'].lower()
                is_foil_variant = any(term in name_lower for term in [
                    'parallel', 'foil', 'holo', 'alternate art', 'full art',
                    'rainbow', 'secret', 'texture', 'manga'
                ])

                if is_foil_variant:
                    candidate['foil_match'] = 1.0

        # Stage 5: Dynamic score fusion with adaptive weighting
        if self.verbose:
            print(f"\n[Stage 5] Dynamic score fusion...")

        for candidate in candidates:
            visual = candidate['visual_score']
            geom = candidate['geometric_score']
            card_num_boost = candidate['card_number_match'] * 0.12  # 12% boost (reduced from 15%)
            foil_boost = candidate['foil_match'] * 0.05  # 5% boost

            # Adaptive weighting based on geometric quality
            # Updated 2025-10-21: Shifted to visual-heavy based on shop testing
            # Analysis showed geometric is unreliable on real photos (fails 28%, weak 43%)
            # Visual is consistent (never fails) and works well on shop conditions
            # See: VISUAL_VS_GEOMETRIC_ANALYSIS.md for detailed analysis
            if geom > 0.15:
                # Geometric successful - but still favor visual for shop photos
                weight_visual = 0.75  # Was 0.60 (+15% visual)
                weight_geometric = 0.25  # Was 0.40
            elif geom > 0.05:
                # Geometric weak - heavily favor visual
                weight_visual = 0.85  # Was 0.75 (+10% visual)
                weight_geometric = 0.15  # Was 0.25
            else:
                # Geometric failed - almost pure visual
                weight_visual = 0.95  # Was 0.90 (+5% visual)
                weight_geometric = 0.05  # Was 0.10

            # Base score with dynamic weights
            final_score = (
                weight_visual * visual +
                weight_geometric * geom
            )

            # Apply boosts
            final_score += card_num_boost + foil_boost

            # Store weights used for debugging
            candidate['weights_used'] = {
                'visual': weight_visual,
                'geometric': weight_geometric
            }

            candidate['final_score'] = min(final_score, 1.0)  # Cap at 1.0

        # Sort by final score
        candidates.sort(key=lambda x: x['final_score'], reverse=True)

        # Re-rank
        for idx, candidate in enumerate(candidates):
            candidate['rank'] = idx + 1

        # Stage 6: Variant classification (if enabled and multiple variants detected)
        stage6_time = 0
        best = candidates[0]

        if self.variant_classifier and card_num_result:
            # Check if we have multiple candidates with same card number (variants)
            base_card_number = best['number']
            same_number_candidates = [c for c in candidates[:10] if c['number'] == base_card_number]

            if len(same_number_candidates) >= 2:
                # Multiple variants detected - run variant classifier
                if self.verbose:
                    print(f"\n[Stage 6] Variant classification ({len(same_number_candidates)} variants detected)...")
                stage6_start = time.time()

                # Prepare metadata for variant candidates
                variant_metadata = []
                for c in same_number_candidates:
                    # Add full metadata
                    full_meta = self.metadata.get(c['card_id'], {})
                    full_meta['id'] = c['card_id']
                    full_meta['card_id'] = c['card_id']
                    variant_metadata.append(full_meta)

                # Classify variants
                variant_results = self.variant_classifier.classify_variant(
                    query_image_path=image_path,
                    base_card_number=base_card_number,
                    variant_candidates=variant_metadata,
                    query_foil_detected=foil_result.is_foil,
                    query_foil_type=foil_result.foil_type.value if foil_result.is_foil else None
                )

                # Re-rank candidates based on variant classification
                variant_scores = {vc.card_id: vc.final_score for vc in variant_results}

                for candidate in candidates:
                    if candidate['card_id'] in variant_scores:
                        # Blend original score with variant score (70% original, 30% variant)
                        variant_boost = variant_scores[candidate['card_id']] * 0.30
                        candidate['variant_score'] = variant_scores[candidate['card_id']]
                        candidate['final_score'] = min(
                            candidate['final_score'] * 0.70 + variant_boost,
                            1.0
                        )

                # Re-sort with variant scores
                candidates.sort(key=lambda x: x['final_score'], reverse=True)

                # Re-rank
                for idx, candidate in enumerate(candidates):
                    candidate['rank'] = idx + 1

                # Update best match
                best = candidates[0]

                stage6_time = time.time() - stage6_start
                if self.verbose:
                    print(f"  [OK] Variant classified: {best['name']}")
                    print(f"  Variant type: {variant_results[0].variant_type.value}")
                    print(f"  Variant confidence: {variant_results[0].final_score:.3f}")
                    print(f"  Processing time: {stage6_time*1000:.0f}ms")

        # Determine confidence with improved logic
        confidence = "LOW"
        margin = 0.0

        if len(candidates) > 1:
            margin = best['final_score'] - candidates[1]['final_score']

        # Multi-factor confidence determination
        if best['final_score'] >= THRESHOLD_HIGH:
            # High score = high confidence
            confidence = "HIGH"
        elif best['final_score'] >= THRESHOLD_MODERATE and margin >= THRESHOLD_MARGIN:
            # Good score + clear winner = high confidence
            confidence = "HIGH"
        elif best['final_score'] >= THRESHOLD_MODERATE:
            # Good score but close race = moderate confidence
            confidence = "MODERATE"
        elif best['geometric_score'] > 0.3 and best['visual_score'] > 0.65:
            # Strong geometric + decent visual = moderate confidence (rescue case)
            confidence = "MODERATE"
        elif margin >= THRESHOLD_MARGIN * 1.5:
            # Clear winner despite low score = moderate confidence
            confidence = "MODERATE"
        else:
            # Everything else = low confidence
            confidence = "LOW"

        # Finalize result
        total_time = time.time() - start_time

        result['matches'] = candidates
        result['best_match'] = best
        result['scores'] = {
            'visual': best['visual_score'],
            'geometric': best['geometric_score'],
            'card_number_boost': best['card_number_match'] * 0.15,
            'foil_boost': best['foil_match'] * 0.05,
            'final': best['final_score'],
        }
        result['time_ms'] = int(total_time * 1000)
        result['confidence'] = confidence

        # Performance breakdown
        result['timing'] = {
            'feature_extraction_ms': int(stage0_time * 1000),
            'visual_search_ms': int(stage1_time * 1000),
            'geometric_verify_ms': int(stage3_time * 1000) if use_geometric else 0,
            'variant_classify_ms': int(stage6_time * 1000),
            'total_ms': int(total_time * 1000),
        }

        if self.verbose:
            print(f"\n{'='*70}")
            self._print_result(result)

        return result

    def _get_image_embedding(self, image_path: str) -> np.ndarray:
        """
        Generate DINOv2 embedding WITH preprocessing to match index embeddings.

        CRITICAL: Must match preprocessing in embed_onepiece_dinov2_with_preprocessing.py
        to ensure embeddings are in the same vector space.
        """
        image = Image.open(image_path).convert("RGB")

        # Apply same preprocessing as embedder (bilateral filter + contrast enhancement)
        img_array = np.array(image)

        # Bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)

        # Contrast enhancement
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)

        # Convert back to PIL Image
        image = Image.fromarray(enhanced)

        # Generate embedding with DINOv2
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def _compute_orb_similarity(self, query_path: str, candidate_path: str) -> float:
        """
        Compute ORB geometric similarity with robust preprocessing.

        Uses bilateral filtering + CLAHE + multi-threshold matching for
        watermark-resistant feature detection.
        """
        try:
            img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Apply bilateral filter first (consistent with visual embedding)
            img1 = cv2.bilateralFilter(img1, 5, 50, 50)
            img2 = cv2.bilateralFilter(img2, 5, 50, 50)

            # Upscale if too small (improves feature detection)
            min_size = 400  # Increased from 300 for better feature quality
            if min(img1.shape) < min_size:
                scale = min_size / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            if min(img2.shape) < min_size:
                scale = min_size / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            # CLAHE enhancement (improves contrast for feature detection)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img1 = clahe.apply(img1)
            img2 = clahe.apply(img2)

            # Detect features for query image (always on-the-fly)
            kp1, des1 = self.orb.detectAndCompute(img1, None)

            if des1 is None or len(des1) < 8:
                return 0.0

            # Get candidate (reference) features - use pre-computed if available
            candidate_id = Path(candidate_path).stem

            if hasattr(self, 'precomputed_keypoints') and self.precomputed_keypoints is not None and candidate_id in self.precomputed_keypoints:
                # FAST PATH: Use pre-computed descriptors
                ref_data = self.precomputed_keypoints[candidate_id].item()
                des2 = ref_data.get('descriptors')

                if des2 is None or len(des2) < 8:
                    return 0.0

                # Use pre-computed num_keypoints for scoring
                num_kp2 = ref_data.get('num_keypoints', len(des2))
            else:
                # FALLBACK: Compute on-the-fly (for cards without pre-computed keypoints)
                kp2, des2 = self.orb.detectAndCompute(img2, None)

                if des2 is None or len(des2) < 8:
                    return 0.0

                num_kp2 = len(kp2)

            # Match using BFMatcher with Hamming distance
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Lowe's ratio test (relaxed from 0.75 to 0.80 for more matches)
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    # Relaxed threshold allows more valid matches through
                    if m.distance < 0.80 * n.distance:
                        good_matches.append(m)

            # Require minimum matches (lowered from 4 to 3)
            if len(good_matches) < 3:
                return 0.0

            # Calculate match quality with improved scoring
            num_keypoints_max = max(len(kp1), num_kp2)
            num_keypoints_min = min(len(kp1), num_kp2)

            # Match ratio based on max keypoints (how many of the features matched)
            match_ratio = len(good_matches) / num_keypoints_max

            # Coverage ratio (ensures both images contributed to matches)
            coverage_ratio = len(good_matches) / num_keypoints_min

            # Distance quality (lower distance = better match)
            avg_distance = np.mean([m.distance for m in good_matches])
            distance_quality = 1.0 / (1.0 + avg_distance / 40.0)  # Adjusted from 50.0

            # Combine metrics with balanced weighting
            score = (
                match_ratio * 0.5 +          # 50% weight on match coverage
                coverage_ratio * 0.3 +       # 30% weight on bilateral coverage
                distance_quality * 0.20       # 20% weight on match quality
            )

            # Amplify score (tuned from 2.5 to 2.2 for more realistic range)
            final_score = min(score * 2.2, 1.0)

            return final_score

        except Exception as e:
            if self.verbose:
                print(f"  Warning: ORB matching error: {e}")
            return 0.0

    def _compute_akaze_similarity(self, query_path: str, candidate_path: str) -> float:
        """
        NEW: AKAZE geometric similarity (more robust for compressed/distance images).

        AKAZE is more resilient to:
        - JPEG compression artifacts
        - Lower resolution images (200-300px)
        - Distance blur
        - Lighting variations

        Compared to ORB:
        - Slower (~1.5-2x) but more accurate on poor quality images
        - Better feature detection on compressed images
        - More stable under perspective changes
        """
        try:
            img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Same preprocessing as ORB for consistency
            img1 = cv2.bilateralFilter(img1, 5, 50, 50)
            img2 = cv2.bilateralFilter(img2, 5, 50, 50)

            # Upscale if too small
            min_size = 400
            if min(img1.shape) < min_size:
                scale = min_size / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            if min(img2.shape) < min_size:
                scale = min_size / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            # CLAHE enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img1 = clahe.apply(img1)
            img2 = clahe.apply(img2)

            # Detect AKAZE features
            kp1, des1 = self.akaze.detectAndCompute(img1, None)
            kp2, des2 = self.akaze.detectAndCompute(img2, None)

            if des1 is None or des2 is None or len(des1) < 8 or len(des2) < 8:
                return 0.0

            # Match using BFMatcher (AKAZE uses Hamming distance like ORB)
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Lowe's ratio test (stricter for AKAZE: 0.75)
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 3:
                return 0.0

            # Calculate match quality (same as ORB)
            num_keypoints_max = max(len(kp1), len(kp2))
            num_keypoints_min = min(len(kp1), len(kp2))

            match_ratio = len(good_matches) / num_keypoints_max
            coverage_ratio = len(good_matches) / num_keypoints_min

            avg_distance = np.mean([m.distance for m in good_matches])
            distance_quality = 1.0 / (1.0 + avg_distance / 40.0)

            score = (
                match_ratio * 0.5 +
                coverage_ratio * 0.3 +
                distance_quality * 0.20
            )

            # AKAZE tends to have fewer but higher quality matches - amplify slightly more
            final_score = min(score * 2.5, 1.0)

            return final_score

        except Exception as e:
            if self.verbose:
                print(f"  Warning: AKAZE matching error: {e}")
            return 0.0

    def _compute_sift_similarity(self, query_path: str, candidate_path: str) -> float:
        """
        Compute SIFT geometric similarity (most accurate).

        SIFT (Scale-Invariant Feature Transform):
        - Best discriminative power (most accurate)
        - Scale and rotation invariant
        - Robust to lighting changes
        - Floating-point descriptors (128-dim)
        - Slower than ORB but worth it for accuracy

        Patent expired March 2020 - now free to use!
        """
        try:
            img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Light preprocessing (SIFT works better on less-processed images)
            # Upscale if too small
            min_size = 400
            if min(img1.shape) < min_size:
                scale = min_size / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            if min(img2.shape) < min_size:
                scale = min_size / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            # Very light CLAHE (SIFT is sensitive to over-processing)
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
            img1 = clahe.apply(img1)
            img2 = clahe.apply(img2)

            # Detect SIFT features
            kp1, des1 = self.sift.detectAndCompute(img1, None)
            kp2, des2 = self.sift.detectAndCompute(img2, None)

            if des1 is None or des2 is None or len(des1) < 8 or len(des2) < 8:
                return 0.0

            # Match using FLANN (optimized for floating-point descriptors)
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            flann = cv2.FlannBasedMatcher(index_params, search_params)

            matches = flann.knnMatch(des1, des2, k=2)

            # Lowe's ratio test (classic 0.75 threshold for SIFT)
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 4:
                return 0.0

            # Scoring (similar to ORB but adjusted for SIFT characteristics)
            num_keypoints_max = max(len(kp1), len(kp2))
            num_keypoints_min = min(len(kp1), len(kp2))

            match_ratio = len(good_matches) / num_keypoints_max
            coverage_ratio = len(good_matches) / num_keypoints_min

            # SIFT distances are different scale (0-~200+ vs ORB's 0-256)
            avg_distance = np.mean([m.distance for m in good_matches])
            distance_quality = 1.0 / (1.0 + avg_distance / 100.0)

            score = (
                match_ratio * 0.5 +
                coverage_ratio * 0.3 +
                distance_quality * 0.2
            )

            # SIFT typically produces more reliable matches - amplify appropriately
            final_score = min(score * 2.5, 1.0)

            return final_score

        except Exception as e:
            if self.verbose:
                print(f"  Warning: SIFT matching error: {e}")
            return 0.0

    def _compute_geometric_similarity_hybrid(self, query_path: str, candidate_path: str) -> float:
        """
        UPDATED: Triple cascade SIFT → ORB → AKAZE strategy.

        Cascade Strategy:
        1. Try SIFT first (most accurate: ~100-150ms)
        2. If SIFT score > 0.12, use it (excellent match)
        3. If SIFT score ≤ 0.12, try ORB (fast fallback: ~50-100ms)
        4. If ORB score > 0.10, use it (good enough)
        5. If ORB score ≤ 0.10, try AKAZE (last resort for compressed images)
        6. Return best score

        This gives us:
        - SIFT accuracy when it matters (80% of cases)
        - ORB speed when SIFT uncertain (15% of cases)
        - AKAZE robustness on poor quality (5% of cases)
        - Best of all three algorithms with intelligent fallback
        """
        # Try SIFT first (most accurate)
        sift_score = self._compute_sift_similarity(query_path, candidate_path)

        # If SIFT works well, use it (best accuracy)
        if sift_score > 0.12:
            return sift_score

        # If SIFT uncertain, try ORB (faster, still good)
        orb_score = self._compute_orb_similarity(query_path, candidate_path)

        # If ORB works well, use it
        if orb_score > 0.10:
            return orb_score

        # If both failed or very weak, try AKAZE (most robust to compression)
        # This rescues compressed/distance images where SIFT and ORB return low scores
        akaze_score = self._compute_akaze_similarity(query_path, candidate_path)

        # Return best of all three
        return max(sift_score, orb_score, akaze_score)

    def _print_result(self, result: Dict):
        """Pretty print identification result."""
        best = result['best_match']
        scores = result['scores']

        print(f"IDENTIFICATION RESULT")
        print(f"{'='*70}")
        print(f"\nBest Match: {best['name']}")
        print(f"  Product ID: {best['product_id']}")
        print(f"  Card Number: {best['number']}")
        print(f"  Rarity: {best['rarity']}")

        # Display prices
        prices = best.get('prices', {})
        if prices:
            print(f"\nPrices (TCGPlayer):")
            # Check for foil/normal prices
            if 'foil' in prices and prices['foil']:
                foil_prices = prices['foil']
                market = foil_prices.get('market')
                low = foil_prices.get('low')
                mid = foil_prices.get('mid')
                high = foil_prices.get('high')

                if market:
                    print(f"  Market (Foil): ${market:.2f}")
                if low:
                    print(f"  Low (Foil):    ${low:.2f}")
                if mid:
                    print(f"  Mid (Foil):    ${mid:.2f}")

            if 'normal' in prices and prices['normal']:
                normal_prices = prices['normal']
                market = normal_prices.get('market')
                low = normal_prices.get('low')
                mid = normal_prices.get('mid')
                high = normal_prices.get('high')

                if market:
                    print(f"  Market:        ${market:.2f}")
                if low and mid:
                    print(f"  Range:         ${low:.2f} - ${mid:.2f}")
        else:
            print(f"\nPrices: Not available")
        print(f"\nConfidence: {result['confidence']}")
        print(f"  Final Score: {scores['final']:.4f}")
        print(f"  Visual:      {scores['visual']:.4f}")
        print(f"  Geometric:   {scores['geometric']:.4f}")
        if scores.get('card_number_boost', 0) > 0:
            print(f"  Card# Boost: +{scores['card_number_boost']:.4f}")
        if scores.get('foil_boost', 0) > 0:
            print(f"  Foil Boost:  +{scores['foil_boost']:.4f}")

        print(f"\nFeatures:")
        if result['foil_detected']:
            print(f"  Foil: YES ({result['foil_type']}, conf: {result['foil_confidence']:.3f})")
        else:
            print(f"  Foil: NO")

        if result['card_number_extracted']:
            print(f"  Card#: {result['card_number_extracted']} ({result['tcg_detected']})")

        print(f"\nPerformance:")
        timing = result['timing']
        print(f"  Total: {timing['total_ms']}ms")
        print(f"  - Feature extraction: {timing['feature_extraction_ms']}ms")
        print(f"  - Visual search: {timing['visual_search_ms']}ms")
        print(f"  - Geometric verify: {timing['geometric_verify_ms']}ms")
        if timing.get('variant_classify_ms', 0) > 0:
            print(f"  - Variant classify: {timing['variant_classify_ms']}ms")

        print(f"\nTop 3 Matches:")
        for i, match in enumerate(result['matches'][:3], 1):
            print(f"  {i}. {match['name']}")
            print(f"     Score: {match['final_score']:.4f} (V:{match['visual_score']:.3f} G:{match['geometric_score']:.3f})")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Production Card Identification System - Shop Ready',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python production_card_identifier.py card.jpg
  python production_card_identifier.py card.jpg --tcg one-piece
  python production_card_identifier.py card.jpg --tcg pokemon --json output.json
        """
    )
    parser.add_argument('image', help='Path to card image')
    parser.add_argument('--tcg', default='one-piece', help='TCG hint (default: one-piece)')
    parser.add_argument('--top-k', type=int, default=30, help='Number of candidates (default: 30)')
    parser.add_argument('--json', help='Save result to JSON file')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    try:
        # Initialize identifier
        identifier = ProductionCardIdentifier(
            game=args.tcg,
            verbose=not args.quiet
        )

        # Identify card
        result = identifier.identify(
            args.image,
            top_k=args.top_k,
            tcg_hint=args.tcg
        )

        # Save JSON if requested
        if args.json:
            with open(args.json, 'w') as f:
                json.dump(result, f, indent=2)
            if not args.quiet:
                print(f"\n[OK] Result saved to: {args.json}")

        # Exit code based on confidence
        if result['confidence'] == 'HIGH':
            sys.exit(0)
        elif result['confidence'] == 'MODERATE':
            sys.exit(1)
        else:
            sys.exit(2)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
