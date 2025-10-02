#!/usr/bin/env python3
import os
import json
import faiss
import numpy as np
from pathlib import Path

EMBEDDINGS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata" / "embeddings"
FAISS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "faiss"

def build_index_for_game(game_slug):
    print(f"Building FAISS index for {game_slug}...")

    game_embeddings_dir = EMBEDDINGS_DIR / game_slug
    embeddings_file = game_embeddings_dir / "embeddings.npy"
    metadata_file = game_embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists():
        print(f"No embeddings found for {game_slug}")
        return

    # Load embeddings
    embeddings = np.load(embeddings_file)
    dimension = embeddings.shape[1]

    print(f"Loaded {len(embeddings)} embeddings with dimension {dimension}")

    # Create FAISS index
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype('float32'))

    # Save index
    output_dir = FAISS_DIR / game_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(output_dir / "index.faiss"))

    # Copy metadata
    with open(metadata_file, 'r') as src:
        with open(output_dir / "metadata.jsonl", 'w') as dst:
            dst.write(src.read())

    print(f"FAISS index saved to {output_dir}")

def main():
    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    games = ["mtg", "pokemon", "yugioh", "onepiece", "digimon"]

    for game in games:
        build_index_for_game(game)

    print("\nFAISS index building complete!")

if __name__ == "__main__":
    main()
