# Next Steps: Activating Price Tracking System

> **Status**: 🔴 Price tracking code exists but is NOT operational
> **Created**: 2025-11-07
> **Priority**: HIGH
> **Time to Complete**: 1 week

---

## 📋 Quick Summary

Your price tracking system is **fully coded** but **never integrated**. Here's what needs to happen:

### What Exists ✅
- ✅ Historical backfill script (`services/ingest/bin/backfill_historical_prices.ts`)
- ✅ Daily price scraper (`services/ingest/bin/scrape_prices_tcgplayer.ts`)
- ✅ Package scripts (`pnpm prices:backfill`, `pnpm prices:daily`)
- ✅ Comprehensive documentation

### What's Missing 🔴
- ❌ TCGPlayer API key not configured
- ❌ Historical backfill never run (zero price data)
- ❌ Daily scraper not in CI workflow
- ❌ Price data directory doesn't exist
- ❌ Desktop app can't show prices (no data source)

---

## 🚀 Implementation Steps

### Step 1: Get TCGPlayer API Access (30 minutes)

**You need to do this** - requires your TCGPlayer account:

```bash
# 1. Go to TCGPlayer Developer Portal
https://developer.tcgplayer.com

# 2. Create a new app
App Name: CardFlux Price Tracker
Description: Daily price tracking for card identification app

# 3. Copy the Bearer Token (API Key)
# Should look like: Bearer pk_XXXXXXXXXXXXX

# 4. Add to GitHub Secrets
GitHub repo → Settings → Secrets and variables → Actions → New repository secret
Name: TCGPLAYER_API_KEY
Value: <paste your bearer token>

# 5. Test locally (optional)
export TCGPLAYER_API_KEY="Bearer pk_XXXXX..."
pnpm prices:daily --test-mode
```

**Success Criteria**:
- ✅ API key added to GitHub Secrets
- ✅ Can fetch price data locally (if testing)

---

### Step 2: Run Historical Price Backfill (2-4 hours ONE-TIME)

**Important**: This is a **one-time** operation that downloads ~640 days of historical price data.

**Prerequisites**:
```bash
# Install 7-Zip (required for archive extraction)

# Windows (PowerShell as Admin):
choco install 7zip

# Mac:
brew install p7zip

# Linux:
sudo apt-get install p7zip-full

# Verify installation:
7z --help
```

**Run Backfill**:
```bash
# 1. Create required directories
mkdir -p data/prices/historical/one-piece
mkdir -p .temp/price-archives
mkdir -p data/state

# 2. Pull latest curated data (has product IDs we need)
git lfs pull

# 3. Start backfill (will take 2-4 hours, runs unattended)
pnpm prices:backfill

# This will:
# - Download 638 daily archives from tcgcsv.com (Feb 8, 2024 → yesterday)
# - Each archive is ~200-300 KB compressed
# - Extract category 68 (One Piece TCG) only
# - Match productIds with our 5,390 cards
# - Create 638 JSONL files: data/prices/historical/one-piece/{YYYY-MM-DD}.jsonl
# - Resume automatically if interrupted
# - Show progress every 10 files

# 4. Monitor progress (in another terminal)
watch -n 10 "ls data/prices/historical/one-piece/*.jsonl | wc -l"
# Should eventually show 638 files

# 5. Verify completion
ls -lh data/prices/historical/one-piece/ | wc -l  # Should be 639 (638 + total line)
du -sh data/prices/                                 # Should be ~640 MB
```

**Success Criteria**:
- ✅ 638 JSONL files created (one per day)
- ✅ Total size ~640 MB
- ✅ Each file has ~5,390 lines (one per card)
- ✅ No errors in console

**If It Fails Mid-Way**:
- Just run `pnpm prices:backfill` again
- It has resume support (checks `data/state/backfill-state.json`)
- Will skip already-downloaded dates

---

### Step 3: Set Up Git LFS for Price Data (15 minutes)

**Important**: Do this BEFORE committing the backfill data!

```bash
# 1. Update .gitattributes to track price files
cat >> .gitattributes << 'EOF'

# Price data (historical tracking - large files)
data/prices/**/*.jsonl filter=lfs diff=lfs merge=lfs -text
EOF

# 2. Track price files in LFS
git lfs track "data/prices/**/*.jsonl"

# 3. Verify LFS is tracking
git lfs ls-files
# Should show price JSONL files

# 4. Check Git LFS status
git lfs status
# Should show files to be committed

# 5. Add files
git add .gitattributes
git add data/prices/

# 6. Commit (this will upload to LFS)
git commit -m "feat: Add historical price data (Feb 2024 - present)

Historical price backfill from tcgcsv.com archives:
- 638 days of price history (Feb 8, 2024 → Nov 6, 2025)
- 5,390 cards tracked daily
- ~640 MB total (1 MB/day average)
- Source: tcgcsv.com/archive/tcgplayer/

Data format: JSONL (one snapshot per day)
Storage: Git LFS (640 MB)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 7. Push to GitHub (may take a few minutes for LFS upload)
git push origin main
```

**Success Criteria**:
- ✅ `.gitattributes` updated
- ✅ Files committed to LFS (not regular Git)
- ✅ Push succeeds (may take 5-10 min for 640 MB upload)
- ✅ GitHub shows files with LFS badge

---

### Step 4: Activate Daily Price Scraping in CI (15 minutes)

**Option A**: Replace current workflow (RECOMMENDED)

```bash
# 1. Backup current workflow
cp .github/workflows/daily-update.yml .github/workflows/daily-update-BACKUP.yml

# 2. Replace with price-enabled version
cp .github/workflows/daily-update-with-prices.yml .github/workflows/daily-update.yml

# 3. Commit the workflow update
git add .github/workflows/daily-update.yml
git commit -m "feat(ci): Add daily price scraping to automated workflow

Integrated price tracking into daily CI pipeline:
- Scrapes current prices from TCGPlayer API after card updates
- Creates daily price snapshot in data/prices/historical/{game}/{date}.jsonl
- Commits and pushes price data automatically
- Continues if price scraping fails (won't break card updates)

New workflow features:
- skip_prices input (for testing without price API)
- Price scrape status reporting
- Enhanced commit messages with price counts
- Health check includes price data validation

Requires: TCGPLAYER_API_KEY secret in GitHub

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Push to GitHub
git push origin main
```

**Option B**: Manually integrate (if you want to review/customize)

See: `docs/audits/DATA_PIPELINE_AUDIT_2025-11-07.md` Section "1.4 Integrate Price Scraping into GitHub Actions"

**Success Criteria**:
- ✅ Workflow file updated
- ✅ Pushed to GitHub
- ✅ Can see new workflow in Actions tab

---

### Step 5: Test the Full Pipeline (30 minutes)

**Manual Workflow Test**:

```bash
# 1. Go to GitHub Actions tab
https://github.com/ericsngyun/cardflux/actions

# 2. Click "Daily Card Database Update with Price Tracking"

# 3. Click "Run workflow" button
   Game: one-piece
   Dry run: false
   Skip LFS: false
   Skip prices: false

# 4. Click "Run workflow" (green button)

# 5. Watch the workflow run (takes ~10-15 min)
   - Should see all steps succeed
   - "Scrape daily prices from TCGPlayer" step should succeed
   - Commit message should include price count

# 6. Verify new price file was created
git pull origin main
ls -lh data/prices/historical/one-piece/$(date +%Y-%m-%d).jsonl
# Should exist and be ~1 MB

# 7. Inspect price data
head data/prices/historical/one-piece/$(date +%Y-%m-%d).jsonl
# Should show JSON with productId, prices, etc.
```

**Success Criteria**:
- ✅ Workflow completes successfully
- ✅ Today's price file created
- ✅ File has ~5,390 lines (one per card)
- ✅ Prices look correct (market price, low, high, etc.)
- ✅ Committed and pushed automatically

---

## 📊 Expected Results After Completion

### Data Structure
```
data/prices/
└── historical/
    └── one-piece/
        ├── 2024-02-08.jsonl  (backfilled)
        ├── 2024-02-09.jsonl  (backfilled)
        ├── ...
        ├── 2025-11-06.jsonl  (backfilled)
        └── 2025-11-07.jsonl  (scraped today by CI)
```

### File Stats
- **Total files**: 639 (638 backfilled + 1 today)
- **Total size**: ~641 MB
- **Per file**: ~1 MB
- **Lines per file**: ~5,390 (one per card)

### Daily Automation
- **Runs at**: 2 PM PDT (21:00 UTC) daily
- **Updates**: Cards + Prices + Embeddings + Index
- **Commits**: Automatically with detailed message
- **Time**: ~15-20 minutes total

---

## 🎯 Phase 2: Desktop App Integration (Week 2)

After price data is flowing, integrate into desktop app:

### Features to Add
1. **Show current price** in identification results
2. **Price history graph** (7-day, 30-day, all-time)
3. **Price change indicators** (↑ ↓ with % change)
4. **Total value** of scanned card stack
5. **Price alerts** (if card spikes >10%)

### Technical Approach
```typescript
// services/pricefeed/bin/build_price_database.ts
// Build SQLite database from JSONL for fast queries

CREATE TABLE prices (
  product_id TEXT,
  date DATE,
  market_price INTEGER,  // cents
  low_price INTEGER,
  high_price INTEGER,
  is_foil BOOLEAN,
  PRIMARY KEY (product_id, date, is_foil)
);

CREATE INDEX idx_product_date ON prices(product_id, date);
```

### Query Performance
- JSONL scan: ~2-5 seconds
- SQLite query: ~10-50ms ✅

---

## ⚠️ Important Notes

### Git LFS Storage
- **Free tier**: 1 GB storage, 1 GB bandwidth/month
- **Your usage**: ~640 MB initial + 1.1 MB/day
- **Will last**: ~1 year before hitting 1 GB
- **Then**: Need $5/month paid tier OR migrate to S3

### TCGPlayer API Rate Limits
- **Limit**: 300 requests/hour
- **Our usage**: ~108 requests (5,390 cards ÷ 50 per batch)
- **Well within limit** ✅

### Backup Strategy
- Historical data is **append-only** (never changes)
- Daily CI commits create **automatic backups**
- Git history preserves all price snapshots
- Can always re-run backfill if data lost

---

## 🐛 Troubleshooting

### "7z command not found"
```bash
# Install 7-Zip
# Windows: choco install 7zip
# Mac: brew install p7zip
# Linux: sudo apt-get install p7zip-full
```

### "TCGPLAYER_API_KEY not set"
```bash
# Local testing:
export TCGPLAYER_API_KEY="Bearer pk_XXXXX..."

# CI:
Add to GitHub Secrets (see Step 1)
```

### "Git LFS upload failed"
```bash
# Check LFS quota
git lfs env

# If over quota, consider:
# 1. Upgrade to paid tier ($5/month)
# 2. Store only last 30 days in Git
# 3. Migrate historical data to S3
```

### "No price data in JSONL"
```bash
# Check if productIds match
head data/curated/one-piece.jsonl | jq '.productId'
head data/prices/historical/one-piece/2024-02-08.jsonl | jq '.productId'

# Should be same format (string or number)
```

---

## 📚 Reference Documents

- **Full Audit**: `docs/audits/DATA_PIPELINE_AUDIT_2025-11-07.md`
- **Price System Docs**: `docs/architecture/PRICE_TRACKING_SYSTEM.md`
- **Implementation Guide**: `docs/architecture/PRICE_TRACKING_IMPLEMENTATION.md`
- **Status Report**: `docs/STATUS_PRICE_TRACKING.md`

---

## ✅ Completion Checklist

### Week 1: Data Collection
- [ ] Step 1: TCGPlayer API access configured
- [ ] Step 2: Historical backfill completed (638 files)
- [ ] Step 3: Git LFS tracking configured
- [ ] Step 4: CI workflow updated with price scraping
- [ ] Step 5: Full pipeline tested successfully
- [ ] **Milestone**: Price data flowing daily ✅

### Week 2: App Integration
- [ ] Build SQLite price database
- [ ] Add price query API
- [ ] Show current price in card results
- [ ] Add price history graphs
- [ ] Display total stack value
- [ ] **Milestone**: Users see prices in app ✅

### Month 1: Production
- [ ] 30 days of continuous price tracking
- [ ] Zero missed daily collections
- [ ] Price alerts working
- [ ] Analytics dashboard live
- [ ] **Milestone**: Full price tracking operational ✅

---

## 🎊 Success! What You'll Have

After completing all steps:

1. ✅ **640+ days of historical price data** (Feb 2024 → present)
2. ✅ **Daily automatic price updates** (runs at 2 PM PDT)
3. ✅ **Desktop app shows live prices** for identified cards
4. ✅ **Price history graphs** and trend analysis
5. ✅ **Market insights** for shop inventory management
6. ✅ **Production-ready price tracking system**

---

**Ready to start?** Begin with **Step 1: Get TCGPlayer API Access** 🚀

**Questions?** Refer to the full audit: `docs/audits/DATA_PIPELINE_AUDIT_2025-11-07.md`
