#!/usr/bin/env python3
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

def load_model():
    print(f"Loading model {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
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

def process_game(game_slug, model, processor, device):
    print(f"\nProcessing {game_slug}...")

    curated_path = CURATED_DIR / f"{game_slug}.jsonl"
    game_images_dir = IMAGES_DIR / game_slug

    if not curated_path.exists():
        print(f"No curated data found for {game_slug}")
        return

    if not game_images_dir.exists():
        print(f"No images directory found for {game_slug}")
        return

    # Load cards
    cards = []
    with open(curated_path, 'r') as f:
        for line in f:
            if line.strip():
                cards.append(json.loads(line))

    # Process embeddings
    embeddings = []
    metadata = []

    for card in tqdm(cards, desc=f"Embedding {game_slug}"):
        # Find image file
        image_files = list(game_images_dir.glob(f"{card['id']}.*"))

        if not image_files:
            continue

        image_path = image_files[0]
        embedding = get_image_embedding(image_path, model, processor, device)

        if embedding is not None:
            embeddings.append(embedding)
            metadata.append({
                "id": card["id"],
                "game": card["game"],
                "name": card["name"],
                "set": card.get("set"),
                "rarity": card.get("rarity"),
                "type": card.get("type"),
            })

    # Save embeddings
    embeddings_array = np.array(embeddings)
    output_dir = ARTIFACTS_DIR / "embeddings" / game_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_dir / "embeddings.npy", embeddings_array)

    with open(output_dir / "metadata.jsonl", 'w') as f:
        for item in metadata:
            f.write(json.dumps(item) + '\n')

    print(f"Saved {len(embeddings)} embeddings for {game_slug}")

def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    model, processor, device = load_model()

    # Save model info
    model_info = {
        "name": MODEL_NAME,
        "dimension": 512,
        "type": "clip",
    }

    with open(MODELS_DIR / "model_info.json", 'w') as f:
        json.dump(model_info, f, indent=2)

    # Process each game
    games = ["mtg", "pokemon", "yugioh", "onepiece", "digimon"]

    for game in games:
        process_game(game, model, processor, device)

    print("\nEmbedding complete!")

if __name__ == "__main__":
    main()
