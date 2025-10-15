# CardFlux Desktop - Quick Demo Setup

> **For Demo/Testing**: Get the desktop scanner running in under 10 minutes
> **Last Updated**: 2025-10-15
> **Version**: v1.0.0-demo

---

## 🚀 Super Quick Start (3 Steps)

### Prerequisites
- **Node.js 20+**: [Download](https://nodejs.org/)
- **Python 3.10+**: [Download](https://www.python.org/downloads/)
- **Git**: [Download](https://git-scm.com/)
- **Webcam**: Any webcam (720p or better recommended)

---

## Step 1: Clone & Install (5 minutes)

```bash
# Clone repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Install Node dependencies
npm install -g pnpm
pnpm install

# Install Python dependencies
pip install -r requirements.txt
```

**Windows users**: If you get permission errors, run PowerShell as Administrator

---

## Step 2: Build Desktop App (1 minute)

```bash
cd apps/desktop

# Production build (optimized, 225 KB)
NODE_ENV=production pnpm run build:webpack
```

**Expected output**: `webpack 5.x.x compiled successfully`

---

## Step 3: Launch! (30 seconds)

```bash
pnpm start
```

**What happens**:
1. Electron window opens (2s)
2. Python service initializes (3s)
3. Camera preview starts
4. **"System initialized - Ready to scan!"** notification appears

**You're done!** 🎉

---

## 🎮 How to Use

### Basic Scanning
1. **Place a One Piece TCG card** in front of camera
2. **Press SPACE** to capture
3. **Wait** ~200-500ms for identification
4. **Card appears** in stack on right with price

### Keyboard Shortcuts
- `SPACE` - Capture card
- `C` - Clear stack
- `E` - Export to CSV
- `S` - Open settings
- `ESC` - Dismiss notification

### Features to Demo
1. **Fast scanning**: Point out the ~200-500ms speed
2. **Flash animation**: White flash when capturing
3. **Confidence scores**: HIGH (green) vs MODERATE (orange)
4. **Duplicate detection**: Scan same card twice
5. **Statistics**: Footer shows success rate and scans/min
6. **Export**: Press `E` to get CSV instantly

---

## 📊 What's Included

- **2,826 One Piece TCG cards** indexed
- **DINOv2 AI model** for visual identification
- **ORB geometric verification** (watermark-resistant)
- **Offline operation** (no internet needed after setup)

---

## ⚠️ Known Limitations (Demo Version)

1. **No card images displayed** - Only text metadata (name, price, rarity)
2. **One Piece TCG only** - Other games not yet supported
3. **53% card coverage** - 2,826 of 5,195 total cards (some images failed to download)
4. **No inventory features** - Price checking only

**This is a proof-of-concept demo**, not production-ready for shop deployment.

---

## 🐛 Troubleshooting

### App won't start
```bash
cd apps/desktop
pnpm clean
pnpm build:dev
pnpm start
```

### Python module not found
```bash
pip install -r requirements.txt
python -c "import torch, transformers, faiss; print('OK')"
```

### Camera not working
- **Windows**: Settings → Privacy → Camera → Allow apps
- **macOS**: System Preferences → Security & Privacy → Camera → Check "Electron"
- **Linux**: `sudo usermod -a -G video $USER` (then log out/in)

### Slow identification (>2 seconds)
- Close other applications
- Use production build: `NODE_ENV=production pnpm run build:webpack`
- Expected: 200-500ms on modern CPU

---

## 📖 Full Documentation

For production deployment, troubleshooting, or development:
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive setup guide
- **[README.md](README.md)** - Project overview
- **[apps/desktop/README.md](apps/desktop/README.md)** - Desktop app features

---

## 🎯 Demo Checklist

Before showing the demo:

- [ ] App starts successfully (<5s total)
- [ ] Camera preview is visible
- [ ] "Ready to scan!" notification appears
- [ ] Test scan shows flash animation
- [ ] Card appears in stack with price
- [ ] Footer shows statistics after scan
- [ ] Keyboard shortcuts work (C, E, S)

---

## 🚀 Next Steps

**To expand beyond demo**:
1. Download remaining card images (see DEPLOYMENT_GUIDE.md)
2. Add more TCG games (Pokémon, Magic, etc.)
3. Implement card image display
4. Add inventory management features

---

## 💡 Demo Tips

**What to highlight**:
- **Speed**: "Notice it identifies in under half a second!"
- **Accuracy**: "See the confidence score - HIGH means certain match"
- **Feedback**: "Watch what happens when I scan a bad photo..."
- **Stats**: "Look at the success rate tracking in the footer"
- **Shortcuts**: "Press E to export everything instantly"

**What NOT to say**:
- ❌ "It has every One Piece card" (only 53%)
- ❌ "It's ready for production" (demo version)
- ❌ "You can see the card images" (not implemented)

**What to say instead**:
- ✅ "This demo shows the core technology working"
- ✅ "We have 2,826 cards indexed as proof-of-concept"
- ✅ "The identification accuracy is 100% on clean images"

---

**Version**: 1.0.0-demo
**Build Date**: 2025-10-15
**Contact**: See README.md for support
