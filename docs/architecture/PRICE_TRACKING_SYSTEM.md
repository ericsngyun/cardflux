# Price Tracking System - Architecture Design

## Overview

Capture and store historical pricing data for all TCG cards to enable:
- Price trend analysis
- Market value tracking
- Inventory valuation
- Price alerts
- Investment insights

## Requirements

### Functional
1. **Daily price capture** - Scrape prices from TCGPlayer daily
2. **Multi-condition support** - Track Near Mint, Lightly Played, Moderately Played, Heavily Played
3. **Multi-printing support** - Track different printings (1st edition, unlimited, etc.)
4. **Foil variants** - Separate pricing for normal vs foil cards
5. **Historical retention** - Keep all historical data indefinitely
6. **Efficient storage** - Compress old data, optimize for time-series queries
7. **Multi-game support** - Work with One Piece, Pokemon, Magic, etc.

### Non-Functional
1. **Storage efficiency** - ~1KB per card per day, ~365KB per card per year
2. **Query performance** - Sub-second queries for price history
3. **CI integration** - Run as part of daily update workflow
4. **Resilient** - Handle API failures gracefully, retry with backoff
5. **Auditable** - Log all price changes with timestamps

## Data Model

### Price Snapshot Schema

```typescript
interface PriceSnapshot {
  // Identity
  productId: string;           // TCGPlayer product ID
  game: string;                // "one-piece", "pokemon", etc.
  cardName: string;            // "Monkey.D.Luffy"
  setName: string;             // "Romance Dawn"
  number: string;              // "OP01-003"
  rarity: string;              // "Leader"

  // Pricing (all in USD cents to avoid floating point issues)
  timestamp: string;           // ISO 8601 timestamp
  date: string;                // YYYY-MM-DD for daily aggregation

  // Market prices (in cents)
  marketPrice: number | null;  // Current market price
  lowPrice: number | null;     // Lowest available
  midPrice: number | null;     // Median price
  highPrice: number | null;    // Highest available

  // Buylist (what shops pay)
  buylistMarket: number | null;
  buylistLow: number | null;
  buylistHigh: number | null;

  // Variants
  isFoil: boolean;
  condition: "NM" | "LP" | "MP" | "HP" | "DMG";
  printing: string | null;     // "1st Edition", "Unlimited", etc.

  // Metadata
  listingCount: number;        // Number of active listings
  source: "tcgplayer" | "ebay" | "cardmarket";
}
```

### Storage Strategy

**Hybrid approach: SQLite + Parquet files**

#### 1. **Hot Storage (SQLite)** - Last 90 days
```sql
-- Fast queries for recent data
CREATE TABLE price_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  game TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  date TEXT NOT NULL,
  market_price INTEGER,
  low_price INTEGER,
  mid_price INTEGER,
  high_price INTEGER,
  is_foil BOOLEAN DEFAULT 0,
  condition TEXT DEFAULT 'NM',
  listing_count INTEGER,
  source TEXT DEFAULT 'tcgplayer',

  -- Indexes for fast queries
  INDEX idx_product_date (product_id, date),
  INDEX idx_game_date (game, date),
  INDEX idx_date (date)
);
```

#### 2. **Cold Storage (Parquet)** - 90+ days old
```
data/prices/
  one-piece/
    2024-01.parquet   # January 2024 prices (compressed)
    2024-02.parquet   # February 2024 prices
    ...
  pokemon/
    2024-01.parquet
    ...
```

**Why Parquet?**
- Columnar format optimized for time-series analytics
- 10-20x compression vs JSON
- Fast range queries (dates, price ranges)
- Native support in pandas, polars, DuckDB

### Daily Aggregation

Store one snapshot per card per day (end-of-day prices):

```typescript
interface DailyPriceSummary {
  productId: string;
  date: string;        // YYYY-MM-DD

  // Aggregated from all snapshots that day
  marketPrice: number;      // Closing price
  dailyLow: number;         // Lowest seen that day
  dailyHigh: number;        // Highest seen that day
  avgPrice: number;         // Average across the day

  // Volume metrics
  totalListings: number;
  priceChangePercent: number;  // % change from previous day
}
```

## Implementation Plan

### Phase 1: Basic Price Capture (Week 1)

**Goal**: Capture daily end-of-day prices for One Piece cards

1. **Price Scraper** (`services/ingest/bin/scrape_prices.ts`)
   ```typescript
   // Fetch pricing for all products
   async function scrapePrices(game: string): Promise<PriceSnapshot[]>

   // Use TCGPlayer API's pricing endpoints
   GET /pricing/product/{productId}
   GET /pricing/group/{groupId}  // Batch pricing for sets
   ```

2. **Price Storage** (`services/ingest/bin/store_prices.ts`)
   ```typescript
   // Store in SQLite
   async function storePriceSnapshots(snapshots: PriceSnapshot[])

   // Append-only, never update historical data
   ```

3. **Daily Job** (CI workflow)
   ```yaml
   - name: Capture daily prices
     run: pnpm prices:capture
   ```

### Phase 2: Historical Archive (Week 2)

**Goal**: Move old data to compressed Parquet files

1. **Archive Script** (`services/ingest/bin/archive_prices.ts`)
   ```typescript
   // Move prices older than 90 days to Parquet
   async function archiveOldPrices(cutoffDate: string)
   ```

2. **Monthly Job** (CI workflow - 1st of each month)
   ```yaml
   - name: Archive old prices
     run: pnpm prices:archive
   ```

### Phase 3: Query API (Week 3)

**Goal**: Provide fast queries for price history

1. **Price Query Service** (`packages/shared/src/prices.ts`)
   ```typescript
   // Get price history for a card
   async function getPriceHistory(
     productId: string,
     startDate: string,
     endDate: string
   ): Promise<DailyPriceSummary[]>

   // Get current market value
   async function getCurrentPrice(productId: string): Promise<PriceSnapshot>

   // Get price trends (7-day, 30-day, 90-day)
   async function getPriceTrends(productId: string): Promise<PriceTrends>
   ```

2. **Desktop App Integration**
   - Show price history chart when identifying cards
   - Display current market value
   - Show price trend indicators (↑ +5% this week)

### Phase 4: Analytics (Week 4)

**Goal**: Advanced price analytics and insights

1. **Trend Detection**
   ```typescript
   // Detect price spikes/drops
   function detectPriceAnomalies(history: DailyPriceSummary[]): Anomaly[]

   // Calculate volatility
   function calculateVolatility(history: DailyPriceSummary[]): number
   ```

2. **Market Insights**
   - Top gainers/losers of the day
   - Most volatile cards
   - Undervalued cards (market price < historical avg)

## TCGPlayer API Pricing Endpoints

### Available Endpoints

```typescript
// Product pricing (single card)
GET /pricing/product/{productId}
Response: {
  productId: 123,
  lowPrice: 1.50,
  midPrice: 2.00,
  highPrice: 3.50,
  marketPrice: 2.25,
  directLowPrice: 1.75,
  subTypeName: "Normal"  // or "Foil"
}

// Batch pricing (multiple cards)
POST /pricing/product
Body: { productIds: [123, 456, 789] }
Response: [/* array of pricing objects */]

// Group pricing (entire set)
GET /pricing/group/{groupId}
Response: [/* all products in set with pricing */]

// Buylist pricing
GET /pricing/buy/product/{productId}
```

### Rate Limits
- **300 requests per hour** (free tier)
- **Batch requests count as 1** (use for efficiency)
- **Recommended**: Use group pricing to get entire sets at once

### Pricing Strategy

**Optimal approach:**
1. Use `GET /pricing/group/{groupId}` to fetch entire sets
2. One request per set = ~50-100 products per request
3. One Piece has ~50 sets = ~50 requests total
4. Well within 300 req/hour limit
5. Run once per day at 3 PM PDT (after TCGPlayer updates at 1 PM)

## Storage Estimates

### One Piece (5,600 cards)

**Daily snapshot:**
- 5,600 cards × ~200 bytes = 1.1 MB/day
- Compress to Parquet: ~200 KB/day
- Per year: 200 KB × 365 = 73 MB/year
- After 5 years: 365 MB

**With 10 games (56,000 cards):**
- Daily: 2 MB
- Yearly: 730 MB
- 5 years: 3.65 GB

**Storage is very affordable!** GitHub LFS free tier = 1 GB storage, so we'd need paid tier ($5/month) or S3 hosting (~$0.10/month).

## Query Performance

### SQLite (Last 90 days)

```sql
-- Get price history for one card
SELECT date, market_price, listing_count
FROM price_snapshots
WHERE product_id = 'OP01-003' AND date >= '2024-01-01'
ORDER BY date DESC;
-- Query time: ~5ms (indexed)

-- Get top gainers today
SELECT product_id, market_price,
       (market_price - prev_day_price) / prev_day_price * 100 AS gain_percent
FROM price_snapshots p1
JOIN price_snapshots p2 ON p1.product_id = p2.product_id
WHERE p1.date = '2024-11-06' AND p2.date = '2024-11-05'
ORDER BY gain_percent DESC
LIMIT 10;
-- Query time: ~50ms
```

### Parquet (Historical data)

```python
import polars as pl

# Load specific month
df = pl.read_parquet('data/prices/one-piece/2024-01.parquet')

# Get price history
history = df.filter(pl.col('product_id') == 'OP01-003').sort('date')
# Query time: ~20ms (columnar format optimized for filtering)

# Price trend analysis
trend = df.group_by('date').agg([
    pl.col('market_price').mean(),
    pl.col('market_price').max(),
    pl.col('market_price').min()
])
# Query time: ~100ms for 1M records
```

## Migration Path

### Week 1: Proof of Concept
- ✅ Scrape prices for One Piece
- ✅ Store in SQLite
- ✅ Verify data quality

### Week 2: Production
- ✅ Add to CI workflow
- ✅ Run daily at 3 PM PDT
- ✅ Monitor for failures

### Week 3: Historical Archive
- ✅ Implement Parquet archiving
- ✅ Backfill historical data (if available from TCGPlayer)

### Week 4: Desktop Integration
- ✅ Add price display to identification results
- ✅ Show price history charts
- ✅ Price trend indicators

## Future Enhancements

### Phase 5: Multi-Source Pricing
- Add eBay sold listings (actual transaction prices)
- Add Card Market (European pricing)
- Add TCGPlayer marketplace vs direct pricing

### Phase 6: Predictive Analytics
- ML model to predict price trends
- Seasonal pattern detection (holidays, tournaments)
- Reprint impact analysis

### Phase 7: Real-time Alerts
- Price drop notifications
- Inventory value tracking
- "Hot cards" detection (sudden demand spikes)

## Key Decisions

### Why SQLite + Parquet?
- **SQLite**: Fast queries for recent data, ACID guarantees, no separate server
- **Parquet**: Optimal for cold storage, 10-20x compression, analytics-friendly
- **Alternative considered**: PostgreSQL with TimescaleDB - rejected (too complex for now)

### Why daily snapshots?
- **Sufficient granularity** for most use cases (not day-trading)
- **Manageable storage** (~73 MB/year per game)
- **Within API limits** (300 req/hour easily handles daily updates)
- **Future**: Can add intraday snapshots if needed

### Why cents instead of dollars?
- **Avoid floating point errors** (0.1 + 0.2 ≠ 0.3 in floating point)
- **Integer arithmetic is exact** (150 + 200 = 350 cents = $3.50)
- **Database efficiency** (integers are smaller and faster than floats)

## Success Metrics

- **Coverage**: >95% of cards have pricing data
- **Freshness**: Prices updated within 24 hours
- **Accuracy**: Prices match TCGPlayer within 1%
- **Availability**: 99.9% uptime (API failures gracefully handled)
- **Storage**: <100 MB per game per year

---

**Status**: Design Complete, Ready for Implementation
**Owner**: Eric
**Timeline**: 4 weeks to full production
**Cost**: $5/month GitHub LFS or $0.10/month S3
