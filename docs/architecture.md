# CardFlux Architecture

## Overview

CardFlux is an **offline-first, real-time desktop TCG card scanner** with sub-second identification and printing-level accuracy across multiple trading card games (Magic: The Gathering, Pokémon, Yu-Gi-Oh!, One Piece, Digimon, and extensible to others).

The system enables card shops to scan cards continuously by sliding them under an overhead camera, with **instant identification (<400ms from card placement to result)**.

## Design Goals

- **Real-Time Scanning**: Continuous video stream processing at 30 FPS with automatic card detection
- **Instant Results**: <400ms from card placement to identification display
- **Offline-First**: All scanning happens locally after initial artifact download
- **Printing-Level Accuracy**: Distinguish between reprints, alternate arts, and language variants
- **Shop-Optimized**: Designed for high-throughput card shop workflows (hundreds of cards per session)
- **Flexible**: Config-driven support for any TCG provided by tcgcsv.com
- **Future-Proof**: Architected for buylists, inventory, POS, label printing, condition grading assist

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLOUD PIPELINE                          │
│                  (ECS Fargate, daily 13:00 PDT)                 │
├─────────────────────────────────────────────────────────────────┤
│ 1. Ingest       → Fetch tcgcsv.com CSVs (per-game)             │
│ 2. Normalize    → Deterministic card_id (SHA1), curate JSON    │
│ 3. Fetch Images → Download/cache with ETag, normalize sRGB     │
│ 4. Embed        → DINOv2-small ONNX (384-dim, L2-normalized)   │
│ 5. Index        → FAISS IVF-PQ per-set shards                  │
│ 6. Metadata     → SQLite snapshot (cards + prices)             │
│ 7. Publish      → Generate manifests, upload to S3/CloudFront  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    artifacts via CDN
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DESKTOP APP (REAL-TIME)                       │
│                     (Electron, offline)                         │
├─────────────────────────────────────────────────────────────────┤
│ SYNC (daily):                                                   │
│   → Download manifests, verify SHA256                           │
│                                                                 │
│ SCAN (continuous video stream):                                │
│   1. Camera Feed      → 30 FPS video stream                    │
│   2. Card Detection   → OpenCV contour detection (<16ms)       │
│   3. Stabilization    → Wait 200ms for card to settle          │
│   4. Crop & Align     → Perspective transform to standard size │
│   5. Embedding        → DINOv2 ONNX (GPU: <20ms)               │
│   6. Retrieval        → FAISS search (<30ms)                   │
│   7. OCR              → Tesseract on region crops (<80ms)      │
│   8. Verification     → ORB feature matching (<60ms)           │
│   9. Fusion           → Score: 0.5E + 0.2O + 0.3G              │
│  10. Lookup           → SQLite query (<10ms)                   │
│  11. Display          → Show result + beep (<10ms)             │
│                                                                 │
│ Total: <400ms from card placement to result display            │
└─────────────────────────────────────────────────────────────────┘
```

## Real-Time Scanning Pipeline (Detailed)

### Stage 1: Camera Feed & Frame Capture (Continuous)

```
Overhead Camera (1080p @ 30 FPS)
        ↓
Electron Renderer (Video Element)
        ↓
Canvas Frame Capture (every 33ms)
        ↓
Send to Main Process via IPC (JPEG buffer)
        ↓
Frame Buffer (skip frames if processing busy)
```

**Performance**: ~3-5ms per frame (negligible overhead)

### Stage 2: Card Detection (Fast Path - Every Frame)

```
Frame Buffer
        ↓
OpenCV Card Detector
  1. Background subtraction (diff from empty scanner surface)
  2. Convert to grayscale + threshold
  3. Find contours
  4. Filter by area (min 10,000 px² for card)
  5. Find largest 4-sided polygon (card edges)
        ↓
Card Detected?
  ├─ NO  → Continue monitoring next frame
  └─ YES → Extract bounding box + trigger Stage 3
```

**Performance**: 10-16ms per frame (60+ FPS capable)

**Optimization**: Run on every frame without blocking UI

### Stage 3: Stabilization & Debouncing

```
Card Detected
        ↓
First detection? → Start stability timer (200ms)
        ↓
Card still detected after 200ms?
  ├─ NO  → Reset (card was moving/removed)
  └─ YES → Card is stable, proceed to identification
        ↓
Check debounce: Same card scanned <2s ago?
  ├─ YES → Skip (prevent re-scanning same card)
  └─ NO  → Proceed to Stage 4
```

**Performance**: 200ms intentional delay (user perception: card must settle)

### Stage 4: Crop & Perspective Correction

```
Stable Card Detection (bounding box + 4 corners)
        ↓
Order corners: [top-left, top-right, bottom-right, bottom-left]
        ↓
Compute perspective transform matrix
        ↓
Warp image to standard size (600×840 px, 2.5"×3.5" at 240 DPI)
        ↓
Result: Straight-on, aligned card image
```

**Performance**: ~5ms (OpenCV warpPerspective is highly optimized)

**Why this matters**: Removes camera angle distortion, ensures consistent input to embedding model

### Stage 5: Embedding (DINOv2)

```
Aligned Card Image (600×840)
        ↓
Preprocessing:
  1. Resize to 256×256 (bilinear)
  2. Center crop to 224×224
  3. Normalize: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]
  4. Convert to NCHW tensor (batch, channels, height, width)
        ↓
ONNX Runtime Inference (GPU-accelerated)
  Model: DINOv2-small
  Input: [1, 3, 224, 224] float32
  Output: [1, 384] float32
        ↓
L2-Normalize to unit vector (for cosine similarity)
        ↓
384-dimensional embedding: [0.23, -0.15, 0.47, ..., 0.12]
```

**Performance**:
- CPU: ~80ms (Intel i7)
- GPU (CUDA/DirectML): ~15ms
- GPU (Metal/CoreML): ~20ms

**Optimization**: Use GPU via ONNX Runtime execution providers (DirectML on Windows, CoreML on macOS)

### Stage 6: FAISS Retrieval

```
Query Embedding (384-dim unit vector)
        ↓
Search all loaded set indexes in parallel
  For each set:
    1. FAISS IVF-PQ search (nprobe=16)
    2. Return top-K candidates (K=20) with L2 distances
        ↓
Aggregate results across sets
        ↓
Convert L2 distance to cosine similarity:
  cosine_sim = 1 - (L2_distance² / 2)
        ↓
Sort by similarity, take top-20 candidates
        ↓
Look up card_ids from ids_shard_{set}.bin
```

**Performance**:
- Single set: ~5ms
- 10 sets in parallel: ~30ms
- All MTG sets (~300): ~50ms (load sets on-demand to save RAM)

**Optimization**: Keep frequently-used sets (recent releases) in memory, lazy-load older sets

### Stage 7: OCR Disambiguation (Parallel with Stage 8)

```
Aligned Card Image (600×840)
        ↓
Extract region crops (per-game config):
  - Set code region (e.g., bottom-left, 60×30 px)
  - Collector number region (e.g., bottom-right, 60×30 px)
        ↓
Run Tesseract in parallel (worker pool)
  Thread 1: OCR set code → "WOE" (confidence: 0.92)
  Thread 2: OCR collector number → "001" (confidence: 0.88)
        ↓
Normalize with per-game regex:
  MTG set_code: ^[A-Z0-9]{3,5}$
  MTG collector_number: ^\d+[a-z]?$
        ↓
Filter FAISS candidates:
  Keep only candidates matching OCR results
```

**Performance**: ~80ms (parallel Tesseract on 2 regions)

**Accuracy**: 95%+ on clean cards, degrades on damaged/worn text

### Stage 8: Geometric Verification (Parallel with Stage 7)

```
Query Image (aligned card)
        ↓
For each top-5 FAISS candidate:
  1. Load reference image from disk
  2. Extract ORB features (query: 500 kp, reference: 500 kp)
  3. Match features with BFMatcher (Hamming distance)
  4. Filter matches with ratio test (Lowe's ratio: 0.75)
  5. Compute homography with RANSAC
  6. Calculate inlier ratio (% of matches that fit homography)
  7. Calculate reprojection error
        ↓
Verification Score:
  - Inlier ratio ≥ 0.2 → Pass
  - Reprojection error ≤ 2.5px → Pass
  - Combined score: (inlier_ratio * 100) / (1 + reprojection_error)
```

**Performance**: ~60ms for 5 candidates (parallelized)

**Why this matters**: Catches cases where embedding + OCR agree but wrong card (e.g., two cards with same art, different set symbol)

### Stage 9: Fusion Scoring

```
For each candidate after OCR filtering:
  embedding_score = cosine_similarity (from FAISS)
  ocr_score = (set_code_confidence + collector_number_confidence) / 2
  geometry_score = verification_score (from ORB)

  final_score = 0.5 * embedding_score
              + 0.2 * ocr_score
              + 0.3 * geometry_score
        ↓
Sort candidates by final_score
        ↓
Auto-accept if:
  - final_score ≥ 0.85 (high confidence) OR
  - margin ≥ 0.15 (top1_score - top2_score)
        ↓
If auto-accepted: Display result immediately
Else: Show top-5 for user selection
```

**Performance**: <5ms (simple arithmetic)

**Tuning**: Weights (0.5, 0.2, 0.3) calibrated from real-world testing, adjustable per-game

### Stage 10: Metadata Lookup

```
Winning card_id (e.g., "a3f2b1c4d5e6...")
        ↓
SQLite Query:
  SELECT card_id, name, set_name, set_code, collector_number,
         tcgplayer_market, tcgplayer_low, cardmarket_trend
  FROM cards
  WHERE card_id = ?
        ↓
Result: Full card metadata + prices
```

**Performance**: <5ms (indexed query, in-memory database)

### Stage 11: Display Result

```
Card Metadata + Confidence Score
        ↓
Update UI (React component):
  - Card name (large text)
  - Set name + code (WOE #001)
  - Prices (market: $0.25, low: $0.10)
  - Confidence badge (green if ≥0.85, yellow if ≥0.70, red if <0.70)
  - Processing time breakdown (hover for details)
        ↓
Visual Feedback:
  - Green bounding box around card in video feed
  - Success beep sound
  - Optional: Add to session scan log
        ↓
Wait for card removal
        ↓
Card removed? → Clear UI, reset state, ready for next card
```

**Performance**: <10ms (DOM update + audio playback)

## Performance Budget (Real-Time Scanning)

| Stage                   | CPU (i7)  | GPU (GTX 1060) | Notes                          |
|-------------------------|-----------|----------------|--------------------------------|
| Card detection          | 10-16ms   | 10-16ms        | Runs every frame (OpenCV)      |
| Stabilization wait      | 200ms     | 200ms          | Intentional delay              |
| Crop & align            | 5ms       | 5ms            | OpenCV warpPerspective         |
| **Embedding**           | **80ms**  | **15ms**       | **DINOv2 ONNX (GPU critical)** |
| FAISS search            | 30ms      | 30ms           | In-memory, per-set shards      |
| OCR (parallel)          | 80ms      | 80ms           | Tesseract (CPU-bound)          |
| Geometric verify        | 60ms      | 60ms           | ORB + RANSAC (OpenCV)          |
| Fusion scoring          | 5ms       | 5ms            | Simple arithmetic              |
| SQLite lookup           | 5ms       | 5ms            | Indexed query                  |
| UI update               | 10ms      | 10ms           | React render + audio           |
| **Total (CPU)**         | **~475ms**| **~410ms**     | **Target: <400ms with GPU**    |

**Hardware Requirements** (for <400ms performance):
- **CPU**: Intel i7-10700 / AMD Ryzen 7 3700X or better (8+ cores)
- **GPU**: NVIDIA GTX 1060 / AMD RX 580 or better (for GPU-accelerated inference)
- **RAM**: 16GB (FAISS indexes + SQLite in memory)
- **Camera**: 1080p USB camera at 30 FPS (Logitech C920 or equivalent)

## Hardware Setup (Recommended)

### Overhead Camera Mount

```
                    ┌─────────────────┐
                    │  Camera (1080p) │
                    │  + Ring Light   │
                    └────────┬────────┘
                             │
                         12-18"
                             │
         ┌───────────────────┼───────────────────┐
         │                   ↓                   │
         │         ┌──────────────────┐          │
         │         │                  │          │
         │         │   Card Surface   │          │
         │         │  (Black/Green    │          │
         │         │   Mat)           │          │
         │         │                  │          │
         │         └──────────────────┘          │
         │                                       │
         └───────────────────────────────────────┘
                     Desktop Surface
```

**Components**:
1. **Camera**: Logitech C920 HD Pro (1080p @ 30 FPS, ~$70)
   - Auto-focus (critical for varying card positions)
   - Good low-light performance
   - USB 2.0/3.0 compatible

2. **Mount**: Articulating arm mount (e.g., NEEWER 26" arm, ~$40)
   - Height: 12-18 inches above card surface
   - Adjustable angle (straight down, slight tilt)

3. **Lighting**: LED ring light (attach to camera or separate, ~$25)
   - Diffused light (eliminates glare on foil cards)
   - Color temperature: 5000-5500K (daylight)
   - Dimmable (adjust for different card finishes)

4. **Background Mat**: Black or chroma-green mat (8"×10", ~$10)
   - High contrast with card edges (aids detection)
   - Non-reflective surface
   - Optional: Grid lines for card alignment

**Total Setup Cost**: ~$145

### Alternative: Document Scanner Conversion

Some shops already have document scanners. You can:
1. Use scanner's built-in camera (if it outputs video stream)
2. OR: Mount USB camera in scanner housing
3. Software detects card presence (same detection pipeline)

## Data Flow

### Cloud Pipeline (Daily at 13:00 PDT)

**Input**: tcgcsv.com per-game CSVs (cards, sets, prices)

**Pipeline Steps**:

1. **Ingest & Normalize** (`services/ingest/bin/normalize.ts`):
   - Fetch CSVs for all games (env: `TCG_LIST=mtg,pokemon,yugioh,onepiece,digimon`)
   - Compute deterministic `card_id = SHA1(game_id|set_code|collector_number|language|artwork_hash?)`
   - Output: `data/curated/{game}/cards.json`

2. **Fetch Images** (`services/ingest/bin/fetch_images.ts`):
   - Download images from `image_url` with ETag/If-Modified-Since caching
   - Normalize to sRGB colorspace (consistent preprocessing)
   - Generate thumbnails (320x448, sharp)
   - Directory: `data/images/{game}/{set_code}/{lang}/{collector_number}__{card_id}/`
   - Files: `canonical.jpg`, `thumb.jpg`, `meta.json` (SHA256)

3. **Embed** (`services/embedder/bin/embed_cards.py`):
   - DINOv2-small ONNX model (384-dim output)
   - Preprocessing: resize 256×256 → center crop 224×224 → normalize (ImageNet stats)
   - L2-normalize output to unit vector (cosine similarity via dot product)
   - Output: `embedding.npy` (float32, 384-dim)

4. **Index** (`services/indexer/bin/build_faiss.py`):
   - Per-set FAISS index: `IVF{nlist},PQ{m}x{nbits}`
   - Defaults: `nlist=4096`, `m=8`, `nbits=8` (tuned per-game via config)
   - Train on set vectors (min 10×nlist), add all
   - Output per set:
     - `artifacts/faiss/{game}/{version}/index_ivfpq_shard_{set}.faiss`
     - `artifacts/faiss/{game}/{version}/ids_shard_{set}.bin` (20-byte SHA1 per vector)
     - `artifacts/faiss/{game}/{version}/meta_shard_{set}.json`

5. **Metadata** (`services/ingest/bin/build_sqlite.ts`):
   - SQLite snapshot: `artifacts/metadata/{version}/cards.sqlite.ro`
   - Schema: `cards(card_id PRIMARY KEY, game_id, set_code, set_name, collector_number, name, language)`
   - Index: `(game_id, set_code, collector_number)`
   - WAL mode, checkpoint on close, atomic write (.tmp → rename)

6. **Publish** (`services/publisher/bin/generate_manifests.ts`):
   - Compute SHA256 for all artifacts
   - Generate `artifacts/manifests/index_manifest.json`:
     - Schema version, games, shards[], metadata_snapshot, models_manifest
     - All paths use POSIX format (cross-platform)
   - Validate with Zod schema (fail-fast on errors)
   - Upload to S3 → invalidate CloudFront cache

**Output**: CDN-hosted artifacts (manifests, FAISS indexes, SQLite, models)

### Desktop App (Real-Time Scanning)

**Sync Phase** (on app launch or manual trigger):

1. Fetch `index_manifest.json` from CDN
2. Parse and validate with Zod schema
3. Compare local SHA256 hashes; download only changed files
4. Verify integrity (SHA256) before replacing local files
5. Load FAISS indexes and SQLite into memory/disk

**Scan Phase** (continuous video stream):

1. **Camera Feed**: 30 FPS video stream via `navigator.mediaDevices.getUserMedia()`
2. **Frame Capture**: Canvas drawImage() every 33ms → JPEG buffer → IPC to main process
3. **Card Detection**: OpenCV contour detection (background subtraction + polygon fitting)
4. **Stabilization**: Wait 200ms for card to settle (prevent false triggers)
5. **Crop & Align**: Perspective transform to 600×840 standard size
6. **Embedding**: DINOv2 ONNX Runtime (GPU-accelerated) → 384-dim unit vector
7. **Retrieval**: FAISS search across per-set indexes → top-20 candidates
8. **OCR**: Tesseract on region crops (set code, collector number) in parallel
9. **Verification**: ORB feature matching + RANSAC homography (top-5 candidates)
10. **Fusion**: Weighted score (0.5×embedding + 0.2×OCR + 0.3×geometry)
11. **Lookup**: SQLite query by card_id → metadata + prices
12. **Display**: Update UI with result, beep, show green bounding box
13. **Wait for Removal**: Monitor for card removal → reset state

## Per-Game Configuration

All TCG-specific logic is externalized to JSON configs (`packages/config/src/{game}.json`):

- **Regex patterns**: `collector_number_regex`, `set_code_regex`
- **OCR regions**: Normalized coordinates (0–1) for set code, collector number, game-specific fields
- **Index parameters**: `nlist`, `m`, `nbits` (FAISS tuning per set size)
- **Shard strategy**: `per_set` (future: `per_rarity`, `by_size`)

**Adding a new TCG**:

1. Create `packages/config/src/{game}.json` (copy template from existing)
2. Update `TCG_LIST` env var in pipeline
3. No code changes required (config-driven ingestion, indexing, scanning)

## Technology Stack

**Cloud**:
- AWS: ECS Fargate (pipeline), EventBridge (scheduler), S3 (storage), CloudFront (CDN)
- IaC: AWS CDK (TypeScript)
- Python 3.11: FAISS, numpy, ONNX Runtime (batch embeddings)
- Node 20: TypeScript services (ingest, metadata, manifests)

**Desktop**:
- Electron 28: Cross-platform (Windows/macOS), camera access, IPC
- React 18: UI components (video feed, results panel)
- ONNX Runtime Node: DINOv2 inference with GPU support (DirectML/CoreML)
- OpenCV (opencv4nodejs): Card detection, perspective transform, ORB verification
- Tesseract.js: OCR (pure JavaScript, no native dependencies)
- better-sqlite3: Metadata queries
- Node-FAISS (or Python subprocess): FAISS search

**Monorepo**:
- pnpm 9 (workspaces), Turbo (build caching), TypeScript 5.3
- ESLint + Prettier (code quality)
- Zod (runtime schema validation)

## Deployment

**Pipeline**:

1. Build Docker image with Node 20 + Python 3.11 + FAISS + ONNX Runtime
2. Push to ECR: `cardflux-pipeline:latest`
3. ECS Fargate task runs daily at 13:00 PDT (EventBridge cron: `0 20 * * ? *` UTC)
4. Task writes artifacts to S3, publishes manifests
5. CloudFront invalidation triggers desktop updates

**Desktop**:

1. Build Electron app: `npm run build` (electron-builder)
2. Sign binaries (Windows: Authenticode; macOS: notarization)
3. Distribute via GitHub Releases or auto-update server

## Future Features

- **Buylists**: Define per-card buy prices; batch scan inventories → generate purchase orders
- **Inventory Management**: Multi-user; track quantity, condition, location
- **POS Integration**: Square/Stripe; barcode printing
- **Label Printing**: Dymo/Brother; custom templates
- **Condition Assist**: ML-based surface/edge/corner grading
- **Connectors**: TCGPlayer/eBay/Cardmarket APIs for pricing, listing, order fulfillment
- **YOLOv8 Detection**: Replace OpenCV with learned card detection (higher accuracy, GPU-accelerated)
- **SuperGlue**: Replace ORB with learned feature matching (higher accuracy, slower)

## Performance Optimization Roadmap

### Phase 1 (Current): OpenCV Detection
- Background subtraction + contour detection
- CPU-based, 10-16ms per frame
- Good enough for 30 FPS monitoring

### Phase 2: GPU-Accelerated Detection
- Train YOLOv8-nano on card detection dataset
- ONNX export, run on GPU alongside DINOv2
- <5ms per frame, enables 120+ FPS monitoring

### Phase 3: End-to-End GPU Pipeline
- All CV operations on GPU (detection, embedding, verification)
- Minimize CPU↔GPU transfers
- Target: <200ms total pipeline

### Phase 4: Multi-Card Scanning
- Detect and identify multiple cards simultaneously
- Batch embedding inference (process 4 cards in ~20ms vs. 4×20ms)
- Parallel FAISS searches
- Target: 500+ cards/hour throughput

---

**Document Version**: 2.0 (Real-Time Scanning)
**Last Updated**: 2025-10-01
**Author**: CardFlux Engineering
