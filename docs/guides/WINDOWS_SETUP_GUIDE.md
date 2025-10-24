# CardFlux Windows Setup Guide - Complete & Verified

> **Last Updated**: 2025-10-24
> **Status**: Verified on Windows 10/11
> **Time**: 15-20 minutes (fresh install)

---

## Overview

This guide provides **step-by-step instructions** for setting up CardFlux on a fresh Windows machine. Every step has been tested and verified to work correctly.

### What You'll Need

- **Windows 10/11** (64-bit)
- **4 GB free disk space** (temp: 2 GB for downloads)
- **Administrator access** (for installing software)
- **Internet connection** (for downloads)

### What You'll Get

- **Fully functional desktop scanner app**
- **AI identification** (sub-1-second per card)
- **4,813 One Piece TCG cards** indexed and ready
- **Offline operation** (no internet after setup)

---

## Prerequisites Installation

### 1. Install Node.js 20+

**Download**: https://nodejs.org/

1. Click **"Download for Windows"** (LTS version recommended)
2. Run the installer (`node-v20.x.x-x64.msi`)
3. **Check ALL boxes** during installation:
   - ✅ Node.js runtime
   - ✅ npm package manager
   - ✅ Add to PATH
   - ✅ Tools for Native Modules (optional but recommended)
4. Click **Install** and wait (~2 minutes)
5. **Restart your terminal/PowerShell**

**Verify**:
```powershell
node --version
# Should show: v20.15.0 or higher
```

### 2. Install Python 3.10+

**Download**: https://www.python.org/downloads/

1. Download **Python 3.10.x or newer** (Windows installer 64-bit)
2. Run the installer (`python-3.10.x-amd64.exe`)
3. **⚠️ CRITICAL**: Check **"Add Python to PATH"** at the bottom!
4. Click **Install Now**
5. Wait for installation (~3 minutes)
6. **Restart your terminal/PowerShell**

**Verify**:
```powershell
python --version
# Should show: Python 3.10.x or higher
```

**Troubleshooting**:
- If `python` command not found, try `python3` or `py`
- If still not found, add Python to PATH manually:
  1. Search "Environment Variables" in Start menu
  2. Edit "Path" variable
  3. Add: `C:\Users\<YourName>\AppData\Local\Programs\Python\Python310\`
  4. Add: `C:\Users\<YourName>\AppData\Local\Programs\Python\Python310\Scripts\`

### 3. Install Git (Optional but Recommended)

**Download**: https://git-scm.com/download/win

1. Run installer (`Git-2.x.x-64-bit.exe`)
2. Use default options (just click "Next")
3. **Restart your terminal/PowerShell**

**Verify**:
```powershell
git --version
# Should show: git version 2.x.x
```

---

## Project Setup

### Step 1: Clone Repository

```powershell
# Navigate to where you want to install CardFlux
cd C:\Users\YourName\Documents

# Clone the repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux
```

**Alternative** (if not using Git):
1. Download ZIP from GitHub
2. Extract to `C:\Users\YourName\Documents\cardflux`
3. Open PowerShell in that directory

### Step 2: Install pnpm (Node Package Manager)

```powershell
# Install pnpm globally
npm install -g pnpm

# Verify installation
pnpm --version
# Should show: 9.0.0 or higher
```

### Step 3: Install Node.js Dependencies

```powershell
# Install all Node.js packages (takes 2-3 minutes)
pnpm install
```

**Expected output**:
```
Packages: +500
Progress: resolved 500, reused 450, downloaded 50
Done in 2m 15s
```

**Troubleshooting**:
- **Error: EACCES permission denied**: Run PowerShell as Administrator
- **Error: Network timeout**: Check firewall/antivirus settings

### Step 4: Install Python Dependencies

```powershell
# Install Python packages (takes 5-10 minutes, downloads ~2 GB)
pip install -r requirements.txt
```

**Expected output**:
```
Successfully installed torch-2.8.0 transformers-4.57.0 faiss-cpu-1.12.0 ...
```

**Verify installation**:
```powershell
python -c "import torch, transformers, faiss, cv2, PIL; print('✅ All Python packages OK')"
```

**Troubleshooting**:
- **Error: Microsoft Visual C++ required**:
  - Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
  - Install and retry
- **Error: pip not found**:
  - Use `python -m pip install -r requirements.txt`
- **Slow download**:
  - Normal, PyTorch is ~2 GB
  - Use `pip install --upgrade pip` first for better download speeds

---

## Data & Artifacts Setup

CardFlux needs card data and ML artifacts to function. You have **two options**:

### Option A: Download Pre-Built Artifacts (Recommended - 5 minutes)

If artifacts are available in the repository:

```powershell
# Download latest card data and FAISS index from GitHub
pnpm update:sync
```

**What this downloads**:
- `data/curated/one-piece.jsonl` - 4,813 card records (~10 MB)
- `data/images/one-piece/*.jpg` - Card images (~400 MB)
- `artifacts/faiss/one-piece-dinov2/index.faiss` - FAISS index (~7 MB)
- `artifacts/metadata/embeddings/one-piece-dinov2/*.npy` - Embeddings (~7 MB)

**Total**: ~430 MB download

**Verify data**:
```powershell
# Check if files exist
ls data/curated/one-piece.jsonl
ls artifacts/faiss/one-piece-dinov2/index.faiss
ls artifacts/metadata/embeddings/one-piece-dinov2/
```

### Option B: Build Pipeline from Scratch (15-20 minutes)

If you want to build everything yourself:

```powershell
# 1. Scrape card data from TCGPlayer (~2 min)
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# 2. Download card images (~3-5 min)
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# 3. Generate DINOv2 embeddings (~5-8 min on CPU)
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# 4. Build FAISS index (~1 min)
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

**Total time**: 15-20 minutes (mostly image downloads and embedding generation)

---

## Build & Run Desktop App

### Step 1: Build the Desktop App

```powershell
# Navigate to desktop app
cd apps/desktop

# Build for development (includes source maps, faster build)
pnpm build:dev
```

**Expected output**:
```
webpack 5.102.0 compiled with 1 warning in 12095 ms
```

**Note**: The "tar" warning is non-critical and can be ignored.

**Alternative** (production build, slower but optimized):
```powershell
$env:NODE_ENV="production"
pnpm run build:webpack
```

### Step 2: Start the App

```powershell
# Start Electron app
pnpm start
```

**What happens**:
1. **Electron window opens** (~2 seconds)
2. **Python service initializes** (~3-5 seconds)
   - Loads DINOv2 model
   - Loads FAISS index
   - Initializes card detector
3. **Camera preview appears** (if camera connected)
4. **Ready to scan!**

**Expected console output**:
```
[PY] Card Identification Service started
[PY] Waiting for requests...
[PY] Initializing identifier for game: one-piece (version: v2, fallback: True, auto_capture: True)
[PY] Initializing polished card detector...
[PY] Capture manager not available (skipping)
[PY] Identifier, card detector, and capture manager ready (version: v2)
```

**Troubleshooting**:
- **Python service fails to start**:
  - Check Python is in PATH: `python --version`
  - Check Python packages: `python -c "import torch, faiss; print('OK')"`
  - Check logs in console for specific error

- **FAISS index not found**:
  - Verify file exists: `ls ../../artifacts/faiss/one-piece-dinov2/index.faiss`
  - If missing, run Option A or B in Data Setup section

- **Camera not detected**:
  - Windows Settings → Privacy → Camera → Allow desktop apps
  - Restart app after enabling camera

---

## Testing Identification

### Test with Sample Image

```powershell
# Test with a downloaded card image
python ../../scripts/identification/core/production_card_identifier.py ../../data/images/one-piece/288230.jpg
```

**Expected output**:
```
✅ Identified: Marshall.D.Teach (OP05-002) (SR) [HIGH confidence: 0.92]
   Visual: 0.95 | Geometric: 0.87 | Final: 0.92
   Time: 623ms (DINOv2: 112ms | FAISS: 0.2ms | Geometric: 487ms)
```

### Using the Desktop App

1. **Place a card in front of your camera**
2. **Press SPACEBAR** to capture
3. **Wait for identification** (~500-800ms)
4. **Result appears** on the right side panel with:
   - Card name
   - Card number & set
   - Rarity
   - Confidence level (HIGH/MODERATE/LOW)
   - Market price

---

## Common Issues & Solutions

### Issue 1: Python ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'torch'`

**Solution**:
```powershell
# Reinstall Python packages
pip install -r requirements.txt

# Verify
python -c "import torch, transformers, faiss, cv2; print('OK')"
```

### Issue 2: FAISS Index Not Found

**Error**: `FileNotFoundError: FAISS index not found`

**Solution**:
```powershell
# Check if index exists
ls artifacts/faiss/one-piece-dinov2/index.faiss

# If missing, download or rebuild
pnpm update:sync  # OR build from scratch (see Option B above)
```

### Issue 3: Desktop App Won't Start

**Error**: Electron fails to load or crashes

**Solution**:
```powershell
# Clean and rebuild
pnpm clean
pnpm build:dev
pnpm start
```

### Issue 4: Slow Identification (>2 seconds)

**Causes**: Running on CPU (expected), low RAM, antivirus

**Solutions**:
- Close other applications
- Add Python to antivirus exclusions
- Consider GPU acceleration (see Advanced section)
- Use production build: `NODE_ENV=production pnpm run build:webpack`

### Issue 5: PowerShell Execution Policy Error

**Error**: `cannot be loaded because running scripts is disabled`

**Solution**:
```powershell
# Allow scripts for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Retry the command
```

### Issue 6: Camera Permission Denied

**Solution**:
1. Open **Windows Settings**
2. Go to **Privacy → Camera**
3. Enable **"Allow apps to access your camera"**
4. Enable **"Allow desktop apps to access your camera"**
5. Restart the app

---

## Performance Expectations

### Hardware Performance

| Hardware | Identification Speed | Notes |
|----------|---------------------|-------|
| i5-8250U + 8GB RAM | 700-900ms | Typical laptop |
| i7-9700K + 16GB RAM | 500-700ms | Desktop CPU |
| i9-10900K + 32GB RAM | 400-600ms | High-end desktop |
| With NVIDIA GPU | 200-400ms | Requires CUDA setup |

### Component Timing Breakdown

- **DINOv2 Embedding**: 70-130ms (CPU)
- **FAISS Search**: 0.1-0.3ms (very fast!)
- **Geometric Matching** (ORB+AKAZE): 300-800ms (most time)
- **Total**: 500-900ms average on CPU

---

## Advanced Configuration

### GPU Acceleration (NVIDIA Only)

If you have an NVIDIA GPU, you can speed up identification by 2-3x:

1. **Install CUDA Toolkit 12.1+**: https://developer.nvidia.com/cuda-downloads

2. **Install GPU-enabled PyTorch**:
```powershell
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

3. **Install FAISS GPU**:
```powershell
pip uninstall faiss-cpu
pip install faiss-gpu
```

4. **Verify GPU detection**:
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
# Should show: CUDA available: True
```

**Expected speedup**: 200-400ms identification time (vs 500-900ms on CPU)

### Updating Card Data

To get the latest card data:

```powershell
# Pull latest updates from GitHub (if using Git)
pnpm update:sync

# OR rebuild pipeline from scratch
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

---

## File Structure Reference

```
C:\Users\YourName\Documents\cardflux\
├── apps/
│   └── desktop/                    # Electron desktop app
│       ├── src/
│       │   ├── main/               # Electron main process
│       │   ├── renderer/           # React UI
│       │   └── python/             # Python bridge service ⭐
│       ├── dist/                   # Built app (after build)
│       └── package.json
│
├── scripts/
│   └── identification/
│       ├── core/                   # Production identifier ⭐
│       │   ├── production_card_identifier.py
│       │   ├── polished_card_detector.py
│       │   ├── foil_detector.py
│       │   └── __init__.py         # (required for imports)
│       └── tools/                  # Version manager, utilities
│           ├── identifier_version_manager.py
│           └── __init__.py         # (required for imports)
│
├── services/
│   ├── ingest/                     # Data scraping
│   ├── embedder/                   # DINOv2 embedding generation
│   └── indexer/                    # FAISS index building
│
├── data/
│   ├── curated/
│   │   └── one-piece.jsonl         # 4,813 card records ⭐
│   └── images/
│       └── one-piece/              # ~4,700 card images ⭐
│
├── artifacts/
│   ├── faiss/
│   │   └── one-piece-dinov2/
│   │       └── index.faiss         # FAISS index ⭐
│   └── metadata/
│       └── embeddings/
│           └── one-piece-dinov2/
│               ├── embeddings.npy  # DINOv2 embeddings ⭐
│               └── metadata.json
│
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies
└── README.md
```

**⭐ = Critical files required for app to work**

---

## Disk Space Usage

| Component | Size | Can Delete? | Notes |
|-----------|------|-------------|-------|
| `node_modules/` | ~500 MB | No | Required for app |
| `data/images/one-piece/` | ~400 MB | Yes | Can re-download |
| `artifacts/faiss/` | ~7 MB | No | Required for search |
| `artifacts/metadata/embeddings/` | ~7 MB | No | Required for search |
| `data/curated/` | ~10 MB | No | Card metadata |
| Python packages | ~2 GB | No | PyTorch, transformers, etc. |
| **Total** | **~3 GB** | - | - |

---

## Next Steps

After successful setup:

1. **Test with real cards** - Scan some One Piece cards!
2. **Adjust settings** - Open Settings panel in app (confidence thresholds, etc.)
3. **Add more games** - See `docs/guides/LOCAL_DEVELOPMENT.md`
4. **Report issues** - Create GitHub issue if you encounter problems

---

## Support & Documentation

- **This Guide** - Complete Windows setup
- **README.md** - Project overview
- **docs/guides/LOCAL_DEVELOPMENT.md** - Development workflow
- **CLAUDE.md** - Senior engineer context (architecture, design decisions)
- **GitHub Issues** - https://github.com/yourusername/cardflux/issues

---

## Verification Checklist

Before considering setup complete, verify:

- [ ] Node.js 20+ installed (`node --version`)
- [ ] Python 3.10+ installed (`python --version`)
- [ ] pnpm installed (`pnpm --version`)
- [ ] Python packages installed (`python -c "import torch, faiss; print('OK')"`)
- [ ] Node modules installed (`ls node_modules`)
- [ ] Card data exists (`ls data/curated/one-piece.jsonl`)
- [ ] FAISS index exists (`ls artifacts/faiss/one-piece-dinov2/index.faiss`)
- [ ] Desktop app builds (`cd apps/desktop && pnpm build:dev`)
- [ ] Desktop app starts (`pnpm start`)
- [ ] Python service initializes (check console logs)
- [ ] Test identification works (test with sample image)

---

**Document Version**: 1.0
**Last Tested**: 2025-10-24
**Platform**: Windows 10/11 (64-bit)
**Maintained By**: CardFlux Engineering Team
