#!/usr/bin/env python3
"""
Generate embeddings for One Piece TCG cards only.
Faster for testing the identification pipeline.
"""
import os
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm

IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
CURATED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "curated"
ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "models"

MODEL_NAME = "openai/clip-vit-base-patch32"
GAME = "one-piece"

def load_model():
    print(f"Loading model {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return model, processor, device

def get_image_embedding(image_path, model, processor, device):
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)

        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            embedding = image_features.cpu().numpy()[0]

        return embedding
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def main():
    print(f"\n=== Embedding One Piece TCG Cards ===\n")

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

    # Check images
    image_files = list(game_images_dir.glob("*"))
    print(f"Found {len(image_files)} image files")

    if len(image_files) == 0:
        print("\nERROR: No images found! Run image fetcher first:")
        print("  tsx services/ingest/bin/fetch_images_onepiece.ts")
        return

    # Load model
    model, processor, device = load_model()

    # Process embeddings
    embeddings = []
    metadata = []
    skipped = 0

    print(f"\nGenerating embeddings...")
    for card in tqdm(cards, desc="Processing cards"):
        # Get card ID (use productId for TCGPlayer data)
        card_id = card.get('id') or str(card.get('productId', 'unknown'))

        # Find image file (check multiple extensions)
        image_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            candidate = game_images_dir / f"{card_id}{ext}"
            if candidate.exists():
                image_path = candidate
                break

        if not image_path:
            skipped += 1
            continue

        embedding = get_image_embedding(image_path, model, processor, device)

        if embedding is not None:
            embeddings.append(embedding)
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

    # Save embeddings
    embeddings_array = np.array(embeddings)
    output_dir = ARTIFACTS_DIR / "embeddings" / GAME
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings_file = output_dir / "embeddings.npy"
    metadata_file = output_dir / "metadata.jsonl"

    np.save(embeddings_file, embeddings_array)

    with open(metadata_file, 'w', encoding='utf-8') as f:
        for item in metadata:
            f.write(json.dumps(item) + '\n')

    # Save model info
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_info = {
        "name": MODEL_NAME,
        "dimension": 512,
        "type": "clip",
    }

    with open(MODELS_DIR / "model_info.json", 'w') as f:
        json.dump(model_info, f, indent=2)

    print(f"\n=== Summary ===")
    print(f"Embeddings generated: {len(embeddings)}")
    print(f"Cards skipped (no image): {skipped}")
    print(f"Embedding shape: {embeddings_array.shape}")
    print(f"\nSaved to:")
    print(f"  {embeddings_file}")
    print(f"  {metadata_file}")

if __name__ == "__main__":
    main()
