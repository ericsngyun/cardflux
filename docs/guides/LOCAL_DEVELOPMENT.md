

# 🛠️ Local Development Guide

Complete guide for developing and testing CardFlux locally without cloud infrastructure.

---

## 🚀 Quick Start

### **1. Health Check**
```bash
pnpm dev:health
```
Checks:
- ✅ Node.js version (>=20.0.0)
- ✅ Python installation
- ✅ Directory structure
- ✅ Scraped data
- ✅ Database
- ✅ FAISS indices
- ✅ Disk usage
- ✅ API connectivity

### **2. Test Scraper (Fast)**
```bash
pnpm dev:test-scrape
```
- Scrapes only **Magic: The Gathering** (for testing)
- ~5 minutes vs ~30 minutes for full scrape
- Perfect for development

### **3. Validate Data**
```bash
pnpm dev:validate
```
Checks data quality:
- Missing required fields
- Invalid prices
- Duplicate cards
- File integrity
- Returns errors if >5% invalid

### **4. Run Complete Pipeline**
```bash
pnpm dev:pipeline
```
Full local pipeline:
1. Test scrape (Magic only)
2. Data validation
3. Build database
4. Fetch images
5. Generate embeddings
6. Build FAISS index
7. Generate manifests

---

## 📦 Available Commands

### **Development Scripts**
| Command | Description | Duration |
|---------|-------------|----------|
| `pnpm dev:health` | System health check | <1s |
| `pnpm dev:test-scrape` | Quick test scrape (Magic only) | ~5 min |
| `pnpm dev:validate` | Data quality validation | ~10s |
| `pnpm dev:pipeline` | Complete local pipeline | ~15 min |

### **Production Scripts**
| Command | Description | Duration |
|---------|-------------|----------|
| `pnpm tcgplayer:scrape` | Full scrape (all games) | ~30 min |
| `pnpm tcgplayer:scrape:incremental` | Smart incremental update | ~5 min |
| `pnpm tcgplayer:db` | Build SQLite database | ~30s |

### **Legacy Pipeline (Old Multi-API)**
| Command | Description |
|---------|-------------|
| `pnpm pipeline:all` | Full pipeline (old system) |
| `pnpm pipeline:update` | Incremental update (old system) |

---

## 🔬 Testing Workflow

### **Scenario 1: First Time Setup**
```bash
# 1. Check system
pnpm dev:health

# 2. Test scraper with limited data
pnpm dev:test-scrape

# 3. Validate scraped data
pnpm dev:validate

# 4. Build database
pnpm tcgplayer:db

# 5. Query database
sqlite3 artifacts/metadata/cards.db
sqlite> SELECT name, market_price FROM cards JOIN prices ON cards.product_id = prices.product_id LIMIT 10;
```

### **Scenario 2: Full Pipeline Test**
```bash
# One command does it all
pnpm dev:pipeline
```

### **Scenario 3: Incremental Updates**
```bash
# First run: Full scrape
pnpm tcgplayer:scrape

# Later: Only fetch changes
pnpm tcgplayer:scrape:incremental
```

### **Scenario 4: Debug Specific Issue**
```bash
# Test scraper only
pnpm dev:test-scrape

# Check what failed
pnpm dev:validate

# Manual inspection
cat data/curated/magic.jsonl | jq '.prices'
```

---

## 📊 Data Validation

### **What Gets Validated:**
```typescript
✅ Required fields (productId, name, categoryId)
✅ Image URLs (must be HTTPS, from TCGplayer)
✅ Price data (normal/foil, no negatives)
✅ Card names (length, non-empty)
✅ Rarity values (common, uncommon, rare, etc.)
✅ No duplicates
✅ File integrity (JSON parsing)
```

### **Validation Thresholds:**
- ❌ Fails if >5% invalid cards
- ⚠️  Warns if duplicates found
- ⚠️  Warns if malformed lines

### **Sample Output:**
```
📊 MAGIC
------------------------------------------------------------
✓ File size: 42.3 MB
✓ Lines: 52,487
✓ Total cards: 52,487
✓ Valid cards: 52,245 (99%)
⚠️  Invalid cards: 242 (1%)

Top Issues:
  • Missing imageUrl: 189 occurrences
    Examples: Token (ID: 12345), Emblem (ID: 23456)
  • No price data: 53 occurrences
    Examples: Promo Card (ID: 34567)
```

---

## 🗄️ Database Schema

### **Cards Table:**
```sql
CREATE TABLE cards (
  product_id INTEGER PRIMARY KEY,
  category_id INTEGER NOT NULL,
  category_name TEXT NOT NULL,
  group_id INTEGER NOT NULL,
  group_name TEXT NOT NULL,
  name TEXT NOT NULL,
  clean_name TEXT NOT NULL,
  image_url TEXT,
  tcgplayer_url TEXT,
  rarity TEXT,
  card_number TEXT,
  sub_type TEXT,
  oracle_text TEXT,
  modified_on TEXT
);
```

### **Prices Table:**
```sql
CREATE TABLE prices (
  product_id INTEGER NOT NULL,
  finish TEXT NOT NULL,  -- 'normal' or 'foil'
  low_price REAL,
  mid_price REAL,
  high_price REAL,
  market_price REAL,
  direct_low_price REAL,
  FOREIGN KEY (product_id) REFERENCES cards(product_id)
);
```

### **Example Queries:**
```sql
-- Find expensive cards
SELECT c.name, p.market_price
FROM cards c
JOIN prices p ON c.product_id = p.product_id
WHERE p.finish = 'normal' AND p.market_price > 100
ORDER BY p.market_price DESC;

-- Full-text search
SELECT * FROM cards_fts WHERE cards_fts MATCH 'flying dragon';

-- Price statistics by category
SELECT category_name, AVG(market_price) as avg_price
FROM cards c
JOIN prices p ON c.product_id = p.product_id
GROUP BY category_name;
```

---

## 🔧 Troubleshooting

### **Issue: Python not found**
```bash
# Install Python 3.10+
https://www.python.org/downloads/

# Install dependencies
pip install -r requirements.txt
```

### **Issue: FAISS import error**
```bash
# Install FAISS
pip install faiss-cpu
# OR for GPU
pip install faiss-gpu
```

### **Issue: No scraped data**
```bash
# Run test scraper
pnpm dev:test-scrape

# Check output
ls -la data/curated/
```

### **Issue: Database not found**
```bash
# Build database
pnpm tcgplayer:db

# Verify
ls -la artifacts/metadata/cards.db
```

### **Issue: Validation fails**
```bash
# See detailed errors
pnpm dev:validate

# Fix data and re-scrape
pnpm dev:test-scrape
```

### **Issue: Disk space**
```bash
# Check usage
pnpm dev:health

# Clean old data
rm -rf data/raw/*
rm -rf data/images/*
```

---

## 📁 Directory Structure

```
cardflux/
├── data/                          # Pipeline working data
│   ├── raw/tcgplayer/            # Raw API responses
│   │   ├── magic/
│   │   ├── pokemon/
│   │   └── yugioh/
│   ├── curated/                  # Processed JSONL
│   │   ├── magic.jsonl           # 50k+ cards with prices
│   │   ├── pokemon.jsonl
│   │   └── yugioh.jsonl
│   ├── images/                   # Card images
│   │   ├── magic/
│   │   └── pokemon/
│   └── state/                    # Pipeline state
│       ├── tcgplayer-scrape.state.json
│       └── tcgplayer-incremental.state.json
│
├── artifacts/                    # Build outputs
│   ├── metadata/
│   │   ├── cards.db             # SQLite database
│   │   └── embeddings/
│   │       ├── magic/
│   │       │   ├── embeddings.npy
│   │       │   └── metadata.jsonl
│   │       └── pokemon/
│   ├── faiss/                   # Search indices
│   │   ├── magic/
│   │   │   ├── index.faiss
│   │   │   └── metadata.jsonl
│   │   └── pokemon/
│   └── manifests/              # Version info
│       ├── magic.json
│       └── manifest.json
│
└── scripts/dev/                # Development tools
    ├── check-health.mjs        # Health check
    ├── test-scraper.mjs        # Test scraper
    └── local-pipeline.mjs      # Full pipeline
```

---

## 🎯 Development Best Practices

### **1. Always Run Health Check First**
```bash
pnpm dev:health
```

### **2. Use Test Scraper for Development**
```bash
# Fast iteration (5 min)
pnpm dev:test-scrape

# Not this (30 min)
pnpm tcgplayer:scrape
```

### **3. Validate Before Building**
```bash
pnpm dev:test-scrape
pnpm dev:validate  # ← Catch issues early
pnpm tcgplayer:db
```

### **4. Incremental Updates for Production**
```bash
# First run
pnpm tcgplayer:scrape

# Daily updates
pnpm tcgplayer:scrape:incremental
```

### **5. Monitor Disk Space**
```bash
# Check usage
pnpm dev:health

# Clean periodically
rm -rf data/raw/*  # Can re-download
```

---

## 🔄 Incremental Update Logic

### **How It Works:**
```typescript
1. Load previous state (modifiedOn timestamps)
2. Fetch all groups for category
3. Compare modifiedOn dates:
   - If group.modifiedOn > previousState.lastModified → Update
   - Else → Skip
4. Only fetch changed groups
5. Merge with existing cards
6. Save new state
```

### **State File:**
```json
{
  "lastSync": "2024-10-03T12:00:00Z",
  "groups": [
    {
      "categoryId": 1,
      "groupId": 1,
      "groupName": "10th Edition",
      "lastModified": "2024-07-08T16:26:12.31",
      "productCount": 398,
      "checksum": "abc123..."
    }
  ]
}
```

### **Performance:**
- **Full scrape**: ~30 minutes (all games)
- **Incremental**: ~5 minutes (only changes)
- **Time saved**: ~80-90% on daily updates

---

## 📈 Expected Performance

| Operation | Duration | Output Size |
|-----------|----------|-------------|
| Test scrape (Magic only) | ~5 min | ~40 MB |
| Full scrape (5 games) | ~30 min | ~150 MB |
| Incremental update | ~5 min | Varies |
| Data validation | ~10 sec | - |
| Build database | ~30 sec | ~500 MB |
| Fetch images (Magic) | ~30 min | ~5 GB |
| Generate embeddings | ~10 min | ~200 MB |
| Build FAISS index | ~30 sec | ~100 MB |

**Total Storage:**
- Data: ~10 GB (images + raw)
- Artifacts: ~2 GB (database + indices)
- **Total: ~12 GB**

---

## ✅ Testing Checklist

Before deploying to production:

- [ ] Health check passes
- [ ] Test scrape completes without errors
- [ ] Data validation <5% invalid
- [ ] Database queries work
- [ ] Full-text search functional
- [ ] Images download correctly
- [ ] Embeddings generate successfully
- [ ] FAISS search returns results
- [ ] Incremental updates work
- [ ] Disk usage acceptable

---

## 🔗 Next Steps

### **After Local Testing:**
1. ✅ Run full scrape: `pnpm tcgplayer:scrape`
2. ✅ Build complete pipeline: `pnpm dev:pipeline`
3. ✅ Test desktop app with real data
4. ⏳ Deploy to cloud (see `TCGPLAYER_MIGRATION.md`)
5. ⏳ Set up daily scraper (Lambda/GCF)

### **Resources:**
- API Structure: `TCGPLAYER_MIGRATION.md`
- Cloud Deployment: `TCGPLAYER_MIGRATION.md#cloud-deployment`
- Desktop App: `apps/desktop/README.md`
