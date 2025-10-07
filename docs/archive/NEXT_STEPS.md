# 🚀 Next Steps for CardFlux

## ✅ What's Working Now

- ✅ TCGplayer scraper (tcgcsv.com) - 192K+ cards across 5 games
- ✅ SQLite database with full-text search and pricing
- ✅ Incremental updates (smart modifiedOn tracking)
- ✅ Data validation and quality checks
- ✅ Local development environment
- ✅ Health check system

---

## 📋 Critical Next Steps

### **1. Fix Data Validation Rules** ⚠️ HIGH PRIORITY

**Issue**: Validation currently shows 39% invalid cards, but most are false positives.

**What to do**:
```bash
# Edit: services/ingest/bin/validate-data.ts
```

**Changes needed**:
1. Add valid rarity types to whitelist:
   - `T` (Tutorial/Theme)
   - `P` (Promo)
   - `Hero` (One Piece/Final Fantasy)
   - `Fixed` (Digimon)
   - `Promo` (all games)
   - `None` (sealed products)

2. Allow products without prices (sealed boxes, displays, bundles)
   - Don't flag sealed products as invalid
   - Check if `productId` contains keywords: "Booster", "Box", "Display", "Pack", "Bundle"

3. Adjust validation threshold:
   - Change from 5% to 15% for initial testing
   - Most "errors" are expected (sealed products don't have individual card pricing)

**Expected result**: ~95%+ validation rate

---

### **2. Run Full Production Scrape** 📦

**Current status**: Only test data exists (~200K cards)

**What to do**:
```bash
# Full scrape (all games, all sets) - takes ~30 min
pnpm tcgplayer:scrape

# Or incremental (if you've run full before)
pnpm tcgplayer:scrape:incremental
```

**Expected output**:
- Magic: ~110K cards
- YuGiOh: ~45K cards
- Pokemon: ~30K cards
- One Piece: ~5K cards
- Digimon: ~2K cards
- **Total: ~200K cards**

---

### **3. Set Up Embeddings Pipeline** 🤖

**Prerequisites**:
```bash
# Install Python dependencies (if not done)
pip install -r requirements.txt
pip install torch transformers pillow faiss-cpu numpy
```

**Run pipeline**:
```bash
# 1. Fetch card images (~30 min, ~5GB)
pnpm pipeline:fetch-images:incremental

# 2. Generate CLIP embeddings (~10 min)
pnpm pipeline:embed:incremental

# 3. Build FAISS search index (~30 sec)
pnpm pipeline:index

# 4. Generate manifests
pnpm pipeline:manifests
```

**Expected artifacts**:
- `data/images/` - Card images (~5GB)
- `artifacts/metadata/embeddings/` - CLIP vectors (~200MB)
- `artifacts/faiss/` - Search indices (~100MB)
- `artifacts/manifests/` - Version metadata

---

### **4. Test Desktop App Integration** 🖥️

**What to do**:
```bash
cd apps/desktop
pnpm install
pnpm dev
```

**Test checklist**:
- [ ] App launches without errors
- [ ] Camera access works
- [ ] Card detection works (may need OpenCV fixes)
- [ ] Search finds cards from database
- [ ] Price info displays correctly

**Known issue**: OpenCV build failures (not critical for scraper, but needed for desktop app)
- May need to install CMake: https://cmake.org/download/
- Or disable OpenCV features temporarily

---

### **5. Set Up Incremental Updates (Daily)** ⏰

**Goal**: Scrape only changed data daily instead of full re-scrape

**How it works**:
- Scraper compares `modifiedOn` timestamps
- Only fetches groups that changed since last run
- Saves ~80-90% time (5 min vs 30 min)

**Setup**:
```bash
# First run: Full scrape
pnpm tcgplayer:scrape

# Daily: Incremental updates
pnpm tcgplayer:scrape:incremental
```

**State file**: `data/state/tcgplayer-incremental.state.json`
- Tracks last sync time
- Stores group checksums
- Auto-updates on each run

---

### **6. Cloud Deployment (When Ready)** ☁️

**Current status**: Everything runs locally, no cloud provider configured

**When you're ready to deploy**:

See `TCGPLAYER_MIGRATION.md#cloud-deployment` for full guide.

**Quick overview**:
1. Choose cloud provider (AWS, GCP, or Azure)
2. Update storage config in code
3. Deploy scraper as scheduled job (Lambda/Cloud Functions)
4. Upload artifacts to CDN
5. Point desktop app to cloud storage

**Cloud-agnostic storage** already implemented:
- `packages/shared/src/cloud-storage.ts`
- Supports S3, GCS, Azure, and local filesystem
- Just update `provider` config when ready

---

## 🍎 Running on MacBook

### **Setup**:
```bash
# 1. Clone repo
git clone https://github.com/ericsngyun/cardflux.git
cd cardflux

# 2. Install Node.js (if not installed)
# Download from: https://nodejs.org (v20+)

# 3. Install pnpm
npm install -g pnpm

# 4. Install dependencies
pnpm install

# 5. Install Python dependencies
pip3 install -r requirements.txt
```

### **Run Health Check**:
```bash
pnpm dev:health
```

**Expected output**:
```
✅ Node.js Version: Node.js v20.x ✓
✅ Python Installation: Python 3.x ✓
✅ Directory Structure: All directories exist ✓
✅ Scraped Data: No curated JSONL files (run scraper first)
✅ Database: Database not built (run: pnpm tcgplayer:db)
✅ FAISS Indices: No FAISS indices built
✅ Disk Usage: Using X GB ✓
✅ API Connectivity: tcgcsv.com API reachable ✓
```

### **Test Scraper (Fast - Magic Only)**:
```bash
# Quick test (~5 min)
pnpm dev:test-scrape

# Validate data
pnpm dev:validate

# Build database
pnpm tcgplayer:db
```

### **Full Pipeline**:
```bash
# One command does it all (~15 min)
pnpm dev:pipeline
```

### **Production Scrape (All Games)**:
```bash
# Full scrape (~30 min)
pnpm tcgplayer:scrape

# Build database
pnpm tcgplayer:db
```

---

## 🐛 Known Issues & Fixes

### **1. OpenCV Build Errors (Desktop App)**
**Error**: `cmake: command not found`

**Fix**:
```bash
# macOS
brew install cmake

# Or disable OpenCV temporarily
# Edit apps/desktop/package.json - remove opencv4nodejs
```

### **2. Python Import Errors**
**Error**: `ModuleNotFoundError: No module named 'faiss'`

**Fix**:
```bash
pip3 install faiss-cpu numpy torch transformers pillow
```

### **3. Disk Space Warnings**
**Issue**: Pipeline uses ~15GB total

**What uses space**:
- Card images: ~5GB (`data/images/`)
- Raw API data: ~2GB (`data/raw/`)
- Database: ~500MB (`artifacts/metadata/`)
- Embeddings: ~200MB (`artifacts/metadata/embeddings/`)

**Cleanup**:
```bash
# Delete raw data (can re-scrape)
rm -rf data/raw/*

# Delete images (can re-download)
rm -rf data/images/*
```

---

## 📊 Performance Benchmarks

| Operation | Duration | Output Size |
|-----------|----------|-------------|
| Health check | <1s | - |
| Test scrape (Magic only) | ~5 min | ~80 MB |
| Full scrape (5 games) | ~30 min | ~115 MB |
| Incremental update | ~5 min | Varies |
| Database build | ~30s | ~500 MB |
| Image fetch (Magic) | ~30 min | ~5 GB |
| Embeddings | ~10 min | ~200 MB |
| FAISS index | ~30s | ~100 MB |
| Full pipeline | ~15 min | All artifacts |

---

## 🎯 Immediate Action Items (Priority Order)

### **This Week**:
1. ✅ ~~Test pipeline with small batch~~ (DONE)
2. 🔧 Fix validation rules (add missing rarity types)
3. 📦 Run full production scrape
4. 🖥️ Test desktop app with real data

### **Next Week**:
5. 🤖 Set up embeddings pipeline
6. 🔍 Test search functionality
7. ⏰ Verify incremental updates work
8. 📝 Document any remaining issues

### **Future**:
9. ☁️ Choose cloud provider
10. 🚀 Deploy to production
11. 📅 Set up daily scraper (Lambda/Cloud Functions)
12. 📊 Add monitoring/alerting

---

## 📚 Related Documentation

- `LOCAL_DEVELOPMENT.md` - Local dev guide
- `TESTING_GUIDE.md` - Complete test procedures
- `TCGPLAYER_MIGRATION.md` - API structure & cloud deployment
- `README.md` - Project overview

---

## 🆘 Need Help?

### **Check logs**:
```bash
# Health check
pnpm dev:health

# Validate data quality
pnpm dev:validate

# Check database
ls -lh artifacts/metadata/cards.db
```

### **Common commands**:
```bash
# Quick test
pnpm dev:test-scrape

# Full pipeline
pnpm dev:pipeline

# Clean and restart
rm -rf data/curated/*
rm -rf artifacts/metadata/*
pnpm tcgplayer:scrape
pnpm tcgplayer:db
```

### **If stuck**:
1. Run health check: `pnpm dev:health`
2. Check for errors in terminal output
3. Review validation report: `pnpm dev:validate`
4. Check git status: `git status`
5. Review recent changes: `git log --oneline -5`

---

**Last updated**: 2025-10-03
**Pipeline status**: ✅ Working (192K cards tested)
**Next milestone**: Production deployment with embeddings
