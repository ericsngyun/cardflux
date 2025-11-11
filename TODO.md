# CardFlux TODO - Project Task Tracker

> **Last Updated**: 2025-11-10
> **Current Version**: v0.2.2 (Production-Ready)
> **Next Release**: v0.3.0 (Optimization Release)

---

## 🚀 v0.3.0 - Optimization Release (Next Sprint)

**Goal**: Integrate optimized Python bridge for instant UX (225ms camera flow)

### High Priority

- [ ] **Integrate Optimized Python Bridge** `apps/desktop/src/main/identifier/`
  - [ ] Update `python-bridge.ts` to spawn `optimized_identification_service.py`
  - [ ] Add warmup phase configuration (2 dummy inferences)
  - [ ] Test model preloading on app startup
  - [ ] Verify persistent process architecture
  - [ ] **Target**: 2.3s cold start, 98ms first ID, 225ms camera flow
  - **Files**:
    - `apps/desktop/src/python/optimized_identification_service.py` (EXISTS)
    - `apps/desktop/src/main/identifier/python-bridge.ts` (UPDATE)
    - `docs/performance/PYTHON_BRIDGE_OPTIMIZATION.md` (REFERENCE)

- [ ] **Fix App Integration Tests** `apps/desktop/src/__tests__/app.test.tsx`
  - [ ] Resolve async timing issues with useEffect status polling
  - [ ] Use Jest fake timers properly with waitFor
  - [ ] Test initialization flow (loading → ready transition)
  - [ ] Test all 21 failing integration tests
  - [ ] **Target**: 100% test pass rate (currently 60/82)

- [ ] **End-to-End Performance Validation**
  - [ ] Test camera capture → detection → identification flow
  - [ ] Measure real-world latency with optimized bridge
  - [ ] Verify warmup completes on app startup
  - [ ] Test with 10+ rapid captures (no slowdown)
  - [ ] **Success Criteria**: <300ms average, <500ms p99

### Medium Priority

- [ ] **Load Testing & Stress Testing**
  - [ ] 100-card continuous scanning session
  - [ ] Memory leak detection (check for model memory growth)
  - [ ] CPU usage profiling during sustained use
  - [ ] Test with different image sizes/qualities
  - [ ] **Success Criteria**: Stable performance over 1000+ scans

- [ ] **User Validation** (Real Shop Testing)
  - [ ] Partner with local card shop for beta testing
  - [ ] Collect 50-100 real-world scans
  - [ ] Track accuracy metrics in production environment
  - [ ] Gather UX feedback on speed/workflow
  - [ ] **Success Criteria**: 95%+ accuracy, positive UX feedback

### Documentation

- [ ] Update `SETUP.md` with optimized service setup
- [ ] Add performance troubleshooting guide
- [ ] Document warmup configuration options
- [ ] Update architecture diagrams for new flow
- [ ] Create v0.3.0 migration guide

---

## 🎮 v0.4.0 - Multi-Game Expansion (1-2 Months)

### Pokémon TCG Support

- [ ] **Data Pipeline**
  - [ ] Scrape Pokémon cards from TCGPlayer (estimate: ~15,000 cards)
  - [ ] Download Pokémon card images
  - [ ] Generate DINOv2 embeddings for Pokémon
  - [ ] Build FAISS index for Pokémon
  - [ ] Pre-compute ORB keypoints for Pokémon

- [ ] **Identification System**
  - [ ] Test Fast Identifier v2 on Pokémon cards
  - [ ] Tune geometric matching thresholds if needed
  - [ ] Create Pokémon-specific test image set
  - [ ] Validate 95%+ accuracy on Pokémon

- [ ] **UI Updates**
  - [ ] Enable multi-game selector in Settings
  - [ ] Add game-switching without app restart (hot-swap indices)
  - [ ] Update UI to handle Pokémon card metadata
  - [ ] Add Pokémon-specific price display

### Magic: The Gathering Support

- [ ] **Data Pipeline** (same steps as Pokémon, ~30,000 cards)
- [ ] **Identification System** (test & validate)
- [ ] **UI Updates** (game selector, metadata)

### Architecture Improvements

- [ ] **Multi-Game Index Manager**
  - [ ] Create `IndexManager` class to handle multiple FAISS indices
  - [ ] Implement index switching without process restart
  - [ ] Cache management for multiple games (memory limits)
  - [ ] Lazy loading for non-active games

- [ ] **Storage Optimization**
  - [ ] Migrate to S3/CloudFront for images (avoid Git LFS limits)
  - [ ] Implement on-demand index downloading
  - [ ] Compressed index storage format
  - [ ] **Target**: Support 5+ games within 500 MB app size

---

## ⚡ Performance & Scalability

### GPU Acceleration (Optional)

- [ ] Add CUDA support for FAISS (10x speedup potential)
- [ ] GPU-accelerated DINOv2 inference (5x speedup)
- [ ] Benchmark GPU vs CPU performance
- [ ] Graceful CPU fallback if no GPU available
- [ ] **Target**: <20ms identification on GPU

### Batch Scanning Mode

- [ ] Design batch UI workflow (scan multiple cards before review)
- [ ] Parallel identification (queue + workers)
- [ ] Batch export to CSV
- [ ] Progress tracking for large batches
- [ ] **Target**: 100 cards in <10 seconds (GPU)

---

## 🎯 Features & Enhancements

### Variant Classifier

- [ ] **Problem**: Identify alternate art vs base version
- [ ] Research image similarity methods for variants
- [ ] Build variant dataset (label alternate arts)
- [ ] Train or fine-tune classifier
- [ ] Integrate into identification pipeline
- [ ] **Success Criteria**: 90%+ variant classification accuracy

### Price Tracking & Analytics

- [ ] **Historical Price Charts**
  - [ ] Integrate with existing price scraping
  - [ ] Store daily price snapshots
  - [ ] Visualize price trends in UI
  - [ ] Alert on price spikes/drops

- [ ] **Inventory Analytics**
  - [ ] Total inventory value tracking
  - [ ] High-value card alerts
  - [ ] Set-based analytics (completion %)
  - [ ] Export to accounting software

### Cloud Sync

- [ ] Design cloud sync architecture (Firebase/Supabase)
- [ ] User authentication system
- [ ] Real-time inventory sync across devices
- [ ] Conflict resolution for offline edits
- [ ] **Target**: <2s sync latency

---

## 🐛 Bug Fixes & Technical Debt

### Critical

- [ ] **App Integration Tests** (async timing issues)
  - 21 failing tests in `app.test.tsx`
  - Affects: initialization, settings, identification flows
  - **Blocker for**: Confident v0.3.0 release

### High Priority

- [ ] Investigate watermarked reference images (5-10% of dataset)
  - TCGPlayer "SAMPLE" watermarks reduce similarity
  - Consider watermark removal in preprocessing
  - Or scrape non-watermarked sources

- [ ] Improve error handling in Python bridge
  - Better error messages for common failures
  - Retry logic for transient errors
  - Graceful degradation when models fail to load

### Medium Priority

- [ ] Memory leak detection in long-running sessions
- [ ] Improve card detection on poor lighting conditions
- [ ] Handle multi-card images (split & identify each)
- [ ] Add keyboard shortcuts documentation

### Low Priority

- [ ] Settings panel visual polish
- [ ] Add dark mode support
- [ ] Improve loading animations
- [ ] Add sound effects for scan success/failure

---

## 📚 Documentation

### User Documentation

- [ ] **User Guide** (non-technical)
  - [ ] Installation guide for shop owners
  - [ ] Quick start tutorial
  - [ ] Common workflows (scanning, exporting, pricing)
  - [ ] Troubleshooting FAQ

- [ ] **Video Tutorials**
  - [ ] Installation walkthrough
  - [ ] Basic scanning workflow
  - [ ] Advanced features demo

### Developer Documentation

- [ ] **Architecture Deep Dive**
  - [ ] System design document
  - [ ] Data flow diagrams
  - [ ] API reference
  - [ ] Extension guide (adding new games)

- [ ] **Contributing Guide**
  - [ ] Code style guidelines
  - [ ] Testing requirements
  - [ ] PR review process
  - [ ] Development workflow

---

## 🧪 Testing & Quality Assurance

### Unit Tests

- [ ] Increase coverage to 80% (currently ~70%)
- [ ] Add tests for Python bridge error handling
- [ ] Test settings persistence edge cases
- [ ] Test export functionality

### Integration Tests

- [ ] Fix existing 21 failing app tests
- [ ] Add tests for multi-game switching
- [ ] Test price sync workflows
- [ ] Test batch scanning mode

### E2E Tests

- [ ] Set up Playwright or Cypress for desktop app
- [ ] Test full user workflows (install → scan → export)
- [ ] Cross-platform E2E tests (Windows, macOS, Linux)
- [ ] Performance regression testing

---

## 🚢 Deployment & DevOps

### CI/CD Improvements

- [ ] Auto-build installers on release tags
- [ ] Automated smoke tests on built installers
- [ ] Performance benchmarks in CI
- [ ] Automated changelog generation

### Packaging & Distribution

- [ ] Code signing for Windows installer
- [ ] macOS notarization
- [ ] Linux AppImage auto-update support
- [ ] Release to app stores (Microsoft Store, Mac App Store)

### Monitoring & Analytics

- [ ] Add anonymous usage analytics (opt-in)
- [ ] Error reporting (Sentry integration)
- [ ] Performance metrics (identification time, accuracy)
- [ ] User retention tracking

---

## 💡 Research & Exploration

### Model Improvements

- [ ] **Fine-tuning DINOv2** on TCG cards
  - Collect larger labeled dataset
  - Fine-tune on card-specific features
  - Evaluate improvement over generic DINOv2
  - **Hypothesis**: 5-10% accuracy improvement

- [ ] **Condition Grading**
  - Research: Image analysis for card condition (NM/LP/MP/HP)
  - Dataset: Collect images of cards in various conditions
  - Model: Train classifier or use rule-based approach
  - **Challenge**: Subjective grading standards

### Alternative Technologies

- [ ] **ONNX Runtime** (replace PyTorch)
  - Smaller runtime footprint
  - Faster inference
  - Easier deployment
  - **Goal**: Eliminate PyTorch dependency

- [ ] **CLIP** for multi-modal search
  - Text + image queries ("blue eyes white dragon foil")
  - Natural language card descriptions
  - **Research**: Compare vs pure vision approach

---

## 📝 Notes & Ideas

### Backlog (Someday/Maybe)

- Mobile app (React Native or Flutter)
- Real-time video stream identification (no manual capture)
- Multi-camera support (scan multiple cards simultaneously)
- POS system integration (Shopify, Square)
- Marketplace integration (eBay, TCGPlayer seller tools)
- Card grading service integration (PSA, BGS)
- Bulk pricing API for third-party apps
- OCR for card text (rules, flavor text)
- Deck building mode (track collections by deck)
- Trade matching (find traders with cards you need)

### Feature Requests (From Users)

> Add user requests here as they come in

---

## ✅ Completed (Archive)

### v0.2.2 (2025-11-10)

- ✅ UI cleanup & test improvements
- ✅ Deployment checklist created
- ✅ Accessibility improvements (aria-labels)
- ✅ Python bridge optimization research (78% faster)
- ✅ Component tests (60/60 passing)
- ✅ Production validation (9/9, 100% accuracy)

### v0.2.1 (2025-11-03)

- ✅ Fast Identifier v2 (12x speedup, 100% accuracy)
- ✅ Pre-computed ORB keypoints cache (60% geometric speedup)
- ✅ Benchmark validation framework
- ✅ Version manager (v2 default, v1 fallback)
- ✅ Cross-platform SETUP.md guide

### v0.2.0 (2025-10-27)

- ✅ Card detection system (100% success rate)
- ✅ AKAZE hybrid geometric matching
- ✅ Comprehensive test suite (19 test images)
- ✅ Codebase organization & cleanup
- ✅ Sealed product filtering (+577 cards)

---

**Maintained by**: CardFlux Engineering Team
**Priority System**: Critical > High > Medium > Low
**Review Cadence**: Weekly (adjust priorities based on user feedback)
