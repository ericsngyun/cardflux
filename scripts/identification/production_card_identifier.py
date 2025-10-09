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
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("  pip install numpy opencv-python pillow torch transformers faiss-cpu easyocr")
    sys.exit(1)

# Configuration
ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "faiss"
IMAGES_DIR = Path(__file__).parent.parent.parent / "data" / "images"

MODEL_NAME = "facebook/dinov2-small"
DEFAULT_GAME = "one-piece"

# Scoring weights
WEIGHT_VISUAL = 0.75
WEIGHT_GEOMETRIC = 0.25

# Thresholds
THRESHOLD_AUTO_ACCEPT = 0.60
THRESHOLD_MARGIN = 0.12


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

    def __init__(self, game: str = DEFAULT_GAME, verbose: bool = True):
        """
        Initialize production identifier.

        Args:
            game: Game to identify (default: one-piece)
            verbose: Print status messages
        """
        self.game = game
        self.verbose = verbose

        if self.verbose:
            print("="*70)
            print("PRODUCTION CARD IDENTIFICATION SYSTEM")
            print("="*70)
            print(f"Initializing for game: {game}")

        # Load DINOv2 model
        if self.verbose:
            print("\n[1/5] Loading DINOv2 vision model...")
        start = time.time()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        if self.verbose:
            print(f"  [OK] Model loaded on {self.device} ({time.time()-start:.1f}s)")

        # Load FAISS index
        if self.verbose:
            print(f"\n[2/5] Loading FAISS index for {game}...")
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
            print(f"\n[3/5] Loading card metadata...")
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

        # Initialize ORB detector
        if self.verbose:
            print(f"\n[4/5] Initializing geometric matcher (ORB)...")
        self.orb = cv2.ORB_create(nfeatures=500)
        if self.verbose:
            print(f"  [OK] ORB initialized")

        # Initialize universal extractors
        if self.verbose:
            print(f"\n[5/5] Initializing universal extractors...")
        start = time.time()

        self.card_extractor = UniversalCardExtractor(ocr_backend='easy')
        self.foil_detector = FoilDetector()

        if self.verbose:
            print(f"  [OK] Extractors ready ({time.time()-start:.1f}s)")
            print("\n" + "="*70)
            print("SYSTEM READY")
            print("="*70 + "\n")

    def identify(
        self,
        image_path: str,
        top_k: int = 30,
        use_geometric: bool = True,
        tcg_hint: Optional[str] = None
    ) -> Dict:
        """
        Identify card with full analysis.

        Args:
            image_path: Path to card image
            top_k: Number of visual candidates (default: 30, increased for variants)
            use_geometric: Enable geometric verification (default: True)
            tcg_hint: TCG hint for card number extraction

        Returns:
            Complete identification result
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
        }

        # Stage 0: Foil detection and card number extraction (parallel)
        if self.verbose:
            print(f"Analyzing: {Path(image_path).name}")
            print("-" * 70)
            print("[Stage 0] Feature extraction...")

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

        # Stage 3: Geometric verification (top 15, increased from 10)
        if use_geometric:
            if self.verbose:
                print(f"\n[Stage 3] Geometric verification (ORB, top 15)...")
            stage3_start = time.time()

            top_candidates = candidates[:15]
            verified = 0

            for candidate in top_candidates:
                card_id = candidate['card_id']

                # Find candidate image
                candidate_image = None
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    candidate_path = IMAGES_DIR / self.game / f"{card_id}{ext}"
                    if candidate_path.exists():
                        candidate_image = str(candidate_path)
                        break

                if candidate_image:
                    geom_score = self._compute_orb_similarity(image_path, candidate_image)
                    candidate['geometric_score'] = geom_score
                    if geom_score > 0.1:
                        verified += 1

            stage3_time = time.time() - stage3_start
            if self.verbose:
                print(f"  [OK] Verified {verified}/15 candidates ({stage3_time*1000:.0f}ms)")

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

        # Stage 5: Score fusion
        if self.verbose:
            print(f"\n[Stage 5] Score fusion...")

        for candidate in candidates:
            visual = candidate['visual_score']
            geom = candidate['geometric_score']
            card_num_boost = candidate['card_number_match'] * 0.15  # 15% boost
            foil_boost = candidate['foil_match'] * 0.05  # 5% boost

            # Base score
            final_score = (
                WEIGHT_VISUAL * visual +
                WEIGHT_GEOMETRIC * geom
            )

            # Apply boosts
            final_score += card_num_boost + foil_boost

            candidate['final_score'] = min(final_score, 1.0)  # Cap at 1.0

        # Sort by final score
        candidates.sort(key=lambda x: x['final_score'], reverse=True)

        # Re-rank
        for idx, candidate in enumerate(candidates):
            candidate['rank'] = idx + 1

        # Determine confidence
        best = candidates[0]
        confidence = "LOW"

        if best['final_score'] >= THRESHOLD_AUTO_ACCEPT:
            confidence = "HIGH"
        elif len(candidates) > 1:
            margin = best['final_score'] - candidates[1]['final_score']
            if margin >= THRESHOLD_MARGIN:
                confidence = "MODERATE"

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
            'total_ms': int(total_time * 1000),
        }

        if self.verbose:
            print(f"\n{'='*70}")
            self._print_result(result)

        return result

    def _get_image_embedding(self, image_path: str) -> np.ndarray:
        """Generate DINOv2 embedding (no preprocessing for consistency)."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def _compute_orb_similarity(self, query_path: str, candidate_path: str) -> float:
        """Compute ORB geometric similarity."""
        try:
            img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Upscale if too small
            if min(img1.shape) < 300:
                scale = 300 / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            if min(img2.shape) < 300:
                scale = 300 / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            # CLAHE enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img1 = clahe.apply(img1)
            img2 = clahe.apply(img2)

            # Detect features
            kp1, des1 = self.orb.detectAndCompute(img1, None)
            kp2, des2 = self.orb.detectAndCompute(img2, None)

            if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
                return 0.0

            # Match
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 4:
                return 0.0

            # Score
            match_ratio = len(good_matches) / max(len(kp1), len(kp2))
            avg_distance = np.mean([m.distance for m in good_matches])
            quality_factor = 1.0 / (1.0 + avg_distance / 50.0)

            score = match_ratio * quality_factor
            return min(score * 2.5, 1.0)

        except Exception as e:
            if self.verbose:
                print(f"  Warning: ORB matching error: {e}")
            return 0.0

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
        print(f"\nConfidence: {result['confidence']}")
        print(f"  Final Score: {scores['final']:.4f}")
        print(f"  Visual:      {scores['visual']:.4f} (weight: {WEIGHT_VISUAL})")
        print(f"  Geometric:   {scores['geometric']:.4f} (weight: {WEIGHT_GEOMETRIC})")
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
