#!/usr/bin/env python3
"""
Hybrid card identification system combining:
1. DINOv2 visual embeddings (primary retrieval)
2. PaddleOCR text extraction (verification)
3. ORB geometric matching (disambiguation)

This approach provides higher accuracy for art-heavy cards,
screenshots, and challenging real-world conditions.
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
from typing import List, Dict, Optional, Tuple

# Import OCR service
import sys
sys.path.insert(0, str(Path(__file__).parent))
from ocr_service import CardOCRService

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "faiss"
IMAGES_DIR = Path(__file__).parent.parent.parent / "data" / "images"

MODEL_NAME = "facebook/dinov2-small"
GAME = "one-piece"

# Scoring weights
WEIGHT_VISUAL = 0.50    # DINOv2 similarity
WEIGHT_OCR = 0.30       # Text match score
WEIGHT_GEOMETRIC = 0.20 # ORB feature match

# Confidence thresholds
THRESHOLD_AUTO_ACCEPT = 0.85  # Auto-accept if score >= this
THRESHOLD_MARGIN = 0.15       # Auto-accept if (top1 - top2) >= this
OCR_CONF_MIN = 0.70           # Minimum OCR confidence


class HybridCardIdentifier:
    """
    Multi-modal card identifier using visual, text, and geometric features.
    """

    def __init__(self):
        print("Loading hybrid identification system...")
        start = time.time()

        # Load DINOv2 model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        # Load FAISS index
        index_file = FAISS_DIR / f"{GAME}-dinov2" / "index.faiss"
        ids_file = FAISS_DIR / f"{GAME}-dinov2" / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {index_file}\\n"
                "Run: python services/embedder/bin/embed_onepiece_dinov2.py && "
                "python services/indexer/bin/build_faiss_onepiece_dinov2.py"
            )

        self.index = faiss.read_index(str(index_file))

        with open(ids_file, 'r', encoding='utf-8') as f:
            self.card_ids = json.load(f)

        # Load metadata
        metadata_file = ARTIFACTS_DIR / "embeddings" / f"{GAME}-dinov2" / "metadata.jsonl"
        self.metadata = {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    card_id = meta['id']
                    self.metadata[card_id] = meta

        # Initialize OCR service
        self.ocr_service = CardOCRService(lang='en')

        # Initialize ORB detector for geometric verification
        self.orb = cv2.ORB_create(nfeatures=500)

        elapsed = time.time() - start
        print(f"[OK] Loaded {self.index.ntotal} cards in {elapsed:.2f}s\\n")

    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Generate DINOv2 embedding for an image."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def compute_orb_similarity(
        self,
        query_image_path: str,
        candidate_image_path: str
    ) -> float:
        """
        Compute ORB-based geometric similarity between two images.

        Returns:
            Similarity score [0.0, 1.0] based on feature matching
        """
        try:
            # Load images
            img1 = cv2.imread(query_image_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_image_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Detect ORB keypoints and descriptors
            kp1, des1 = self.orb.detectAndCompute(img1, None)
            kp2, des2 = self.orb.detectAndCompute(img2, None)

            if des1 is None or des2 is None:
                return 0.0

            # Match descriptors using BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)

            # Sort matches by distance
            matches = sorted(matches, key=lambda x: x.distance)

            # Calculate match ratio
            if len(kp1) == 0 or len(kp2) == 0:
                return 0.0

            # Use top 50 matches
            good_matches = matches[:50]
            match_score = len(good_matches) / min(len(kp1), len(kp2))

            # Normalize to [0, 1]
            return min(match_score, 1.0)

        except Exception as e:
            print(f"ORB matching error: {e}")
            return 0.0

    def identify(
        self,
        image_path: str,
        top_k: int = 20,
        use_ocr: bool = True,
        use_geometric: bool = True
    ) -> Dict:
        """
        Identify a card using hybrid multi-modal approach.

        Args:
            image_path: Path to query image
            top_k: Number of initial candidates from visual search
            use_ocr: Enable OCR verification
            use_geometric: Enable geometric verification

        Returns:
            {
                'matches': [...],
                'best_match': {...},
                'scores': {...},
                'time_ms': int,
                'confidence': str,
            }
        """
        start = time.time()
        results = {
            'image_path': image_path,
            'matches': [],
            'best_match': None,
            'scores': {},
            'time_ms': 0,
            'confidence': 'UNKNOWN',
        }

        # Stage 1: DINOv2 visual retrieval
        print(f"[Stage 1] Visual retrieval (DINOv2)...")
        embedding = self.get_image_embedding(image_path)
        embedding_2d = np.array([embedding])

        distances, indices = self.index.search(embedding_2d, top_k)

        # Build initial candidates
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
                'imageUrl': meta.get('imageUrl'),
                'visual_score': float(dist),
                'ocr_score': 0.0,
                'geometric_score': 0.0,
                'final_score': 0.0,
            })

        print(f"  Found {len(candidates)} visual candidates")

        # Stage 2: OCR verification
        ocr_info = {}
        if use_ocr and self.ocr_service.enabled:
            print(f"[Stage 2] OCR text extraction...")
            ocr_info = self.ocr_service.extract_card_info(image_path)
            print(f"  Extracted: name='{ocr_info.get('name', '')}', "
                  f"number='{ocr_info.get('card_number', '')}'")

            # Score candidates based on OCR match
            for candidate in candidates:
                ocr_score = 0.0

                # Name match (if confidence sufficient)
                if ocr_info.get('name_confidence', 0) >= OCR_CONF_MIN:
                    name_sim = self.ocr_service.fuzzy_match_name(
                        ocr_info['name'],
                        candidate['name']
                    )
                    ocr_score += name_sim * 0.7  # 70% weight to name

                # Card number exact match (if available)
                # Extract number from database name (e.g., "Luffy - OP01-001")
                card_name = candidate['name']
                if ' - ' in card_name and ocr_info.get('card_number'):
                    db_number = card_name.split(' - ')[-1].strip()
                    if self.ocr_service.exact_match_number(
                        ocr_info['card_number'],
                        db_number
                    ):
                        ocr_score += 0.3  # 30% weight to exact number

                candidate['ocr_score'] = ocr_score

        # Stage 3: Geometric verification (top 10 candidates only)
        if use_geometric:
            print(f"[Stage 3] Geometric verification (ORB)...")
            top_candidates = candidates[:10]

            for candidate in top_candidates:
                card_id = candidate['card_id']

                # Find candidate image
                candidate_image = None
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    candidate_path = IMAGES_DIR / GAME / f"{card_id}{ext}"
                    if candidate_path.exists():
                        candidate_image = str(candidate_path)
                        break

                if candidate_image:
                    geom_score = self.compute_orb_similarity(
                        image_path,
                        candidate_image
                    )
                    candidate['geometric_score'] = geom_score

        # Stage 4: Score fusion
        print(f"[Stage 4] Score fusion...")
        for candidate in candidates:
            visual = candidate['visual_score']
            ocr = candidate['ocr_score']
            geom = candidate['geometric_score']

            # Weighted fusion
            final_score = (
                WEIGHT_VISUAL * visual +
                WEIGHT_OCR * ocr +
                WEIGHT_GEOMETRIC * geom
            )
            candidate['final_score'] = final_score

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

        elapsed = time.time() - start

        results['matches'] = candidates
        results['best_match'] = best
        results['scores'] = {
            'visual': best['visual_score'],
            'ocr': best['ocr_score'],
            'geometric': best['geometric_score'],
            'final': best['final_score'],
        }
        results['time_ms'] = int(elapsed * 1000)
        results['confidence'] = confidence
        results['ocr_info'] = ocr_info

        return results


def print_results(result: Dict):
    """Pretty print identification results."""
    print("=" * 80)
    print("HYBRID CARD IDENTIFICATION")
    print(f"Image: {result['image_path']}")
    print(f"Time: {result['time_ms']}ms")
    print("=" * 80)

    best = result['best_match']
    scores = result['scores']

    print(f"\\nBEST MATCH:")
    print(f"  {best['name']}")
    print(f"  Card ID: {best['card_id']}")
    print(f"  Product ID: {best['product_id']}")
    print(f"  Set: {best['set']}")
    print(f"  Rarity: {best['rarity']}")

    print(f"\\nSCORES:")
    print(f"  Visual (DINOv2):  {scores['visual']:.4f} (weight: {WEIGHT_VISUAL})")
    print(f"  OCR (PaddleOCR):  {scores['ocr']:.4f} (weight: {WEIGHT_OCR})")
    print(f"  Geometric (ORB):  {scores['geometric']:.4f} (weight: {WEIGHT_GEOMETRIC})")
    print(f"  Final Score:      {scores['final']:.4f}")

    print(f"\\nCONFIDENCE: {result['confidence']}")

    if result.get('ocr_info'):
        ocr = result['ocr_info']
        print(f"\\nOCR EXTRACTED:")
        print(f"  Name: '{ocr.get('name', '')}' (conf: {ocr.get('name_confidence', 0):.2f})")
        print(f"  Number: '{ocr.get('card_number', '')}' (conf: {ocr.get('number_confidence', 0):.2f})")

    # Show top 5 matches
    print(f"\\n{'=' * 80}")
    print("TOP 5 MATCHES:")
    print("-" * 80)
    for match in result['matches'][:5]:
        print(f"\\n#{match['rank']} - {match['name']}")
        print(f"  Final: {match['final_score']:.4f} "
              f"(V: {match['visual_score']:.3f}, "
              f"O: {match['ocr_score']:.3f}, "
              f"G: {match['geometric_score']:.3f})")

    print(f"\\n{'=' * 80}")


def main():
    if len(sys.argv) < 2:
        print("=" * 80)
        print("HYBRID CARD IDENTIFICATION")
        print("=" * 80)
        print("\\nUsage:")
        print("  python scripts/identification/identify_card_hybrid.py <image_path> [top_k]")
        print("\\nExamples:")
        print("  python scripts/identification/identify_card_hybrid.py test-images/one-piece/luffy.jpg")
        print("  python scripts/identification/identify_card_hybrid.py my_card.jpg 30")
        print("=" * 80)
        sys.exit(1)

    image_path = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        sys.exit(1)

    # Initialize identifier
    identifier = HybridCardIdentifier()

    # Identify card
    result = identifier.identify(image_path, top_k=top_k)

    # Print results
    print_results(result)


if __name__ == "__main__":
    main()
