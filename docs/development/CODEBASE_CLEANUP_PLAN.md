# Codebase Cleanup Plan

**Date**: 2025-10-22
**Goal**: Organize codebase into clean, maintainable structure

---

## Current State Analysis

### Problems Identified:
1. **Root directory cluttered** with 36+ markdown files
2. **49 Python scripts** in `scripts/identification/` (many obsolete)
3. **Versioned files** (v1, v2, v3) not archived
4. **Debug scripts** scattered everywhere
5. **Test results** (JSON) mixed with code
6. **No clear separation** between production, development, and archived code

---

## Proposed Directory Structure

```
cardflux/
├── docs/
│   ├── guides/              # User-facing documentation
│   │   ├── fine-tuning.md
│   │   ├── colab-quickstart.md
│   │   ├── testing-commands.md
│   │   └── sync-feature.md
│   ├── architecture/        # Technical design docs
│   │   ├── identification-pipeline.md
│   │   ├── visual-vs-geometric.md
│   │   └── realtime-analysis.md
│   ├── deployment/          # Production readiness
│   │   ├── production-readiness.md
│   │   └── confidence-calibration.md
│   ├── development/         # Dev workflow
│   │   ├── contributing.md
│   │   ├── project-organization.md
│   │   └── next-session.md
│   ├── status/              # Progress tracking (ACTIVE)
│   │   ├── week1-status.md
│   │   ├── session-summary.md
│   │   └── before-after-comparison.md
│   └── archive/             # Historical docs (ARCHIVE)
│       ├── sessions/        # Old session summaries
│       ├── improvements/    # Past improvement docs
│       └── test-results/    # Historical test data
│
├── scripts/
│   ├── identification/
│   │   ├── core/            # Production-ready modules
│   │   │   ├── production_card_identifier.py ⭐ MAIN
│   │   │   ├── polished_card_detector.py
│   │   │   ├── foil_detector.py
│   │   │   ├── ocr_service.py
│   │   │   ├── variant_classifier.py
│   │   │   └── universal_card_extractor.py
│   │   ├── tools/           # Utility scripts
│   │   │   ├── identifier_version_manager.py
│   │   │   ├── precompute_keypoints.py
│   │   │   └── shop_scanner.py
│   │   ├── tests/           # Test suites
│   │   │   ├── test_all_production_images.py
│   │   │   ├── test_summary_report.py
│   │   │   ├── test_card_detection.py
│   │   │   ├── test_production_suite.py
│   │   │   └── test_real_cards.py
│   │   ├── experiments/     # R&D scripts (kept for reference)
│   │   │   ├── analyze_visual_vs_geometric.py
│   │   │   ├── finetune_dinov2.py
│   │   │   └── colab_finetune_notebook.py
│   │   └── archive/         # Obsolete versions (ARCHIVE)
│   │       ├── v1_1/
│   │       │   ├── production_card_identifier_v1_1.py
│   │       │   ├── production_card_identifier_v1_tta.py
│   │       │   └── test_v1_1_optimizations.py
│   │       ├── v2/
│   │       │   ├── production_card_identifier_v2.py
│   │       │   ├── production_card_identifier_v2_1.py
│   │       │   └── test_v2_improvements.py
│   │       ├── v3/
│   │       │   ├── production_card_identifier_v3.py
│   │       │   └── test_v3_compressed.py
│   │       └── debug/       # Debug scripts (kept for reference)
│   │           ├── debug_blackbeard.py
│   │           ├── debug_embedding.py
│   │           ├── trace_embedding_issue.py
│   │           └── analyze_confidence_issue.py
│   └── ...
│
├── test-images/             # Test data
│   └── one-piece/
│       └── (keep only source images, move generated to temp/)
│
├── test-results/            # NEW: All test outputs
│   ├── current/
│   │   ├── test_all_production_results.json
│   │   └── visual_test_results.json
│   └── archive/
│       ├── v1_1_test_results.json
│       ├── v2_1_test_results.json
│       └── v3_test_results.json
│
└── (root files)
    ├── README.md            # Main project README
    ├── CLAUDE.md            # AI context file (KEEP)
    ├── CONTRIBUTING.md      # Move to docs/development/
    ├── package.json
    ├── tsconfig.json
    └── turbo.json
```

---

## Files to Archive (Move to docs/archive/)

### Session Summaries (Historical):
- [x] `GEOMETRIC_MATCHING_SESSION_SUMMARY.md` → `docs/archive/sessions/`
- [x] `GEOMETRIC_OPTIMIZATION_SESSION_SUMMARY.md` → `docs/archive/sessions/`
- [x] `DAY1_PROGRESS.md` → `docs/archive/sessions/`
- [x] `DAY1_STATUS_UPDATE.md` → `docs/archive/sessions/`
- [x] `SESSION_SUMMARY.md` → `docs/archive/sessions/`

### Improvement Docs (Historical):
- [x] `GEOMETRIC_MATCHING_IMPROVEMENTS.md` → `docs/archive/improvements/`
- [x] `CONFIDENCE_IMPROVEMENT_FINDINGS.md` → `docs/archive/improvements/`
- [x] `CONFIDENCE_IMPROVEMENT_PLAN.md` → `docs/archive/improvements/`
- [x] `DISTANCE_DETECTION_IMPROVEMENTS.md` → `docs/archive/improvements/`
- [x] `V1_ACCURACY_IMPROVEMENT_OPPORTUNITIES.md` → `docs/archive/improvements/`
- [x] `V2_IMPLEMENTATION_COMPLETE.md` → `docs/archive/improvements/`
- [x] `V2_UPGRADE_SUMMARY.md` → `docs/archive/improvements/`
- [x] `V3_COMPRESSED_IMAGE_TEST_RESULTS.md` → `docs/archive/improvements/`

### Week 1 Docs (Historical):
- [x] `WEEK1_STATUS.md` → `docs/archive/week1/`
- [x] `WEEK1_COMPLETE_STATUS.md` → `docs/archive/week1/`
- [x] `WEEK1_FINAL_RESULTS.md` → `docs/archive/week1/`
- [x] `WEEK1_FINAL_SUMMARY.md` → `docs/archive/week1/`
- [x] `WEEK1_IMPLEMENTATION_COMPLETE.md` → `docs/archive/week1/`

### Test Results (Historical):
- [x] `VARIANT_CLASSIFICATION_TEST_RESULTS.md` → `docs/archive/test-results/`
- [x] `VISUAL_HEAVY_TEST_RESULTS.md` → `docs/archive/test-results/`
- [x] `VISUAL_VS_GEOMETRIC_ANALYSIS.md` → `docs/archive/test-results/`
- [x] `BEFORE_AFTER_COMPARISON.md` → `docs/archive/test-results/`

---

## Files to Keep in Root (Active):
- [x] `README.md` - Main project README
- [x] `CLAUDE.md` - AI context (CRITICAL - keep current)
- [x] `package.json`, `tsconfig.json`, `turbo.json` - Config files

---

## Files to Move to docs/

### docs/guides/
- [x] `FINE_TUNING_GUIDE.md`
- [x] `COLAB_QUICKSTART.md`
- [x] `COLAB_TRAINING_FIX.md`
- [x] `COLAB_TROUBLESHOOTING.md`
- [x] `TESTING_COMMANDS.md`
- [x] `SYNC_FEATURE_DOCUMENTATION.md`

### docs/development/
- [x] `CONTRIBUTING.md`
- [x] `PROJECT_ORGANIZATION.md`
- [x] `NEXT_SESSION.md`

### docs/deployment/
- [x] `PRODUCTION_READINESS_ASSESSMENT.md`

### docs/architecture/
- [x] `REALTIME_IDENTIFICATION_ANALYSIS.md`

### docs/status/ (CURRENT STATUS DOCS)
- [x] `SESSION_FINAL_SUMMARY.md` - Latest session
- [x] `BEFORE_AFTER_COMPARISON.md` - Move to archive after confirmed

---

## Python Scripts to Archive

### scripts/identification/archive/v1_1/
- [x] `production_card_identifier_v1_1.py`
- [x] `production_card_identifier_v1_tta.py`
- [x] `test_v1_1_optimizations.py`
- [x] `test_v1_tta.py`

### scripts/identification/archive/v2/
- [x] `production_card_identifier_v2.py`
- [x] `production_card_identifier_v2_1.py`
- [x] `test_v2_improvements.py`
- [x] `test_v2_1_improvements.py`
- [x] `test_v2_quick.py`

### scripts/identification/archive/v3/
- [x] `production_card_identifier_v3.py`
- [x] `test_v3_compressed.py`

### scripts/identification/archive/debug/
- [x] `debug_blackbeard.py`
- [x] `debug_embedding.py`
- [x] `trace_embedding_issue.py`
- [x] `analyze_confidence_issue.py`

### scripts/identification/archive/obsolete/
- [x] `identify_card.py` (superseded by production version)
- [x] `identify_card_hybrid.py`
- [x] `identify_card_optimized.py`
- [x] `identify_card_production.py`
- [x] `card_detector.py` (superseded by polished version)
- [x] `shop_scanner_pro.py` (experimental)
- [x] `shop_scanner_with_prices.py` (experimental)
- [x] `test_fixes.py` (one-off debug)
- [x] `test_all_images.py` (superseded by test_all_production_images.py)
- [x] `visual_test_report.py` (superseded by test_summary_report.py)

---

## Test Results to Move (test-results/)

### test-results/archive/
- [x] `v1_1_test_results.json`
- [x] `test_results.json`
- [x] `test_report.json`
- [x] `visual_test_results.json`
- [x] `system_analysis.json`

### test-results/current/
- [x] Keep `test_all_production_results.json` in scripts/identification/ for now

---

## Generated Test Images to Clean Up

Move to temp or delete:
- [x] `test-images/one-piece/cropped_*.{png,jpg}` (9 files)
- [x] `test-images/one-piece/detected_*.png` (visualization overlays)

Keep original source images only.

---

## Scripts to Keep in scripts/identification/ (Production)

### Core (Production-Ready):
- [x] `production_card_identifier.py` ⭐ **MAIN SYSTEM**
- [x] `polished_card_detector.py` ⭐ **100% success rate**
- [x] `foil_detector.py`
- [x] `ocr_service.py`
- [x] `variant_classifier.py`
- [x] `universal_card_extractor.py`

### Tools:
- [x] `identifier_version_manager.py`
- [x] `precompute_keypoints.py`
- [x] `shop_scanner.py`

### Tests:
- [x] `test_all_production_images.py` ⭐ **Comprehensive test suite**
- [x] `test_summary_report.py`
- [x] `test_card_detection.py`
- [x] `test_production_suite.py`
- [x] `test_production_system.py`
- [x] `test_real_cards.py`
- [x] `test_geometric_features.py`
- [x] `test_finetuned_model.py`
- [x] `test_resolution_comparison.py`
- [x] `test_akaze_improvements.py`

### Experiments (Keep for Reference):
- [x] `analyze_visual_vs_geometric.py`
- [x] `finetune_dinov2.py`
- [x] `colab_finetune_notebook.py`
- [x] `analyze_system.py`
- [x] `verify_800x800_upgrade.py`

---

## Shell Scripts to Move

### Root → scripts/
- [x] `test_refined_system.sh` → `scripts/identification/archive/`

---

## Implementation Steps

1. **Create directory structure**
   ```bash
   mkdir -p docs/{guides,architecture,deployment,development,status,archive/{sessions,improvements,week1,test-results}}
   mkdir -p scripts/identification/{core,tools,tests,experiments,archive/{v1_1,v2,v3,debug,obsolete}}
   mkdir -p test-results/{current,archive}
   ```

2. **Move documentation files** (36 markdown files → organized structure)

3. **Move Python scripts** (49 scripts → organized by purpose)

4. **Move test results** (JSON files → test-results/)

5. **Clean up generated images** (cropped_*, detected_*)

6. **Update imports** in scripts that reference moved files

7. **Update CLAUDE.md** with new structure

8. **Test production system** to ensure nothing broke

9. **Commit with detailed message**

---

## Success Criteria

- [x] Root directory has <10 files (README, CLAUDE.md, configs)
- [x] All docs organized in `docs/` by category
- [x] Production scripts clearly separated from experiments/archive
- [x] All tests pass after reorganization
- [x] CLAUDE.md updated with new paths

---

**Status**: Ready to execute
**Estimated Time**: 30 minutes
**Risk**: LOW (git tracks all moves, easy to revert)
