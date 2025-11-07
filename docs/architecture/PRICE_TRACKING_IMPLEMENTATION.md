# Price Tracking System - Implementation Guide

## System Architecture

### Two-Phase Approach

**Phase 1: Historical Backfill** (Feb 8, 2024 → Yesterday)
- Source: tcgcsv.com archives
- Data: Daily price snapshots (compressed 7z archives)
- Runs: One-time backfill, then never again

**Phase 2: Daily Updates** (Today → Future)
- Source: TCGPlayer API direct
- Data: Current market prices
- Runs: Daily at 3 PM PDT (after TCGPlayer updates)

### Data Flow

```
Historical (Past):
tcgcsv.com archives → Download → Extract → Match productIds → Store JSONL

Current (Daily):
TCGPlayer API → Batch fetch → Match productIds → Store JSONL → Append to history

Query (Anytime):
JSONL files → Load → SQLite in-memory → Fast queries
```

## tcgcsv Archive Structure

### Archive URL Pattern
```
https://tcgcsv.com/archive/tcgplayer/prices-{YYYY-MM-DD}.ppmd.7z
```

Example: `https://tcgcsv.com/archive/tcgplayer/prices-2024-02-08.ppmd.7z`

### Extracted Structure
```
2024-02-08/
  ├── 3/           # Pokemon (categoryId: 3)
  ├── 68/          # One Piece Card Game (categoryId: 68) ⭐
  │   ├── 24303/   # Group: "Carrying On His Will"
  │   │   └── prices    # JSON file with productId → price data
  │   ├── 24304/   # Group: "Romance Dawn"
  │   │   └── prices
  │   ├── 24688/   # Group: "Paramount War"
  │   │   └── prices
  │   └── ...      # ~50 more groups
  └── 80/          # Lorcana
```

### prices File Format
```json
{
  "123456": {
    "lowPrice": 1.50,
    "midPrice": 2.00,
    "highPrice": 3.50,
    "marketPrice": 2.25,
    "directLowPrice": 1.75,
    "subTypeName": "Normal"  // or "Foil"
  },
  "123457": { ... },
  ...
}
```

## Implementation Files

### 1. Historical Backfill Script
**File**: `services/ingest/bin/backfill_historical_prices.ts`

**What it does:**
1. Downloads daily archives from Feb 8, 2024 → yesterday
2. Extracts category 68 (One Piece) data only
3. For each group (set) in our curated data:
   - Load the `prices` file
   - Match productIds with our cards
   - Convert prices to cents (avoid floating point errors)
4. Save as JSONL: `data/prices/historical/{game}/{YYYY-MM-DD}.jsonl`
5. Resume support: Can continue after interruption

**Usage:**
```bash
pnpm prices:backfill
```

**Requirements:**
- 7-Zip installed (`7z` command available)
- ~2 GB disk space for temp archives
- Internet connection
- Time: ~2-4 hours for full backfill (640+ days of data)

### 2. Daily Price Scraper
**File**: `services/ingest/bin/scrape_prices_tcgplayer.ts`

**What it does:**
1. Fetches current prices from TCGPlayer API
2. Batch requests (50 products per request)
3. Rate limiting (300 req/hour limit)
4. Saves to JSONL: `data/prices/snapshots/{game}/{YYYY-MM-DD}.jsonl`

**Usage:**
```bash
pnpm prices:daily
```

**Runs:** Daily at 3 PM PDT via CI workflow

### 3. SQLite Storage (Future)
**File**: `services/ingest/bin/build_price_database.ts` (TODO)

**What it does:**
1. Reads all JSONL files (historical + daily)
2. Imports into SQLite database
3. Creates indexes for fast queries
4. Supports time-range queries

**Schema:**
```sql
CREATE TABLE price_snapshots (
  product_id TEXT NOT NULL,
  game TEXT NOT NULL,
  date TEXT NOT NULL,
  market_price INTEGER,    -- cents
  low_price INTEGER,
  high_price INTEGER,
  is_foil BOOLEAN,
  source TEXT,             -- 'tcgcsv-archive' or 'tcgplayer-api'

  PRIMARY KEY (product_id, date, is_foil),
  INDEX idx_product_date (product_id, date),
  INDEX idx_game_date (game, date)
);
```

## Data Verification

### Matching Logic

**Critical**: Must match our productIds exactly!

```typescript
// Our curated data
{
  "id": "OP01-003",
  "productId": 123456,
  "groupId": 24304,
  "name": "Monkey.D.Luffy",
  ...
}

// tcgcsv archive: /68/24304/prices
{
  "123456": {
    "marketPrice": 3.50,
    ...
  }
}

// Match on productId
if (archiveData[card.productId]) {
  // Found price data!
}
```

### Validation Checks

1. **Product ID exists** in our curated data
2. **Group ID matches** archive structure
3. **Price is reasonable** (not null, not negative, not absurdly high)
4. **Date continuity** (no huge gaps in historical data)

## Storage Strategy

### File Structure
```
data/prices/
  historical/
    one-piece/
      2024-02-08.jsonl
      2024-02-09.jsonl
      ...
      2025-11-05.jsonl     # Yesterday
  snapshots/
    one-piece/
      2025-11-06.jsonl     # Today (from TCGPlayer API)
      2025-11-07.jsonl     # Tomorrow
      ...
```

### JSONL Format
One price snapshot per line:
```json
{"productId":"123456","game":"one-piece","cardName":"Monkey.D.Luffy","date":"2024-02-08","marketPrice":350,"lowPrice":250,"isFoil":false,"source":"tcgcsv-archive"}
{"productId":"123457","game":"one-piece","cardName":"Roronoa.Zoro","date":"2024-02-08","marketPrice":450","lowPrice":300,"isFoil":false,"source":"tcgcsv-archive"}
```

### Why JSONL?
- **Append-only**: Easy to add daily snapshots
- **Line-by-line parsing**: Memory efficient for large files
- **Human-readable**: Easy debugging
- **Git-friendly**: Clean diffs when adding new days

## Storage Estimates

### One Piece (5,600 cards)

**Historical (Feb 8, 2024 → Nov 5, 2025 = 640 days):**
- 5,600 cards × 640 days = 3,584,000 snapshots
- ~200 bytes per snapshot (JSON)
- Total: 3,584,000 × 200 = 716.8 MB

**Daily (ongoing):**
- 5,600 cards × ~200 bytes = 1.1 MB/day
- Per year: 1.1 MB × 365 = 401.5 MB

**Total after 1 year:** ~1.1 GB

### Multi-Game (10 games = 56,000 cards)
- Historical: 7.2 GB
- Daily: 11 MB/day
- Per year: 4 GB

**Git LFS Consideration:**
- Free tier: 1 GB storage
- Need paid tier ($5/month) or S3 hosting

## Integration Points

### Desktop App
```typescript
// When identifying a card
const identifyResult = await identifyCard(image);
const currentPrice = await getCurrentPrice(identifyResult.productId);

// Show in UI
console.log(`${identifyResult.name}: $${currentPrice.marketPrice / 100}`);
console.log(`7-day trend: ${currentPrice.trend7d > 0 ? '↑' : '↓'} ${currentPrice.trend7d}%`);
```

### CI Workflow
```yaml
- name: Update daily prices
  run: pnpm prices:daily

- name: Commit price data
  run: |
    git add data/prices/snapshots/
    git commit -m "chore: Daily price update - $(date +%Y-%m-%d)"
```

## Error Handling

### Common Issues

**Issue 1: Archive not available**
```
⚠️  Archive not available for 2024-12-25
```
**Solution**: Skip date, log to failedDates, continue

**Issue 2: 7z not installed**
```
✗ Extraction failed: 7z command not found
```
**Solution**: Install 7-Zip, see README

**Issue 3: Group not in archive**
```
Group 24303 not found in archive
```
**Solution**: Skip group, log warning, continue (likely new set)

**Issue 4: Rate limiting**
```
✗ Download failed: 429 Too Many Requests
```
**Solution**: Implement exponential backoff, retry after delay

## Testing Strategy

### 1. Small Date Range Test
```bash
# Test with just one week
node services/ingest/bin/backfill_historical_prices.ts --start-date 2024-02-08 --end-date 2024-02-14
```

### 2. Verify Data Quality
```typescript
// Check for reasonable prices
const snapshot = await loadSnapshot('one-piece', '2024-02-08');
assert(snapshot.marketPrice > 0);
assert(snapshot.marketPrice < 100000); // $1000 max
assert(snapshot.lowPrice <= snapshot.highPrice);
```

### 3. Coverage Check
```bash
# Count unique product IDs with price data
cat data/prices/historical/one-piece/*.jsonl | jq -r .productId | sort -u | wc -l

# Should be close to total card count
wc -l data/curated/one-piece.jsonl
```

## Performance Optimization

### Download Optimization
- **Parallel downloads**: Download 5 archives concurrently
- **Resume downloads**: Skip already-downloaded archives
- **Cleanup old archives**: Delete after extraction (save 2 GB)

### Extraction Optimization
- **Extract only category 68**: Use 7z filters
- **In-memory processing**: Don't write intermediate files
- **Parallel group processing**: Process multiple groups concurrently

### Storage Optimization
- **Compress old JSONL**: gzip files older than 90 days (10x smaller)
- **Archive to Parquet**: Convert old JSONL to Parquet (20x smaller, better queries)
- **S3 cold storage**: Move 1+ year old data to S3 Glacier ($0.004/GB/month)

## Rollout Plan

### Week 1: Backfill Historical Data
- ✅ Implement backfill script
- ✅ Test with one week of data
- ⏳ Run full backfill (Feb 8, 2024 → present)
- ⏳ Verify data quality
- ⏳ Commit historical JSONL to Git LFS

### Week 2: Daily Price Updates
- ⏳ Implement TCGPlayer API scraper
- ⏳ Add to CI workflow (daily at 3 PM)
- ⏳ Test automated updates
- ⏳ Monitor for failures

### Week 3: SQLite Database
- ⏳ Import JSONL into SQLite
- ⏳ Create query API
- ⏳ Benchmark performance

### Week 4: Desktop Integration
- ⏳ Add price display to card identification
- ⏳ Show price history charts
- ⏳ Price trend indicators

## Key Decisions Made

### ✅ Use tcgcsv.com for historical data
**Why**: Free, comprehensive, daily snapshots from Feb 2024
**Alternative**: TCGPlayer API historical endpoint (requires paid plan)

### ✅ Store prices in cents
**Why**: Avoid floating point errors ($0.01 + $0.02 = $0.03 exactly)
**Alternative**: Store as floats (JavaScript has precision issues)

### ✅ JSONL for raw storage
**Why**: Append-only, parseable, git-friendly
**Alternative**: Direct SQLite insert (harder to version control)

### ✅ Two-phase approach (backfill + daily)
**Why**: Don't re-download historical data every day
**Alternative**: Always fetch from API (wasteful, slow)

---

**Status**: Design Complete, Backfill Script Implemented
**Next**: Test backfill with small date range, then run full backfill
**Owner**: Eric
**Timeline**: Week 1 in progress
