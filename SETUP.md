# CardFlux Setup Guide

> Complete setup instructions for developers on Windows, macOS, and Linux

This guide ensures you can successfully build and run CardFlux on any device after cloning from the repository.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Verification](#verification)
- [Common Issues](#common-issues)
- [Platform-Specific Notes](#platform-specific-notes)

---

## Prerequisites

**Install these BEFORE cloning the repository:**

### 1. Git with Git LFS

Git LFS is **CRITICAL** - without it, you'll get pointer files instead of actual data.

```bash
# Check if Git LFS is installed
git lfs version

# If not installed:
# Windows: Download from https://git-lfs.github.com/
# macOS: brew install git-lfs
# Linux: sudo apt-get install git-lfs

# Initialize Git LFS (first time only)
git lfs install
```

### 2. Node.js 20+

```bash
# Check version
node --version  # Must be >= v20.0.0

# If not installed or wrong version:
# Windows: Download from https://nodejs.org/
# macOS: brew install node@20
# Linux: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
#        sudo apt-get install -y nodejs
```

### 3. pnpm 9+

```bash
# Check version
pnpm --version  # Must be >= 9.0.0

# Install pnpm globally
npm install -g pnpm@9.0.0
```

### 4. Python 3.10+

```bash
# Check version
python --version  # Must be >= 3.10

# If not installed:
# Windows: Download from https://www.python.org/downloads/
# macOS: brew install python@3.10
# Linux: sudo apt-get install python3.10 python3.10-venv python3-pip
```

### 5. Build Tools (Platform-Specific)

**Windows:**
```powershell
# Install Visual Studio Build Tools (required for node-gyp, better-sqlite3)
# Download: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++" workload
# OR install via chocolatey:
choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools"
```

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

**Linux (Ubuntu/Debian):**
```bash
# Install build essentials
sudo apt-get update
sudo apt-get install -y build-essential python3-dev
```

---

## Quick Start

**For experienced developers who have all prerequisites installed:**

```bash
# 1. Clone with LFS
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# 2. Verify LFS files downloaded
git lfs ls-files
# Should show 3 files: index.faiss, metadata.jsonl, one-piece.jsonl

# 3. Install Node dependencies
pnpm install

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Build all packages
pnpm build

# 6. Run desktop app
cd apps/desktop
pnpm start
```

---

## Detailed Setup

### Step 1: Clone Repository with Git LFS

```bash
# Clone repository (LFS files auto-download)
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Verify LFS files downloaded correctly
git lfs ls-files

# Expected output:
# e5d9378db9 * artifacts/faiss/one-piece-dinov2/index.faiss
# eda3a723de * artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl
# dc60a79c16 * data/curated/one-piece.jsonl

# If files show as small (<1KB), LFS didn't work. Run:
git lfs pull
```

### Step 2: Install Node.js Dependencies

```bash
# From project root
pnpm install

# This installs dependencies for all workspaces:
# - Root monorepo
# - apps/desktop
# - packages/config
# - packages/shared
# - services/*
```

### Step 3: Install Python Dependencies

**Option A: System-wide installation**
```bash
pip install -r requirements.txt
```

**Option B: Virtual environment (recommended)**
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Python dependencies installed:**
- PyTorch 2.1+ (ML framework)
- Transformers 4.35+ (DINOv2 model)
- FAISS 1.7.4+ (vector search)
- OpenCV 4.8+ (image processing)
- Pillow 10.1+ (image loading)
- EasyOCR/PaddleOCR (text recognition)
- NumPy 1.24+ (numerical computing)

### Step 4: Verify Installation

```bash
# Check Node environment
node --version    # >= v20.0.0
pnpm --version    # >= 9.0.0

# Check Python environment
python --version  # >= 3.10
pip list | grep torch
pip list | grep faiss
pip list | grep opencv

# Check Git LFS
git lfs ls-files | wc -l  # Should be 3
```

### Step 5: Build Project

```bash
# Build all packages (from root)
pnpm build

# This builds in order:
# 1. packages/config
# 2. packages/shared
# 3. services/*
# 4. apps/desktop
```

**What gets built:**
- TypeScript files compiled to JavaScript
- Webpack bundles for Electron app
- Python scripts copied to dist

### Step 6: Run Desktop App

```bash
# Development mode (hot reload)
cd apps/desktop
pnpm build:dev
pnpm start

# Production mode
cd apps/desktop
pnpm build
pnpm start
```

**First run:**
- Python subprocess starts (3-5 seconds)
- FAISS index loads (~7MB)
- Embeddings load (~7MB)
- Camera permission prompt (allow for scanning)

---

## Data Pipeline Setup (Optional)

**Note:** The repository includes pre-built FAISS index and embeddings for One Piece TCG. You only need to run the pipeline if:
- You want to update the data
- You want to add a new TCG game
- You're developing pipeline features

### Download Card Images (Not in Git)

Card images (~400MB) are excluded from Git. To download:

```bash
# Option 1: Download from GitHub Releases (fastest)
# Visit: https://github.com/yourusername/cardflux/releases
# Download: cardflux-data-one-piece-vX.X.X.zip
# Extract to: data/images/

# Option 2: Scrape from TCGPlayer (requires API, ~3 minutes)
pnpm tsx services/ingest/bin/fetch_images.ts
```

### Run Data Pipeline

```bash
# Full pipeline (from scratch, ~15 minutes)
# 1. Scrape card data from TCGPlayer
pnpm tcgplayer:scrape

# 2. Download card images (~400MB, 3 min)
pnpm tsx services/ingest/bin/fetch_images.ts

# 3. Generate embeddings with DINOv2 (5 min)
pnpm pipeline:embed

# 4. Build FAISS index (2 min)
pnpm pipeline:index

# OR: Run all steps at once
pnpm pipeline:all
```

### Incremental Updates (Daily)

```bash
# Update only new/changed cards
pnpm pipeline:update

# Sync from cloud (GitHub artifacts)
pnpm update:sync
```

---

## Verification

### Test Desktop App Build

```bash
cd apps/desktop
pnpm build:dev

# Check dist folder exists
ls dist/main/index.js
ls dist/renderer/app.js
ls dist/python/identification_service.py

# Run app
pnpm start
```

### Test Card Identification

```bash
# Test with sample image
python scripts/identification/core/production_card_identifier.py test-images/one-piece/luffy.jpg

# Expected output:
# Identified: Monkey.D.Luffy [OP01-001]
# Confidence: HIGH
# Score: 0.92
# Time: ~500ms
```

### Test Full Identification Suite

```bash
# Run comprehensive test suite (19 test images)
python scripts/identification/tests/test_all_production_images.py

# Expected results:
# - 100% detection rate
# - 47% HIGH confidence
# - 42% MODERATE confidence
# - 11% LOW confidence
# - 778ms average time
```

### Verify Git LFS Files

```bash
# Check file sizes (should be large, not <1KB)
ls -lh artifacts/faiss/one-piece-dinov2/index.faiss
# Expected: ~7MB

ls -lh data/curated/one-piece.jsonl
# Expected: ~3MB

# If files are <1KB, they're LFS pointers. Fix with:
git lfs pull
```

---

## Common Issues

### Issue 1: Git LFS Files Not Downloaded

**Symptoms:**
```bash
Error: Cannot load FAISS index
FileNotFoundError: artifacts/faiss/one-piece-dinov2/index.faiss
```

**Cause:** Git LFS not installed before cloning, or `git lfs pull` never ran.

**Solution:**
```bash
# Install Git LFS
git lfs install

# Pull LFS files
git lfs pull

# Verify
git lfs ls-files
```

---

### Issue 2: `better-sqlite3` Build Failure

**Symptoms:**
```
Error: node-gyp rebuild failed
gyp ERR! stack Error: Could not find Visual Studio
```

**Cause:** Missing C++ build tools.

**Solution (Windows):**
```powershell
# Install Visual Studio Build Tools
# https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"

# OR use npm windows-build-tools (deprecated but may work):
npm install --global windows-build-tools
```

**Solution (macOS):**
```bash
xcode-select --install
```

**Solution (Linux):**
```bash
sudo apt-get install build-essential python3-dev
```

---

### Issue 3: Workspace Dependencies Not Found

**Symptoms:**
```
Error: Cannot find module '@cardflux/config'
Module not found: @cardflux/shared
```

**Cause:** Workspace packages not built before dependent packages.

**Solution:**
```bash
# Clean and rebuild from root
pnpm clean
rm -rf node_modules
pnpm install
pnpm build
```

---

### Issue 4: Python Module Not Found

**Symptoms:**
```python
ModuleNotFoundError: No module named 'torch'
ModuleNotFoundError: No module named 'faiss'
```

**Cause:** Python dependencies not installed.

**Solution:**
```bash
# Check Python version first
python --version  # Must be >= 3.10

# Reinstall dependencies
pip install -r requirements.txt

# If using virtual environment, make sure it's activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\Activate.ps1  # Windows
```

---

### Issue 5: FAISS CPU vs GPU Mismatch

**Symptoms:**
```
RuntimeError: module compiled against API version 0x10 but this version of numpy is 0x10
```

**Cause:** Incompatible NumPy/FAISS versions, or trying to use GPU FAISS without CUDA.

**Solution:**
```bash
# Reinstall compatible versions
pip uninstall faiss-cpu faiss-gpu numpy -y
pip install faiss-cpu==1.7.4 numpy==1.24.0

# For GPU support (requires CUDA 11+):
pip install faiss-gpu==1.7.4
```

---

### Issue 6: pnpm Not Found

**Symptoms:**
```
pnpm: command not found
```

**Cause:** pnpm not installed globally.

**Solution:**
```bash
npm install -g pnpm@9.0.0

# Verify
pnpm --version
```

---

### Issue 7: Wrong Node Version

**Symptoms:**
```
error Engine "node" is incompatible with this module
```

**Cause:** Node.js version < 20.0.0.

**Solution:**
```bash
# Check version
node --version

# Install Node 20 using nvm (recommended):
# Install nvm: https://github.com/nvm-sh/nvm
nvm install 20
nvm use 20

# Or download directly:
# https://nodejs.org/en/download/
```

---

### Issue 8: Build Hangs on Windows

**Symptoms:**
Build process freezes during webpack compilation.

**Cause:** Windows Defender or antivirus scanning node_modules.

**Solution:**
```powershell
# Add exclusions to Windows Defender
# 1. Open Windows Security
# 2. Virus & threat protection > Manage settings
# 3. Exclusions > Add an exclusion > Folder
# 4. Add: C:\Users\<your-username>\eric\cardflux\node_modules
```

---

## Platform-Specific Notes

### Windows

**PowerShell Execution Policy:**
```powershell
# If you get "script execution disabled" errors:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Long Path Support:**
```powershell
# Enable long paths (node_modules can be deep)
# Run as Administrator:
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

**Python from Microsoft Store:**
If you installed Python from Microsoft Store, use `python3` instead of `python`:
```powershell
python3 --version
python3 -m pip install -r requirements.txt
```

---

### macOS

**Apple Silicon (M1/M2/M3):**
```bash
# PyTorch supports Apple Silicon natively
# Install with MPS (Metal Performance Shaders) support:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Rosetta 2 not required
```

**Homebrew Permissions:**
```bash
# If brew install fails with permissions error:
sudo chown -R $(whoami) /usr/local/Homebrew
```

---

### Linux

**Ubuntu/Debian:**
```bash
# Install all prerequisites at once
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  python3.10 \
  python3.10-venv \
  python3-pip \
  git \
  git-lfs \
  curl

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install pnpm
npm install -g pnpm@9.0.0
```

**Fedora/RHEL:**
```bash
# Install build tools
sudo dnf groupinstall "Development Tools"
sudo dnf install python3-devel

# Install Node.js 20
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# Install pnpm
npm install -g pnpm@9.0.0
```

---

## Environment Variables (Optional)

Create `.env` file in project root for advanced configuration:

```bash
# Python environment
PYTHON_PATH=/path/to/python3.10

# Identification settings
FAISS_INDEX_PATH=artifacts/faiss/one-piece-dinov2/index.faiss
EMBEDDINGS_PATH=artifacts/metadata/embeddings/one-piece-dinov2
CONFIDENCE_THRESHOLD_HIGH=0.75
CONFIDENCE_THRESHOLD_MODERATE=0.62

# OCR settings
OCR_ENGINE=easyocr  # or 'paddleocr'

# Development
NODE_ENV=development
```

---

## Next Steps

After successful setup:

1. **Test the Desktop App:**
   ```bash
   cd apps/desktop
   pnpm start
   ```

2. **Read the Documentation:**
   - [CLAUDE.md](CLAUDE.md) - Project overview and architecture
   - [docs/guides/LOCAL_DEVELOPMENT.md](docs/guides/LOCAL_DEVELOPMENT.md) - Development workflow
   - [docs/guides/TESTING_GUIDE.md](docs/guides/TESTING_GUIDE.md) - Testing procedures

3. **Run Tests:**
   ```bash
   # TypeScript type checking
   pnpm typecheck

   # Identification accuracy tests
   python scripts/identification/tests/test_all_production_images.py
   ```

4. **Try Card Identification:**
   - Launch desktop app
   - Point camera at a One Piece card
   - Press SPACE to capture
   - See instant identification

---

## Troubleshooting Checklist

If build fails, verify each item:

- [ ] Git LFS installed and initialized (`git lfs version`)
- [ ] LFS files downloaded (3 files, not pointers)
- [ ] Node.js 20+ installed (`node --version`)
- [ ] pnpm 9+ installed (`pnpm --version`)
- [ ] Python 3.10+ installed (`python --version`)
- [ ] Build tools installed (Visual Studio/Xcode/build-essential)
- [ ] `pnpm install` completed without errors
- [ ] `pip install -r requirements.txt` completed
- [ ] `pnpm build` from root successful
- [ ] No firewall/antivirus blocking node_modules

---

## Getting Help

If you're still stuck after following this guide:

1. **Check existing issues:** [GitHub Issues](https://github.com/yourusername/cardflux/issues)
2. **Search documentation:** `/docs` directory
3. **Create new issue:** Include:
   - Operating system and version
   - Node/pnpm/Python versions
   - Full error message
   - Steps you've already tried

---

## Quick Reference Commands

```bash
# Setup
git lfs install
git clone <repo>
pnpm install
pip install -r requirements.txt
pnpm build

# Development
pnpm dev                    # Run desktop app dev mode
pnpm typecheck              # Type check all packages
pnpm build                  # Build all packages

# Desktop App
cd apps/desktop
pnpm build:dev              # Build dev version
pnpm start                  # Run app

# Testing
python scripts/identification/tests/test_all_production_images.py
python scripts/identification/core/production_card_identifier.py <image>

# Data Pipeline
pnpm tcgplayer:scrape       # Scrape card data
pnpm pipeline:update        # Incremental update
pnpm update:sync            # Sync from cloud

# Cleanup
pnpm clean                  # Clean build outputs
rm -rf node_modules         # Remove dependencies
git lfs pull                # Re-download LFS files
```

---

**Status**: Last updated 2025-10-29 | Production-ready for One Piece TCG
