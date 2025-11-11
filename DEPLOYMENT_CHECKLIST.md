# CardFlux Deployment Checklist

**Version**: v0.2.2 | **Date**: 2025-11-10
**Purpose**: Ensure seamless setup on any machine with zero issues

---

## Pre-Deployment Verification

Use this checklist before pushing code or creating releases.

### 1. Repository State

- [ ] All code committed and pushed to `main`
- [ ] No uncommitted changes (`git status` clean)
- [ ] Git LFS files tracked and pushed
- [ ] All branches merged (no stale branches)
- [ ] Version numbers updated in `package.json` files

**Commands**:
```bash
git status
git lfs ls-files  # Should show 4 files
git push origin main
git push --tags
```

### 2. Required Git LFS Files

Verify these 4 critical files are in LFS (not regular git):

- [ ] `artifacts/faiss/one-piece-dinov2/index.faiss` (~7 MB)
- [ ] `artifacts/keypoints/one-piece/orb_keypoints.npz` (~120 MB) ⭐ **CRITICAL**
- [ ] `artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl` (~7 MB)
- [ ] `data/curated/one-piece.jsonl` (~3 MB)

**Verify**:
```bash
# Check LFS tracking
git lfs ls-files

# Verify file sizes (not pointer files <1KB)
ls -lh artifacts/faiss/one-piece-dinov2/index.faiss  # Should be ~7 MB
ls -lh artifacts/keypoints/one-piece/orb_keypoints.npz  # Should be ~120 MB
ls -lh artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl  # Should be ~7 MB
ls -lh data/curated/one-piece.jsonl  # Should be ~3 MB
```

**If files are <1KB (pointers)**:
```bash
# Re-push LFS files
git lfs push origin main --all
```

### 3. Documentation Completeness

- [ ] `SETUP.md` up to date with all prerequisites
- [ ] `CLAUDE.md` reflects current architecture
- [ ] `README.md` has accurate quick start
- [ ] `requirements.txt` has all Python dependencies
- [ ] `DEPLOYMENT_CHECKLIST.md` (this file) complete
- [ ] API documentation in `docs/` is current

**Critical Sections in SETUP.md**:
- [ ] Git LFS installation instructions
- [ ] **Pre-compute keypoints step** (MANDATORY for Fast v2)
- [ ] Python dependencies with version numbers
- [ ] Build tools for each platform
- [ ] Common issues and solutions

### 4. Python Environment

- [ ] `requirements.txt` complete and tested
- [ ] All Python scripts have proper imports
- [ ] Python 3.10+ compatibility verified
- [ ] PyTorch CPU version specified (GPU optional)
- [ ] FAISS CPU version specified (GPU optional)

**Test Python env**:
```bash
# Create fresh venv
python -m venv test_venv
source test_venv/bin/activate  # or test_venv\Scripts\activate on Windows

# Install and verify
pip install -r requirements.txt
python -c "import torch, transformers, faiss, cv2, PIL; print('All imports OK')"

# Cleanup
deactivate
rm -rf test_venv
```

### 5. Node.js Environment

- [ ] `package.json` has correct engines (Node 20+, pnpm 9+)
- [ ] `pnpm-lock.yaml` is committed
- [ ] All workspace dependencies specified
- [ ] Build scripts tested on all platforms
- [ ] No deprecated packages

**Test Node env**:
```bash
# Clean install
rm -rf node_modules
pnpm install

# Verify workspaces
pnpm list --depth=0

# Build all packages
pnpm build

# Typecheck
pnpm typecheck
```

### 6. Desktop App Verification

- [ ] Electron build succeeds (`pnpm build`)
- [ ] App starts without errors (`pnpm start`)
- [ ] Python bridge connects successfully
- [ ] Optimized service loads in <5s
- [ ] Camera permissions work
- [ ] Card identification succeeds (test with sample images)

**Test desktop app**:
```bash
cd apps/desktop
pnpm build:dev
pnpm start

# Should see:
# - Python service starts
# - "Initialization complete: 3-4s"
# - Camera view appears
# - Test identification with SPACE key
```

### 7. Identification Performance

- [ ] Fast identifier loads successfully
- [ ] ORB keypoints cache exists (~120 MB)
- [ ] Warmup completes (2 inferences)
- [ ] First identification <200ms
- [ ] Warm identification <150ms
- [ ] 100% accuracy on test images

**Test performance**:
```bash
# Run camera flow simulation
pnpm dev:camera-sim:optimized

# Expected results:
# - Initialization: <5s
# - Camera flow: <300ms average
# - UX: EXCELLENT (feels instant)
```

### 8. Test Coverage

- [ ] Unit tests pass (`pnpm test`)
- [ ] Production validation passes (95%+ accuracy)
- [ ] Benchmark tests pass
- [ ] Integration tests succeed
- [ ] No failing tests in CI

**Run tests**:
```bash
# Python tests
python scripts/identification/tests/benchmark_fast_vs_production.py
python scripts/identification/tests/production_validation.py

# Node tests (if implemented)
pnpm test

# Typecheck
pnpm typecheck
```

### 9. CI/CD Pipeline

- [ ] `.github/workflows/ci-tests.yml` exists and runs
- [ ] All CI jobs pass (desktop-tests, production-validation, build-check)
- [ ] Git LFS configured in CI
- [ ] Python dependencies cached in CI
- [ ] Build artifacts generated

**Verify CI**:
```bash
# Check workflow file
cat .github/workflows/ci-tests.yml

# Trigger manual run
gh workflow run ci-tests.yml
```

### 10. Platform Testing

Test on each target platform:

- [ ] **Windows 10/11**: Build succeeds, app runs
- [ ] **macOS 12+**: Build succeeds, app runs
- [ ] **Ubuntu 20.04+**: Build succeeds, app runs

**Platform-specific issues to check**:
- Windows: Visual Studio Build Tools installed
- macOS: Xcode Command Line Tools installed
- Linux: build-essential installed

---

## Fresh Machine Setup Test

Simulate a new developer/user setting up from scratch.

### Test Scenario 1: New Developer (with prerequisites)

**Prerequisites installed**: Git LFS, Node 20, pnpm 9, Python 3.10, build tools

```bash
# 1. Clone
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# 2. Verify LFS
git lfs ls-files  # Should show 4 files
ls -lh artifacts/faiss/one-piece-dinov2/index.faiss  # Should be ~7 MB, not <1KB

# 3. Install Node deps
pnpm install  # Should complete without errors

# 4. Install Python deps
pip install -r requirements.txt  # Should complete without errors

# 5. Pre-compute keypoints (CRITICAL)
python scripts/identification/tools/precompute_geometric_features.py
# Should complete in ~45s, create 120 MB file

# 6. Build
pnpm build  # Should complete without errors

# 7. Run app
cd apps/desktop
pnpm start  # Should start in <10s

# 8. Test identification
# Point at test image, press SPACE
# Should identify in <300ms with HIGH confidence
```

**Success criteria**:
- No errors in any step
- Total setup time: <10 minutes (excluding downloads)
- App starts and identifies cards correctly

### Test Scenario 2: New User (no prerequisites)

**Starting from scratch**:

1. Follow `SETUP.md` step-by-step
2. Install all prerequisites
3. Clone and setup
4. Run first identification

**Success criteria**:
- User can follow guide without external help
- No undocumented errors
- Setup completes in <30 minutes

---

## Common Failure Points

These are the most likely issues during deployment. Test each one:

### 1. Git LFS Not Installed

**Test**:
```bash
# Simulate missing Git LFS
git lfs uninstall
git clone <repo>
# Files should be pointer files (<1KB)
```

**Expected behavior**:
- User sees error: "Cannot load FAISS index"
- `SETUP.md` provides clear fix: `git lfs install && git lfs pull`

### 2. Missing ORB Keypoints

**Test**:
```bash
# Delete keypoints
rm -rf artifacts/keypoints/

# Run identifier
python scripts/identification/core/fast_card_identifier.py test-images/one-piece/blackbeard.png
```

**Expected behavior**:
- Warning: "ORB keypoints cache not found"
- Fallback to runtime detection (180ms vs 111ms)
- `SETUP.md` provides clear fix: run pre-compute script

### 3. Wrong Python Version

**Test**:
```bash
# Try with Python 3.9
python3.9 -m venv test_venv
source test_venv/bin/activate
pip install -r requirements.txt
```

**Expected behavior**:
- Some packages fail to install
- Clear error message: "Python 3.10+ required"

### 4. Missing Build Tools

**Test on Windows**:
```bash
# Uninstall Visual Studio Build Tools
# Try: pnpm install
```

**Expected behavior**:
- `better-sqlite3` build fails
- `SETUP.md` provides clear fix with download link

### 5. Workspace Dependencies Not Built

**Test**:
```bash
# Skip root build
cd apps/desktop
pnpm build
```

**Expected behavior**:
- Error: "Cannot find module '@cardflux/config'"
- `SETUP.md` provides clear fix: run `pnpm build` from root first

---

## Release Checklist

Before creating a GitHub release:

### Pre-Release

- [ ] All tests pass locally
- [ ] All tests pass in CI
- [ ] Version bumped in all `package.json` files
- [ ] `CHANGELOG.md` updated
- [ ] Git LFS files verified and pushed
- [ ] Documentation reviewed and updated
- [ ] Performance benchmarks run and recorded

### Create Release

- [ ] Create git tag: `git tag v0.2.2`
- [ ] Push tag: `git push origin v0.2.2`
- [ ] Create GitHub release with tag
- [ ] Attach build artifacts (optional):
  - Windows installer (.exe)
  - macOS DMG
  - Linux AppImage
- [ ] Release notes include:
  - New features
  - Performance improvements
  - Bug fixes
  - Breaking changes
  - Migration guide (if needed)

### Post-Release

- [ ] Test installation from release
- [ ] Verify Git LFS files download correctly
- [ ] Monitor for issues
- [ ] Update documentation links if needed

---

## Performance Baselines

Record these metrics for each release to track regression:

| Metric | Target | Current (v0.2.2) | Status |
|--------|--------|------------------|--------|
| **Cold Start** | <5s | 2.3s | ✅ EXCELLENT |
| **Initialization** | <5s | 3.5s | ✅ EXCELLENT |
| **First Identification** | <200ms | 98ms | ✅ EXCELLENT |
| **Warm Identification** | <150ms | 98ms | ✅ EXCELLENT |
| **Camera Flow** | <500ms | 225ms | ✅ EXCELLENT |
| **Accuracy** | ≥95% | 100% (6/6) | ✅ EXCELLENT |
| **HIGH Confidence Rate** | ≥80% | 100% (6/6) | ✅ EXCELLENT |

**Regression test**:
```bash
# Run comprehensive benchmark
python scripts/identification/tests/benchmark_fast_vs_production.py

# Run camera flow simulation
pnpm dev:camera-sim:optimized

# Run production validation
python scripts/identification/tests/production_validation.py
```

---

## Deployment Artifacts Checklist

### Required Files in Repository

**Critical (must be in LFS)**:
- [ ] `artifacts/faiss/one-piece-dinov2/index.faiss`
- [ ] `artifacts/keypoints/one-piece/orb_keypoints.npz`
- [ ] `artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl`
- [ ] `data/curated/one-piece.jsonl`

**Documentation**:
- [ ] `README.md`
- [ ] `SETUP.md`
- [ ] `CLAUDE.md`
- [ ] `DEPLOYMENT_CHECKLIST.md` (this file)
- [ ] `requirements.txt`
- [ ] `CHANGELOG.md`

**Code**:
- [ ] All source files in `apps/`, `packages/`, `services/`
- [ ] All scripts in `scripts/`
- [ ] All tests in `tests/` or `**/tests/`

**Configuration**:
- [ ] `package.json` (root + workspaces)
- [ ] `pnpm-lock.yaml`
- [ ] `.github/workflows/ci-tests.yml`
- [ ] `.gitattributes` (LFS config)
- [ ] `.gitignore`

### Files to EXCLUDE

**Never commit these**:
- [ ] `node_modules/` (gitignored)
- [ ] `.venv/` or `venv/` (gitignored)
- [ ] `dist/` (build output, gitignored)
- [ ] `data/images/` (too large, download separately)
- [ ] `.env` (secrets, gitignored)
- [ ] `*.log` (gitignored)
- [ ] OS files (`.DS_Store`, `Thumbs.db`, etc.)

**Temporary/test files to remove**:
- [ ] `validate_prices.py` (one-off script)
- [ ] `backfill-log.txt` (test output)
- [ ] `data/curated/one-piece-card-game.jsonl` (duplicate)
- [ ] `.github/workflows/daily-update-BACKUP.yml` (backup file)
- [ ] Any `nul` or temp files

---

## Quick Deployment Commands

```bash
# === PRE-DEPLOYMENT ===

# 1. Clean and verify
git status  # Should be clean
git lfs ls-files  # Should show 4 files
pnpm clean && pnpm build  # Fresh build
pnpm typecheck  # Type check

# 2. Test performance
pnpm dev:camera-sim:optimized  # Should be <300ms avg
python scripts/identification/tests/benchmark_fast_vs_production.py  # Should be 100% accuracy

# 3. Run tests
pnpm test  # All tests pass
python scripts/identification/tests/production_validation.py  # ≥95% accuracy

# === DEPLOYMENT ===

# 1. Commit final changes
git add -A
git commit -m "chore: Release v0.2.2"

# 2. Create tag
git tag v0.2.2 -a -m "Release v0.2.2: Python bridge optimization, instant UX"

# 3. Push
git push origin main
git push origin v0.2.2
git lfs push origin main --all  # Ensure LFS files pushed

# 4. Verify on GitHub
# - Check LFS files appear correctly (not text pointers)
# - Check CI passes
# - Check release notes

# === POST-DEPLOYMENT ===

# Test fresh clone
cd /tmp
git clone https://github.com/yourusername/cardflux.git test-deploy
cd test-deploy
git lfs ls-files  # Verify 4 files
ls -lh artifacts/faiss/one-piece-dinov2/index.faiss  # Should be ~7 MB
pnpm install && pip install -r requirements.txt
python scripts/identification/tools/precompute_geometric_features.py
pnpm build
cd apps/desktop && pnpm start

# Cleanup
cd /tmp && rm -rf test-deploy
```

---

## Troubleshooting Deployment Issues

### Issue: LFS Files Not Downloading

**Symptoms**:
```
Error: index.faiss is 132 bytes (should be ~7 MB)
```

**Solution**:
```bash
git lfs install
git lfs pull
git lfs ls-files  # Verify
```

### Issue: Keypoints Missing After Clone

**Symptoms**:
```
Warning: ORB keypoints cache not found
Identification slow (180ms vs 111ms)
```

**Solution**:
```bash
# Check if file exists
ls -lh artifacts/keypoints/one-piece/orb_keypoints.npz

# If missing, run pre-compute
python scripts/identification/tools/precompute_geometric_features.py
```

### Issue: Build Fails on Fresh Clone

**Symptoms**:
```
Error: Cannot find module '@cardflux/config'
```

**Solution**:
```bash
# Build from root first (builds dependencies in order)
cd <project-root>
pnpm clean
pnpm install
pnpm build
```

### Issue: Python Imports Fail

**Symptoms**:
```
ModuleNotFoundError: No module named 'torch'
```

**Solution**:
```bash
# Check Python version first
python --version  # Must be 3.10+

# Install dependencies
pip install -r requirements.txt

# Verify
python -c "import torch, transformers, faiss, cv2; print('OK')"
```

---

## Success Criteria

Deployment is successful when:

✅ **Setup completes without errors** on all platforms (Windows, macOS, Linux)
✅ **Fresh clone works** without manual intervention beyond SETUP.md
✅ **All LFS files download** correctly (~137 MB total)
✅ **Desktop app starts** in <10s
✅ **First identification** completes in <300ms
✅ **Accuracy** ≥95% on production validation
✅ **Tests pass** in CI/CD pipeline
✅ **Documentation** is complete and accurate
✅ **No undocumented errors** or edge cases

---

**Last Updated**: 2025-11-10
**Maintained By**: Claude Code
**Next Review**: Before each major release
