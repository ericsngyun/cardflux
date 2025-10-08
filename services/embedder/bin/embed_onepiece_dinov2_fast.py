#!/usr/bin/env python3
"""
OPTIMIZED DINOv2 embedder with batch processing and multi-threading.

Speed improvements:
- Batch processing (process multiple images at once)
- DataLoader with num_workers for parallel image loading
- GPU utilization if available
- Pre-allocated arrays for better memory efficiency

Expected: 3-5x faster than sequential processing
"""
import os
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from tqdm import tqdm
from torch.utils.data import Dataset, DataLoader
from concurrent.futures import ThreadPoolExecutor
import time

IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
CURATED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "curated"
ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "models"

MODEL_NAME = "facebook/dinov2-small"
GAME = "one-piece"

# Optimization parameters
BATCH_SIZE = 32  # Process 32 images at once (adjust based on RAM)
NUM_WORKERS = 4  # Parallel image loading threads


class CardImageDataset(Dataset):
    """Dataset for efficient batch loading of card images."""

    def __init__(self, cards, game_images_dir, processor):
        self.cards = cards
        self.game_images_dir = game_images_dir
        self.processor = processor
        self.valid_items = []

        # Pre-scan which cards have images (faster than checking during iteration)
        print("Pre-scanning available images...")
        for card in tqdm(cards, desc="Scanning"):
            card_id = card.get('id') or str(card.get('productId', 'unknown'))

            # Check for image
            image_path = None
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                candidate = game_images_dir / f"{card_id}{ext}"
                if candidate.exists():
                    image_path = candidate
                    break

            if image_path:
                self.valid_items.append({
                    'card': card,
                    'card_id': card_id,
                    'image_path': image_path
                })

    def __len__(self):
        return len(self.valid_items)

    def __getitem__(self, idx):
        item = self.valid_items[idx]

        try:
            # Load and process image
            image = Image.open(item['image_path']).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")

            # Extract the pixel values tensor
            pixel_values = inputs['pixel_values'].squeeze(0)  # Remove batch dim

            return {
                'pixel_values': pixel_values,
                'card_id': item['card_id'],
                'card': item['card']
            }
        except Exception as e:
            print(f"Error loading {item['image_path']}: {e}")
            # Return dummy data on error
            return {
                'pixel_values': torch.zeros(3, 224, 224),
                'card_id': item['card_id'],
                'card': item['card'],
                'error': True
            }


def collate_fn(batch):
    """Custom collate function to handle batch processing."""
    # Filter out errors
    valid_batch = [item for item in batch if 'error' not in item]

    if not valid_batch:
        return None

    # Stack pixel values
    pixel_values = torch.stack([item['pixel_values'] for item in valid_batch])

    return {
        'pixel_values': pixel_values,
        'card_ids': [item['card_id'] for item in valid_batch],
        'cards': [item['card'] for item in valid_batch]
    }


def load_model():
    """Load DINOv2 model and processor."""
    print(f"Loading model {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Load with optimizations
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    # Enable inference optimizations
    if device == "cuda":
        model = model.half()  # Use FP16 for GPU (2x speedup)

    return model, processor, device


def main():
    start_time = time.time()
    print(f"\n=== OPTIMIZED DINOv2 Embedding (Batch Processing) ===\n")

    curated_path = CURATED_DIR / f"{GAME}.jsonl"
    game_images_dir = IMAGES_DIR / GAME

    if not curated_path.exists():
        print(f"ERROR: No curated data found at {curated_path}")
        return

    if not game_images_dir.exists():
        print(f"ERROR: No images directory found at {game_images_dir}")
        return

    # Load cards
    print(f"Loading cards from {curated_path}...")
    cards = []
    with open(curated_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cards.append(json.loads(line))

    print(f"Found {len(cards)} cards in database")

    # Load model
    model, processor, device = load_model()

    # Create dataset
    dataset = CardImageDataset(cards, game_images_dir, processor)
    print(f"Found {len(dataset)} cards with images")
    print(f"Skipped {len(cards) - len(dataset)} cards without images")

    # Create DataLoader for batch processing
    dataloader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        collate_fn=collate_fn,
        pin_memory=True if device == "cuda" else False
    )

    # Pre-allocate arrays
    total_items = len(dataset)
    embeddings = np.zeros((total_items, 384), dtype=np.float32)
    metadata = []

    # Process batches
    print(f"\nGenerating embeddings in batches of {BATCH_SIZE}...")
    processed = 0

    with torch.no_grad():
        for batch_idx, batch in enumerate(tqdm(dataloader, desc="Processing batches")):
            if batch is None:
                continue

            # Move to device
            pixel_values = batch['pixel_values'].to(device)

            # Get embeddings for whole batch
            outputs = model(pixel_values=pixel_values)
            batch_embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()

            # Store embeddings
            batch_size = len(batch['card_ids'])
            embeddings[processed:processed + batch_size] = batch_embeddings

            # Store metadata
            for card_id, card in zip(batch['card_ids'], batch['cards']):
                metadata.append({
                    "id": card_id,
                    "productId": card.get("productId"),
                    "game": card.get("game") or card.get("categoryName", "one-piece"),
                    "name": card.get("name", "Unknown"),
                    "set": card.get("set") or card.get("groupName"),
                    "rarity": card.get("rarity"),
                    "type": card.get("type"),
                    "imageUrl": card.get("imageUrl"),
                })

            processed += batch_size

    # Trim to actual size (in case of errors)
    embeddings = embeddings[:processed]

    # Save embeddings
    output_dir = ARTIFACTS_DIR / "embeddings" / f"{GAME}-dinov2"
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings_file = output_dir / "embeddings.npy"
    metadata_file = output_dir / "metadata.jsonl"

    np.save(embeddings_file, embeddings)

    with open(metadata_file, 'w', encoding='utf-8') as f:
        for item in metadata:
            f.write(json.dumps(item) + '\n')

    # Save model info
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_info = {
        "name": MODEL_NAME,
        "dimension": 384,
        "type": "dinov2",
        "variant": "small",
    }

    with open(MODELS_DIR / "model_info_dinov2.json", 'w') as f:
        json.dump(model_info, f, indent=2)

    elapsed = time.time() - start_time
    cards_per_sec = processed / elapsed if elapsed > 0 else 0

    print(f"\n=== Summary ===")
    print(f"Embeddings generated: {processed}")
    print(f"Cards skipped (no image): {len(cards) - processed}")
    print(f"Embedding shape: {embeddings.shape}")
    print(f"Model: {MODEL_NAME} (384-dim)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Speed: {cards_per_sec:.1f} cards/sec")
    print(f"\nSaved to:")
    print(f"  {embeddings_file}")
    print(f"  {metadata_file}")


if __name__ == "__main__":
    main()
