# TCGplayer Integration via tcgcsv.com

## 🎯 Overview

CardFlux now uses **tcgcsv.com** as a unified data source for all TCG games. This provides:
- ✅ **Single API** for all games (Magic, Pokemon, YuGiOh, etc.)
- ✅ **Price Data** included (normal + foil prices)
- ✅ **Daily Updates** available
- ✅ **Structured Hierarchy** (Categories → Groups → Products → Prices)

---

## 📊 API Structure

### **Hierarchy:**
```
tcgcsv.com/tcgplayer/
├── categories                           # GET all categories
├── {categoryId}/
│   ├── groups                           # GET all sets in category
│   └── {groupId}/
│       ├── products                     # GET products in set
│       └── prices                       # GET prices for products
```

### **Category IDs:**
- `1` = Magic: The Gathering
- `2` = Yu-Gi-Oh!
- `3` = Pokemon
- `24` = One Piece
- `26` = Digimon

Full list: `https://tcgcsv.com/tcgplayer/categories`

### **Example URLs:**
```
# Get Magic groups (sets)
https://tcgcsv.com/tcgplayer/1/groups

# Get products from "10th Edition" (groupId=1)
https://tcgcsv.com/tcgplayer/1/1/products

# Get prices for "10th Edition"
https://tcgcsv.com/tcgplayer/1/1/prices
```

---

## 📦 Data Models

### **Product Response:**
```typescript
{
  productId: 15023,
  name: "Abundance",
  cleanName: "Abundance",
  imageUrl: "https://tcgplayer-cdn.tcgplayer.com/product/15023_200w.jpg",
  categoryId: 1,
  groupId: 1,
  url: "https://www.tcgplayer.com/product/15023/...",
  modifiedOn: "2024-07-08T16:26:12.31",
  extendedData: [
    { name: "Rarity", value: "R" },
    { name: "Number", value: "249" },
    { name: "SubType", value: "Enchantment" },
    { name: "OracleText", value: "..." }
  ]
}
```

### **Price Response:**
```typescript
{
  productId: 15023,
  lowPrice: 0.95,
  midPrice: 1.50,
  highPrice: 14.99,
  marketPrice: 1.58,
  directLowPrice: null,
  subTypeName: "Normal"  // or "Foil"
}
```

### **Merged Card Data:**
```typescript
{
  productId: 15023,
  name: "Abundance",
  categoryName: "Magic",
  groupName: "10th Edition",
  rarity: "R",
  number: "249",
  prices: {
    normal: { low: 0.95, mid: 1.50, high: 14.99, market: 1.58 },
    foil: { low: 64.05, mid: 85.50, high: 120.00, market: 66.42 }
  }
}
```

---

## 🚀 Usage

### **1. Scrape TCGplayer Data**
```bash
# Scrape all enabled categories (Magic, Pokemon, YuGiOh, One Piece, Digimon)
pnpm tcgplayer:scrape
```

**What it does:**
1. Fetches categories from tcgcsv.com
2. For each category, fetches all groups (sets)
3. For each group, fetches products + prices in parallel
4. Merges product and price data
5. Saves to `data/curated/{category}.jsonl`

**Output:**
```
data/
├── raw/tcgplayer/
│   ├── magic/
│   │   ├── 1_10th_Edition.json
│   │   └── 5_Alara_Reborn.json
│   └── pokemon/
│       └── ...
└── curated/
    ├── magic.jsonl          # All Magic cards with prices
    ├── pokemon.jsonl
    └── yugioh.jsonl
```

### **2. Build Database**
```bash
# Build SQLite with price data
pnpm tcgplayer:db
```

**Schema:**
```sql
-- Cards table
CREATE TABLE cards (
  product_id INTEGER PRIMARY KEY,
  category_id INTEGER,
  category_name TEXT,
  group_name TEXT,
  name TEXT,
  rarity TEXT,
  card_number TEXT,
  image_url TEXT,
  oracle_text TEXT
);

-- Prices table
CREATE TABLE prices (
  product_id INTEGER,
  finish TEXT,              -- 'normal' or 'foil'
  low_price REAL,
  mid_price REAL,
  high_price REAL,
  market_price REAL,
  FOREIGN KEY (product_id) REFERENCES cards(product_id)
);

-- Full-text search
CREATE VIRTUAL TABLE cards_fts USING fts5(name, oracle_text);
```

**Queries:**
```sql
-- Find card by name
SELECT * FROM cards WHERE name LIKE '%Lightning Bolt%';

-- Get prices for a card
SELECT c.*, p.*
FROM cards c
LEFT JOIN prices p ON c.product_id = p.product_id
WHERE c.name = 'Abundance';

-- Full-text search
SELECT * FROM cards_fts WHERE cards_fts MATCH 'flying dragon';
```

---

## 🔧 Configuration

### **Enable/Disable Categories:**
Edit `packages/config/src/tcgplayer-config.ts`:
```typescript
enabledCategories: [
  { categoryId: 1, name: 'Magic', enabled: true },
  { categoryId: 2, name: 'YuGiOh', enabled: true },
  { categoryId: 3, name: 'Pokemon', enabled: true },
  { categoryId: 24, name: 'One Piece', enabled: true },
  { categoryId: 26, name: 'Digimon', enabled: true },
  { categoryId: 68, name: 'Lorcana', enabled: false }, // Disabled
]
```

### **Rate Limiting:**
```typescript
rateLimit: {
  requestsPerSecond: 5,
  delayBetweenGroups: 2000,     // 2 sec between sets
  delayBetweenCategories: 5000, // 5 sec between games
  maxRetries: 3,
}
```

---

## ☁️ Cloud Deployment (Future)

### **Cloud-Agnostic Architecture:**
```typescript
// Storage abstraction supports AWS S3, GCS, Azure
import { createStorage } from '@cardflux/shared';

const storage = createStorage({
  provider: 's3',  // or 'gcs', 'azure', 'local'
  bucket: 'cardflux-data',
  region: 'us-east-1'
});

// Upload to cloud
await storage.upload(buffer, 'curated/magic.jsonl');
```

### **Daily Scraper (Recommended Setup):**

**Option 1: AWS Lambda + EventBridge**
```yaml
# serverless.yml
functions:
  dailyScraper:
    handler: services/ingest/bin/tcgplayer-scraper.handler
    events:
      - schedule: cron(0 6 * * ? *)  # Daily at 6 AM UTC
    environment:
      STORAGE_PROVIDER: s3
      STORAGE_BUCKET: cardflux-data
```

**Option 2: Google Cloud Functions + Scheduler**
```typescript
// Deploy to GCF
export const dailyScraper = functions.pubsub
  .schedule('0 6 * * *')  // Daily at 6 AM
  .onRun(async () => {
    // Run scraper
  });
```

**Option 3: Docker + Cron (Any Cloud)**
```dockerfile
FROM node:20
COPY . /app
RUN pnpm install
CMD ["pnpm", "tcgplayer:scrape"]
```

```bash
# Run daily via cron
0 6 * * * docker run cardflux-scraper
```

---

## 📈 Incremental Updates (TODO)

**Strategy:**
1. Store last `modifiedOn` timestamp per group
2. On daily run, compare timestamps
3. Only re-fetch groups that changed
4. Merge with existing data

**State File:**
```json
{
  "lastSync": "2024-10-03T06:00:00Z",
  "groups": [
    {
      "categoryId": 1,
      "groupId": 1,
      "lastModified": "2024-07-08T16:26:12.31",
      "productCount": 398
    }
  ]
}
```

---

## 🔍 Desktop App Integration (TODO)

**Display Prices in UI:**
```typescript
// After card detection
const card = await findCard(warpedImage);

// Show price info
displayCard({
  name: card.name,
  image: card.imageUrl,
  prices: {
    normal: `$${card.prices.normal.market}`,
    foil: `$${card.prices.foil.market}`
  }
});
```

---

## 🎯 Migration Status

| Component | Status | Notes |
|-----------|--------|-------|
| ✅ TCGplayer Config | Complete | `tcgplayer-config.ts` |
| ✅ Unified Scraper | Complete | `tcgplayer-scraper.ts` |
| ✅ Database Schema | Complete | Includes prices table |
| ✅ Cloud Storage Abstraction | Complete | Supports S3/GCS/Azure |
| ⏳ Incremental Updates | TODO | Needs `modifiedOn` comparison |
| ⏳ Desktop App UI | TODO | Display prices in scanner |
| ⏳ Cloud Deployment | TODO | AWS Lambda / GCF |

---

## 🚨 Important Notes

1. **Rate Limiting**: Be respectful! Current limit: 5 req/sec
2. **Price Accuracy**: Prices update daily (~6 AM UTC)
3. **SKU Limitation**: tcgcsv.com doesn't provide condition-specific prices
4. **Normal vs Foil**: Each product has 2 price entries (normal + foil)

---

## 📝 Next Steps

1. ✅ Run `pnpm tcgplayer:scrape` to test
2. ✅ Run `pnpm tcgplayer:db` to build database
3. ⏳ Implement incremental update logic
4. ⏳ Add price display to desktop app
5. ⏳ Deploy daily scraper to cloud

---

## 🔗 Resources

- TCGplayer API: https://tcgcsv.com/
- Categories: https://tcgcsv.com/tcgplayer/categories
- Example Products: https://tcgcsv.com/tcgplayer/1/1/products
- Example Prices: https://tcgcsv.com/tcgplayer/1/1/prices
