# Python Bundler Usage Guide

> **TL;DR**: Bundling runs automatically during production builds. Development uses system Python. App updates won't trigger rebundling unless you explicitly run it.

---

## Overview

The Python bundler downloads Python runtime and dependencies, packaging them with the Electron app for distribution. This ensures users don't need Python installed.

### Key Principles

1. **Separation**: Bundling is separate from app development
2. **Development-Friendly**: Uses system Python during development
3. **Production-Only**: Bundled Python only used in packaged app
4. **Cached**: Bundle persists until you explicitly clean it
5. **Platform-Specific**: Each OS has its own bundler

---

## When Bundling Happens

### Automatic (Production Build)
```bash
pnpm build
# Runs: bundle:python → webpack → electron-builder
```

The `build` script automatically bundles Python before packaging.

### Manual (When Needed)
```bash
pnpm bundle:python        # Auto-detect platform
pnpm bundle:python:windows  # Windows explicitly
pnpm bundle:python:macos    # macOS explicitly
pnpm bundle:python:linux    # Linux explicitly
```

Run manually when:
- Python version updated
- Dependencies added/removed
- Bundle corrupted
- Testing bundler changes

---

## When Bundling Does NOT Happen

### Development Workflow ✓
```bash
pnpm build:dev    # Webpack only, NO bundling
pnpm start        # Run app, NO bundling
pnpm typecheck    # Type check, NO bundling
pnpm lint         # Lint code, NO bundling
```

**Development is fast because bundling is skipped.**

### App Feature Updates ✓
When you update TypeScript/React code:
```typescript
// Edit src/renderer/app.tsx
// Edit src/main/index.ts
// Edit src/renderer/components/*.tsx
```

Then:
```bash
pnpm build:dev    # Fast rebuild (seconds)
pnpm start        # Run immediately
```

**No bundling needed. Uses existing bundle or system Python.**

### Python Script Updates ✓
When you update Python scripts:
```python
# Edit scripts/identification/production_card_identifier.py
# Edit src/python/identification_service.py
```

Scripts are copied during bundling, but **development uses scripts directly from source**.

**No bundling needed for development.**

---

## Development vs Production

### Development Mode
```
apps/desktop/
├── dist/                    # Webpack output
│   └── main/
│       ├── index.js         # Compiled TS
│       └── core/            # ResourceManager, etc.
└── src/
    └── python/              # Scripts run directly from here
```

**Python**: System Python
**Scripts**: `src/python/` (source files)
**Data**: `data/` and `artifacts/` in project root

### Production Mode (Packaged)
```
CardFlux/
├── CardFlux.exe             # Electron executable
└── resources/
    ├── python-runtime/      # Bundled Python
    ├── python-site-packages/  # Bundled dependencies
    └── python-scripts/      # Copied Python scripts
```

**Python**: Bundled Python
**Scripts**: `resources/python-scripts/` (copied)
**Data**: Downloaded from CDN on first run

---

## Bundler Workflow

### 1. Download Python (First Time Only)
```
Downloads: python-3.13.1-embed-amd64.zip (~25 MB)
Extracts to: resources/python-runtime/win32/
Time: ~30 seconds
```

### 2. Install Dependencies (First Time Only)
```
Installs: torch, transformers, faiss, opencv, numpy, etc.
Target: resources/python-site-packages/
Time: ~5-10 minutes (large downloads)
```

### 3. Copy Scripts (Every Time)
```
Copies: *.py from scripts/identification/ and src/python/
Target: resources/python-scripts/
Time: <1 second
```

### 4. Cleanup (Every Time)
```
Removes: __pycache__, tests, *.pyc, etc.
Reduces bundle size by ~30%
Time: <5 seconds
```

**Total First Run**: ~10 minutes
**Total Subsequent Runs**: ~10 seconds (cached Python + deps)

---

## Bundle Cache

Bundled files persist in `resources/` until you clean them:

```bash
pnpm bundle:clean   # Delete bundled Python
pnpm clean          # Delete bundle + dist + out
```

**Cache behavior:**
- Bundle persists across `pnpm build:dev`
- Bundle persists across code edits
- Bundle persists across git pulls
- Bundle deleted by `pnpm clean`

**Why cache?** Avoid re-downloading Python/deps every time.

---

## Seamless Updates

### Adding App Features
```typescript
// Add new React component
// Update UI logic
// Add IPC handlers
```

**Build**: `pnpm build:dev` (seconds)
**Bundler**: Not triggered
**Production Build**: Bundler runs once during `pnpm build`

### Updating Dependencies
```bash
# Add new npm package
pnpm add some-package

# Update TypeScript code to use it
# Build and test
pnpm build:dev && pnpm start
```

**Bundler**: Not triggered
**Impact**: None

### Updating Python Dependencies
```txt
# Edit resources/python-requirements.txt
torch==2.2.0  # Updated version
```

**Then**:
```bash
pnpm bundle:clean       # Clear old bundle
pnpm bundle:python      # Re-bundle with new deps
pnpm build:dev          # Rebuild app
pnpm start              # Test
```

**Bundler**: Triggered manually
**Time**: 5-10 minutes (re-download deps)

---

## Verification

After bundling, verify it worked:

```bash
pnpm bundle:verify
```

Output:
```
========================================
  CardFlux Bundle Verification
========================================

Platform: win32
Python executable: C:\...\resources\python-runtime\win32\python.exe

--- Python Runtime ---
✓ Python executable exists
✓ Python home directory exists

--- Site Packages ---
✓ Site packages directory exists
✓ Package: torch exists
✓ Package: transformers exists
✓ Package: faiss exists
✓ Package: cv2 exists
✓ Package: numpy exists
✓ Package: PIL exists

--- Python Scripts ---
✓ Scripts directory exists
✓ Script: identification_service.py exists
✓ Script: production_card_identifier.py exists
✓ Script: card_detector.py exists

--- Python Execution Tests ---
ℹ Testing: Python --version
✓ Python --version - OK
  Output: Python 3.13.1

ℹ Testing: Import torch
✓ Import torch - OK
  Output: PyTorch 2.1.2

[... more tests ...]

========================================
  Verification Summary
========================================

✓ All checks passed!

Bundle is ready for production.
```

---

## Troubleshooting

### Bundle Failed to Download Python
**Error**: `Download failed: HTTP 404`
**Fix**: Check `PYTHON_VERSION` in `bundle-python-windows.js`, ensure version exists on python.org

### Bundle Failed to Install Dependencies
**Error**: `pip install failed`
**Fix**:
1. Check `resources/python-requirements.txt` syntax
2. Ensure internet connection
3. Try `pnpm bundle:clean` then `pnpm bundle:python`

### Verification Failed: Missing Packages
**Error**: `Package: torch NOT FOUND`
**Fix**:
1. Run `pnpm bundle:clean`
2. Run `pnpm bundle:python`
3. Check console output for errors during pip install

### Development Mode Not Finding Scripts
**Error**: `Python service script not found`
**Fix**: Ensure `src/python/identification_service.py` exists (development mode uses source files)

### Production Mode Not Finding Scripts
**Error**: `Python service script not found`
**Fix**: Run `pnpm bundle:python` to copy scripts to `resources/python-scripts/`

---

## Advanced Usage

### Skip Bundling During Build
```bash
# Build without bundling (uses existing bundle)
pnpm build:webpack && pnpm package
```

### Force Re-bundle
```bash
pnpm bundle:clean && pnpm bundle:python
```

### Bundle for Different Platform
```bash
# On Windows, bundle for macOS (if implemented)
pnpm bundle:python:macos
```

### Test Bundle Without Packaging
```bash
pnpm bundle:python    # Create bundle
pnpm bundle:verify    # Verify it works
# App will use bundled Python even in development
```

---

## Summary

| Scenario | Command | Bundler Runs? | Time |
|----------|---------|---------------|------|
| Development build | `pnpm build:dev` | No | Seconds |
| Development run | `pnpm start` | No | Instant |
| Code changes | `pnpm build:dev` | No | Seconds |
| Production build | `pnpm build` | Yes (auto) | 10 min first, 10 sec cached |
| Manual bundle | `pnpm bundle:python` | Yes | 10 min first, 10 sec cached |
| Clean all | `pnpm clean` | Deletes bundle | Instant |

**Key Takeaway**: Bundling is **completely separate** from daily development. Update app code freely without worrying about bundling.

---

## Next Steps

1. **For Development**: Just run `pnpm build:dev && pnpm start`
2. **For Production**: Run `pnpm build` (bundles automatically)
3. **For Release**: Run `pnpm build`, distribute `out/CardFlux-Setup-*.exe`

---

**Questions?** Check `IMPLEMENTATION_STATUS.md` or `BUNDLED_PYTHON_ARCHITECTURE.md`
