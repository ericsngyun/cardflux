# CI FAISS Builder Fix - 2025-11-06

## Problem

GitHub Actions CI was failing at the "Run incremental update" step with a Python FileNotFoundError:

```
FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/work/cardflux/cardflux/artifacts/embeddings'
```

The error occurred in the `build_faiss.py` script when it tried to iterate over the `artifacts/embeddings/` directory to find games to index.

## Root Cause

The FAISS index builder (`services/indexer/bin/build_faiss.py`) expects a specific directory structure:

```
artifacts/embeddings/{game_id}/
  ├── embeddings.npy
  └── metadata.jsonl
```

However, the **One Piece-specific embedder** (`services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py`) builds the FAISS index **DIRECTLY** during the embedding process and writes to:

```
artifacts/metadata/embeddings/{game_id}/
  └── metadata.jsonl
artifacts/faiss/{game_id}-dinov2/
  ├── index.faiss
  └── ids.json
```

**The game-specific embedder does NOT create an `artifacts/embeddings/` directory or intermediate `embeddings.npy` file.**

### Why This Architecture?

The One Piece embedder combines preprocessing, embedding, and indexing into a single optimized pipeline:

1. **Preprocessing**: Bilateral filter + contrast enhancement (CRITICAL for consistency)
2. **Embedding**: DINOv2 384-dim vectors with FP16 optimization
3. **Indexing**: FAISS IndexFlatIP built inline (no intermediate NPY file)

This is more efficient than the generic pipeline which separates these steps.

### Timeline of Events

1. **Local development**: We ran the One Piece embedder which created indices directly
2. **Git commit**: Pushed curated data, FAISS indices, and keypoints to Git LFS
3. **CI incremental pipeline**: Tried to run `build_faiss.py` as part of the pipeline
4. **Failure**: `build_faiss.py` looked for `artifacts/embeddings/` which doesn't exist

## Solution

Modified `services/indexer/bin/build_faiss.py` to gracefully skip when no games are found:

### Before

```python
# Find games
if args.game:
    games = [args.game]
else:
    games = [d.name for d in EMBEDDINGS_DIR.iterdir() if d.is_dir()]

if not games:
    print("\nNo games found in artifacts/embeddings/")
    print("Run: python services/embedder/bin/embed_cards.py")
    sys.exit(1)  # ERROR - causes pipeline to fail
```

### After

```python
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
    sys.exit(0)  # SUCCESS - pipeline continues
```

### Key Changes

1. **Check directory existence**: Added `if not EMBEDDINGS_DIR.exists()` before trying to iterate
2. **Graceful exit**: Changed `sys.exit(1)` to `sys.exit(0)` - this is a normal condition, not an error
3. **Informative message**: Explains why no games were found and that this is expected behavior
4. **Windows compatibility**: Used `[INFO]` instead of emoji (Unicode encoding issues on Windows)

## Why This Works

The incremental pipeline (`scripts/make/run-pipeline-incremental.mjs`) runs these steps:

1. ✅ **scrape** - incremental TCGPlayer scrape (skips if no curated data)
2. ✅ **normalize** - normalize data (skips if no curated data)
3. ✅ **images** - download images (skips if no curated data)
4. ✅ **sqlite** - build metadata database (skips if no curated data)
5. ✅ **embed** - generate embeddings (skips if no curated data)
6. ✅ **index** - build FAISS index (**NOW skips if no embeddings directory**)
7. ✅ **manifests** - generate manifests

**Before this fix**: Step 6 would FAIL with exit code 1, stopping the entire pipeline

**After this fix**: Step 6 exits with code 0 (success), allowing the pipeline to complete

## When FAISS Builder IS Used

The generic FAISS builder is still used for:

1. **Multi-game support** (future): When we add Pokemon, Magic, etc. using the generic embedder
2. **Full rebuilds**: When explicitly running `python services/indexer/bin/build_faiss.py --game <game>`
3. **Generic pipeline**: When using `services/embedder/bin/embed_cards.py` (creates intermediate NPY files)

## Architecture Implications

### Current State (One Piece Only)

```
Data Flow:
TCGPlayer API → Scraper → Curated JSONL → Images
                                         ↓
                            One Piece Embedder (all-in-one)
                                         ↓
                            ┌────────────┴────────────┐
                            ↓                         ↓
                    FAISS Index              Metadata JSONL
            (artifacts/faiss/)         (artifacts/metadata/)
```

**FAISS builder is NOT used** - One Piece embedder builds index inline

### Future State (Multi-Game)

```
Data Flow:
TCGPlayer API → Scraper → Curated JSONL → Images
                                         ↓
                            Generic Embedder
                                         ↓
                            Intermediate NPY files
                            (artifacts/embeddings/)
                                         ↓
                                  FAISS Builder
                                         ↓
                            ┌────────────┴────────────┐
                            ↓                         ↓
                    FAISS Index              Metadata JSONL
```

**FAISS builder IS used** - Generic pipeline separates embedding and indexing

## Testing

Verified locally that the fix works:

```bash
$ python services/indexer/bin/build_faiss.py

================================================================================
PRODUCTION FAISS INDEX BUILDER
IndexFlatIP (Exact Matching) with Sealed Product Filtering
================================================================================

[INFO] No games found in artifacts/embeddings/
This is expected when using game-specific embedders (e.g., embed_onepiece_dinov2_with_preprocessing.py)
which build FAISS indices directly without intermediate embeddings directory.

Skipping FAISS index building step.

$ echo $?
0  # Exit code 0 = success
```

## Prevention

To prevent this issue in the future:

### 1. Document Architecture Clearly

Add comments to `run-pipeline-incremental.mjs` explaining when each step runs:

```javascript
const STEPS = [
  { name: 'scrape', cmd: 'pnpm', args: ['tcgplayer:scrape:incremental'] },
  { name: 'normalize', cmd: 'pnpm', args: ['pipeline:normalize:incremental'] },
  { name: 'images', cmd: 'pnpm', args: ['pipeline:fetch-images:incremental'] },
  { name: 'sqlite', cmd: 'pnpm', args: ['pipeline:metadata'] },
  { name: 'embed', cmd: 'pnpm', args: ['pipeline:embed:incremental'] },
  // NOTE: Generic FAISS builder - skips if using game-specific embedders
  { name: 'index', cmd: 'pnpm', args: ['pipeline:index'] },
  { name: 'manifests', cmd: 'pnpm', args: ['pipeline:manifests'] },
];
```

### 2. Always Exit 0 for "No Work" Conditions

Pipeline scripts should distinguish between:
- **Error conditions**: Exit 1 (file corruption, API failure, etc.)
- **No work conditions**: Exit 0 (no games to process, already up-to-date, etc.)

### 3. Test Pipeline in CI Environment

Before adding new games, test the incremental pipeline in CI to ensure all steps handle "no data" gracefully.

## Related Issues

This fix resolves the third GitHub Actions CI failure after:
1. **TypeScript module resolution** (`CI_TYPESCRIPT_FIX.md`) - Fixed by updating to node16
2. **Memory exhaustion** (`CI_MEMORY_FIX.md`) - Fixed by filtering to games with curated data
3. **Missing embeddings directory** (THIS FIX) - Fixed by graceful exit when no games found

## Key Takeaway

**Pipeline scripts should distinguish between "error" and "no work" conditions.**

Exit code 1 = Error (stop pipeline)
Exit code 0 = Success or no work needed (continue pipeline)

**Always check if resources exist before trying to access them, and exit gracefully if they don't.**

---

**Fixed By**: Claude Code (Sonnet 4.5)
**Date**: 2025-11-06
**Impact**: Allows CI incremental pipeline to complete successfully when using game-specific embedders
**Files Changed**: 1 (`services/indexer/bin/build_faiss.py`)
