#!/usr/bin/env python3
import os
import sys
import json
import faiss
import numpy as np
from pathlib import Path
import signal
import shutil

EMBEDDINGS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata" / "embeddings"
FAISS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "faiss"
STATE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "state"

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
        print("Finishing current index and saving state...\n")

    def is_shutting_down(self):
        return self.shutting_down

    def set_current_operation(self, operation):
        self.current_operation = operation

shutdown_handler = ShutdownHandler()

# Register signal handlers
signal.signal(signal.SIGINT, shutdown_handler.request_shutdown)
signal.signal(signal.SIGTERM, shutdown_handler.request_shutdown)

def validate_embeddings(embeddings, metadata_lines, game_slug):
    """Validate embeddings data before building index"""
    if embeddings.size == 0:
        raise ValueError(f"Empty embeddings array for {game_slug}")

    if len(embeddings.shape) != 2:
        raise ValueError(f"Invalid embeddings shape: {embeddings.shape}, expected 2D array")

    num_embeddings = embeddings.shape[0]
    dimension = embeddings.shape[1]

    # Validate dimension
    if dimension != 512:  # CLIP dimension
        raise ValueError(f"Invalid embedding dimension: {dimension}, expected 512")

    # Validate count matches metadata
    if num_embeddings != metadata_lines:
        raise ValueError(
            f"Mismatch: {num_embeddings} embeddings but {metadata_lines} metadata lines"
        )

    # Check for NaN or Inf values
    if np.isnan(embeddings).any():
        raise ValueError(f"Embeddings contain NaN values for {game_slug}")

    if np.isinf(embeddings).any():
        raise ValueError(f"Embeddings contain Inf values for {game_slug}")

    print(f"✓ Validation passed: {num_embeddings} embeddings, dimension {dimension}")
    return num_embeddings, dimension

def save_index_state(game_slug, total_indices):
    """Save indexing state for recovery"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / "faiss.indexing.state.json"

    state = {
        "last_indexed_game": game_slug,
        "total_indices_built": total_indices,
        "timestamp": str(np.datetime64('now'))
    }

    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)

def build_index_for_game(game_slug):
    shutdown_handler.set_current_operation(f"Building FAISS index for {game_slug}")

    print(f"\n{'='*60}")
    print(f"Building FAISS index for {game_slug}")
    print(f"{'='*60}")

    # Check for shutdown signal
    if shutdown_handler.is_shutting_down():
        print(f"\n⚠️  Shutdown requested, skipping {game_slug}...")
        return {"success": False, "skipped": True}

    game_embeddings_dir = EMBEDDINGS_DIR / game_slug
    embeddings_file = game_embeddings_dir / "embeddings.npy"
    metadata_file = game_embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists():
        print(f"⚠️  No embeddings found for {game_slug}")
        return {"success": False, "reason": "no_embeddings"}

    if not metadata_file.exists():
        print(f"⚠️  No metadata found for {game_slug}")
        return {"success": False, "reason": "no_metadata"}

    try:
        # Load embeddings
        print(f"Loading embeddings from {embeddings_file}...")
        embeddings = np.load(embeddings_file)

        # Count metadata lines
        with open(metadata_file, 'r') as f:
            metadata_lines = sum(1 for line in f if line.strip())

        # Validate data
        num_embeddings, dimension = validate_embeddings(embeddings, metadata_lines, game_slug)

        # Create FAISS index
        print(f"Creating FAISS index...")
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings.astype('float32'))

        # Prepare output directory
        output_dir = FAISS_DIR / game_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        # Atomic save: write to temp file first
        temp_index_path = output_dir / "index.faiss.tmp"
        temp_metadata_path = output_dir / "metadata.jsonl.tmp"

        print(f"Saving index atomically...")

        # Write index to temp file
        faiss.write_index(index, str(temp_index_path))

        # Copy metadata to temp file
        shutil.copy2(metadata_file, temp_metadata_path)

        # Atomic rename (both files must succeed)
        final_index_path = output_dir / "index.faiss"
        final_metadata_path = output_dir / "metadata.jsonl"

        temp_index_path.rename(final_index_path)
        temp_metadata_path.rename(final_metadata_path)

        print(f"✓ {game_slug}: Index built successfully")
        print(f"  Location: {output_dir}")
        print(f"  Vectors: {num_embeddings}")
        print(f"  Dimension: {dimension}")

        return {"success": True, "vectors": num_embeddings, "dimension": dimension}

    except Exception as e:
        print(f"❌ Failed to build index for {game_slug}: {e}")

        # Cleanup temp files on error
        if (output_dir / "index.faiss.tmp").exists():
            (output_dir / "index.faiss.tmp").unlink()
        if (output_dir / "metadata.jsonl.tmp").exists():
            (output_dir / "metadata.jsonl.tmp").unlink()

        return {"success": False, "reason": "error", "error": str(e)}

def main():
    # Ensure directories exist
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    games = ["mtg", "pokemon", "yugioh", "onepiece", "digimon"]

    stats = {"successful": 0, "failed": 0, "skipped": 0}
    results = []

    for game in games:
        if shutdown_handler.is_shutting_down():
            print("\n⚠️  Shutdown requested, stopping indexing pipeline...")
            break

        result = build_index_for_game(game)
        results.append({"game": game, **result})

        if result.get("success"):
            stats["successful"] += 1
            save_index_state(game, stats["successful"])
        elif result.get("skipped"):
            stats["skipped"] += 1
        else:
            stats["failed"] += 1

    shutdown_handler.set_current_operation(None)

    print(f"\n{'='*60}")
    print("FAISS INDEX BUILDING COMPLETE")
    print(f"{'='*60}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")

    if stats['failed'] > 0:
        print("\n⚠️  Some indices failed to build:")
        for result in results:
            if not result.get("success") and not result.get("skipped"):
                reason = result.get("error", result.get("reason", "unknown"))
                print(f"  - {result['game']}: {reason}")
        sys.exit(1)

if __name__ == "__main__":
    main()
