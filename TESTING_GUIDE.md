# 🧪 Testing Guide

Complete guide for testing CardFlux locally before production deployment.

---

## 🚀 Quick Test (5 Minutes)

```bash
# 1. Health check
pnpm dev:health

# 2. Quick test scrape (Magic only)
pnpm dev:test-scrape

# 3. Validate data
pnpm dev:validate

# 4. Build database
pnpm tcgplayer:db

# 5. Query database
sqlite3 artifacts/metadata/cards.db "SELECT COUNT(*) FROM cards;"
```

**Expected Results:**
- ✅ Health check passes
- ✅ ~50k Magic cards scraped
- ✅ <5% validation errors
- ✅ Database created (~500 MB)

---

## 📋 Complete Test Checklist

### **Phase 1: Environment Setup**
```bash
□ pnpm install
□ pip install -r requirements.txt
□ pnpm dev:health
```

**Expected:**
- ✅ All dependencies installed
- ✅ Node.js >=20.0.0
- ✅ Python installed
- ✅ Directories created

### **Phase 2: Data Scraping**
```bash
□ pnpm dev:test-scrape
```

**Expected:**
- ✅ API connectivity works
- ✅ Rate limiting respected
- ✅ Data saved to `data/curated/magic.jsonl`
- ✅ File size ~40-50 MB
- ✅ ~50k cards scraped

**Validation:**
```bash
# Check file exists
ls -lh data/curated/magic.jsonl

# Count cards
wc -l data/curated/magic.jsonl

# Sample data
head -5 data/curated/magic.jsonl | jq '.'
```

### **Phase 3: Data Validation**
```bash
□ pnpm dev:validate
```

**Expected:**
- ✅ >95% valid cards
- ✅ No critical issues
- ✅ Price data present
- ✅ Image URLs valid

**Common Issues:**
- ⚠️ Missing imageUrl (tokens, emblems) - OK
- ⚠️ No price data (promos) - OK
- ❌ Missing productId - NOT OK
- ❌ >5% invalid - NOT OK

### **Phase 4: Database Build**
```bash
□ pnpm tcgplayer:db
```

**Expected:**
- ✅ Database created at `artifacts/metadata/cards.db`
- ✅ Size ~500 MB
- ✅ Tables: cards, prices, cards_fts
- ✅ No insertion errors

**Validation:**
```bash
# Check database
sqlite3 artifacts/metadata/cards.db ".tables"

# Count cards
sqlite3 artifacts/metadata/cards.db "SELECT COUNT(*) FROM cards;"

# Count prices
sqlite3 artifacts/metadata/cards.db "SELECT COUNT(*) FROM prices;"

# Sample query
sqlite3 artifacts/metadata/cards.db "
  SELECT c.name, p.market_price
  FROM cards c
  JOIN prices p ON c.product_id = p.product_id
  WHERE p.finish = 'normal'
  LIMIT 5;
"
```

### **Phase 5: Image Fetching** (Optional - Takes ~30 min)
```bash
□ pnpm pipeline:fetch-images:incremental
```

**Expected:**
- ✅ Images in `data/images/magic/`
- ✅ ~50k images downloaded
- ✅ Size ~5 GB
- ✅ No corrupt images (<1KB)

**Validation:**
```bash
# Count images
find data/images/magic -type f | wc -l

# Check sizes
find data/images/magic -type f -size -1k | wc -l  # Should be 0
```

### **Phase 6: Embeddings** (Optional - Takes ~10 min)
```bash
□ pnpm pipeline:embed:incremental
```

**Expected:**
- ✅ Embeddings in `artifacts/metadata/embeddings/magic/`
- ✅ File: `embeddings.npy` (~200 MB)
- ✅ File: `metadata.jsonl`
- ✅ Dimensions: [N x 512]

**Validation:**
```python
import numpy as np

embeddings = np.load('artifacts/metadata/embeddings/magic/embeddings.npy')
print(f"Shape: {embeddings.shape}")  # Should be (N, 512)
print(f"Min: {embeddings.min()}, Max: {embeddings.max()}")
```

### **Phase 7: FAISS Index**
```bash
□ pnpm pipeline:index
```

**Expected:**
- ✅ Index in `artifacts/faiss/magic/`
- ✅ File: `index.faiss` (~100 MB)
- ✅ Search works

**Validation:**
```python
import faiss
import numpy as np

# Load index
index = faiss.read_index('artifacts/faiss/magic/index.faiss')
print(f"Total vectors: {index.ntotal}")

# Test search
query = np.random.rand(1, 512).astype('float32')
distances, indices = index.search(query, 5)
print(f"Top 5 matches: {indices[0]}")
```

### **Phase 8: Manifests**
```bash
□ pnpm pipeline:manifests
```

**Expected:**
- ✅ Manifest in `artifacts/manifests/magic.json`
- ✅ Contains version, files, stats
- ✅ Checksums present

**Validation:**
```bash
cat artifacts/manifests/magic.json | jq '.'
```

---

## 🔄 Incremental Update Test

### **Setup:**
```bash
# 1. Full scrape first
pnpm tcgplayer:scrape

# 2. Note stats
pnpm dev:validate
```

### **Test Incremental:**
```bash
# 3. Wait a bit (or modify state file for testing)

# 4. Run incremental
pnpm tcgplayer:scrape:incremental
```

**Expected:**
- ✅ Most groups skipped (unchanged)
- ✅ Only new/modified groups fetched
- ✅ Data merged correctly
- ✅ ~80-90% time saved

**Validation:**
```bash
# Check state file
cat data/state/tcgplayer-incremental.state.json | jq '.'

# Compare card counts
wc -l data/curated/magic.jsonl
```

---

## 🎯 Integration Tests

### **Test 1: Full Pipeline**
```bash
pnpm dev:pipeline
```

**Expected Duration:** ~15 min (test mode)

**Steps:**
1. Test scrape (Magic only)
2. Validate data
3. Build database
4. Fetch images (partial)
5. Generate embeddings
6. Build FAISS index
7. Generate manifests

**Success Criteria:**
- ✅ All steps complete
- ✅ No errors
- ✅ All artifacts created

### **Test 2: Desktop App Integration**
```bash
# 1. Build pipeline
pnpm dev:pipeline

# 2. Start desktop app
cd apps/desktop
pnpm install
pnpm dev
```

**Expected:**
- ✅ App starts
- ✅ Camera access works
- ✅ Card detection works
- ✅ Search finds cards
- ✅ Price info displays (TODO)

### **Test 3: Production Scrape**
```bash
# Full scrape (all games)
pnpm tcgplayer:scrape
```

**Expected Duration:** ~30 min

**Expected Results:**
- ✅ 5 categories scraped
- ✅ ~100k total cards
- ✅ All prices included
- ✅ Data validated

---

## 🐛 Debugging Tests

### **Test Failure: API Connectivity**
```bash
# Check API
curl https://tcgcsv.com/tcgplayer/categories

# Expected: JSON response with categories
```

**Fix:**
- Check internet connection
- Verify firewall settings
- Check proxy settings

### **Test Failure: Python Import**
```bash
# Test imports
python -c "import numpy; import faiss; print('OK')"
```

**Fix:**
```bash
pip install numpy faiss-cpu
```

### **Test Failure: Validation**
```bash
# See detailed errors
pnpm dev:validate

# Fix: Check data/curated/*.jsonl for issues
```

### **Test Failure: Database**
```bash
# Check database
sqlite3 artifacts/metadata/cards.db ".schema"

# Fix: Drop and rebuild
rm artifacts/metadata/cards.db
pnpm tcgplayer:db
```

---

## 📊 Performance Benchmarks

| Test | Expected Duration | Expected Output |
|------|-------------------|-----------------|
| Health check | <1s | System status |
| Test scrape | ~5 min | ~50k Magic cards |
| Full scrape | ~30 min | ~100k cards (5 games) |
| Incremental | ~5 min | Only changes |
| Validation | ~10s | Quality report |
| Database build | ~30s | 500 MB SQLite |
| Image fetch | ~30 min | ~5 GB images |
| Embeddings | ~10 min | 200 MB vectors |
| FAISS index | ~30s | 100 MB index |
| Full pipeline | ~15 min | All artifacts |

---

## ✅ Acceptance Criteria

### **Before Production:**
- [ ] All health checks pass
- [ ] Test scrape completes <5 min
- [ ] Data validation <5% errors
- [ ] Database queries work
- [ ] Full-text search functional
- [ ] Incremental updates work
- [ ] Desktop app integrates successfully
- [ ] No memory leaks
- [ ] Disk usage <20 GB
- [ ] All documentation complete

### **Performance Thresholds:**
- [ ] Scrape: <35 min (full), <7 min (incremental)
- [ ] Validation: <15s
- [ ] Database: <45s
- [ ] Search: <5ms per query
- [ ] Memory: <2 GB during scrape

---

## 🔧 CI/CD Integration (Future)

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 20

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.10

      - name: Install deps
        run: |
          pnpm install
          pip install -r requirements.txt

      - name: Health check
        run: pnpm dev:health

      - name: Test scrape
        run: pnpm dev:test-scrape

      - name: Validate
        run: pnpm dev:validate

      - name: Build database
        run: pnpm tcgplayer:db
```

---

## 📝 Test Reporting

### **Generate Test Report:**
```bash
# Run all tests and save output
pnpm dev:health > test-report.txt
pnpm dev:test-scrape >> test-report.txt
pnpm dev:validate >> test-report.txt

# View report
cat test-report.txt
```

### **Sample Report:**
```
=== HEALTH CHECK ===
✅ Node.js Version: Node.js v20.11.0 ✓
✅ Python Installation: Python 3.10.12 ✓
✅ Directory Structure: All directories exist ✓
...

=== TEST SCRAPE ===
Starting CardFlux scraper...
✓ Magic: 52,487 cards scraped
Duration: 4m 32s

=== VALIDATION ===
📊 MAGIC
✓ Total cards: 52,487
✓ Valid cards: 52,245 (99%)
⚠️  Invalid cards: 242 (1%)
```

---

## 🎯 Next Steps

After all tests pass:
1. ✅ Run full production scrape
2. ✅ Deploy to cloud storage
3. ✅ Set up daily scraper (Lambda/GCF)
4. ✅ Deploy desktop app
5. ✅ Monitor production metrics
