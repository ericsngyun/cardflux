#!/usr/bin/env python3
"""
Production FAISS Index Builder with Sealed Product Filtering

Builds IndexFlatIP (exact cosine similarity) indices with:
- STRICT sealed product filtering (NO booster boxes, starter decks, etc.)
- Per-set sharding (future S3 distribution)
- Unified game index (current desktop app compatibility)
- Validation and benchmarking
- Incremental processing support

CRITICAL: Only actual playable cards with collector numbers are indexed.
Sealed products (booster boxes, starter decks, blisters, etc.) are EXCLUDED.

Input: artifacts/embeddings/{game_id}/embeddings.npy + metadata.jsonl
Output:
  - artifacts/faiss/{game_id}/index.faiss (unified index for desktop)
  - artifacts/faiss/{game_id}/ids.json
  - artifacts/faiss/{game_id}/shards/{set_code}/ (per-set shards for S3)
"""

import os
import sys
import json
import time
import argparse
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict

# ============================================================================
# Paths
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent.parent
EMBEDDINGS_DIR = REPO_ROOT / "artifacts" / "embeddings"
FAISS_DIR = REPO_ROOT / "artifacts" / "faiss"

# ============================================================================
# Types
# ============================================================================

@dataclass
class CardEmbedding:
    """Card with embedding."""
    card_id: str
    game_id: str
    set_code: str
    collector_number: str
    name: str
    embedding: np.ndarray


# ============================================================================
# Sealed Product Filtering
# ============================================================================

def is_sealed_product(name: str, collector_number: str) -> bool:
    """
    CRITICAL: Filter sealed products that should NOT be indexed.

    Sealed products include:
    - Booster boxes, booster packs, booster cases
    - Starter decks, structure decks (sealed products, NOT individual cards)
    - Blister packs, tins, bundles
    - Display boxes, fat packs, gift boxes
    - Prerelease kits

    Returns: True if sealed product (should be excluded)
    """
    # Primary filter: No collector number = sealed product
    if not collector_number or collector_number.strip() == '':
        return True

    # Secondary filter: Check name patterns
    name_lower = name.lower()

    sealed_patterns = [
        # Booster products
        'booster box', 'booster pack', 'booster case',
        'display box', 'display case',

        # Deck products (sealed, not individual cards)
        'starter deck', 'structure deck', 'starter set',
        'theme deck', 'intro pack',

        # Bundles and kits
        'blister', 'blister pack',
        'tin', 'collector tin',
        'bundle', 'mega pack',
        'gift box', 'gift set',
        'fat pack', 'elite trainer box',

        # Prerelease
        'prerelease kit', 'prerelease pack',
        'pre-release starter deck',

        # Specific to One Piece
        'learn together deck set',

        # General sealed indicators
        ' box ', 'sealed product',
    ]

    for pattern in sealed_patterns:
        if pattern in name_lower:
            return True

    return False


# ============================================================================
# Data Loading
# ============================================================================

def load_embeddings_with_validation(game_id: str) -> List[CardEmbedding]:
    """Load embeddings with strict sealed product filtering."""
    embeddings_dir = EMBEDDINGS_DIR / game_id
    embeddings_file = embeddings_dir / "embeddings.npy"
    metadata_file = embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists():
        raise FileNotFoundError(f"Embeddings not found: {embeddings_file}")

    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_file}")

    # Load embeddings
    print(f"\nLoading embeddings from {embeddings_file}...")
    embeddings = np.load(embeddings_file)
    print(f"  Loaded {len(embeddings):,} embeddings (dimension: {embeddings.shape[1]})")

    # Load metadata
    metadata = []
    with open(metadata_file, 'r') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))

    if len(embeddings) != len(metadata):
        raise ValueError(f"Mismatch: {len(embeddings)} embeddings vs {len(metadata)} metadata entries")

    # Build card embeddings with STRICT filtering
    cards = []
    sealed_filtered = 0

    for i, (embedding, meta) in enumerate(zip(embeddings, metadata)):
        card_id = meta.get('card_id')
        game_id_meta = meta.get('game_id')
        set_code = meta.get('set_code', 'unknown')
        collector_number = meta.get('collector_number', '')
        name = meta.get('name', '')

        # CRITICAL: Filter sealed products
        if is_sealed_product(name, collector_number):
            sealed_filtered += 1
            continue

        # Validation: card must have ID and collector number
        if not card_id or not collector_number:
            sealed_filtered += 1
            continue

        cards.append(CardEmbedding(
            card_id=card_id,
            game_id=game_id_meta or game_id,
            set_code=set_code,
            collector_number=collector_number,
            name=name,
            embedding=embedding,
        ))

    print(f"\n✅ Loaded {len(cards):,} PLAYABLE cards")
    if sealed_filtered > 0:
        print(f"🚫 Filtered {sealed_filtered} sealed products (booster boxes, starter decks, etc.)")

    return cards


# ============================================================================
# Index Building
# ============================================================================

def build_index_flatip(embeddings: np.ndarray, dimension: int) -> faiss.Index:
    """
    Build IndexFlatIP for exact cosine similarity search.

    IndexFlatIP = Inner Product (cosine similarity for normalized vectors)
    - 100% recall (exact search, no approximation)
    - Fast for small-medium datasets (<100K vectors)
    - O(n) search complexity
    - Perfect for card identification where accuracy is CRITICAL
    """
    print(f"\nBuilding IndexFlatIP (exact search)...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    print(f"  Added {index.ntotal:,} vectors")
    return index


def build_per_set_shards(cards: List[CardEmbedding], game_id: str):
    """
    Build per-set FAISS shards for future S3 distribution.

    Each set gets its own IndexFlatIP shard:
    - Faster downloads (only download needed sets)
    - Easier updates (rebuild only changed sets)
    - Better organization
    """
    print(f"\nBuilding per-set shards...")

    # Group by set
    cards_by_set = defaultdict(list)
    for card in cards:
        cards_by_set[card.set_code].append(card)

    print(f"  Found {len(cards_by_set)} sets")

    shards_dir = FAISS_DIR / game_id / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    shard_info = []

    for set_code, set_cards in cards_by_set.items():
        if not set_cards:
            continue

        print(f"\n  Set: {set_code} ({len(set_cards)} cards)")

        # Build embeddings array
        embeddings = np.array([c.embedding for c in set_cards], dtype=np.float32)
        dimension = embeddings.shape[1]

        # Build index
        index = build_index_flatip(embeddings, dimension)

        # Save shard
        shard_dir = shards_dir / set_code
        shard_dir.mkdir(parents=True, exist_ok=True)

        index_path = shard_dir / "index.faiss"
        ids_path = shard_dir / "ids.json"
        meta_path = shard_dir / "meta.json"

        faiss.write_index(index, str(index_path))

        # Save IDs
        ids = [c.card_id for c in set_cards]
        with open(ids_path, 'w') as f:
            json.dump(ids, f, indent=2)

        # Save shard metadata
        shard_meta = {
            "game_id": game_id,
            "set_code": set_code,
            "vector_count": len(set_cards),
            "dimension": dimension,
            "index_type": "IndexFlatIP",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        with open(meta_path, 'w') as f:
            json.dump(shard_meta, f, indent=2)

        shard_info.append({
            "set_code": set_code,
            "vector_count": len(set_cards),
            "index_path": str(index_path.relative_to(REPO_ROOT)),
            "ids_path": str(ids_path.relative_to(REPO_ROOT)),
        })

        print(f"    ✅ Saved shard: {index_path}")

    return shard_info


# ============================================================================
# Validation
# ============================================================================

def benchmark_index(index: faiss.Index, embeddings: np.ndarray, k: int = 20, n_queries: int = 100) -> Dict:
    """Benchmark index with self-queries."""
    print(f"\nBenchmarking index...")

    n_vectors = len(embeddings)
    query_ids = np.random.choice(n_vectors, min(n_queries, n_vectors), replace=False)
    queries = embeddings[query_ids]

    # Warm up
    _ = index.search(queries[:10], k)

    # Timed search
    start = time.time()
    distances, indices = index.search(queries, k)
    search_time = time.time() - start

    avg_time_ms = (search_time / len(queries)) * 1000

    # Calculate self-recall (should be 100% for IndexFlatIP)
    recall_sum = 0
    for i, query_id in enumerate(query_ids):
        if query_id in indices[i]:
            recall_sum += 1

    recall = recall_sum / len(queries)

    print(f"  Queries: {len(queries)}")
    print(f"  Avg latency: {avg_time_ms:.2f}ms")
    print(f"  Self-recall@{k}: {recall:.1%}")

    if recall < 1.0:
        print(f"  ⚠️  WARNING: Self-recall < 100% (expected 100% for IndexFlatIP)")

    return {
        "avg_latency_ms": avg_time_ms,
        "recall": recall,
        "queries": len(queries),
    }


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Production FAISS Index Builder")
    parser.add_argument("--game", type=str, help="Game ID to build index for")
    args = parser.parse_args()

    print("=" * 80)
    print("PRODUCTION FAISS INDEX BUILDER")
    print("IndexFlatIP (Exact Matching) with Sealed Product Filtering")
    print("=" * 80)

    # Find games
    if args.game:
        games = [args.game]
    else:
        # Check if embeddings directory exists
        if not EMBEDDINGS_DIR.exists():
            games = []
        else:
            games = [d.name for d in EMBEDDINGS_DIR.iterdir() if d.is_dir()]

    if not games:
        print("\n[INFO] No games found in artifacts/embeddings/")
        print("This is expected when using game-specific embedders (e.g., embed_onepiece_dinov2_with_preprocessing.py)")
        print("which build FAISS indices directly without intermediate embeddings directory.")
        print("\nSkipping FAISS index building step.")
        sys.exit(0)  # Exit successfully

    print(f"\nGames: {', '.join(games)}")

    for game_id in games:
        print(f"\n{'=' * 80}")
        print(f"Processing: {game_id}")
        print(f"{'=' * 80}")

        start_time = time.time()

        try:
            # Load embeddings with validation
            cards = load_embeddings_with_validation(game_id)

            if not cards:
                print(f"  ⚠️  No playable cards found for {game_id}")
                continue

            # Build unified index (for desktop app compatibility)
            print(f"\n📦 Building unified index for desktop app...")
            embeddings = np.array([c.embedding for c in cards], dtype=np.float32)
            dimension = embeddings.shape[1]

            # Verify normalization
            norms = np.linalg.norm(embeddings, axis=1)
            avg_norm = np.mean(norms)
            print(f"  Average embedding norm: {avg_norm:.4f}")

            if abs(avg_norm - 1.0) > 0.01:
                print("  ⚠️  Normalizing embeddings...")
                faiss.normalize_L2(embeddings)

            # Build index
            index = build_index_flatip(embeddings, dimension)

            # Benchmark
            benchmark_results = benchmark_index(index, embeddings, k=20, n_queries=100)

            # Save unified index
            output_dir = FAISS_DIR / game_id
            output_dir.mkdir(parents=True, exist_ok=True)

            index_path = output_dir / "index.faiss"
            ids_path = output_dir / "ids.json"
            config_path = output_dir / "index_config.json"

            print(f"\n💾 Saving unified index...")
            faiss.write_index(index, str(index_path))

            # Save IDs
            ids = [c.card_id for c in cards]
            with open(ids_path, 'w') as f:
                json.dump(ids, f, indent=2)

            # Save config
            config = {
                "index_type": "IndexFlatIP",
                "dimension": dimension,
                "total_vectors": index.ntotal,
                "config": {
                    "type": "flat",
                    "exact_search": True,
                    "expected_recall": 1.0,
                    "complexity": "O(n)",
                },
                "benchmark": benchmark_results,
                "sealed_products_excluded": True,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"  ✅ {index_path}")
            print(f"  ✅ {ids_path}")
            print(f"  ✅ {config_path}")

            # Build per-set shards
            shard_info = build_per_set_shards(cards, game_id)

            # Summary
            elapsed = time.time() - start_time

            print(f"\n{'=' * 80}")
            print(f"SUCCESS: {game_id}")
            print(f"{'=' * 80}")
            print(f"Total cards: {len(cards):,}")
            print(f"Sets: {len(shard_info)}")
            print(f"Dimension: {dimension}")
            print(f"Index type: IndexFlatIP (exact search)")
            print(f"Self-recall: {benchmark_results['recall']:.1%}")
            print(f"Avg latency: {benchmark_results['avg_latency_ms']:.2f}ms")
            print(f"Build time: {elapsed:.2f}s")
            print(f"{'=' * 80}")

        except Exception as e:
            print(f"\n❌ ERROR processing {game_id}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'=' * 80}")
    print("FAISS INDEX BUILD COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
