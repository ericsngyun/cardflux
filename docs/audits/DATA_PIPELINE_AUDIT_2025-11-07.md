# Data Pipeline Deep Audit & Action Plan

> **Date**: 2025-11-07
> **Auditor**: Senior Principal Engineer (Claude Code)
> **Status**: 🔴 **CRITICAL ISSUES IDENTIFIED**
> **Priority**: **HIGH** - Price tracking not operational, CI incomplete

---

## 🎯 Executive Summary

### Current State Assessment

| Component | Status | Health | Notes |
|-----------|--------|--------|-------|
| **GitHub Actions Workflow** | 🟡 Partial | 70% | Scrapes cards, but NO price tracking |
| **Daily Card Scraper** | ✅ Working | 90% | Incremental updates functional |
| **Price Tracking System** | 🔴 **NOT OPERATIONAL** | 0% | Code exists but not integrated |
| **Historical Price Backfill** | 🔴 **NEVER RUN** | 0% | No historical data collected |
| **Daily Price Scraper** | 🔴 **NOT IN CI** | 0% | Not running daily |
| **Price Data Storage** | 🔴 **MISSING** | 0% | `data/prices/` doesn't exist |

### Critical Findings

1. ✅ **Card scraping works** - GitHub Actions runs daily, updates cards
2. 🔴 **Price tracking NOT operational** - Code exists but never runs
3. 🔴 **No historical data** - `data/prices/` directory doesn't exist
4. 🔴 **CI workflow incomplete** - Workflow doesn't call price scrapers
5. 🔴 **No price display** - Desktop app can't show prices (no data)

---

## 📊 Detailed Component Analysis

### 1. GitHub Actions Workflow (`.github/workflows/daily-update.yml`)

**Status**: 🟡 **Partially Functional**

**What Works**:
- ✅ Runs daily at 2 PM PDT (21:00 UTC)
- ✅ Scrapes TCGPlayer for new cards
- ✅ Downloads card images
- ✅ Generates DINOv2 embeddings
- ✅ Builds FAISS index
- ✅ Commits and pushes updates
- ✅ Git LFS support fixed (Nov 6)
- ✅ Incremental pipeline works

**What's MISSING** (CRITICAL):
- ❌ **NO price tracking integration**
- ❌ Workflow never calls `pnpm prices:daily`
- ❌ No historical price backfill step
- ❌ No price data collection
- ❌ No price storage directory creation

**Impact**:
- Users see cards but **NO PRICES**
- Historical analysis **IMPOSSIBLE**
- Market trends **UNAVAILABLE**
- Shop pricing features **NON-FUNCTIONAL**

---

### 2. Price Tracking Implementation

**Status**: 🔴 **Code Exists, Never Executed**

**What Was Built** (Nov 6, 2025):
- ✅ `services/ingest/bin/backfill_historical_prices.ts` (482 lines)
  - Downloads tcgcsv.com archives (Feb 8, 2024 → present)
  - Extracts category 68 (One Piece)
  - Matches productIds with curated cards
  - Outputs JSONL: `data/prices/historical/{game}/{YYYY-MM-DD}.jsonl`

- ✅ `services/ingest/bin/scrape_prices_tcgplayer.ts` (369 lines)
  - Fetches current prices from TCGPlayer API
  - Batch requests (50 products/request)
  - Rate limiting (1s between requests)
  - Retry logic with exponential backoff
  - Unified output: `data/prices/historical/{game}/{YYYY-MM-DD}.jsonl`

- ✅ Package scripts defined:
  ```json
  "prices:backfill": "tsx services/ingest/bin/backfill_historical_prices.ts",
  "prices:daily": "tsx services/ingest/bin/scrape_prices_tcgplayer.ts"
  ```

- ✅ Comprehensive documentation:
  - `docs/architecture/PRICE_TRACKING_SYSTEM.md`
  - `docs/architecture/PRICE_TRACKING_IMPLEMENTATION.md`
  - `docs/STATUS_PRICE_TRACKING.md`

**What's BROKEN**:
- ❌ **Never been run** - `data/prices/` directory doesn't exist
- ❌ **Not in CI workflow** - GitHub Actions doesn't call it
- ❌ **No historical data** - Backfill never executed
- ❌ **No daily collection** - Daily scraper not scheduled

**Root Cause**: Implementation complete but **integration incomplete**

---

### 3. Data Architecture Analysis

#### Current TCGPlayer Scraper (Working)

**Location**: `services/ingest/bin/tcgplayer-scraper-onepiece.ts`

**What It Scrapes**:
- ✅ Card metadata (name, set, number, rarity)
- ✅ Product IDs
- ✅ Group IDs (used for tcgcsv matching)
- ✅ Image URLs
- ✅ **Current prices** (but only stored in initial JSONL, not tracked historically)

**Data Flow**:
```
TCGPlayer API → tcgplayer-scraper-onepiece.ts
  ↓
Raw JSONL (data/raw/one-piece.jsonl)
  ↓
Normalization (normalize.ts)
  ↓
Curated JSONL (data/curated/one-piece.jsonl) ← Git LFS
  ↓
Current prices embedded here, but NOT tracked over time
```

**The Problem**:
- Current scraper fetches prices
- But prices are **NOT stored separately for historical tracking**
- Prices get **overwritten** on each scrape
- **No price history** accumulates

#### Designed Price Tracking (Not Operational)

**tcgcsv.com Archive Structure**:
```
https://tcgcsv.com/archive/tcgplayer/prices-{YYYY-MM-DD}.ppmd.7z
  └─ Extracted: {date}/68/{groupId}/prices
     └─ JSON: { "productId": { "marketPrice": 3.50, "lowPrice": 2.50, ... } }
```

**For One Piece Card Game**:
- **categoryId**: 68 (One Piece Card Game)
- **groupIds**: Extracted from our curated cards (e.g., 5001, 5002, 5003...)
- **Example**: `2024-02-08/68/5001/prices` contains all product prices for Romance Dawn

**Designed Data Flow** (not running):
```
[HISTORICAL]
tcgcsv.com archive (Feb 8, 2024 → yesterday)
  ↓
backfill_historical_prices.ts
  ↓
data/prices/historical/one-piece/{YYYY-MM-DD}.jsonl

[DAILY]
TCGPlayer API (today → future)
  ↓
scrape_prices_tcgplayer.ts
  ↓
data/prices/historical/one-piece/{YYYY-MM-DD}.jsonl
```

**Unified JSONL Format**:
```json
{
  "productId": "123456",
  "game": "one-piece",
  "cardName": "Monkey.D.Luffy",
  "setName": "Romance Dawn",
  "number": "OP01-003",
  "date": "2024-02-08",
  "marketPrice": 350,  // cents ($3.50)
  "lowPrice": 250,
  "midPrice": 300,
  "highPrice": 400,
  "directLowPrice": 275,
  "isFoil": false,
  "source": "tcgcsv-archive" | "tcgplayer-api"
}
```

---

## 🔍 Critical Issues Identified

### Issue #1: 🔴 No Price Data Being Collected
**Severity**: CRITICAL
**Impact**: Desktop app cannot display prices, no historical analysis possible

**Current State**:
```bash
$ ls data/prices/
ls: cannot access 'data/prices/': No such file or directory
```

**Expected State**:
```bash
data/prices/
└── historical/
    └── one-piece/
        ├── 2024-02-08.jsonl  # Historical backfill start
        ├── 2024-02-09.jsonl
        ├── ...
        └── 2025-11-07.jsonl  # Today
```

**Why This Matters**:
- ❌ Users can identify cards but see **no prices**
- ❌ Cannot track market trends
- ❌ Cannot show price history graphs
- ❌ Missing core shop functionality

---

### Issue #2: 🔴 GitHub Actions Workflow Incomplete
**Severity**: CRITICAL
**Impact**: Prices never update automatically

**Current Workflow** (line 215-235 in `daily-update.yml`):
```yaml
- name: Run incremental update
  run: |
    pnpm pipeline:update  # Scrapes cards, but NOT prices
```

**What's Missing**:
```yaml
# MISSING: Daily price scraper step
- name: Scrape current prices
  run: |
    echo "Scraping current prices from TCGPlayer..."
    pnpm prices:daily

# MISSING: Commit price data
- name: Commit price updates
  run: |
    git add data/prices/
    git commit -m "chore: Daily price update - $(date +%Y-%m-%d)"
```

---

### Issue #3: 🔴 Historical Backfill Never Run
**Severity**: HIGH
**Impact**: Missing ~640 days of price history (Feb 2024 → present)

**Current State**: Zero historical data

**Expected State** (after backfill):
- **Date range**: Feb 8, 2024 → Nov 6, 2025 (638 days)
- **File count**: 638 JSONL files
- **Estimated size**: ~640 MB (1 MB/day average)
- **Cards tracked**: 5,390 One Piece cards
- **Price points**: ~3.4 million (5,390 cards × 638 days)

**Why It Matters**:
- Historical trends analysis
- Price spike detection
- Investment insights
- Market volatility tracking

---

### Issue #4: 🔴 TCGPlayer API Not Configured
**Severity**: HIGH
**Impact**: Cannot fetch current prices from TCGPlayer

**Current State**:
```typescript
// services/ingest/bin/scrape_prices_tcgplayer.ts:30
const TCGPLAYER_API_BASE = 'https://api.tcgplayer.com';
// No API key configured
```

**Problem**: TCGPlayer API requires authentication
- Need API key from TCGPlayer Developer Portal
- Must add to GitHub Secrets
- Currently will fail with 401 Unauthorized

**Solution**:
1. Register at https://developer.tcgplayer.com
2. Create API app
3. Get Bearer token
4. Add to GitHub Secrets: `TCGPLAYER_API_KEY`

---

### Issue #5: 🟡 Price Data Not in Git LFS
**Severity**: MEDIUM
**Impact**: Will hit GitHub storage limits quickly

**Estimate**:
- Historical backfill: ~640 MB
- Daily additions: ~1.1 MB/day = ~401 MB/year
- Total first year: ~1 GB

**GitHub LFS**:
- Free tier: 1 GB storage, 1 GB bandwidth/month
- Will exceed in ~1 year
- Need paid tier ($5/month for 50 GB)

**Alternatives**:
1. Use Git LFS paid tier
2. Store in S3 + CloudFront (cheaper long-term)
3. Use database instead of JSONL (SQLite → much smaller)

---

## ✅ What's Working Well

### Strengths of Current Implementation

1. ✅ **Card scraping is solid**
   - Incremental updates work
   - Git LFS integration fixed
   - Handles ~5,390 cards efficiently

2. ✅ **Price tracking code is professional**
   - Well-designed architecture
   - Resume support for interruptions
   - Error handling and retry logic
   - Comprehensive documentation

3. ✅ **Data model is sound**
   - JSONL format (append-only, git-friendly)
   - Prices in cents (no floating point errors)
   - Unified historical/daily structure

4. ✅ **tcgcsv.com integration is clever**
   - Free historical data source
   - Daily snapshots since Feb 2024
   - Matches our product IDs perfectly

---

## 🎯 Recommended Action Plan

### Phase 1: Immediate Fixes (Week 1) - CRITICAL

#### 1.1 Set Up TCGPlayer API Access
**Priority**: 🔴 CRITICAL
**Time**: 30 minutes
**Owner**: You (need access to TCGPlayer account)

**Steps**:
```bash
# 1. Register for TCGPlayer API
Visit: https://developer.tcgplayer.com
Create app: "CardFlux Price Tracker"

# 2. Get API credentials
Copy: Bearer Token

# 3. Add to GitHub Secrets
GitHub repo → Settings → Secrets → Actions
Name: TCGPLAYER_API_KEY
Value: <your bearer token>

# 4. Test locally
export TCGPLAYER_API_KEY="your_token_here"
pnpm prices:daily --test-mode
```

**Success Criteria**:
- ✅ API returns price data
- ✅ No 401 errors
- ✅ Can fetch all One Piece card prices

#### 1.2 Run Historical Price Backfill (ONE-TIME)
**Priority**: 🔴 CRITICAL
**Time**: 2-4 hours (automated, just needs monitoring)
**Disk Space**: ~2 GB temp, 640 MB final

**Steps**:
```bash
# 1. Install 7-Zip (if not installed)
# Windows: choco install 7zip
# Mac: brew install p7zip
# Linux: sudo apt-get install p7zip-full

# 2. Verify 7z command works
7z --help

# 3. Create price directories
mkdir -p data/prices/historical/one-piece
mkdir -p .temp/price-archives

# 4. Run backfill (will take 2-4 hours)
pnpm prices:backfill

# This will:
# - Download ~640 days of archives (Feb 8, 2024 → yesterday)
# - Extract category 68 (One Piece) only
# - Match productIds with our 5,390 cards
# - Create data/prices/historical/one-piece/{YYYY-MM-DD}.jsonl
# - Resume if interrupted (state tracking)

# 5. Verify output
ls -lh data/prices/historical/one-piece/ | wc -l
# Should show ~640 files

# 6. Check file sizes
du -sh data/prices/
# Should show ~640 MB
```

**Success Criteria**:
- ✅ 638 JSONL files created (Feb 8, 2024 → yesterday)
- ✅ Total size ~640 MB
- ✅ Each file contains price data for 5,390 cards
- ✅ No errors in logs

#### 1.3 Set Up Git LFS for Price Data
**Priority**: 🔴 CRITICAL (before committing backfill data)
**Time**: 15 minutes

**Steps**:
```bash
# 1. Update .gitattributes
cat >> .gitattributes << 'EOF'
# Price data (historical tracking - large files)
data/prices/**/*.jsonl filter=lfs diff=lfs merge=lfs -text
EOF

# 2. Track existing price files
git lfs track "data/prices/**/*.jsonl"

# 3. Verify LFS tracking
git lfs ls-files
# Should show price JSONL files

# 4. Add files
git add .gitattributes
git add data/prices/

# 5. Check Git LFS status
git lfs status
```

**Success Criteria**:
- ✅ Price files tracked in LFS
- ✅ `.gitattributes` updated
- ✅ `git lfs ls-files` shows price data

#### 1.4 Integrate Price Scraping into GitHub Actions
**Priority**: 🔴 CRITICAL
**Time**: 1 hour

**Changes to `.github/workflows/daily-update.yml`**:

```yaml
# Add after line 235 (after incremental update)

- name: Scrape daily prices from TCGPlayer
  id: scrape_prices
  if: steps.check_data.outputs.has_data == 'true'
  env:
    TCGPLAYER_API_KEY: ${{ secrets.TCGPLAYER_API_KEY }}
  run: |
    echo "🔄 Scraping current prices from TCGPlayer..."
    echo "Date: $(date +%Y-%m-%d)"
    echo ""

    # Run daily price scraper
    pnpm prices:daily

    # Verify output
    TODAY=$(date +%Y-%m-%d)
    PRICE_FILE="data/prices/historical/one-piece/${TODAY}.jsonl"

    if [ -f "$PRICE_FILE" ]; then
      PRICE_COUNT=$(wc -l < "$PRICE_FILE")
      echo "✅ Scraped prices for $PRICE_COUNT cards"
      echo "File: $PRICE_FILE"
      echo "Size: $(du -h "$PRICE_FILE" | cut -f1)"
    else
      echo "⚠️  Price file not created: $PRICE_FILE"
      exit 1
    fi

    echo "price_scrape_status=success" >> $GITHUB_OUTPUT
  continue-on-error: false

# Update commit step (line 312-338) to include price data
- name: Commit and push changes
  if: steps.check_changes.outputs.has_changes == 'true' && github.event.inputs.dry_run != 'true'
  run: |
    # Get stats for commit message
    CARDS_ADDED=$(git diff --cached data/curated/*.jsonl | grep -c "^+" || echo "0")
    PRICES_UPDATED=$(git diff --staged data/prices/ --name-only | wc -l || echo "0")
    FILES_CHANGED=$(git diff --staged --name-only | wc -l)

    # Create detailed commit message
    git commit -m "chore: Automated database update - $(date +%Y-%m-%d)

    Incremental update from TCGPlayer API:
    - Scraped latest card data
    - Downloaded new images ($CARDS_ADDED new cards)
    - Scraped current prices ($PRICES_UPDATED price snapshots)
    - Generated embeddings (DINOv2 with preprocessing)
    - Rebuilt FAISS indices
    - Updated metadata and manifests

    Files changed: $FILES_CHANGED

    🤖 Automated update via GitHub Actions
    📅 $(date -u +%Y-%m-%dT%H:%M:%SZ)
    🔗 Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

    echo "Pushing changes to main..."
    git push origin main

    echo "✅ Changes committed and pushed"
```

**Success Criteria**:
- ✅ Workflow runs `pnpm prices:daily`
- ✅ Prices scraped successfully
- ✅ Price JSONL created for today
- ✅ Committed and pushed automatically

---

### Phase 2: Database Integration (Week 2)

#### 2.1 Build SQLite Price Query Database
**Priority**: 🟡 MEDIUM
**Time**: 4 hours

**Why**: JSONL is great for append-only storage, but slow for queries

**Design**:
```sql
CREATE TABLE prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  game TEXT NOT NULL,
  card_name TEXT NOT NULL,
  set_name TEXT,
  number TEXT,
  date DATE NOT NULL,

  market_price INTEGER,  -- cents
  low_price INTEGER,
  mid_price INTEGER,
  high_price INTEGER,
  direct_low_price INTEGER,

  is_foil BOOLEAN,
  source TEXT,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(product_id, date, is_foil)
);

CREATE INDEX idx_product_date ON prices(product_id, date);
CREATE INDEX idx_game_date ON prices(game, date);
CREATE INDEX idx_card_name ON prices(card_name);
```

**Query Performance**:
- JSONL: ~2-5 seconds to scan 640 files
- SQLite: ~10-50ms with indexes

**Implementation**:
```bash
# Create script: services/ingest/bin/build_price_database.ts
pnpm db:prices:build   # One-time build from JSONL
pnpm db:prices:update  # Daily update (add today's prices)
```

#### 2.2 Integrate with Desktop App
**Priority**: 🟡 MEDIUM
**Time**: 6 hours

**Features**:
1. Show current price in card identification results
2. Show price history graph (7 days, 30 days, all-time)
3. Price change indicators (↑ ↓)
4. Price alerts (if card value changes >10%)

**UI Mockup**:
```
┌─────────────────────────────────────────┐
│ Identified: Monkey.D.Luffy (OP01-003)   │
│                                         │
│ Current Price: $12.50 ↑ (+$1.20, +10%) │
│                                         │
│ Price History (30 days):                │
│ ╭─────────────────╮                     │
│ │  Graph here     │                     │
│ ╰─────────────────╯                     │
│                                         │
│ Low: $9.00  High: $15.00  Avg: $11.80  │
└─────────────────────────────────────────┘
```

---

### Phase 3: Advanced Features (Month 2)

#### 3.1 Price Analytics Dashboard
- Portfolio tracking (total value of scanned cards)
- Market trends (cards gaining/losing value)
- Rarity analysis (price by rarity over time)

#### 3.2 Price Notifications
- Daily email/Discord with price changes
- Alert if any scanned card spikes >20%
- Weekly market summary

#### 3.3 Multi-Game Expansion
- Add Pokémon price tracking
- Add Magic: The Gathering price tracking
- Unified price database for all games

---

## 📝 Implementation Checklist

### Immediate (This Week)
- [ ] Register for TCGPlayer API access
- [ ] Add `TCGPLAYER_API_KEY` to GitHub Secrets
- [ ] Test price scraper locally
- [ ] Run historical price backfill (2-4 hours)
- [ ] Set up Git LFS for price data
- [ ] Update `.github/workflows/daily-update.yml`
- [ ] Test full CI workflow end-to-end
- [ ] Verify daily prices are collected

### Short-Term (Next 2 Weeks)
- [ ] Build SQLite price database
- [ ] Add price query API
- [ ] Integrate price display in desktop app
- [ ] Add price history graphs
- [ ] Test with real shop inventory

### Long-Term (Next Month)
- [ ] Add price analytics dashboard
- [ ] Implement price alerts
- [ ] Add multi-game support
- [ ] Consider S3 storage for historical data

---

## 🎓 Key Learnings & Recommendations

### What Went Wrong
1. **Implementation ≠ Integration** - Code was written but never wired up
2. **CI incomplete** - Workflow updated for cards but forgot prices
3. **No validation** - Never verified prices were being collected
4. **Documentation drift** - Docs say "ready" but system not operational

### Best Practices Going Forward
1. ✅ **End-to-end testing** - Run full pipeline locally before CI
2. ✅ **Validation steps** - Add health checks to CI workflow
3. ✅ **Monitoring** - Track price scrape success/failure rates
4. ✅ **Documentation accuracy** - Docs should match reality

### Storage Strategy Recommendation

**Short-term** (< 1 year):
- Use Git LFS free tier (1 GB)
- Store JSONL files directly
- Simple, works with existing infrastructure

**Long-term** (> 1 year):
- Migrate to S3 + SQLite hybrid:
  - S3: Raw JSONL archives (cold storage, ~$0.023/GB/month)
  - SQLite: Query database (< 100 MB, fast queries)
  - CloudFront: CDN for price API (fast global access)
- Cost: ~$2-3/month for 10 GB vs $5/month Git LFS

---

## 📊 Success Metrics

### Week 1 (After Implementation)
- ✅ 638 historical JSONL files created
- ✅ Daily prices collected automatically
- ✅ CI workflow runs without errors
- ✅ Git LFS tracking working

### Week 2 (After Database Integration)
- ✅ SQLite database built (< 100 MB)
- ✅ Queries return in < 50ms
- ✅ Desktop app shows current prices
- ✅ Price history graphs working

### Month 1 (Production)
- ✅ 30+ days of continuous price tracking
- ✅ Zero missed daily collections
- ✅ Users see prices on all identified cards
- ✅ Price analytics working

---

## 🚨 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| TCGPlayer API rate limits | Medium | High | Batch requests, 1s delay, retry logic ✅ |
| Git LFS storage exceeded | High | Medium | Monitor usage, migrate to S3 if needed |
| Historical backfill fails | Low | Medium | Resume support, state tracking ✅ |
| Price data corruption | Low | High | Validation checks, immutable JSONL |
| CI workflow breaks | Medium | High | Extensive testing, rollback plan |

---

## 💰 Cost Analysis

### Option A: Git LFS (Current Plan)
- **Free tier**: 1 GB storage, 1 GB bandwidth/month
- **Will last**: ~12 months
- **Then**: $5/month for 50 GB data pack
- **Total Year 1**: $0
- **Total Year 2**: $60

### Option B: AWS S3 + CloudFront
- **S3 storage**: ~10 GB × $0.023/GB = $0.23/month
- **CloudFront**: ~5 GB transfer × $0.085/GB = $0.43/month
- **Total**: ~$0.70/month = **$8.40/year**
- **Savings**: $51.60/year after Year 1

**Recommendation**: Start with Git LFS, migrate to S3 when storage > 1 GB

---

## 🎯 Conclusion

**Current State**: 🔴 Price tracking is **100% non-operational** despite having code

**Root Cause**: Integration gap between implementation and CI workflow

**Priority Actions**:
1. 🔴 **CRITICAL**: Add price scraping to GitHub Actions (2 hours)
2. 🔴 **CRITICAL**: Run historical backfill (2-4 hours one-time)
3. 🔴 **CRITICAL**: Set up Git LFS for price data (30 min)
4. 🟡 **HIGH**: Build SQLite query database (4 hours)
5. 🟡 **MEDIUM**: Integrate with desktop app (6 hours)

**Timeline**: Can be fully operational in **1 week** with focused effort

**Expected Outcome**:
- ✅ 640+ days of historical price data
- ✅ Daily automatic price updates
- ✅ Desktop app shows prices
- ✅ Price history analysis available
- ✅ Production-ready price tracking

---

**Audited By**: Senior Principal Engineer (Claude Code)
**Date**: November 7, 2025
**Next Review**: After Phase 1 completion
