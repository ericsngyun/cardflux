#!/usr/bin/env python3
"""
Build FAISS index for One Piece TCG embeddings only.
"""
import json
import numpy as np
import faiss
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "faiss"

GAME = "one-piece"

def main():
    print(f"\n=== Building FAISS Index for One Piece ===\n")

    embeddings_dir = ARTIFACTS_DIR / "embeddings" / GAME
    embeddings_file = embeddings_dir / "embeddings.npy"
    metadata_file = embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists():
        print(f"ERROR: No embeddings found at {embeddings_file}")
        print("Run the embedder first: python services/embedder/bin/embed_onepiece.py")
        return

    # Load embeddings
    print(f"Loading embeddings from {embeddings_file}...")
    embeddings = np.load(embeddings_file)
    print(f"Loaded {embeddings.shape[0]} embeddings with dimension {embeddings.shape[1]}")

    # Load metadata
    metadata = []
    with open(metadata_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))

    print(f"Loaded {len(metadata)} metadata entries")

    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)

    # Build index
    dimension = embeddings.shape[1]
    print(f"\nBuilding FAISS index (dimension={dimension})...")

    # Use IndexFlatIP for exact cosine similarity search
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"Index built with {index.ntotal} vectors")

    # Save index
    output_dir = FAISS_DIR / GAME
    output_dir.mkdir(parents=True, exist_ok=True)

    index_file = output_dir / "index.faiss"
    ids_file = output_dir / "ids.json"

    faiss.write_index(index, str(index_file))

    # Save card IDs in same order as embeddings
    ids = [m["id"] for m in metadata]
    with open(ids_file, 'w', encoding='utf-8') as f:
        json.dump(ids, f)

    print(f"\n=== Summary ===")
    print(f"Index type: IndexFlatIP (cosine similarity)")
    print(f"Total vectors: {index.ntotal}")
    print(f"Dimension: {dimension}")
    print(f"\nSaved to:")
    print(f"  {index_file}")
    print(f"  {ids_file}")

if __name__ == "__main__":
    main()
