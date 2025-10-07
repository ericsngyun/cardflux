#!/usr/bin/env python3
"""
Test card identification from static images.
Upload a photo of a One Piece card and find the best match.
"""
import sys
import json
import numpy as np
import faiss
import torch
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent / "artifacts" / "faiss"
MODELS_DIR = Path(__file__).parent.parent / "artifacts" / "models"

MODEL_NAME = "openai/clip-vit-base-patch32"
GAME = "one-piece"

class CardIdentifier:
    def __init__(self):
        print("Loading CLIP model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        # Load FAISS index
        index_file = FAISS_DIR / GAME / "index.faiss"
        ids_file = FAISS_DIR / GAME / "ids.json"

        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_file}. Run build_faiss_onepiece.py first.")

        print(f"Loading FAISS index from {index_file}...")
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

        print(f"Loaded index with {self.index.ntotal} cards")
        print("Ready for identification!\n")

    def get_image_embedding(self, image_path):
        """Generate embedding for an image."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            embedding = image_features.cpu().numpy()[0]

        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def identify(self, image_path, top_k=5):
        """Identify a card from an image."""
        print(f"Processing image: {image_path}")

        embedding = self.get_image_embedding(image_path)

        # Search in FAISS
        embedding_2d = np.array([embedding])
        distances, indices = self.index.search(embedding_2d, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            card_id = self.card_ids[idx]
            meta = self.metadata[card_id]

            # Convert distance to similarity score (0-1)
            similarity = float(dist)  # Already cosine similarity with IndexFlatIP

            results.append({
                "rank": i + 1,
                "similarity": similarity,
                "card_id": card_id,
                "name": meta['name'],
                "set": meta.get('set', 'Unknown'),
                "rarity": meta.get('rarity', 'Unknown'),
                "type": meta.get('type', 'Unknown'),
            })

        return results

def print_results(results):
    """Pretty print identification results."""
    print("\n" + "="*80)
    print("IDENTIFICATION RESULTS")
    print("="*80)

    for result in results:
        print(f"\n#{result['rank']} - Similarity: {result['similarity']:.4f} ({result['similarity']*100:.1f}%)")
        print(f"  Card ID: {result['card_id']}")
        print(f"  Name: {result['name']}")
        print(f"  Set: {result['set']}")
        print(f"  Rarity: {result['rarity']}")
        print(f"  Type: {result['type']}")

    print("\n" + "="*80)

    best = results[0]
    if best['similarity'] > 0.9:
        print(f"[HIGH CONFIDENCE MATCH]: {best['name']}")
    elif best['similarity'] > 0.7:
        print(f"[MODERATE CONFIDENCE]: {best['name']}")
    else:
        print(f"[LOW CONFIDENCE] - May not be a match")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_identification.py <image_path> [top_k]")
        print("\nExample:")
        print("  python test_identification.py test_card.jpg")
        print("  python test_identification.py test_card.jpg 10")
        sys.exit(1)

    image_path = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        sys.exit(1)

    # Initialize identifier
    identifier = CardIdentifier()

    # Identify card
    results = identifier.identify(image_path, top_k=top_k)

    # Print results
    print_results(results)

if __name__ == "__main__":
    main()
