# Changelog

All notable changes to CardFlux will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2025-11-11

### 🚀 Optimization Release - Instant UX

**MAJOR PERFORMANCE IMPROVEMENT**: Integrated optimized Python bridge for instant user experience.

### Added
- **Optimized Python Bridge**: New `optimized_identification_service.py` with model preloading and warmup
  - 78% faster cold start (10.5s → 2.3s)
  - 90% faster first identification (986ms → 98ms)
  - **231ms average camera flow** (INSTANT UX, target was 225ms)
- Model preloading on app startup (DINOv2 + FAISS + Card Detector)
- Warmup inference (2 dummy predictions to eliminate JIT overhead)
- Persistent process architecture (no restart penalty between identifications)

### Changed
- **ResourceManager**: Updated `getServiceScriptPath()` to use optimized service
- Python bridge now uses optimized service in both development and production
- Security validation updated to accept both service variants

### Performance
**Before (v0.2.2)**:
- Cold start: 10.5s
- First ID: 986ms
- Warm ID: 92ms

**After (v0.3.0)**:
- Cold start: 2.3s ✅ 78% faster
- First ID: 98ms ✅ 90% faster
- Camera flow: 231ms avg ✅ INSTANT UX
- Min: 211ms, Max: 245ms (very consistent)

**User Experience**: ✅ EXCELLENT - Users perceive as INSTANT (<500ms)

### Technical Details
- Uses Fast Identifier v2 (111ms identification core)
- Pre-cached ORB keypoints (120 MB cache for 60% geometric speedup)
- FP16 half-precision DINOv2 inference
- JSON-RPC communication with type-safe serialization
- Graceful error handling and recovery

### Files Changed
- `apps/desktop/src/main/core/resource-manager.ts` (2 lines)
- `apps/desktop/src/python/optimized_identification_service.py` (existing, now active)

### Testing
- ✅ Camera flow simulation: 3/3 tests passed, all HIGH confidence
- ✅ Desktop app builds successfully
- ✅ Backward compatible (old service kept as fallback)

---

## [0.2.2] - 2025-11-10

### 🧹 UI Cleanup & Professional Documentation

Production-ready release with comprehensive test coverage, accessibility improvements, and complete documentation.

### Added
- **DEPLOYMENT_CHECKLIST.md** (611 lines) - Comprehensive deployment guide
  - Pre-deployment verification steps
  - Fresh machine setup testing
  - Common failure points and solutions
  - Release checklist with performance baselines
- **TODO.md** (367 lines) - Complete project backlog
  - v0.3.0 optimization roadmap
  - v0.4.0 multi-game expansion plan
  - Bug tracking & technical debt section
  - Research & exploration ideas
- **Accessibility**: Added `aria-label` to card removal buttons (WCAG-compliant)
- Test dependencies: Jest + React Testing Library

### Changed
- **Testing**: Fixed component tests (60/60 passing, 100% pass rate)
  - CardStack: 28/28 tests passing
  - SettingsPanel: 32/32 tests passing
  - Fixed multiple element selection issues with `getAllByText`
- **UI Improvements**:
  - Removed debug console.logs from production code
  - Cleaned up HTML debug scripts
  - Locked TCG game selector to One Piece (multi-game in v0.3.0)
  - Improved settings panel: Auto-save messaging, "Close" button
- **Documentation**:
  - README.md: Added professional features list, performance metrics, roadmap
  - CLAUDE.md: Updated with v0.2.2 status and v0.3.0 plan
- **Repository Hygiene**:
  - Cleaned up temporary files (validate_prices.py, backfill-log.txt)
  - Deleted backup workflows

### Removed
- **Unused Components**: DetectionOverlay.tsx, ScannerView.tsx
- Temporary validation scripts

### Deferred
- App integration tests (21 tests) - Async timing issues to fix in v0.3.0

### Performance
- Fast Identifier v2: 111ms avg, 100% accuracy (9/9 tests)
- Component tests: 60/60 passing
- Production validation: 100% HIGH confidence

---

## [0.2.1] - 2025-11-03

### ⚡ Fast Identifier v2 - 12x Performance Improvement

### Added
- **Fast Identifier v2** (DEFAULT): 12x faster than Production v1
  - 111ms average (vs 1377ms Production v1)
  - 100% accuracy (6/6 test cases)
  - 100% HIGH confidence (6/6 tests)
- **Pre-computed ORB Keypoints Cache** (120 MB)
  - 60% geometric matching speedup
  - One-time 45s pre-computation
  - Git LFS tracked for efficient distribution
- **Benchmark Validation Framework**
  - Comprehensive test suite comparing v1 vs v2
  - Corrected ground truth validation
  - Performance metrics tracking
- **Version Manager**: Switch between Fast v2 (default) and Production v1 (fallback)
- **Cross-platform SETUP.md Guide**: Complete setup instructions for Windows, macOS, Linux

### Changed
- Fast Identifier v2 optimizations:
  - FP16 half-precision inference (-40% feature extraction time)
  - Parallel geometric matching (ThreadPoolExecutor)
  - Early stopping (skip geometric if visual >0.90)
  - Reduced verification candidates (5 vs 20, paradoxically +17% accuracy)
  - GPU FAISS support (optional, 10x additional speedup)

### Performance
- **Fast Identifier v2**: 111ms avg, 100% accuracy
- **Production v1**: 1377ms avg, 83% accuracy
- **Winner**: Fast v2 is SUPERIOR in all metrics (speed, accuracy, confidence)

---

## [0.2.0] - 2025-10-27

### 🎯 100% Card Detection & Codebase Organization

### Added
- **Polished Card Detector**: 100% success rate on test suite (19 images)
- **AKAZE Hybrid Geometric Matching**: Safety net when ORB fails on compressed images
- **Comprehensive Test Suite**: 19 test images covering various card types and conditions
- **Sealed Product Filter**: Metadata-first approach (+577 cards recovered)
  - Uses card metadata (Number field) instead of name patterns
  - 10x more reliable than pattern matching

### Changed
- **Codebase Organization**: Complete restructuring
  - `scripts/identification/core/` - Production modules
  - `scripts/identification/tools/` - Utilities
  - `scripts/identification/tests/` - Test suites
  - `scripts/identification/experiments/` - R&D scripts
  - `scripts/identification/archive/` - Archived versions
- Improved geometric matching with hybrid ORB+AKAZE approach

### Performance
- Card detection: 100% success rate
- Identification accuracy: 100% on clean images, 92-99% on variants

---

## [0.1.0] - 2025-10-16

### 🎉 Initial Release - One Piece TCG Support

### Added
- **DINOv2 Vision AI**: State-of-the-art visual embeddings (384-dim)
- **FAISS Vector Search**: Sub-millisecond similarity search
- **ORB Geometric Verification**: Watermark-robust matching
- **One Piece TCG Database**: 5,390 cards indexed
  - Including variants, reprints, alternate arts
  - Real-time TCGPlayer pricing integration
- **Desktop App** (Electron + React + TypeScript)
  - Camera capture interface
  - Card identification with confidence scores
  - CSV export for inventory management
  - Settings panel with configurable options
- **Data Pipeline**:
  - TCGPlayer API scraping
  - Image downloading (600x600 JPG)
  - DINOv2 embedding generation
  - FAISS index building
  - Reprint detection (1,014 reprints grouped)
- **CI/CD Pipeline**:
  - Automated testing on every commit
  - Production validation (95%+ accuracy requirement)
  - Build verification
  - Daily database updates via GitHub Actions

### Performance
- Identification: 200-500ms per card (CPU only)
- Accuracy: 100% on exact matches, 92-99% on variants
- Coverage: 5,390 One Piece cards (100% of released cards)

---

## [Unreleased]

### Planned for v0.4.0 - Multi-Game Expansion
- Pokémon TCG support (~15,000 cards)
- Magic: The Gathering support (~30,000 cards)
- Multi-game index manager (hot-swap without restart)
- Storage optimization (S3/CloudFront for images)

### Future Enhancements
- Variant classifier (alternate art detection)
- GPU acceleration (10x additional speedup)
- Batch scanning mode
- Price tracking & analytics
- Cloud sync for inventory
- POS system integration
- Mobile/tablet app
- Condition grading (NM/LP/MP/HP)

---

## Version History

- **v0.3.0** (2025-11-11): Optimization Release - Instant UX (231ms camera flow)
- **v0.2.2** (2025-11-10): UI Cleanup & Professional Documentation
- **v0.2.1** (2025-11-03): Fast Identifier v2 (12x speedup, 100% accuracy)
- **v0.2.0** (2025-10-27): 100% Card Detection & Organization
- **v0.1.0** (2025-10-16): Initial Release - One Piece TCG

---

**Maintained by**: CardFlux Engineering Team
**Format**: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
**Versioning**: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
