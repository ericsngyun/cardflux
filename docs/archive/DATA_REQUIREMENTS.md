# CardFlux - Required Data Files

> **⚠️ IMPORTANT**: The CardFlux repository does NOT include data files due to size constraints (3+ GB).
> **You must obtain the required data** before the app will work.

---

## 📦 What's Missing from Git

When you clone this repository, these critical directories will be **empty**:

```
data/                    ← All card data (gitignored)
├── curated/
│   └── one-piece.jsonl  ← 2.7 MB - Card metadata (5,195 cards)
└── images/
    └── one-piece/       ← 400 MB - Card images (5,113 files)

artifacts/               ← All ML artifacts (gitignored)
├── faiss/
│   └── one-piece-dinov2/
│       ├── index.faiss  ← 7.1 MB - FAISS vector index
│       ├── ids.json     ← Card ID mapping
│       └── index_config.json
└── metadata/
    └── embeddings/
        └── one-piece-dinov2/
            ├── embeddings.npy    ← 7.4 MB - DINOv2 embeddings
            ├── metadata.jsonl    ← Card information
            └── reprints.json     ← Reprint mapping
```

**Total size**: ~600 MB compressed, ~1.2 GB uncompressed

---

## 🚀 How to Get the Data

You have **3 options** to obtain the required data:

### Option 1: Build from Scratch (Recommended for Development)

**Build the complete pipeline** (takes ~15 minutes):

```bash
# 1. Scrape card data from TCGPlayer
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# 2. Download card images
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# 3. Generate DINOv2 embeddings
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# 4. Build FAISS index
python services/indexer/bin/build_faiss_onepiece_dinov2.py

# 5. Build reprint map
python scripts/pipeline/build_reprint_map.py
```

**Pros**:
- Fresh data from TCGPlayer
- Full control over the process
- No external dependencies

**Cons**:
- Takes 15-20 minutes
- Requires ~3 GB download bandwidth
- May hit rate limits on TCGPlayer API

---

### Option 2: Download Pre-built Package (Fastest for Demo)

**If a pre-built data package is available**:

1. **Download** the artifacts package:
   - Check GitHub Releases for `cardflux-data-v1.0.0.zip`
   - Or contact the maintainer for the latest package

2. **Extract** to project root:
   ```bash
   # Windows
   Expand-Archive cardflux-data-v1.0.0.zip -DestinationPath .

   # macOS/Linux
   unzip cardflux-data-v1.0.0.zip
   ```

3. **Verify** structure:
   ```bash
   # Should see these files
   ls data/curated/one-piece.jsonl
   ls artifacts/faiss/one-piece-dinov2/index.faiss
   ```

**Pros**:
- Instant setup (3-5 minutes)
- No API rate limits
- Guaranteed to work

**Cons**:
- Data may be outdated
- Requires external download source

---

### Option 3: Use Git LFS (If Configured)

**If the repository uses Git LFS** (currently not configured):

```bash
# Install Git LFS
git lfs install

# Pull large files
git lfs pull
```

**Note**: This option is currently **NOT available** as we haven't configured Git LFS yet.

---

## ✅ Verification

After obtaining the data, verify everything is in place:

```bash
# Run verification script
# Windows
pwsh scripts/setup/verify-setup.ps1

# macOS/Linux
./scripts/setup/verify-setup.sh
```

**Expected output**:
```
✓ Node.js 20.x.x installed
✓ Python 3.10.x installed
✓ pnpm 9.x.x installed
✓ Project structure valid
✓ Data files present
✓ Artifacts present
✓ Python packages installed

All checks passed! Ready to build.
```

---

## 📋 Required Files Checklist

Before running the app, ensure these files exist:

### Data Files (Required)
- [ ] `data/curated/one-piece.jsonl` (2.7 MB)
- [ ] `data/images/one-piece/*.jpg` (2,732+ files, ~400 MB)

### Artifacts (Required)
- [ ] `artifacts/faiss/one-piece-dinov2/index.faiss` (7.1 MB)
- [ ] `artifacts/faiss/one-piece-dinov2/ids.json` (~100 KB)
- [ ] `artifacts/faiss/one-piece-dinov2/index_config.json` (~1 KB)
- [ ] `artifacts/metadata/embeddings/one-piece-dinov2/embeddings.npy` (7.4 MB)
- [ ] `artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl` (~10 MB)
- [ ] `artifacts/metadata/embeddings/one-piece-dinov2/reprints.json` (~500 KB)

---

## 🐛 Troubleshooting

### App fails with "FAISS index not found"

**Cause**: Missing `artifacts/faiss/one-piece-dinov2/index.faiss`

**Solution**:
```bash
# Build from scratch
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

---

### App fails with "Card metadata not found"

**Cause**: Missing `data/curated/one-piece.jsonl`

**Solution**:
```bash
# Scrape fresh data
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts
```

---

### Embeddings generation fails

**Cause**: Missing card images

**Solution**:
```bash
# Download images
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# Verify images downloaded
ls data/images/one-piece/ | wc -l  # Should show 2732+
```

---

## 📊 Data Statistics

| Component | Files | Total Size | Compressed |
|-----------|-------|------------|------------|
| Card metadata | 1 | 2.7 MB | ~500 KB |
| Card images | 5,113 | 750 MB | ~400 MB |
| FAISS index | 3 | 7.2 MB | ~3 MB |
| Embeddings | 3 | 18 MB | ~8 MB |
| **Total** | **5,120** | **~778 MB** | **~411 MB** |

---

## 🔄 Keeping Data Up-to-Date

To refresh data with latest cards and prices:

```bash
# Incremental update (recommended)
pnpm pipeline:update

# Or full rebuild
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

**Recommended frequency**: Weekly for price updates, monthly for new card releases

---

## 🚨 What Happens If Data Is Missing?

The desktop app will fail to start with one of these errors:

```
❌ System Error
Failed to initialize system

Troubleshooting:
• Ensure Python 3.10+ is installed
• Check that all Python dependencies are installed
• Verify FAISS index files exist in artifacts/faiss/  ← THIS IS THE ISSUE
• Check the console for detailed error messages
```

**Always verify data files exist** before attempting to run the app.

---

## 📞 Need Help?

1. **Read full setup guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. **Quick demo setup**: [DEMO_SETUP.md](DEMO_SETUP.md)
3. **Run verification**: `./scripts/setup/verify-setup.sh`
4. **Check GitHub Issues**: Look for "data" or "artifacts" tags

---

**Document Version**: 1.0
**Last Updated**: 2025-10-15
**Maintainer**: CardFlux Engineering Team
