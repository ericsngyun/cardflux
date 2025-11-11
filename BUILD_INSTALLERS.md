# CardFlux v0.3.0 - Production Installer Build Guide

> **Last Updated**: 2025-11-11
> **Version**: v0.3.0
> **Status**: Ready for production builds

---

## 📋 Prerequisites

### Required Tools

**All Platforms**:
- Node.js 20+ and pnpm 9+
- Python 3.10+
- Git with Git LFS

**Windows**:
- Visual Studio Build Tools 2019+ (for native modules)
- NSIS 3.x (for installer creation)

**macOS**:
- Xcode Command Line Tools
- Apple Developer Account (for code signing)

**Linux**:
- build-essential package
- fuse (for AppImage)

---

## 🔧 Pre-Build Configuration

### 1. electron-builder.json

Already configured with:
```json
{
  "appId": "com.cardflux.desktop",
  "productName": "CardFlux",
  "extraResources": [
    "python-scripts",
    "artifacts/faiss",
    "artifacts/metadata",
    "artifacts/keypoints",
    "data/curated/one-piece-card-game.jsonl"
  ],
  "win": { "target": "nsis" },
  "mac": { "target": "dmg" },
  "linux": { "target": "AppImage" }
}
```

### 2. package.json

✅ **FIXED**: Moved `electron` from `dependencies` to `devDependencies`

```json
{
  "version": "0.3.0",
  "dependencies": {
    "@cardflux/config": "workspace:*",
    "@cardflux/shared": "workspace:*",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.0"
  }
}
```

---

## 🚀 Build Commands

### Windows NSIS Installer

```bash
cd apps/desktop

# 1. Build production webpack bundle
pnpm build:webpack

# 2. Build Windows installer (x64)
pnpm exec electron-builder --win --x64

# Output: out/CardFlux Setup 0.3.0.exe (~180MB)
```

**Build Time**: ~5-8 minutes
**Output Size**: ~180MB (includes all data files)

### macOS DMG Installer

```bash
cd apps/desktop

# 1. Build production webpack bundle
pnpm build:webpack

# 2. Build macOS installer (Universal: x64 + arm64)
pnpm exec electron-builder --mac --universal

# Output: out/CardFlux-0.3.0-universal.dmg (~190MB)
```

**Build Time**: ~8-12 minutes
**Output Size**: ~190MB (universal binary)

**⚠️ Code Signing Required**:
- Export Apple Developer certificate
- Set environment variables:
  ```bash
  export CSC_LINK=/path/to/certificate.p12
  export CSC_KEY_PASSWORD=your_password
  ```

### Linux AppImage

```bash
cd apps/desktop

# 1. Build production webpack bundle
pnpm build:webpack

# 2. Build Linux AppImage (x64)
pnpm exec electron-builder --linux --x64

# Output: out/CardFlux-0.3.0.AppImage (~185MB)
```

**Build Time**: ~6-9 minutes
**Output Size**: ~185MB

---

## 📦 Build All Platforms

```bash
cd apps/desktop

# Build production webpack once
pnpm build:webpack

# Build all platforms
pnpm exec electron-builder --win --mac --linux
```

**Total Build Time**: ~20-30 minutes
**Total Output Size**: ~555MB

---

## ✅ Post-Build Verification

### 1. Verify Installer Outputs

```bash
cd apps/desktop/out
ls -lh

# Expected outputs:
# - CardFlux Setup 0.3.0.exe          (~180MB, Windows)
# - CardFlux-0.3.0-universal.dmg      (~190MB, macOS)
# - CardFlux-0.3.0.AppImage           (~185MB, Linux)
```

### 2. Test Installation

**Windows**:
1. Run `CardFlux Setup 0.3.0.exe`
2. Install to `C:\Program Files\CardFlux`
3. Launch CardFlux from Start Menu
4. Verify Python service initializes (~4s)
5. Test camera detection
6. Test card identification

**macOS**:
1. Open `CardFlux-0.3.0-universal.dmg`
2. Drag CardFlux.app to Applications
3. Right-click → Open (first launch, bypass Gatekeeper)
4. Grant camera permissions
5. Test functionality

**Linux**:
1. Make executable: `chmod +x CardFlux-0.3.0.AppImage`
2. Run: `./CardFlux-0.3.0.AppImage`
3. Grant camera permissions
4. Test functionality

### 3. Verify Bundled Files

After installation, verify these files exist:

```
CardFlux/
├── resources/
│   ├── python-scripts/
│   │   └── optimized_identification_service.py
│   ├── artifacts/
│   │   ├── faiss/one-piece-dinov2/index.faiss (7.1MB)
│   │   ├── metadata/embeddings/metadata.jsonl (23MB)
│   │   └── keypoints/one-piece/*.npy (120MB)
│   └── data/curated/one-piece-card-game.jsonl (2.3MB)
```

---

## 🐛 Common Build Issues

### Issue 1: "electron must be in devDependencies"

**Error**:
```
⨯ Package "electron" is only allowed in "devDependencies"
```

**Solution**: ✅ **FIXED** - Moved electron to devDependencies

### Issue 2: Large installer size

**Cause**: Bundling 120MB keypoints cache + 23MB metadata

**Solutions**:
- ✅ **Accept it**: Production-ready with instant UX
- ⚠️ **Remove keypoints**: -120MB, but 60% slower geometric matching
- ⚠️ **Download on first run**: Smaller installer, but poor UX

**Recommendation**: Keep current approach for v0.3.0

### Issue 3: Code signing errors (macOS)

**Error**:
```
⨯ Command failed: codesign ...
```

**Solution**:
1. Disable hardening in electron-builder.json:
   ```json
   "mac": { "hardenedRuntime": false }
   ```
2. OR provide proper certificate:
   ```bash
   export CSC_LINK=/path/to/cert.p12
   export CSC_KEY_PASSWORD=password
   ```

### Issue 4: Missing Python dependencies

**Error**:
```
ModuleNotFoundError: No module named 'torch'
```

**Solution**: User must install Python 3.10+ and dependencies:
```bash
pip install -r requirements.txt
```

**⚠️ Note**: We're NOT bundling Python runtime in v0.3.0 (requires system Python)

---

## 📊 Installer Contents

### Included in Installer

✅ **Application Code**:
- Electron main process (dist/main/)
- React renderer (dist/renderer/)
- Python scripts (src/python/)

✅ **Data Files** (v0.3.0):
- FAISS index (7.1MB)
- Card metadata (23MB)
- Pre-computed keypoints (120MB)
- One Piece card database (2.3MB)

✅ **Configuration**:
- electron-builder.json
- package.json

### NOT Included (User Must Install)

❌ **Python Runtime**: System Python 3.10+ required
❌ **Python Dependencies**: torch, transformers, faiss-cpu, opencv-python
❌ **Node.js**: Not needed after installation

---

## 🚢 Distribution Checklist

### Before Release

- [x] Update version in package.json (0.3.0)
- [x] Update CHANGELOG.md
- [x] Git tag v0.3.0
- [x] Move electron to devDependencies
- [x] Update electron-builder.json with data files
- [ ] Build all platform installers
- [ ] Test on clean Windows 10/11
- [ ] Test on clean macOS (Intel + Apple Silicon)
- [ ] Test on clean Ubuntu 22.04
- [ ] Sign macOS installer (optional for beta)
- [ ] Sign Windows installer (optional for beta)
- [ ] Upload to GitHub Releases
- [ ] Create installation guide for users

### GitHub Release

1. Go to https://github.com/ericsngyun/cardflux/releases
2. Click "Draft a new release"
3. Select tag: `v0.3.0`
4. Upload installers:
   - CardFlux Setup 0.3.0.exe
   - CardFlux-0.3.0-universal.dmg
   - CardFlux-0.3.0.AppImage
5. Add release notes (from CHANGELOG.md)
6. Publish release

---

## 📝 Installation Instructions for Users

### Windows

1. Download `CardFlux Setup 0.3.0.exe`
2. Run installer (allow SmartScreen if prompted)
3. Install Python 3.10+ from python.org
4. Install dependencies:
   ```cmd
   pip install torch torchvision transformers faiss-cpu opencv-python pillow numpy
   ```
5. Launch CardFlux from Start Menu

### macOS

1. Download `CardFlux-0.3.0-universal.dmg`
2. Open DMG and drag to Applications
3. Right-click CardFlux.app → Open (first time)
4. Install Python 3.10+ (Homebrew recommended):
   ```bash
   brew install python@3.10
   ```
5. Install dependencies:
   ```bash
   pip3 install torch torchvision transformers faiss-cpu opencv-python pillow numpy
   ```
6. Grant camera permissions when prompted
7. Launch CardFlux

### Linux (Ubuntu/Debian)

1. Download `CardFlux-0.3.0.AppImage`
2. Make executable:
   ```bash
   chmod +x CardFlux-0.3.0.AppImage
   ```
3. Install Python 3.10+:
   ```bash
   sudo apt update
   sudo apt install python3.10 python3-pip
   ```
4. Install dependencies:
   ```bash
   pip3 install torch torchvision transformers faiss-cpu opencv-python pillow numpy
   ```
5. Run:
   ```bash
   ./CardFlux-0.3.0.AppImage
   ```

---

## 🎯 Next Steps (v0.4.0)

### Bundle Python Runtime

**Goal**: Eliminate "install Python" step for users

**Approach**:
1. Use `python-build-standalone` for portable Python
2. Bundle torch, transformers, faiss in installer
3. Update resource-manager.ts to use bundled Python
4. Increase installer size (~400MB)

**Benefit**: One-click install, no dependencies

### Code Signing

**Windows**:
- Purchase code signing certificate (~$200/year)
- Sign .exe with SignTool
- No SmartScreen warnings

**macOS**:
- Apple Developer Program ($99/year)
- Notarize .dmg with Apple
- No Gatekeeper warnings

---

**Status**: Build configuration ready, installers can be built anytime
**Next**: Test builds on clean machines, then distribute to beta testers

