# Bundled Python Architecture

> **Goal**: Ship a self-contained desktop app with no external dependencies

## Architecture Overview

### Current State (Problems)
- Requires users to install Python 3.10+ manually
- Requires users to `pip install` 800MB+ of dependencies
- Fails if wrong Python version or missing packages
- **Result**: 40% install failure rate

### Target State (Solution)
- Download ONE installer (CardFlux-Setup.exe)
- Python runtime bundled inside app
- All dependencies pre-installed
- Data downloads automatically on first run
- **Result**: 99% install success rate

---

## Directory Structure

```
apps/desktop/
├── resources/                       # Bundled resources (packaged with app)
│   ├── python-runtime/              # Python 3.13 embedded runtime
│   │   ├── win32/                   # Windows-specific
│   │   │   ├── python.exe
│   │   │   ├── python313.dll
│   │   │   └── Lib/                 # Standard library
│   │   ├── darwin/                  # macOS-specific
│   │   │   └── python/              # Python framework
│   │   └── linux/                   # Linux-specific
│   │       └── python/
│   │
│   ├── python-site-packages/        # Pre-installed pip packages
│   │   ├── torch/                   # PyTorch (~400MB)
│   │   ├── transformers/            # Hugging Face Transformers (~300MB)
│   │   ├── faiss/                   # FAISS vector search (~10MB)
│   │   ├── cv2/                     # OpenCV (~50MB)
│   │   ├── numpy/                   # NumPy (~30MB)
│   │   ├── PIL/                     # Pillow (~5MB)
│   │   └── ... (all dependencies)
│   │
│   └── python-scripts/              # Application Python scripts
│       ├── identification_service.py
│       ├── production_card_identifier.py
│       ├── card_detector.py
│       └── ... (all scripts)
│
├── src/
│   ├── main/
│   │   ├── core/
│   │   │   ├── resource-manager.ts     # Manages bundled resources
│   │   │   ├── data-manager.ts         # Downloads/manages card databases
│   │   │   ├── python-manager.ts       # Python runtime manager
│   │   │   └── logger.ts               # Structured logging
│   │   │
│   │   ├── identifier/
│   │   │   └── python-bridge.ts        # Updated to use bundled Python
│   │   │
│   │   └── index.ts
│   │
│   └── renderer/
│       └── components/
│           └── FirstRunWizard.tsx      # First-run setup UI
│
├── scripts/build/
│   ├── bundle-python-windows.js        # Bundle Python for Windows
│   ├── bundle-python-macos.js          # Bundle Python for macOS
│   ├── bundle-python-linux.js          # Bundle Python for Linux
│   ├── install-dependencies.js         # Install pip packages
│   ├── copy-scripts.js                 # Copy Python scripts
│   ├── verify-bundle.js                # Verify bundle integrity
│   └── prepare-release.js              # Orchestrate full build
│
├── electron-builder.yml                # Electron Builder config
└── package.json
```

---

## Data Storage Strategy

### Bundled with App (~50MB)
- Python runtime (embedded/portable)
- Python dependencies (torch, transformers, faiss, etc.)
- Application Python scripts
- App icons, UI assets

### Downloaded on First Run (~400MB per game)
- Card images (data/images/one-piece/)
- FAISS indices (artifacts/faiss/one-piece-dinov2/)
- Embeddings (artifacts/metadata/embeddings/)
- Metadata (data/curated/one-piece.jsonl)

**Why separate?**
- Installer size: 50MB vs 450MB (9x smaller)
- Multi-game support: Download only games user needs
- Daily updates: Update data without re-downloading app

---

## Runtime Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. App Launch                                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ResourceManager.initialize()                              │
│    - Locate bundled Python runtime                           │
│    - Verify Python executable exists                         │
│    - Check Python can execute (run --version)                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. DataManager.checkDataFiles()                              │
│    - Check if card database exists locally                   │
│    - If missing → show FirstRunWizard                        │
│    - Download database from CDN (with progress bar)          │
│    - Verify integrity (checksums)                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PythonBridge.start()                                      │
│    - Spawn bundled Python with proper environment            │
│    - Set PYTHONPATH to bundled site-packages                 │
│    - Run identification_service.py                           │
│    - Wait for initialization                                 │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. App Ready                                                 │
│    - Camera feed active                                      │
│    - User can scan cards                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Build Process

### Development Build
```bash
# 1. Install Node dependencies
pnpm install

# 2. Bundle Python (downloads Python, installs packages)
pnpm bundle:python

# 3. Build webpack
pnpm build:dev

# 4. Run Electron
pnpm start
```

### Production Build
```bash
# 1. Clean previous builds
pnpm clean

# 2. Bundle Python runtime + dependencies
pnpm bundle:python:prod

# 3. Build webpack (production mode)
pnpm build:webpack

# 4. Package with Electron Builder
pnpm package

# Output:
# - Windows: out/CardFlux-Setup-1.0.0.exe (NSIS installer)
# - macOS: out/CardFlux-1.0.0.dmg
# - Linux: out/CardFlux-1.0.0.AppImage
```

---

## Error Handling Strategy

### 1. Python Runtime Errors
- **Missing Python**: Show error dialog with download link
- **Corrupted Python**: Re-download/repair bundle
- **Version mismatch**: Auto-update to correct version

### 2. Data Download Errors
- **Network failure**: Retry with exponential backoff (3 attempts)
- **Partial download**: Resume from checkpoint
- **Corrupted file**: Re-download with integrity check

### 3. Python Service Errors
- **Crash**: Auto-restart service (max 3 times)
- **Timeout**: Show warning, allow manual restart
- **Import error**: Check dependencies, re-install if needed

### 4. Graceful Degradation
- **Missing data**: Allow app to open, show setup wizard
- **Old data**: Warn user, allow continued use with "Update" button
- **Low disk space**: Warn before download, allow cancellation

---

## Version Management

### App Version (Semantic Versioning)
```
v1.0.0 → Initial release
v1.0.1 → Bug fixes
v1.1.0 → New features
v2.0.0 → Breaking changes
```

### Data Version (TCG-specific)
```json
{
  "one-piece": {
    "version": "2025.01.17",
    "cardCount": 4813,
    "size": 414000000,
    "checksums": {
      "images": "sha256:abc123...",
      "index": "sha256:def456...",
      "metadata": "sha256:ghi789..."
    }
  }
}
```

### Update Strategy
- **App updates**: Electron auto-updater (background download, prompt on restart)
- **Data updates**: Check daily, download in background, notify user
- **Breaking changes**: Show migration wizard

---

## CDN Configuration

### Data Distribution
```
https://cdn.cardflux.com/
├── databases/
│   ├── manifest.json              # Version info for all games
│   ├── one-piece/
│   │   ├── v2025.01.17/
│   │   │   ├── images.tar.gz      # 400MB compressed
│   │   │   ├── index.tar.gz       # 7MB compressed
│   │   │   ├── metadata.tar.gz    # 5MB compressed
│   │   │   └── checksums.json     # SHA256 checksums
│   │   └── latest.json            # Points to latest version
│   └── pokemon/                   # Future games...
│
└── app-updates/                   # Electron auto-updater
    ├── latest.yml                 # Version info
    ├── CardFlux-Setup-1.0.0.exe
    └── ...
```

### CloudFront Setup (AWS)
- S3 bucket: `cardflux-cdn`
- CloudFront distribution: `cdn.cardflux.com`
- Caching: 24 hours for data, 5 minutes for manifests
- CORS: Enabled for download progress tracking
- Costs: ~$5-10/month for 1TB bandwidth

---

## Testing Strategy

### Unit Tests
- ResourceManager path resolution
- DataManager download/extraction
- PythonManager spawn/communicate
- Error handling edge cases

### Integration Tests
- Full build pipeline
- Python bundle verification
- Data download simulation
- Service initialization

### Manual Tests (Clean Systems)
- Fresh Windows 10/11 install
- Fresh macOS 13+ install
- Fresh Ubuntu 22.04 install
- No Python installed, no dependencies

---

## Rollout Plan

### Phase 1: Internal Testing (Week 1)
- Build bundled installer
- Test on developer machines
- Fix critical bugs

### Phase 2: Beta Testing (Week 2-3)
- Share with 3-5 card shops
- Collect feedback
- Iterate on UX

### Phase 3: Public Release (Week 4)
- Launch on website
- Monitor error reports (Sentry)
- Respond to issues quickly

---

## Success Metrics

- **Install Success Rate**: >95%
- **First-Run Completion**: >90%
- **Crash Rate**: <1%
- **Support Tickets**: <10% related to install

---

**Status**: Design Complete → Ready for Implementation
**Next**: Implement ResourceManager, PythonManager, DataManager
