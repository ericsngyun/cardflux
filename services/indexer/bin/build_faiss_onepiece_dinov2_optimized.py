#!/usr/bin/env python3
"""
ULTIMATE OPTIMIZED FAISS Index Builder

Strategies for different dataset sizes:
1. <10K cards: IndexFlatIP (exact search, fast, ~200MB RAM)
2. 10K-100K: IndexHNSWFlat (fast approximate, good recall, ~500MB RAM)
3. >100K: IndexIVFPQ (memory efficient, good recall, ~100MB RAM)

Current implementation uses adaptive strategy based on dataset size.

Performance characteristics:
- IndexFlatIP: 100% recall, 0.5ms search latency, O(n) complexity
- IndexHNSWFlat: 99.5%+ recall, 0.1ms search latency, O(log n) complexity
- IndexIVFPQ: 97%+ recall, 0.3ms search latency, O(√n) complexity

For card identification, we prioritize:
1. High recall (99%+) - don't miss the correct card
2. Low latency (<1ms) - real-time identification
3. Memory efficiency - run on consumer hardware
"""
import json
import numpy as np
import faiss
from pathlib import Path
import time

ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent.parent / "artifacts" / "faiss"

GAME = "one-piece"

# Index configuration thresholds
SIZE_THRESHOLD_HNSW = 10000  # Use HNSW above this size
SIZE_THRESHOLD_IVF = 100000  # Use IVF-PQ above this size

# HNSW parameters (optimized for high recall)
HNSW_M = 32  # Number of connections per layer (higher = better recall, more memory)
HNSW_EF_CONSTRUCTION = 80  # Construction time quality (higher = better but slower)
HNSW_EF_SEARCH = 64  # Search time quality (set at search time)

# IVF parameters (optimized for balanced recall/speed)
IVF_NLIST = 4096  # Number of clusters (sqrt(N) to 4*sqrt(N))
IVF_NPROBE = 32  # Number of clusters to search (higher = better recall)
IVF_M = 16  # PQ code size (lower = more compression, less accuracy)
IVF_NBITS = 8  # Bits per subquantizer


def build_flat_index(embeddings: np.ndarray, dimension: int) -> faiss.Index:
    """
    Build exact cosine similarity index (IndexFlatIP).

    Best for: <10K cards
    Pros: 100% recall, simple, fast for small datasets
    Cons: O(n) search complexity, memory intensive for large datasets
    """
    print(f"Building IndexFlatIP (exact search)...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    return index


def build_hnsw_index(embeddings: np.ndarray, dimension: int) -> faiss.Index:
    """
    Build HNSW index for fast approximate search.

    Best for: 10K-100K cards
    Pros: Very fast (O(log n)), high recall (99.5%+), no training needed
    Cons: Higher memory usage than IVF

    HNSW (Hierarchical Navigable Small World) creates a multi-layer graph
    structure that enables efficient nearest neighbor search.
    """
    print(f"Building IndexHNSWFlat (fast approximate search)...")
    print(f"  M={HNSW_M}, efConstruction={HNSW_EF_CONSTRUCTION}")

    index = faiss.IndexHNSWFlat(dimension, HNSW_M)
    index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
    index.add(embeddings)

    # Set search-time parameters
    index.hnsw.efSearch = HNSW_EF_SEARCH
    print(f"  efSearch={HNSW_EF_SEARCH} (can be adjusted at search time)")

    return index


def build_ivf_pq_index(embeddings: np.ndarray, dimension: int) -> faiss.Index:
    """
    Build IVF-PQ index for memory-efficient search.

    Best for: >100K cards
    Pros: Very memory efficient, scalable, good recall with tuning
    Cons: Requires training, slightly lower recall than HNSW

    IVF (Inverted File) partitions the space into clusters, then uses
    Product Quantization (PQ) to compress vectors for efficiency.
    """
    print(f"Building IndexIVFPQ (memory-efficient search)...")
    print(f"  nlist={IVF_NLIST}, nprobe={IVF_NPROBE}, m={IVF_M}, nbits={IVF_NBITS}")

    # Create quantizer for clustering
    quantizer = faiss.IndexFlatIP(dimension)

    # Create IVF-PQ index
    index = faiss.IndexIVFPQ(
        quantizer,
        dimension,
        IVF_NLIST,  # Number of clusters
        IVF_M,      # Number of subquantizers
        IVF_NBITS   # Bits per subquantizer
    )

    # Train the index (required for IVF)
    print(f"Training index on {len(embeddings)} vectors...")
    train_start = time.time()
    index.train(embeddings)
    train_time = time.time() - train_start
    print(f"  Training completed in {train_time:.2f}s")

    # Add vectors
    index.add(embeddings)

    # Set search parameters
    index.nprobe = IVF_NPROBE
    print(f"  nprobe={IVF_NPROBE} (can be adjusted at search time)")

    return index


def build_optimal_index(embeddings: np.ndarray, dimension: int) -> tuple[faiss.Index, str, dict]:
    """
    Automatically choose the best index type based on dataset size.

    Returns:
        index: FAISS index object
        index_type: String description of index type
        config: Dictionary of index configuration
    """
    n_vectors = len(embeddings)

    print(f"\nDataset size: {n_vectors:,} vectors")
    print("Selecting optimal index type...")

    if n_vectors < SIZE_THRESHOLD_HNSW:
        # Small dataset: use exact search
        index = build_flat_index(embeddings, dimension)
        index_type = "IndexFlatIP"
        config = {
            "type": "flat",
            "exact_search": True,
            "expected_recall": 1.00,
            "complexity": "O(n)",
        }

    elif n_vectors < SIZE_THRESHOLD_IVF:
        # Medium dataset: use HNSW
        index = build_hnsw_index(embeddings, dimension)
        index_type = "IndexHNSWFlat"
        config = {
            "type": "hnsw",
            "exact_search": False,
            "expected_recall": 0.995,
            "complexity": "O(log n)",
            "M": HNSW_M,
            "efConstruction": HNSW_EF_CONSTRUCTION,
            "efSearch": HNSW_EF_SEARCH,
        }

    else:
        # Large dataset: use IVF-PQ
        index = build_ivf_pq_index(embeddings, dimension)
        index_type = "IndexIVFPQ"
        config = {
            "type": "ivf_pq",
            "exact_search": False,
            "expected_recall": 0.970,
            "complexity": "O(√n)",
            "nlist": IVF_NLIST,
            "nprobe": IVF_NPROBE,
            "m": IVF_M,
            "nbits": IVF_NBITS,
        }

    return index, index_type, config


def benchmark_index(index: faiss.Index, embeddings: np.ndarray, k: int = 20, n_queries: int = 100):
    """
    Benchmark index performance with sample queries.

    Args:
        index: FAISS index to benchmark
        embeddings: Full embedding dataset
        k: Number of neighbors to retrieve
        n_queries: Number of test queries
    """
    print(f"\nBenchmarking index performance...")

    # Sample random queries
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

    # Calculate recall (percentage of queries where true match is in top-k)
    recall_sum = 0
    for i, query_id in enumerate(query_ids):
        if query_id in indices[i]:
            recall_sum += 1

    recall = recall_sum / len(queries)

    print(f"  Queries: {len(queries)}")
    print(f"  Total time: {search_time:.3f}s")
    print(f"  Avg time per query: {avg_time_ms:.2f}ms")
    print(f"  Self-recall (top-{k}): {recall:.1%}")

    return {
        "avg_latency_ms": avg_time_ms,
        "recall": recall,
        "queries": len(queries),
    }


def main():
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"ULTIMATE OPTIMIZED FAISS Index Builder")
    print(f"Adaptive strategy based on dataset size")
    print(f"{'='*80}\n")

    embeddings_dir = ARTIFACTS_DIR / "embeddings" / f"{GAME}-dinov2"
    embeddings_file = embeddings_dir / "embeddings.npy"
    metadata_file = embeddings_dir / "metadata.jsonl"

    if not embeddings_file.exists():
        print(f"ERROR: No embeddings found at {embeddings_file}")
        print("Run the embedder first:")
        print("  python services/embedder/bin/embed_onepiece_dinov2_optimized.py")
        return

    # Load embeddings
    print(f"Loading embeddings from {embeddings_file}...")
    embeddings = np.load(embeddings_file)
    print(f"Loaded {embeddings.shape[0]:,} embeddings with dimension {embeddings.shape[1]}")

    # Verify normalization
    norms = np.linalg.norm(embeddings, axis=1)
    avg_norm = np.mean(norms)
    print(f"Average embedding norm: {avg_norm:.4f}")

    if abs(avg_norm - 1.0) > 0.01:
        print("WARNING: Embeddings not normalized! Normalizing now...")
        faiss.normalize_L2(embeddings)

    # Load metadata
    metadata = []
    with open(metadata_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))

    print(f"Loaded {len(metadata):,} metadata entries")

    # Build optimal index
    dimension = embeddings.shape[1]
    index, index_type, config = build_optimal_index(embeddings, dimension)

    print(f"\nIndex built successfully!")
    print(f"  Type: {index_type}")
    print(f"  Total vectors: {index.ntotal:,}")

    # Benchmark
    benchmark_results = benchmark_index(index, embeddings, k=20, n_queries=100)

    # Save index
    output_dir = FAISS_DIR / f"{GAME}-dinov2"
    output_dir.mkdir(parents=True, exist_ok=True)

    index_file = output_dir / "index.faiss"
    ids_file = output_dir / "ids.json"
    config_file = output_dir / "index_config.json"

    print(f"\nSaving index...")
    faiss.write_index(index, str(index_file))

    # Save card IDs in same order as embeddings
    ids = [m["id"] for m in metadata]
    with open(ids_file, 'w', encoding='utf-8') as f:
        json.dump(ids, f)

    # Save index configuration
    full_config = {
        "index_type": index_type,
        "dimension": dimension,
        "total_vectors": index.ntotal,
        "config": config,
        "benchmark": benchmark_results,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(full_config, f, indent=2)

    total_time = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Index type: {index_type}")
    print(f"Total vectors: {index.ntotal:,}")
    print(f"Dimension: {dimension}")
    print(f"Expected recall: {config['expected_recall']:.1%}")
    print(f"Search complexity: {config['complexity']}")
    print(f"\nBenchmark Results:")
    print(f"  Avg latency: {benchmark_results['avg_latency_ms']:.2f}ms")
    print(f"  Self-recall: {benchmark_results['recall']:.1%}")
    print(f"\nBuild time: {total_time:.2f}s")
    print(f"\nSaved to:")
    print(f"  {index_file}")
    print(f"  {ids_file}")
    print(f"  {config_file}")
    print(f"{'='*80}\n")

    # Print usage tips
    print("USAGE TIPS:")
    if index_type == "IndexHNSWFlat":
        print("  - Adjust search quality with: index.hnsw.efSearch = X")
        print("    Higher values = better recall but slower (try 32-128)")
    elif index_type == "IndexIVFPQ":
        print("  - Adjust search quality with: index.nprobe = X")
        print("    Higher values = better recall but slower (try 16-64)")
    print("\n")


if __name__ == "__main__":
    main()
