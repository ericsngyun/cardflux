#!/usr/bin/env python3
"""
Optimized visual-only card identification system.

Focus: Speed + Accuracy + Confidence
- DINOv2 visual embeddings (primary signal - 85%)
- ORB geometric verification (secondary - 15%)
- OCR removed (too slow, unreliable for cards)

Target: <200ms identification, HIGH confidence for valid matches
"""
import sys
import json
import time
import numpy as np
import faiss
import torch
import cv2
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from typing import Dict, List, Optional

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "faiss"
IMAGES_DIR = Path(__file__).parent.parent.parent / "data" / "images"

MODEL_NAME = "facebook/dinov2-small"
GAME = "one-piece"

# Optimized scoring weights - Balanced for watermark robustness
WEIGHT_VISUAL = 0.70    # DINOv2 similarity (strong signal but affected by watermarks)
WEIGHT_GEOMETRIC = 0.30 # ORB verification (watermark-resistant, crucial for real photos)

# Confidence thresholds - Strict for accuracy
CONFIDENCE_HIGH_VISUAL = 0.80      # Visual score alone for HIGH (very strong match)
CONFIDENCE_MODERATE_VISUAL = 0.70  # Visual score alone for MODERATE
CONFIDENCE_HIGH_MARGIN = 0.10      # Margin between top 2 for HIGH (clear winner)
CONFIDENCE_MODERATE_MARGIN = 0.05  # Margin between top 2 for MODERATE


class OptimizedCardIdentifier:
    """
    Fast, visual-first card identifier optimized for real-world photos.
    """

    def __init__(self, enable_geometric: bool = True):
        """Initialize with lazy loading and minimal overhead."""
        print("Loading optimized identification system...")
        start = time.time()

        # Device setup
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # Load DINOv2 model with optimizations
        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        # Enable inference mode optimizations
        if self.device == "cuda":
            torch.backends.cudnn.benchmark = True

        # Load FAISS index
        index_file = FAISS_DIR / f"{GAME}-dinov2" / "index.faiss"
        ids_file = FAISS_DIR / f"{GAME}-dinov2" / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_file}")

        self.index = faiss.read_index(str(index_file))

        with open(ids_file, 'r', encoding='utf-8') as f:
            self.card_ids = json.load(f)

        # Load metadata (optimized: only essential fields)
        metadata_file = ARTIFACTS_DIR / "embeddings" / f"{GAME}-dinov2" / "metadata.jsonl"
        self.metadata = {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    card_id = meta['id']
                    # Store only essential fields to reduce memory
                    self.metadata[card_id] = {
                        'name': meta.get('name', 'Unknown'),
                        'productId': meta.get('productId'),
                        'set': meta.get('set'),
                        'rarity': meta.get('rarity'),
                    }

        # ORB detector (lazy init)
        self.enable_geometric = enable_geometric
        self.orb = None
        if enable_geometric:
            self.orb = cv2.ORB_create(nfeatures=500)  # More features for better watermark matching

        elapsed = time.time() - start
        print(f"[OK] Loaded {self.index.ntotal} cards in {elapsed:.2f}s\n")

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image with bilateral filter + contrast enhancement.
        MUST match embedder preprocessing EXACTLY!
        """
        img_array = np.array(image)
        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        return Image.fromarray(enhanced)

    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """
        Generate DINOv2 embedding - EXACT same preprocessing as embedder.

        For images <400px, upscaling + bilateral + contrast is applied.
        For images >=400px, just bilateral + contrast.
        """
        image = Image.open(image_path).convert("RGB")

        original_size = image.size
        min_dim = min(original_size)

        # Apply preprocessing (small images)
        if min_dim < 400:
            # Preprocess FIRST
            image = self._preprocess_image(image)

            # THEN upscale
            scale_factor = 400 / min_dim
            new_size = (
                int(original_size[0] * scale_factor),
                int(original_size[1] * scale_factor)
            )
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            # Just preprocess (no upscaling)
            image = self._preprocess_image(image)

        # DINOv2 preprocessing (built-in)
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        # Normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def compute_orb_similarity_fast(
        self,
        query_image_path: str,
        candidate_image_path: str
    ) -> float:
        """
        Fast ORB geometric matching - simplified, no preprocessing.

        Only used for top candidate verification, not scoring.
        """
        try:
            img1 = cv2.imread(query_image_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_image_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Minimal upscaling for tiny images only
            if min(img1.shape) < 200:
                scale = 200 / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_LINEAR)  # Faster than LANCZOS

            if min(img2.shape) < 200:
                scale = 200 / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_LINEAR)

            # Detect features (no CLAHE - saves time)
            kp1, des1 = self.orb.detectAndCompute(img1, None)
            kp2, des2 = self.orb.detectAndCompute(img2, None)

            if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
                return 0.0

            # Match with BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            # Ratio test
            good = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good.append(m)

            if len(good) < 4:
                return 0.0

            # Simple match ratio
            ratio = len(good) / max(len(kp1), len(kp2))
            return min(ratio * 3.0, 1.0)  # Scale to [0, 1]

        except Exception:
            return 0.0

    def calculate_confidence(
        self,
        visual_score: float,
        margin: float,
        geometric_score: float = 0.0
    ) -> str:
        """
        Smart confidence calculation based on visual evidence.

        Priority:
        1. Strong visual match (>70%) = HIGH
        2. Good margin (>8%) = HIGH
        3. Decent visual (>60%) + margin (>5%) = MODERATE
        4. Otherwise = LOW
        """
        # Case 1: Strong visual similarity alone
        if visual_score >= CONFIDENCE_HIGH_VISUAL:
            return "HIGH"

        # Case 2: Significant margin between top 2
        if margin >= CONFIDENCE_HIGH_MARGIN:
            if visual_score >= 0.65:  # Must be reasonable match
                return "HIGH"

        # Case 3: Geometric verification boosts confidence
        if self.enable_geometric and geometric_score >= 0.5:
            if visual_score >= 0.60:
                return "HIGH"

        # Case 4: Moderate scenarios
        if visual_score >= CONFIDENCE_MODERATE_VISUAL and margin >= CONFIDENCE_MODERATE_MARGIN:
            return "MODERATE"

        # Default
        return "LOW"

    def identify(
        self,
        image_path: str,
        top_k: int = 20,  # Need more candidates for geometric re-ranking
        verify_geometric: bool = True
    ) -> Dict:
        """
        Identify card with optimized visual-first pipeline.

        Target: <200ms for most queries
        """
        start = time.time()

        # Stage 1: Visual retrieval (dominant signal)
        t1 = time.time()
        embedding = self.get_image_embedding(image_path)
        embedding_2d = np.array([embedding])
        distances, indices = self.index.search(embedding_2d, top_k)
        stage1_time = (time.time() - t1) * 1000

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
                'set': meta.get('set'),
                'rarity': meta.get('rarity'),
                'visual_score': float(dist),
                'geometric_score': 0.0,
                'final_score': float(dist),
            })

        # Stage 2: Geometric verification (smart selection for performance)
        stage2_time = 0
        if verify_geometric and self.enable_geometric and len(candidates) > 0:
            t2 = time.time()

            # PERFORMANCE OPTIMIZATION: Only verify promising candidates
            # Strategy: Verify top candidates where visual scores are close (competitive)
            # This handles watermark cases where correct card ranks lower visually
            top_score = candidates[0]['visual_score']

            # Always verify top 5 (fast baseline)
            # Then add candidates within 5% of top until we hit 10 total
            candidates_to_verify = candidates[:min(5, len(candidates))]

            # Add more if they're competitive (within 5%)
            threshold = top_score * 0.95
            for candidate in candidates[5:]:
                if candidate['visual_score'] >= threshold and len(candidates_to_verify) < 10:
                    candidates_to_verify.append(candidate)
                elif len(candidates_to_verify) >= 10:
                    break

            # Verify selected candidates
            for candidate in candidates_to_verify:
                card_id = candidate['card_id']

                candidate_image = None
                for ext in ['.jpg', '.jpeg', '.png']:
                    candidate_path = IMAGES_DIR / GAME / f"{card_id}{ext}"
                    if candidate_path.exists():
                        candidate_image = str(candidate_path)
                        break

                if candidate_image:
                    geom_score = self.compute_orb_similarity_fast(
                        image_path,
                        candidate_image
                    )
                    candidate['geometric_score'] = geom_score

                    # Update final score
                    candidate['final_score'] = (
                        WEIGHT_VISUAL * candidate['visual_score'] +
                        WEIGHT_GEOMETRIC * geom_score
                    )

            stage2_time = (time.time() - t2) * 1000

        # Re-sort if geometric was applied
        if verify_geometric:
            candidates.sort(key=lambda x: x['final_score'], reverse=True)
            for idx, c in enumerate(candidates):
                c['rank'] = idx + 1

        # Calculate confidence
        best = candidates[0]
        margin = best['final_score'] - candidates[1]['final_score'] if len(candidates) > 1 else 0.0

        confidence = self.calculate_confidence(
            visual_score=best['visual_score'],
            margin=margin,
            geometric_score=best['geometric_score']
        )

        elapsed = time.time() - start

        return {
            'image_path': image_path,
            'matches': candidates,
            'best_match': best,
            'scores': {
                'visual': best['visual_score'],
                'geometric': best['geometric_score'],
                'final': best['final_score'],
                'margin': margin,
            },
            'confidence': confidence,
            'time_ms': int(elapsed * 1000),
            'timing': {
                'visual_ms': stage1_time,
                'geometric_ms': stage2_time,
                'total_ms': int(elapsed * 1000),
            }
        }


def print_results(result: Dict):
    """Pretty print identification results."""
    print("=" * 80)
    print("OPTIMIZED CARD IDENTIFICATION")
    print(f"Image: {result['image_path']}")
    print(f"Time: {result['time_ms']}ms")
    print("=" * 80)

    best = result['best_match']
    scores = result['scores']

    print(f"\nBEST MATCH:")
    print(f"  {best['name']}")
    print(f"  Card ID: {best['card_id']}")
    print(f"  Product ID: {best['product_id']}")
    print(f"  Set: {best['set']}")
    print(f"  Rarity: {best['rarity']}")

    print(f"\nSCORES:")
    print(f"  Visual (DINOv2):  {scores['visual']:.4f} (weight: {WEIGHT_VISUAL})")
    print(f"  Geometric (ORB):  {scores['geometric']:.4f} (weight: {WEIGHT_GEOMETRIC})")
    print(f"  Final Score:      {scores['final']:.4f}")
    print(f"  Margin (top1-top2): {scores['margin']:.4f}")

    # Confidence
    print(f"\nCONFIDENCE: {result['confidence']}")

    # Timing breakdown
    timing = result.get('timing', {})
    print(f"\nTIMING BREAKDOWN:")
    print(f"  Visual search:  {timing.get('visual_ms', 0):.1f}ms")
    print(f"  Geometric:      {timing.get('geometric_ms', 0):.1f}ms")
    print(f"  Total:          {timing.get('total_ms', 0)}ms")

    # Show top 5 matches
    print(f"\n{'=' * 80}")
    print("TOP 5 MATCHES:")
    print("-" * 80)
    for match in result['matches'][:5]:
        print(f"\n#{match['rank']} - {match['name']}")
        print(f"  Final: {match['final_score']:.4f} "
              f"(V: {match['visual_score']:.3f}, "
              f"G: {match['geometric_score']:.3f})")

    print(f"\n{'=' * 80}")


def main():
    if len(sys.argv) < 2:
        print("=" * 80)
        print("OPTIMIZED CARD IDENTIFICATION")
        print("=" * 80)
        print("\nUsage:")
        print("  python scripts/identification/identify_card_optimized.py <image_path>")
        print("\nExamples:")
        print("  python scripts/identification/identify_card_optimized.py test-images/one-piece/blackbeard.png")
        print("=" * 80)
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        sys.exit(1)

    # Initialize identifier (once per session)
    identifier = OptimizedCardIdentifier(enable_geometric=True)

    # Identify card (fast!)
    result = identifier.identify(image_path, verify_geometric=True)

    # Print results
    print_results(result)


if __name__ == "__main__":
    main()
