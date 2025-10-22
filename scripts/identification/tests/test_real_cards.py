#!/usr/bin/env python3
"""
Test card identification with real card photos.

This script identifies cards from user-provided photos and shows:
1. Top matches with similarity scores
2. Only alternate arts/printings with the SAME base name (not just similar cards)

Usage:
    python scripts/identification/test_real_cards.py <image_path>
    python scripts/identification/test_real_cards.py test-images/one-piece/luffy.jpg
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
from typing import List, Dict, Optional

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "faiss"

MODEL_NAME = "openai/clip-vit-base-patch32"
GAME = "one-piece"

class RealCardTester:
    """
    Test card identification with real photos.
    Shows alternate arts/printings based on normalized card name matching.
    """

    def __init__(self):
        print("Loading identification system...")
        start = time.time()

        # Load CLIP model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        # Load FAISS index
        index_file = FAISS_DIR / GAME / "index.faiss"
        ids_file = FAISS_DIR / GAME / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {index_file}\n"
                "Run: python services/indexer/bin/build_faiss_onepiece.py"
            )

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
                    card_id = meta['id']
                    self.metadata[card_id] = meta

        elapsed = time.time() - start
        print(f"[OK] Loaded {self.index.ntotal} cards in {elapsed:.2f}s")
        print(f"[OK] Device: {self.device}\n")

    def normalize_card_name(self, name: str) -> str:
        """
        Normalize card name to group alternate arts/printings.

        Removes:
        - Variant indicators: (Parallel), (Alternate Art), etc.
        - Card numbers: - OP01-001
        - Deck indicators: (Zoro Deck)
        - Promo indicators: (Championship, Winner, etc.)

        Examples:
            "Monkey.D.Luffy - OP01-001 (Alternate Art)" -> "Monkey.D.Luffy"
            "Roronoa Zoro (Parallel)" -> "Roronoa Zoro"
            "Nami (Championship 2024 Winner)" -> "Nami"
        """
        normalized = name

        # Remove variant suffixes
        variant_patterns = [
            " (Parallel)",
            " (Alternate Art)",
            " (Championship",
            " (Winner)",
            " (Finalist)",
            " (Promo)",
            " (Super Pre-Release)",
            " (Pre-Release)",
            " (Deck)",
        ]

        for pattern in variant_patterns:
            if pattern in normalized:
                normalized = normalized.split(pattern)[0]

        # Remove card numbers like "- OP01-001", "- PRB02-005"
        if " - " in normalized:
            parts = normalized.split(" - ")
            # Check if the last part looks like a card number
            if len(parts) > 1:
                last_part = parts[-1]
                # If it has letters and numbers, likely a card number
                if any(c.isdigit() for c in last_part) and any(c.isalpha() for c in last_part):
                    normalized = " - ".join(parts[:-1])

        return normalized.strip()

    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Generate CLIP embedding for an image."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            embedding = image_features.cpu().numpy()[0]

        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def find_alternate_arts(self, card_id: str, card_name: str) -> List[Dict]:
        """
        Find alternate arts/printings with the same base name.

        Args:
            card_id: The identified card's ID
            card_name: The identified card's name

        Returns:
            List of alternate versions (different IDs, same base name)
        """
        base_name = self.normalize_card_name(card_name)
        alternates = []

        for meta_id, meta in self.metadata.items():
            # Skip the same card
            if meta_id == card_id:
                continue

            # Check if normalized names match
            meta_name = meta.get('name', '')
            meta_base_name = self.normalize_card_name(meta_name)

            if meta_base_name == base_name:
                alternates.append({
                    'id': meta_id,
                    'productId': meta.get('productId'),
                    'name': meta_name,
                    'set': meta.get('set'),
                    'rarity': meta.get('rarity'),
                    'imageUrl': meta.get('imageUrl'),
                })

        return alternates

    def identify(self, image_path: str, top_k: int = 5) -> Dict:
        """
        Identify a card from a photo.

        Returns:
            {
                'matches': [...],      # Top K matches
                'alternates': [...],   # Alternate arts of best match
                'time_ms': int,
                'image_path': str
            }
        """
        start = time.time()

        # Generate embedding
        embedding = self.get_image_embedding(image_path)

        # Search FAISS
        embedding_2d = np.array([embedding])
        distances, indices = self.index.search(embedding_2d, top_k)

        # Build matches
        matches = []
        for idx, (dist, index) in enumerate(zip(distances[0], indices[0])):
            card_id = self.card_ids[int(index)]
            meta = self.metadata.get(card_id, {})

            matches.append({
                'rank': idx + 1,
                'similarity': float(dist),
                'confidence': self._get_confidence_level(dist),
                'card_id': card_id,
                'product_id': meta.get('productId'),
                'name': meta.get('name', 'Unknown'),
                'set': meta.get('set'),
                'rarity': meta.get('rarity'),
                'type': meta.get('type'),
                'imageUrl': meta.get('imageUrl'),
            })

        # Find alternate arts for best match
        best_match = matches[0]
        alternates = self.find_alternate_arts(
            best_match['card_id'],
            best_match['name']
        )

        elapsed = time.time() - start

        return {
            'matches': matches,
            'alternates': alternates,
            'time_ms': int(elapsed * 1000),
            'image_path': image_path,
            'success': elapsed < 2.0,
        }

    def _get_confidence_level(self, similarity: float) -> str:
        """Map similarity to confidence level"""
        if similarity >= 0.95:
            return "HIGH"
        elif similarity >= 0.85:
            return "MODERATE"
        elif similarity >= 0.70:
            return "LOW"
        else:
            return "VERY_LOW"


def print_results(result: Dict):
    """Pretty print identification results"""
    print("=" * 80)
    print(f"CARD IDENTIFICATION TEST")
    print(f"Image: {result['image_path']}")
    print(f"Time: {result['time_ms']}ms")
    print("=" * 80)

    matches = result['matches']
    alternates = result.get('alternates', [])

    # Show top matches
    print(f"\nTOP {len(matches)} MATCHES:")
    print("-" * 80)
    for match in matches:
        print(f"\n#{match['rank']} - {match['name']}")
        print(f"  Similarity: {match['similarity']:.4f} ({match['similarity']*100:.1f}%)")
        print(f"  Confidence: {match['confidence']}")
        print(f"  Card ID: {match['card_id']}")
        print(f"  Product ID: {match['product_id']}")
        print(f"  Set: {match['set']}")
        print(f"  Rarity: {match['rarity']}")

    # Show alternate arts
    if alternates:
        print(f"\n{'=' * 80}")
        print(f"ALTERNATE ARTS/PRINTINGS ({len(alternates)} found)")
        print(f"These are different versions of: {matches[0]['name']}")
        print("-" * 80)
        for alt in alternates[:10]:  # Show top 10
            print(f"\n  {alt['name']}")
            print(f"    Card ID: {alt['id']}")
            print(f"    Product ID: {alt['productId']}")
            print(f"    Set: {alt['set']}")
            print(f"    Rarity: {alt['rarity']}")
    else:
        print(f"\n{'=' * 80}")
        print("NO ALTERNATE ARTS FOUND")
        print("This appears to be the only version of this card.")

    print(f"\n{'=' * 80}")

    # Overall assessment
    best = matches[0]
    print(f"\nBEST MATCH: {best['name']}")
    print(f"Confidence: {best['confidence']} ({best['similarity']*100:.1f}%)")

    if alternates:
        print(f"Alternates: {len(alternates)} other version(s) available")

    # Performance check
    if result['success']:
        print(f"\n[PASS] Identified in {result['time_ms']}ms (target: <2000ms)")
    else:
        print(f"\n[WARN] Took {result['time_ms']}ms (exceeds 2000ms target)")


def main():
    if len(sys.argv) < 2:
        print("=" * 80)
        print("REAL CARD IDENTIFICATION TESTER")
        print("=" * 80)
        print("\nUsage:")
        print("  python scripts/identification/test_real_cards.py <image_path> [top_k]")
        print("\nExamples:")
        print("  python scripts/identification/test_real_cards.py test-images/one-piece/luffy.jpg")
        print("  python scripts/identification/test_real_cards.py my_card.jpg 10")
        print("\nPlace your card photos in: test-images/one-piece/")
        print("=" * 80)
        sys.exit(1)

    image_path = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        print(f"\nMake sure to place your card photos in: test-images/one-piece/")
        sys.exit(1)

    # Initialize tester (one-time model loading)
    tester = RealCardTester()

    # Identify card
    result = tester.identify(image_path, top_k=top_k)

    # Print results
    print_results(result)


if __name__ == "__main__":
    main()
