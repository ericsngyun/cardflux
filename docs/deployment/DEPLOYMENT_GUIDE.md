# CardFlux Desktop - Complete Deployment Guide

> **Last Updated**: 2025-10-15
> **Target**: CardFlux Desktop v0.2.1
> **Platforms**: Windows 10/11, macOS (Intel & Apple Silicon), Linux (Ubuntu/Debian, Fedora/RHEL)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Automated)](#quick-start-automated)
4. [Manual Setup (Step-by-Step)](#manual-setup-step-by-step)
5. [Downloading Pre-built Artifacts](#downloading-pre-built-artifacts)
6. [Building from Scratch](#building-from-scratch)
7. [Running the Desktop App](#running-the-desktop-app)
8. [Troubleshooting](#troubleshooting)
9. [Platform-Specific Notes](#platform-specific-notes)
10. [Uninstallation](#uninstallation)

---

## Overview

CardFlux Desktop is an AI-powered card identification system that runs locally on your machine. This guide will help you set up the desktop scanner from scratch, even on a fresh device.

### What You'll Get

- **Desktop App**: Electron-based GUI with real-time camera scanning
- **AI Models**: DINOv2 vision transformer for card identification
- **Card Database**: 4,813 One Piece TCG cards with prices
- **Offline Operation**: Everything runs locally, no internet required after setup

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10, macOS 10.15, Ubuntu 20.04 | Windows 11, macOS 13+, Ubuntu 22.04+ |
| **CPU** | Intel i5 (2015+), AMD Ryzen 5 | Intel i7 (2018+), AMD Ryzen 7 |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 3 GB free | 5 GB free |
| **GPU** | Optional | NVIDIA (CUDA 12.1+), Apple Silicon (MPS) |
| **Camera** | Webcam (720p) | Document camera (1080p+) |

---

## Prerequisites

### Required Software

1. **Node.js 20+**
   - Download: https://nodejs.org/
   - Verify: `node --version` (should show v20.x.x or higher)

2. **Python 3.10+**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version` or `python3 --version`

3. **Git** (for cloning repository)
   - Download: https://git-scm.com/

### Optional (for GPU acceleration)

- **NVIDIA GPU**: CUDA Toolkit 12.1+ ([Download](https://developer.nvidia.com/cuda-downloads))
- **Apple Silicon**: Pre-installed MPS support in macOS 12.3+

---

## Quick Start (Automated)

The fastest way to get started is using our automated setup scripts.

### Windows

```powershell
# Clone repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Run setup script
pwsh scripts/setup/setup-windows.ps1

# Or with GPU support
pwsh scripts/setup/setup-windows.ps1 -GPU
```

### macOS

```bash
# Clone repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Make script executable
chmod +x scripts/setup/setup-macos.sh

# Run setup script
./scripts/setup/setup-macos.sh

# Or with GPU support (uses MPS on Apple Silicon)
./scripts/setup/setup-macos.sh --gpu
```

### Linux (Ubuntu/Debian/Fedora)

```bash
# Clone repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Make script executable
chmod +x scripts/setup/setup-linux.sh

# Run setup script
./scripts/setup/setup-linux.sh

# Or with GPU support
./scripts/setup/setup-linux.sh --gpu
```

**After running the setup script**, skip to [Downloading Pre-built Artifacts](#downloading-pre-built-artifacts) or [Running the Desktop App](#running-the-desktop-app).

---

## Manual Setup (Step-by-Step)

If you prefer manual setup or the automated script failed, follow these steps.

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/cardflux.git
cd cardflux
```

### Step 2: Install Node.js Dependencies

```bash
# Install pnpm (if not already installed)
npm install -g pnpm

# Install dependencies
pnpm install
```

**Expected output**: `Packages: +XXX` (takes 1-2 minutes)

### Step 3: Install Python Dependencies

#### Option A: CPU-only (default)

```bash
pip install -r requirements.txt
```

#### Option B: NVIDIA GPU (CUDA)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install faiss-gpu
pip install -r requirements.txt --no-deps
```

#### Option C: Apple Silicon (M1/M2/M3)

```bash
# PyTorch with MPS support
pip install torch torchvision

# Other dependencies
pip install -r requirements.txt --no-deps
```

**Expected time**: 5-10 minutes (downloads ~2 GB)

### Step 4: Verify Installation

```bash
# Check Node.js/pnpm
node --version    # Should be v20.x.x or higher
pnpm --version    # Should be 9.x.x or higher

# Check Python
python --version  # Should be 3.10.x or higher (or python3 on macOS/Linux)

# Check Python packages
python -c "import torch, transformers, faiss, cv2, PIL; print('All packages OK')"
```

---

## Downloading Pre-built Artifacts

CardFlux requires card data and ML artifacts to function. You have two options:

### Option 1: Download from GitHub (Recommended)

If pre-built artifacts are available in the repository:

```bash
# Sync artifacts from latest release
pnpm update:sync
```

This downloads:
- `data/curated/one-piece.jsonl` (4,813 cards)
- `data/images/one-piece/*.jpg` (~400 MB)
- `artifacts/faiss/one-piece-dinov2/index.faiss` (7.1 MB)
- `artifacts/metadata/embeddings/one-piece-dinov2/*.npy` (7.4 MB)

**Total download**: ~500 MB
**Time**: 3-5 minutes (depends on connection)

### Option 2: Use External Storage

If artifacts are hosted externally (e.g., Google Drive, Dropbox):

1. **Download the artifacts package** from the provided link
2. **Extract to project root**:
   ```bash
   # The archive should contain 'data/' and 'artifacts/' folders
   unzip cardflux-artifacts.zip -d .
   ```

3. **Verify structure**:
   ```bash
   ls data/curated/one-piece.jsonl
   ls artifacts/faiss/one-piece-dinov2/index.faiss
   ```

---

## Building from Scratch

If you want to build the full data pipeline from scratch (e.g., for development or adding new games):

### Quick Build (One Piece TCG)

```bash
# 1. Scrape card data from TCGPlayer (~2 min)
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# 2. Download card images (~3 min)
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# 3. Generate embeddings (~5 min)
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# 4. Build FAISS index (~1 min)
python services/indexer/bin/build_faiss_onepiece_dinov2.py

# 5. Build reprint map (~1 min)
python scripts/pipeline/build_reprint_map.py
```

**Total time**: ~12 minutes

### Full Build (All Games)

See `docs/guides/LOCAL_DEVELOPMENT.md` for instructions on building the full pipeline with multiple TCG games.

---

## Running the Desktop App

### Step 1: Build the App

```bash
cd apps/desktop

# Development build (faster, includes source maps)
pnpm build:dev

# OR production build (optimized, smaller bundle)
NODE_ENV=production pnpm run build:webpack
```

**Expected time**: 30-60 seconds

### Step 2: Start the App

```bash
pnpm start
```

**What happens**:
1. Electron window opens (~2 seconds)
2. Python service initializes (~3 seconds)
3. Camera preview starts automatically
4. Ready to scan cards!

### Step 3: Test Identification

1. **Place a card in front of the camera**
2. **Press SPACE** to capture
3. **Wait for identification** (200-500ms)
4. **Result appears** in the card stack on the right

---

## Troubleshooting

### Common Issues

#### 1. Python Module Not Found

**Error**: `ModuleNotFoundError: No module named 'torch'` (or similar)

**Solution**:
```bash
# Re-install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import torch, transformers, faiss; print('OK')"
```

#### 2. FAISS Index Not Found

**Error**: `FileNotFoundError: FAISS index not found: artifacts/faiss/one-piece-dinov2/index.faiss`

**Solution**:
```bash
# Option A: Download artifacts
pnpm update:sync

# Option B: Build from scratch
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

#### 3. Camera Not Working

**Error**: Camera preview shows black screen or error

**Solution (Windows)**:
1. Open Windows Settings → Privacy → Camera
2. Enable "Allow apps to access your camera"
3. Enable for desktop apps
4. Restart app

**Solution (macOS)**:
1. System Preferences → Security & Privacy → Camera
2. Check the box next to "Electron" or your app name
3. Restart app

**Solution (Linux)**:
```bash
# Check if camera is detected
ls /dev/video*

# Install v4l-utils (if needed)
sudo apt install v4l-utils

# Check camera permissions
sudo usermod -a -G video $USER
# Log out and log back in
```

#### 4. Slow Identification (>2 seconds)

**Possible causes**:
- Running on CPU (expected 200-500ms, can be up to 1-2s on older CPUs)
- Low RAM (<8 GB)
- Antivirus scanning Python process

**Solutions**:
- Use GPU acceleration (see [Prerequisites](#optional-for-gpu-acceleration))
- Close other applications
- Add Python to antivirus exclusions
- Use production build: `NODE_ENV=production pnpm run build:webpack`

#### 5. Desktop App Won't Start

**Error**: `Electron failed to load` or similar

**Solution**:
```bash
# Clean and rebuild
cd apps/desktop
pnpm clean
pnpm build:dev
pnpm start
```

#### 6. pnpm install fails

**Error**: `EACCES: permission denied`

**Solution (macOS/Linux)**:
```bash
# Fix npm/pnpm permissions
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
```

**Solution (Windows)**:
- Run PowerShell/Command Prompt as Administrator
- Or install Node.js with "Add to PATH" option checked

#### 7. EasyOCR Download Errors

**Error**: `Failed to download EasyOCR models`

**Solution**:
```bash
# Pre-download EasyOCR models
python -c "import easyocr; easyocr.Reader(['en'])"
```

**Note**: EasyOCR downloads ~100 MB of models on first run. This is normal.

---

## Platform-Specific Notes

### Windows

- **PowerShell Execution Policy**: If scripts are blocked, run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- **Long Path Support**: Enable if you encounter path length errors:
  1. Run `gpedit.msc`
  2. Navigate to: Computer Configuration → Administrative Templates → System → Filesystem
  3. Enable "Enable Win32 long paths"

- **Windows Defender**: Add Python and Node.js to exclusions for better performance

### macOS

- **Xcode Command Line Tools**: Required for some native modules
  ```bash
  xcode-select --install
  ```

- **Apple Silicon (M1/M2/M3)**: PyTorch automatically uses Metal Performance Shaders (MPS) for GPU acceleration

- **Rosetta 2**: Not required, but can help with compatibility:
  ```bash
  softwareupdate --install-rosetta
  ```

### Linux

- **Display Server**: X11 and Wayland both supported

- **Electron Sandbox**: If app crashes on startup, try disabling sandbox:
  ```bash
  cd apps/desktop
  npm pkg set "build.linux.executableArgs"='["--no-sandbox"]'
  pnpm build
  ```

- **AppImage Permissions**: Make AppImage executable:
  ```bash
  chmod +x CardFlux-*.AppImage
  ```

---

## Uninstallation

### Remove Application

```bash
# Remove Node.js dependencies
pnpm clean

# Remove Python packages
pip uninstall torch torchvision transformers faiss-cpu opencv-python easyocr paddleocr Pillow numpy tqdm -y

# Remove repository
cd ..
rm -rf cardflux
```

### Clean Up Data (Optional)

If you want to free up disk space:

```bash
# Remove downloaded card images (~400 MB)
rm -rf data/images

# Remove embeddings and indices (~15 MB)
rm -rf artifacts/faiss artifacts/metadata/embeddings

# Remove raw scraped data (if present)
rm -rf data/raw
```

---

## Next Steps

After successful deployment:

1. **Test with sample images**: `python scripts/identification/identify_card.py test-images/one-piece/288230.jpg`

2. **Read the user guide**: See `apps/desktop/README.md` for keyboard shortcuts and features

3. **Add more games**: See `docs/guides/LOCAL_DEVELOPMENT.md` for instructions on adding Pokémon, Magic, etc.

4. **Customize settings**: Settings panel allows adjusting confidence thresholds, geometric verification, etc.

---

## Support

### Documentation

- **README.md** - Project overview and quick start
- **docs/guides/LOCAL_DEVELOPMENT.md** - Development workflow
- **docs/guides/TESTING_GUIDE.md** - Running tests
- **apps/desktop/README.md** - Desktop app usage

### Getting Help

1. Check [Troubleshooting](#troubleshooting) section above
2. Review relevant documentation in `docs/`
3. Check GitHub Issues: https://github.com/yourusername/cardflux/issues
4. Review CLAUDE.md for comprehensive system context

---

## Appendix

### Disk Space Usage

| Component | Size | Can Delete? |
|-----------|------|-------------|
| `node_modules/` | ~500 MB | No (required) |
| `data/images/one-piece/` | ~400 MB | Yes (can re-download) |
| `artifacts/faiss/` | ~7 MB | No (required) |
| `artifacts/metadata/embeddings/` | ~7 MB | No (required) |
| `data/curated/` | ~10 MB | No (required) |
| Python packages | ~2 GB | No (required) |
| **Total** | **~3 GB** | - |

### Network Requirements

| Phase | Download Size | Notes |
|-------|---------------|-------|
| Node.js dependencies | ~500 MB | One-time |
| Python dependencies | ~2 GB | One-time |
| Card images | ~400 MB | One-time per game |
| Artifacts (if remote) | ~500 MB | One-time |
| **Total** | **~3.4 GB** | - |

After initial setup, **no internet connection is required** for card identification.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-15
**Maintained By**: CardFlux Engineering Team
