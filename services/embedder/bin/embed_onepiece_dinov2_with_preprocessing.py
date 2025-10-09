#!/usr/bin/env python3
"""
Generate DINOv2 embeddings WITH preprocessing for One Piece cards.
This matches the preprocessing used in identification for consistency.
"""
import json
import time
import numpy as np
import faiss
import torch
import cv2
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

# Paths
CURATED_DIR = Path("data/curated")
IMAGES_DIR = Path("data/images")
METADATA_DIR = Path("artifacts/metadata/embeddings")
FAISS_DIR = Path("artifacts/faiss")

MODEL_NAME = "facebook/dinov2-small"
GAME = "one-piece"
BATCH_SIZE = 32


def preprocess_image_for_embedding(image: Image.Image) -> Image.Image:
    """
    Preprocess image with bilateral filter + contrast enhancement.
    This MUST match the preprocessing in identify_card_optimized.py!
    """
    img_array = np.array(image)

    # Bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(img_array, 5, 50, 50)

    # Contrast enhancement
    enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)

    return Image.fromarray(enhanced)


class CardDataset(Dataset):
    """Dataset for card images with preprocessing."""

    def __init__(self, curated_path, images_dir, processor):
        self.processor = processor
        self.images_dir = images_dir
        self.valid_items = []

        print(f"Loading cards from {curated_path}...")

        with open(curated_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                card = json.loads(line)
                card_id = card.get('productId')

                if not card_id:
                    continue

                # Filter out sealed products (no card number/rarity, name is product name)
                # Sealed products: "Starter Deck 3: ...", "Booster Box ...", etc.
                card_name = card.get('name', '')
                card_number = card.get('number')
                card_rarity = card.get('rarity')

                # Skip if no card number (sealed products don't have numbers)
                if not card_number:
                    continue

                # Check if image exists
                image_path = None
                for ext in ['.jpg', '.jpeg', '.png']:
                    path = images_dir / f"{card_id}{ext}"
                    if path.exists():
                        image_path = path
                        break

                if image_path:
                    self.valid_items.append({
                        'card': card,
                        'card_id': card_id,
                        'image_path': image_path
                    })

        print(f"Found {len(self.valid_items)} cards with images")

    def __len__(self):
        return len(self.valid_items)

    def __getitem__(self, idx):
        item = self.valid_items[idx]

        try:
            # Load image
            image = Image.open(item['image_path']).convert("RGB")

            original_size = image.size
            min_dim = min(original_size)

            # Apply preprocessing (small images)
            if min_dim < 400:
                # Preprocess first
                image = preprocess_image_for_embedding(image)

                # Then upscale
                scale_factor = 400 / min_dim
                new_size = (
                    int(original_size[0] * scale_factor),
                    int(original_size[1] * scale_factor)
                )
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            else:
                # Just preprocess (no upscaling)
                image = preprocess_image_for_embedding(image)

            # DINOv2 processor
            inputs = self.processor(images=image, return_tensors="pt")
            pixel_values = inputs['pixel_values'].squeeze(0)

            return {
                'pixel_values': pixel_values,
                'card_id': item['card_id'],
                'card': item['card']
            }

        except Exception as e:
            print(f"\nError loading {item['image_path']}: {e}")
            return {
                'pixel_values': torch.zeros(3, 224, 224),
                'card_id': item['card_id'],
                'card': item['card'],
                'error': True
            }


def collate_fn(batch):
    """Custom collate function."""
    valid_batch = [item for item in batch if 'error' not in item]

    if not valid_batch:
        return None

    pixel_values = torch.stack([item['pixel_values'] for item in valid_batch])

    return {
        'pixel_values': pixel_values,
        'card_ids': [item['card_id'] for item in valid_batch],
        'cards': [item['card'] for item in valid_batch]
    }


def load_model():
    """Load DINOv2 model."""
    print(f"Loading model {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    if device == "cuda":
        model = model.half()

    return model, processor, device


def main():
    start_time = time.time()
    print(f"\n=== DINOv2 Embedding WITH Preprocessing ===\n")

    curated_path = CURATED_DIR / f"{GAME}.jsonl"
    game_images_dir = IMAGES_DIR / GAME

    if not curated_path.exists():
        print(f"ERROR: Curated file not found: {curated_path}")
        return

    if not game_images_dir.exists():
        print(f"ERROR: Images directory not found: {game_images_dir}")
        return

    # Load model
    model, processor, device = load_model()

    # Create dataset
    dataset = CardDataset(curated_path, game_images_dir, processor)
    dataloader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        collate_fn=collate_fn
    )

    # Generate embeddings
    embeddings_list = []
    card_ids_list = []
    cards_list = []

    print(f"\nGenerating embeddings (batch_size={BATCH_SIZE})...")

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Processing batches"):
            if batch is None:
                continue

            pixel_values = batch['pixel_values'].to(device)

            # Forward pass
            outputs = model(pixel_values=pixel_values)
            batch_embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()

            # Normalize each embedding
            for i, embedding in enumerate(batch_embeddings):
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm

                embeddings_list.append(embedding)
                card_ids_list.append(batch['card_ids'][i])
                cards_list.append(batch['cards'][i])

    # Convert to numpy array
    embeddings = np.array(embeddings_list, dtype=np.float32)

    print(f"\nGenerated {len(embeddings)} embeddings")
    print(f"Embedding shape: {embeddings.shape}")

    # Save metadata
    output_dir = METADATA_DIR / f"{GAME}-dinov2"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = output_dir / "metadata.jsonl"

    print(f"\nSaving metadata to {metadata_path}...")

    with open(metadata_path, 'w', encoding='utf-8') as f:
        for card in cards_list:
            # Ensure card has 'id' field matching productId
            if 'id' not in card and 'productId' in card:
                card['id'] = card['productId']
            f.write(json.dumps(card, ensure_ascii=False) + '\n')

    # Build FAISS index
    print(f"\nBuilding FAISS index...")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"Index built: {index.ntotal} vectors")

    # Save FAISS index
    faiss_output_dir = FAISS_DIR / f"{GAME}-dinov2"
    faiss_output_dir.mkdir(parents=True, exist_ok=True)

    index_path = faiss_output_dir / "index.faiss"
    ids_path = faiss_output_dir / "ids.json"

    print(f"\nSaving FAISS index to {index_path}...")
    faiss.write_index(index, str(index_path))

    print(f"Saving card IDs to {ids_path}...")
    with open(ids_path, 'w', encoding='utf-8') as f:
        json.dump(card_ids_list, f, ensure_ascii=False, indent=2)

    # Benchmark
    print(f"\nBenchmarking index...")
    query = embeddings[0:1]

    latencies = []
    for _ in range(100):
        t0 = time.time()
        index.search(query, 10)
        latencies.append(time.time() - t0)

    avg_latency = np.mean(latencies) * 1000

    # Save config
    config = {
        "index_type": "IndexFlatIP",
        "dimension": dimension,
        "total_vectors": index.ntotal,
        "preprocessing": {
            "bilateral_filter": {"d": 5, "sigmaColor": 50, "sigmaSpace": 50},
            "contrast": {"alpha": 1.05, "beta": 3},
            "upscaling_threshold": 400,
            "upscaling_method": "LANCZOS"
        },
        "config": {
            "type": "flat",
            "exact_search": True,
            "expected_recall": 1.0,
            "complexity": "O(n)"
        },
        "benchmark": {
            "avg_latency_ms": avg_latency,
            "recall": 1.0,
            "queries": 100
        },
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    config_path = faiss_output_dir / "index_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"SUCCESS!")
    print(f"{'='*60}")
    print(f"Total embeddings: {len(embeddings)}")
    print(f"Embedding dimension: {dimension}")
    print(f"Index type: IndexFlatIP (exact search)")
    print(f"Average query latency: {avg_latency:.2f}ms")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Speed: {len(embeddings)/elapsed:.1f} cards/sec")
    print(f"\nFiles saved:")
    print(f"  - {metadata_path}")
    print(f"  - {index_path}")
    print(f"  - {ids_path}")
    print(f"  - {config_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
