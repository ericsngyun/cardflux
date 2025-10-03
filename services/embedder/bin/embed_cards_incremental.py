#!/usr/bin/env python3
import os
import sys
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm
import hashlib
import signal

IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
CURATED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "curated"
ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
STATE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "state"
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "models"

MODEL_NAME = "openai/clip-vit-base-patch32"

# Graceful shutdown handling
class ShutdownHandler:
    def __init__(self):
        self.shutting_down = False
        self.current_operation = None

    def request_shutdown(self, signum, frame):
        if self.shutting_down:
            print("\n⚠️  Force exit requested...")
            sys.exit(1)

        self.shutting_down = True
        print("\n\n" + "="*60)
        print("GRACEFUL SHUTDOWN INITIATED")
        print("="*60)

        if self.current_operation:
            print(f"Current operation: {self.current_operation}")

        print("\nPress Ctrl+C again to force exit (NOT RECOMMENDED)\n")
        print("Finishing current card and saving state...\n")

    def is_shutting_down(self):
        return self.shutting_down

    def set_current_operation(self, operation):
        self.current_operation = operation

shutdown_handler = ShutdownHandler()

# Register signal handlers
signal.signal(signal.SIGINT, shutdown_handler.request_shutdown)
signal.signal(signal.SIGTERM, shutdown_handler.request_shutdown)

def load_state(game_slug):
    """Load previous embedding state"""
    state_path = STATE_DIR / f"{game_slug}.embeddings.state.json"

    if not state_path.exists():
        return None

    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load embedding state: {e}")
        return None

def save_state(game_slug, state):
    """Save embedding state"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / f"{game_slug}.embeddings.state.json"

    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)

def get_image_hash(image_path):
    """Calculate hash of image file to detect changes"""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:8]

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

def load_existing_embeddings(game_slug):
    """Load existing embeddings and metadata"""
    embeddings_dir = ARTIFACTS_DIR / "embeddings" / game_slug

    if not embeddings_dir.exists():
        return {}, []

    embeddings_file = embeddings_dir / "embeddings.npy"
    metadata_file = embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists() or not metadata_file.exists():
        return {}, []

    # Load embeddings
    embeddings_array = np.load(embeddings_file)

    # Load metadata
    metadata = []
    embeddings_dict = {}

    with open(metadata_file, 'r') as f:
        for i, line in enumerate(f):
            if line.strip():
                meta = json.loads(line)
                metadata.append(meta)
                embeddings_dict[meta['id']] = embeddings_array[i]

    return embeddings_dict, metadata

def process_game_incremental(game_slug, model, processor, device):
    shutdown_handler.set_current_operation(f"Embedding {game_slug}")

    print(f"\n{'='*60}")
    print(f"Processing {game_slug}")
    print(f"{'='*60}")

    # Check for shutdown signal
    if shutdown_handler.is_shutting_down():
        print(f"\n⚠️  Shutdown requested, stopping {game_slug} embedding...")
        return {"new": 0, "skipped": 0, "failed": 0}

    curated_path = CURATED_DIR / f"{game_slug}.jsonl"
    game_images_dir = IMAGES_DIR / game_slug

    if not curated_path.exists():
        print(f"No curated data found for {game_slug}")
        return {"new": 0, "skipped": 0, "failed": 0}

    if not game_images_dir.exists():
        print(f"No images directory found for {game_slug}")
        return {"new": 0, "skipped": 0, "failed": 0}

    # Load previous state
    previous_state = load_state(game_slug)
    image_hashes = previous_state.get("image_hashes", {}) if previous_state else {}

    # Load existing embeddings
    existing_embeddings, existing_metadata = load_existing_embeddings(game_slug)
    print(f"Found {len(existing_embeddings)} existing embeddings")

    # Load cards
    cards = []
    with open(curated_path, 'r') as f:
        for line in f:
            if line.strip():
                cards.append(json.loads(line))

    # Determine which cards need embedding
    cards_to_process = []
    stats = {"new": 0, "skipped": 0, "failed": 0}

    for card in cards:
        # Find image file
        image_files = list(game_images_dir.glob(f"{card['id']}.*"))

        if not image_files:
            continue

        image_path = image_files[0]

        # Check if we already have this embedding
        if card['id'] in existing_embeddings:
            # Check if image changed
            current_hash = get_image_hash(image_path)
            previous_hash = image_hashes.get(card['id'])

            if previous_hash == current_hash:
                stats['skipped'] += 1
                continue
            else:
                print(f"  ↻ Image changed for {card['name']}")

        cards_to_process.append((card, image_path))

    if len(cards_to_process) == 0:
        print(f"✓ All {len(cards)} embeddings up to date")
        return stats

    print(f"Processing {len(cards_to_process)} new/changed cards...")

    # Process new embeddings
    new_embeddings = []
    new_metadata = []
    new_image_hashes = {}

    for i, (card, image_path) in enumerate(tqdm(cards_to_process, desc=f"Embedding {game_slug}")):
        # Check for shutdown every 100 cards
        if i % 100 == 0 and shutdown_handler.is_shutting_down():
            print(f"\n⚠️  Shutdown requested, saving partial embeddings...")
            break

        embedding = get_image_embedding(image_path, model, processor, device)

        if embedding is not None:
            new_embeddings.append(embedding)
            new_metadata.append({
                "id": card["id"],
                "game": card["game"],
                "name": card["name"],
                "set": card.get("set"),
                "rarity": card.get("rarity"),
                "type": card.get("type"),
            })
            new_image_hashes[card["id"]] = get_image_hash(image_path)
            stats['new'] += 1
        else:
            stats['failed'] += 1

    # Merge with existing embeddings
    final_embeddings = []
    final_metadata = []
    final_image_hashes = {}

    # Add all cards from curated data (in order)
    for card in cards:
        if card['id'] in new_image_hashes:
            # Use new embedding
            idx = [m['id'] for m in new_metadata].index(card['id'])
            final_embeddings.append(new_embeddings[idx])
            final_metadata.append(new_metadata[idx])
            final_image_hashes[card['id']] = new_image_hashes[card['id']]
        elif card['id'] in existing_embeddings:
            # Use existing embedding
            final_embeddings.append(existing_embeddings[card['id']])
            idx = [m['id'] for m in existing_metadata].index(card['id'])
            final_metadata.append(existing_metadata[idx])
            final_image_hashes[card['id']] = image_hashes.get(card['id'], '')

    # Save embeddings
    embeddings_array = np.array(final_embeddings)
    output_dir = ARTIFACTS_DIR / "embeddings" / game_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_dir / "embeddings.npy", embeddings_array)

    with open(output_dir / "metadata.jsonl", 'w') as f:
        for item in final_metadata:
            f.write(json.dumps(item) + '\n')

    # Save state
    save_state(game_slug, {
        "game": game_slug,
        "total_embeddings": len(final_embeddings),
        "last_sync": str(np.datetime64('now')),
        "image_hashes": final_image_hashes,
    })

    print(f"\n✓ {game_slug}:")
    print(f"  Total embeddings: {len(final_embeddings)}")
    print(f"  New: {stats['new']}")
    print(f"  Skipped (up to date): {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")

    return stats

def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    model, processor, device = load_model()

    # Save model info
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_info = {
        "name": MODEL_NAME,
        "dimension": 512,
        "type": "clip",
    }

    with open(MODELS_DIR / "model_info.json", 'w') as f:
        json.dump(model_info, f, indent=2)

    # Process each game
    games = ["mtg", "pokemon", "yugioh", "onepiece", "digimon"]
    total_stats = {"new": 0, "skipped": 0, "failed": 0}

    for game in games:
        if shutdown_handler.is_shutting_down():
            print("\n⚠️  Shutdown requested, stopping embedding pipeline...")
            break

        stats = process_game_incremental(game, model, processor, device)
        total_stats['new'] += stats['new']
        total_stats['skipped'] += stats['skipped']
        total_stats['failed'] += stats['failed']

    shutdown_handler.set_current_operation(None)

    print(f"\n{'='*60}")
    print("INCREMENTAL EMBEDDING COMPLETE")
    print(f"{'='*60}")
    print(f"Total embeddings: {total_stats['new'] + total_stats['skipped']}")
    print(f"New: {total_stats['new']}")
    print(f"Skipped (up to date): {total_stats['skipped']}")
    print(f"Failed: {total_stats['failed']}")
    print(f"\nTime saved: ~{round(total_stats['skipped'] / 250)} minutes")

if __name__ == "__main__":
    main()
