# CardFlux - Deployment Status

> **Last Updated**: 2025-10-15
> **Status**: Ready for deployment (with data distribution)

---

## 📋 Current Deployment Readiness

### ✅ Code Repository (100% Ready)
All source code, scripts, and documentation are committed and pushed to GitHub:

- Desktop application (production build, v0.2.1)
- Data pipeline scripts (scraper, embedder, indexer)
- Production identification system (DINOv2 + FAISS + ORB)
- Complete documentation (README, guides, architecture docs)
- Dependencies specified (package.json, requirements.txt)

### ⚠️ Data Files (NOT in Git - 323.9 MB gitignored)

The following critical files are **gitignored** and **NOT included** when someone clones the repository:

| Component | Size | Coverage |
|-----------|------|----------|
| `data/curated/one-piece.jsonl` | 2.7 MB | 5,195 cards |
| `data/images/one-piece/` | 307.4 MB | 5,113 images |
| `artifacts/faiss/one-piece-dinov2/` | 7.1 MB | FAISS index |
| `artifacts/metadata/.../embeddings.npy` | ~7 MB | DINOv2 embeddings |
| `artifacts/metadata/.../metadata.jsonl` | 2.7 MB | Card metadata |
| `artifacts/metadata/.../reprints.json` | 4.0 MB | Reprint map |
| **Total** | **~324 MB** | **4,815 cards indexed** |

---

## 🚀 Deployment Options

### For End Users (Desktop App)

**Option 1: Download Pre-built Data Package (Fastest - 5 minutes)**

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/cardflux.git
   cd cardflux
   ```

2. Download the data package:
   - **GitHub Releases**: [Download cardflux-data-v1.0.0.zip](https://github.com/yourusername/cardflux/releases)
   - **Google Drive / Dropbox**: *(Upload the package and share link)*

3. Extract to repository root:
   ```bash
   # Windows
   Expand-Archive cardflux-data-v1.0.0.zip -DestinationPath .

   # macOS/Linux
   unzip cardflux-data-v1.0.0.zip
   ```

4. Install dependencies:
   ```bash
   pnpm install
   pip install -r requirements.txt
   ```

5. Run the app:
   ```bash
   cd apps/desktop
   NODE_ENV=production pnpm run build:webpack
   pnpm start
   ```

**Option 2: Build Data from Scratch (15-20 minutes)**

See [DATA_REQUIREMENTS.md](DATA_REQUIREMENTS.md) for full instructions:

```bash
# 1. Scrape card data
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# 2. Download images
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# 3. Generate embeddings
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# 4. Build reprint map
python scripts/pipeline/build_reprint_map.py
```

---

## 📦 Creating the Data Package (For Maintainers)

To create the distributable data package for users:

```bash
# Run the packaging script
python scripts/dev/package_data.py

# Output: cardflux-data-v1.0.0-2025-10-15.zip (~324 MB)
```

This creates a ZIP file containing:
- All card data and images
- FAISS index and embeddings
- README with installation instructions

**Upload to:**
1. GitHub Releases (recommended)
2. Google Drive / Dropbox
3. AWS S3 / CloudFront (future)

---

## ✅ Verification Checklist

Before distributing, verify:

- [ ] All code committed and pushed to GitHub
- [ ] Desktop app builds successfully (`NODE_ENV=production pnpm run build:webpack`)
- [ ] Desktop app runs successfully (`pnpm start`)
- [ ] Data package created (`python scripts/dev/package_data.py`)
- [ ] Data package size is ~324 MB
- [ ] Test identification works (HIGH confidence on test images)
- [ ] Documentation is up-to-date (README, DATA_REQUIREMENTS, DEMO_SETUP)

---

## 🎯 Current Coverage

- **Total cards in database**: 5,195 One Piece TCG
- **Cards with images downloaded**: 5,113 (98.4%)
- **Cards in FAISS index**: 4,815 (92.7%)
- **Reprint groups**: 1,011 unique card names

---

## 🔄 What Happens When Someone Clones?

```bash
git clone https://github.com/yourusername/cardflux.git
cd cardflux
```

**They will get:**
- ✅ All source code
- ✅ All documentation
- ✅ All scripts
- ✅ Dependencies list

**They will NOT get:**
- ❌ Card data (5,195 cards)
- ❌ Card images (5,113 files)
- ❌ FAISS index
- ❌ Embeddings
- ❌ Metadata

**The desktop app will fail to start** with error:
```
ERROR: FAISS index not found at artifacts/faiss/one-piece-dinov2/index.faiss
```

**Solution**: They must either:
1. Download the pre-built data package (recommended), OR
2. Run the full pipeline to generate data from scratch

---

## 📝 Next Steps

### To Make Fully Deployable:

1. **Create data package:**
   ```bash
   python scripts/dev/package_data.py
   ```

2. **Upload to GitHub Releases:**
   - Go to: https://github.com/yourusername/cardflux/releases
   - Create new release: "v1.0.0 - One Piece TCG Data"
   - Upload `cardflux-data-v1.0.0-2025-10-15.zip`
   - Add release notes

3. **Update DATA_REQUIREMENTS.md** with download link:
   ```markdown
   ### Option 2: Download Pre-built Package (Fastest for Demo)

   1. Download the data package from GitHub Releases:
      [cardflux-data-v1.0.0.zip](https://github.com/yourusername/cardflux/releases/download/v1.0.0/cardflux-data-v1.0.0.zip)
   ```

4. **Test on a clean machine:**
   - Clone repo on different device
   - Download data package
   - Extract and run
   - Verify app works

---

## 🎉 Summary

**Repository Status**: ✅ **Ready for deployment**

**Code**: Fully committed, documented, and ready
**Data**: Available locally, needs distribution mechanism
**Deployment**: Requires one-time data package upload to GitHub Releases

**Time to deploy on new machine** (after data package is created):
- Download code: 1 min
- Download data package: 2 min
- Extract and install: 2 min
- **Total: ~5 minutes**

---

**Document Version**: 1.0
**Last Updated**: 2025-10-15
**Maintainer**: CardFlux Engineering Team
