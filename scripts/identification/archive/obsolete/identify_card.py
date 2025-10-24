#!/usr/bin/env python3
"""
Optimized card identification with reprint detection.
Target: sub-2 second identification.
"""
import sys
import json
import time
import numpy as np
import faiss
import torch
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent / "artifacts" / "faiss"

MODEL_NAME = "openai/clip-vit-base-patch32"
GAME = "one-piece"

class FastCardIdentifier:
    """Optimized card identifier with < 2s per image goal"""

    def __init__(self):
        start = time.time()

        # Load model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()  # Set to evaluation mode
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        # Load FAISS index
        index_file = FAISS_DIR / GAME / "index.faiss"
        ids_file = FAISS_DIR / GAME / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(f"Index not found: {index_file}")

        self.index = faiss.read_index(str(index_file))

        with open(ids_file, 'r', encoding='utf-8') as f:
            self.card_ids = json.load(f)

        # Load metadata
        metadata_file = ARTIFACTS_DIR / "embeddings" / GAME / "metadata.jsonl"
        self.metadata = {}

        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    self.metadata[meta['id']] = meta

        # Load reprint map
        reprint_file = ARTIFACTS_DIR / "embeddings" / GAME / "reprints.json"
        self.reprints = {}

        if reprint_file.exists():
            with open(reprint_file, 'r', encoding='utf-8') as f:
                self.reprints = json.load(f)

        elapsed = time.time() - start
        print(f"[OK] Loaded {self.index.ntotal} cards in {elapsed:.2f}s")
        print(f"[OK] Device: {self.device}")
        print(f"[OK] Reprint map: {len(self.reprints)} cards with variants\n")

    def identify(self, image_path, top_k=5, show_reprints=True):
        """
        Identify a card from an image.

        Args:
            image_path: Path to image file
            top_k: Number of top matches to return
            show_reprints: If True, include reprints in results

        Returns:
            dict with 'matches' and 'reprints' (if applicable)
        """
        start = time.time()

        # Generate embedding
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            embedding = image_features.cpu().numpy()[0]

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)

        # Search FAISS
        embedding_2d = np.array([embedding])
        distances, indices = self.index.search(embedding_2d, top_k)

        # Build results
        matches = []
        for idx, (dist, index) in enumerate(zip(distances[0], indices[0])):
            card_id = self.card_ids[int(index)]
            meta = self.metadata.get(card_id, {})

            matches.append({
                "rank": idx + 1,
                "similarity": float(dist),
                "confidence": self._get_confidence_level(dist),
                "card_id": card_id,
                "name": meta.get("name", "Unknown"),
                "set": meta.get("set"),
                "rarity": meta.get("rarity"),
                "type": meta.get("type"),
                "imageUrl": meta.get("imageUrl"),
            })

        # Get reprints for best match
        reprints = []
        if show_reprints and matches:
            best_card_id = matches[0]["card_id"]
            if best_card_id in self.reprints:
                reprint_data = self.reprints[best_card_id]
                reprints = reprint_data.get("variants", [])

        elapsed = time.time() - start

        return {
            "matches": matches,
            "reprints": reprints,
            "time_ms": int(elapsed * 1000),
            "success": elapsed < 2.0,  # Target: sub-2s
        }

    def _get_confidence_level(self, similarity):
        """Map similarity to confidence level"""
        if similarity >= 0.95:
            return "HIGH"
        elif similarity >= 0.85:
            return "MODERATE"
        elif similarity >= 0.70:
            return "LOW"
        else:
            return "VERY_LOW"

def print_results(result):
    """Pretty print identification results"""
    print("=" * 80)
    print(f"IDENTIFICATION RESULTS ({result['time_ms']}ms)")
    print("=" * 80)

    matches = result["matches"]
    reprints = result.get("reprints", [])

    # Show top matches
    for match in matches:
        print(f"\n#{match['rank']} - {match['name']}")
        print(f"  Similarity: {match['similarity']:.4f} ({match['similarity']*100:.1f}%)")
        print(f"  Confidence: {match['confidence']}")
        print(f"  Set: {match['set']}")
        print(f"  Rarity: {match['rarity']}")

    # Show reprints if available
    if reprints:
        print(f"\n{'=' * 80}")
        print(f"OTHER VERSIONS/REPRINTS ({len(reprints)} found)")
        print("=" * 80)
        for variant in reprints[:10]:  # Show top 10 reprints
            print(f"  • {variant['name']}")
            print(f"    Set: {variant['set']} | Rarity: {variant['rarity']}")

    print(f"\n{'=' * 80}")

    # Overall assessment
    best = matches[0]
    if best['confidence'] == 'HIGH':
        print(f"[HIGH CONFIDENCE]: {best['name']}")
    elif best['confidence'] == 'MODERATE':
        print(f"[MODERATE CONFIDENCE]: {best['name']}")
    else:
        print(f"[LOW CONFIDENCE] - May not be a match")

    # Performance check
    if result['success']:
        print(f"[PASS] Identified in {result['time_ms']}ms (target: <2000ms)")
    else:
        print(f"[WARN] Took {result['time_ms']}ms (target: <2000ms)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python identify_card.py <image_path> [top_k]")
        print("\nExample:")
        print("  python identify_card.py test_card.jpg")
        print("  python identify_card.py test_card.jpg 10")
        sys.exit(1)

    image_path = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        sys.exit(1)

    # Initialize identifier (one-time cost)
    identifier = FastCardIdentifier()

    # Identify card
    result = identifier.identify(image_path, top_k=top_k)

    # Print results
    print_results(result)

if __name__ == "__main__":
    main()
