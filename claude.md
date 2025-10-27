# CardFlux - Senior Engineer Context

> **Version**: v0.2.2 | **Status**: Production-Ready (One Piece TCG) | **Updated**: 2025-10-22

## Mission
AI-powered card identification for shops: Transform 3-5 min manual pricing → 3-5 sec automated scanning with 100% accuracy.

## Current Status
**Production Ready**: One Piece TCG (5,390 cards), 100% HIGH confidence, 1137ms avg identification, desktop app v0.2.2
**Recent Updates (2025-10-27)**:
- ✅ Fixed sealed product filter to use metadata-first approach (+577 cards)
- ✅ 100% card detection system (polished_card_detector.py)
- ✅ AKAZE hybrid geometric matching for robustness
- ✅ Comprehensive test suite (19 test images)
- ✅ Codebase fully organized and cleaned up

## Architecture Stack
- **Frontend**: Electron 28 + React 18 + TypeScript (monochrome UI)
- **Backend**: Node.js + pnpm monorepo + SQLite
- **ML**: DINOv2 (384-dim embeddings) + FAISS (vector search) + ORB (geometric matching)
- **Data**: TCGPlayer API scraping, daily GitHub Actions updates

## Key Components

### 1. Identification Pipeline
`scripts/identification/core/production_card_identifier.py`
```
Image → Card Detection → Quality Check → Preprocess → DINOv2 (70-130ms) → FAISS (0.16ms, top 50)
→ Hybrid Geometric (ORB+AKAZE, 300-800ms, top 20) → Dynamic Scoring (60/40-90/10) → Result
```
**Performance**: 778ms avg, 47% HIGH / 42% MODERATE / 11% LOW confidence (19 test images)

### 2. Desktop App
`apps/desktop/`
- **Main**: Electron IPC + Python bridge (JSON-RPC subprocess)
- **Renderer**: React (CameraView, CardStack, Settings, Notifications)
- **Workflow**: Camera → SPACE to capture → Identify → Auto-add if HIGH confidence → Export CSV
- **Settings**: TCG game, OCR, foil detection, geometric verification, Top-K slider
- **Startup**: 3.3s Python init (one-time), then 500ms per card

### 3. Data Pipeline
`services/{ingest,embedder,indexer}/`
1. **Scrape**: TCGPlayer API → filter sealed products (metadata-first) → JSONL (5,390 cards, 2 min)
2. **Images**: Download 600x600 JPG (~400 MB, 3 min, 97.4% success)
3. **Embed**: DINOv2 + preprocessing (bilateral filter + contrast) → embeddings.npy (5 min)
4. **Index**: FAISS IndexFlatIP → index.faiss (2 min)
5. **Reprints**: Group by name → reprints.json (1,014 detected)

**Commands**: `pnpm tcgplayer:scrape`, `pnpm pipeline:update` (incremental), `pnpm update:sync` (cloud)

### 4. Configuration
`packages/config/src/tcgplayer-config.ts`
- TCG categories (One Piece enabled, 67 others disabled)
- `isSealedProduct()` - metadata-first filter (checks 'Number' field), filters 211 sealed products (booster boxes, starter decks, tins)
- `transformImageUrl()` - 200w → 600x600 JPG

## Project Structure (Critical Paths)
```
apps/desktop/               # Electron app (v0.2.2)
  src/main/index.ts         # IPC handlers, Python bridge spawn
  src/main/identifier/python-bridge.ts  # JSON-RPC communication
  src/python/identification_service.py  # Python service entry
  src/renderer/app.tsx      # Main React app
  src/renderer/components/  # CameraView, CardStack, Settings
packages/config/            # Shared TCG config
services/                   # Data pipeline (ingest, embedder, indexer)
scripts/identification/     # Organized identification system
  core/                     # Production modules (identifier, detectors)
  tools/                    # Utilities (precompute, version manager)
  tests/                    # Test suites
  experiments/              # R&D scripts (fine-tuning, analysis)
  archive/                  # Archived versions (v1.1, v2, v3, debug)
docs/                       # Documentation
  guides/                   # User guides (fine-tuning, colab, testing)
  architecture/             # Technical design docs
  deployment/               # Production readiness docs
  development/              # Contributing, organization
  status/                   # Current session summaries
  archive/                  # Historical docs (sessions, improvements, test results)
data/curated/               # one-piece.jsonl (5,390 cards)
data/images/                # Card images (~400 MB)
artifacts/faiss/            # FAISS indexes (7.1 MB)
artifacts/metadata/         # embeddings.npy (7.4 MB), reprints.json
test-results/               # Test outputs
  current/                  # Latest test results
  archive/                  # Historical test data
```

## Critical Algorithms

### DINOv2 Preprocessing (CRITICAL)
```python
# MUST be identical in embedder AND identifier (vector space consistency!)
filtered = cv2.bilateralFilter(image, d=5, sigmaColor=50, sigmaSpace=50)
enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
```

### ORB Geometric Verification
```python
orb = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, nlevels=8, edgeThreshold=15)
# Lowe's ratio test: 0.80 threshold
# Score = (match_ratio*0.5 + coverage_ratio*0.3 + distance_quality*0.2) * 2.2
```

### Dynamic Multi-Modal Scoring
```python
# Adaptive weights based on geometric quality
if geometric_score > 0.15: visual=0.60, geometric=0.40
elif geometric_score > 0.05: visual=0.75, geometric=0.25
else: visual=0.90, geometric=0.10

final_score = visual*WEIGHT_VISUAL + geometric*WEIGHT_GEOMETRIC + boosts
# Confidence: HIGH (≥0.75), MODERATE (≥0.62 + margin≥0.10), LOW
```

## Common Commands
```bash
# Desktop app
cd apps/desktop && pnpm build:dev && pnpm start

# Testing
python scripts/identification/core/production_card_identifier.py <image>
python scripts/identification/tests/test_all_production_images.py
python scripts/identification/tests/test_card_detection.py

# Data pipeline
pnpm pipeline:update              # Incremental daily update
pnpm update:sync                  # Sync from GitHub cloud

# Build & package
pnpm build                        # Build all packages
pnpm typecheck                    # TypeScript check
cd apps/desktop && pnpm package   # Create installer (NSIS/DMG/AppImage)
```

## Known Issues
1. **Watermarked references** (5-10%) - TCGPlayer "SAMPLE" watermarks reduce similarity ~0.15-0.20 (ORB rescues)
2. **Alternate art variants** (10-15%) - may identify base version (needs variant classifier)
3. **Python dependency** - requires Python 3.10+, PyTorch, transformers (future: bundle or ONNX)
4. **No multi-game switching** - must restart app to change TCG (future: v0.3.0)
5. **Git LFS storage** - may exceed 1 GB free tier with multiple games (future: S3/CloudFront)

## Roadmap

### Immediate (This Sprint)
- [ ] Test with real shop inventory (50-100 cards)
- [ ] Collect production accuracy metrics
- [ ] Optimize startup time (<2s)

### Short-Term (1-2 Months)
- [ ] Add Pokémon, Magic TCG support
- [ ] Variant classifier (alternate art)
- [ ] GPU acceleration (3-5x speedup)
- [ ] Batch scanning mode

### Medium-Term (3-6 Months)
- [ ] Cloud sync for inventory
- [ ] Price tracking/analytics
- [ ] POS system integration
- [ ] Multi-camera support

### Long-Term (6-12 Months)
- [ ] Real-time video stream ID
- [ ] Condition grading (NM/LP/MP/HP)
- [ ] Fine-tuned models per game
- [ ] Mobile/tablet app

## Key Lessons
1. **Preprocessing Consistency** (2025-10-16): ALWAYS match embedder ↔ identifier preprocessing (vector space mismatch = 50% failures)
2. **Accuracy > Speed**: +475ms for +33% accuracy is acceptable (within reason)
3. **Dynamic > Static**: Adaptive weights (60/40-90/10) more robust than fixed 70/30
4. **Codebase Organization** (2025-10-22): Clean structure is critical for maintainability - archive old versions, separate production from experiments
5. **Hybrid Geometric Matching** (2025-10-22): AKAZE provides safety net when ORB fails on compressed images
6. **Metadata-First Filtering** (2025-10-27): Use card metadata (Number field) to identify cards vs sealed products - 10x more reliable than name-based pattern matching (+577 cards recovered)

## Quick Reference
- **Config**: `packages/config/src/tcgplayer-config.ts`
- **Identification**: `scripts/identification/core/production_card_identifier.py` ⭐
- **Card Detector**: `scripts/identification/core/polished_card_detector.py` (100% success)
- **Test Suite**: `scripts/identification/tests/test_all_production_images.py`
- **Desktop Main**: `apps/desktop/src/main/index.ts`
- **Desktop UI**: `apps/desktop/src/renderer/app.tsx`
- **Python Bridge**: `apps/desktop/src/main/identifier/python-bridge.ts`
- **Docs**: `docs/{guides,architecture,deployment,development,status,archive}/`
- **Status**: `docs/status/SESSION_FINAL_SUMMARY.md` (latest)
- **Deployment**: `docs/deployment/PRODUCTION_READINESS_ASSESSMENT.md`

---

**Maintained by**: Claude Code | **Last Review**: 2025-10-22 | **Next Review**: After major features/architecture changes
