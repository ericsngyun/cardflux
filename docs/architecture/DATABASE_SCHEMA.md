# CardFlux Database Schema
**Date**: 2025-10-31
**Version**: v1.0 (Initial Design)
**Database**: SQLite 3.45+ with WAL mode
**Migration Tool**: Kysely

---

## Design Principles

1. **Offline-First**: All data local, sync-ready design
2. **Event Sourcing**: Append-only `events` table drives read models
3. **ACID Transactions**: All mutations atomic (batch post, buy-in, etc.)
4. **Deterministic IDs**: UUIDs for sync compatibility
5. **Audit Trail**: Every change logged in events table
6. **Performance**: Indexed for common queries (<200ms)

---

## Schema Overview

```
┌─────────────────┐  ┌──────────────┐  ┌───────────────┐
│     cards       │  │  inventory   │  │    batches    │
│  (master data)  │  │ (stock on    │  │  (scan        │
│                 │  │  hand)       │  │   sessions)   │
└────────┬────────┘  └──────┬───────┘  └───────┬───────┘
         │                  │                   │
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  batch_lines   │
                    │  (individual   │
                    │   scanned      │
                    │   cards)       │
                    └────────────────┘

┌─────────────────┐  ┌──────────────┐  ┌───────────────┐
│     events      │  │   prices     │  │buylist_targets│
│  (append-only   │  │ (historical  │  │  (cards to    │
│   audit log)    │  │  pricing)    │  │   buy)        │
└─────────────────┘  └──────────────┘  └───────────────┘

┌─────────────────┐  ┌──────────────┐  ┌───────────────┐
│    settings     │  │   devices    │  │  migrations   │
│  (app config)   │  │ (multi-device│  │  (schema      │
│                 │  │  sync)       │  │   version)    │
└─────────────────┘  └──────────────┘  └───────────────┘
```

---

## Table Definitions

### 1. `cards` - Master Card Data
**Purpose**: TCG card catalog (productId, name, set, rarity, etc.)
**Source**: Synced from TCGPlayer API (existing data manager)

```sql
CREATE TABLE cards (
  product_id TEXT PRIMARY KEY,           -- TCGPlayer productId (e.g., "OP01-001")
  name TEXT NOT NULL,                    -- Card name
  set_code TEXT NOT NULL,                -- Set abbreviation (e.g., "OP01")
  set_name TEXT NOT NULL,                -- Full set name
  number TEXT NOT NULL,                  -- Card number in set
  rarity TEXT,                           -- R, SR, L, etc.
  tcg_game TEXT NOT NULL,                -- "one-piece", "pokemon", etc.
  image_url TEXT,                        -- URL to card image
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Search optimization
  name_normalized TEXT GENERATED ALWAYS AS (lower(trim(name))) STORED,

  -- Constraints
  CHECK (length(product_id) > 0),
  CHECK (length(name) > 0),
  CHECK (tcg_game IN ('one-piece', 'pokemon', 'magic', 'yugioh', 'digimon', 'lorcana'))
);

-- Indices
CREATE INDEX idx_cards_name ON cards(name_normalized);
CREATE INDEX idx_cards_set ON cards(set_code);
CREATE INDEX idx_cards_tcg_game ON cards(tcg_game);
CREATE INDEX idx_cards_updated_at ON cards(updated_at DESC);

-- Full-text search (optional, for fast name search)
CREATE VIRTUAL TABLE cards_fts USING fts5(
  product_id UNINDEXED,
  name,
  set_name,
  content=cards,
  content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER cards_fts_insert AFTER INSERT ON cards BEGIN
  INSERT INTO cards_fts(rowid, product_id, name, set_name)
  VALUES (new.rowid, new.product_id, new.name, new.set_name);
END;

CREATE TRIGGER cards_fts_delete AFTER DELETE ON cards BEGIN
  DELETE FROM cards_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER cards_fts_update AFTER UPDATE ON cards BEGIN
  UPDATE cards_fts SET name = new.name, set_name = new.set_name
  WHERE rowid = new.rowid;
END;
```

---

### 2. `inventory` - Stock on Hand
**Purpose**: Current inventory with qty, condition, cost basis
**Mutations**: Batch post, buy-in, sale, adjustment, count

```sql
CREATE TABLE inventory (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  card_id TEXT NOT NULL REFERENCES cards(product_id) ON DELETE CASCADE,
  condition TEXT NOT NULL DEFAULT 'NM',  -- NM, LP, MP, HP, DMG
  qty INTEGER NOT NULL DEFAULT 0,        -- Quantity in stock
  cost_basis REAL,                       -- Average cost per unit
  sell_price REAL,                       -- Current sell price
  location TEXT,                         -- Shelf/bin location
  notes TEXT,                            -- Free-form notes
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Constraints
  CHECK (condition IN ('NM', 'LP', 'MP', 'HP', 'DMG')),
  CHECK (qty >= 0),
  CHECK (cost_basis IS NULL OR cost_basis >= 0),
  CHECK (sell_price IS NULL OR sell_price >= 0),

  -- Unique constraint: one row per (card, condition)
  UNIQUE (card_id, condition)
);

-- Indices
CREATE INDEX idx_inventory_card_id ON inventory(card_id);
CREATE INDEX idx_inventory_qty ON inventory(qty) WHERE qty > 0; -- Only stock on hand
CREATE INDEX idx_inventory_updated_at ON inventory(updated_at DESC);

-- Trigger: Update updated_at on every change
CREATE TRIGGER inventory_updated_at AFTER UPDATE ON inventory BEGIN
  UPDATE inventory SET updated_at = unixepoch() WHERE id = new.id;
END;
```

---

### 3. `batches` - Scan Sessions
**Purpose**: Group scanned cards into batches (scanning session)
**Lifecycle**: Created → cards added → posted to inventory

```sql
CREATE TABLE batches (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  started_at INTEGER NOT NULL DEFAULT (unixepoch()),
  posted_at INTEGER,                     -- NULL until posted
  total_value REAL NOT NULL DEFAULT 0,   -- Sum of card prices
  card_count INTEGER NOT NULL DEFAULT 0, -- Number of cards in batch
  notes TEXT,                            -- User notes
  created_by TEXT,                       -- User ID (future: multi-user)

  -- Constraints
  CHECK (total_value >= 0),
  CHECK (card_count >= 0),
  CHECK (posted_at IS NULL OR posted_at >= started_at)
);

-- Indices
CREATE INDEX idx_batches_started_at ON batches(started_at DESC);
CREATE INDEX idx_batches_posted_at ON batches(posted_at DESC) WHERE posted_at IS NOT NULL;
CREATE INDEX idx_batches_unposted ON batches(posted_at) WHERE posted_at IS NULL;
```

---

### 4. `batch_lines` - Individual Scanned Cards
**Purpose**: Detailed list of cards in each batch
**Relationships**: Many batch_lines per batch

```sql
CREATE TABLE batch_lines (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  card_id TEXT NOT NULL REFERENCES cards(product_id) ON DELETE CASCADE,
  condition TEXT NOT NULL DEFAULT 'NM',
  scanned_price REAL NOT NULL,           -- Price at time of scan
  confidence TEXT NOT NULL,              -- HIGH, MODERATE, LOW
  scanned_at INTEGER NOT NULL DEFAULT (unixepoch()),
  sequence INTEGER NOT NULL,             -- Order within batch (1, 2, 3...)

  -- Constraints
  CHECK (condition IN ('NM', 'LP', 'MP', 'HP', 'DMG')),
  CHECK (confidence IN ('HIGH', 'MODERATE', 'LOW')),
  CHECK (scanned_price >= 0),
  CHECK (sequence > 0),

  -- Unique sequence per batch
  UNIQUE (batch_id, sequence)
);

-- Indices
CREATE INDEX idx_batch_lines_batch_id ON batch_lines(batch_id, sequence);
CREATE INDEX idx_batch_lines_card_id ON batch_lines(card_id);
CREATE INDEX idx_batch_lines_scanned_at ON batch_lines(scanned_at DESC);

-- Trigger: Update batch totals when line added/removed
CREATE TRIGGER batch_lines_insert AFTER INSERT ON batch_lines BEGIN
  UPDATE batches SET
    card_count = card_count + 1,
    total_value = total_value + new.scanned_price
  WHERE id = new.batch_id;
END;

CREATE TRIGGER batch_lines_delete AFTER DELETE ON batch_lines BEGIN
  UPDATE batches SET
    card_count = card_count - 1,
    total_value = total_value - old.scanned_price
  WHERE id = old.batch_id;
END;
```

---

### 5. `events` - Append-Only Audit Log
**Purpose**: Event sourcing - every domain event logged
**Usage**: Audit trail, dashboard metrics, cloud sync

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  type TEXT NOT NULL,                    -- Event type (card_scanned, price_adjusted, etc.)
  aggregate_type TEXT NOT NULL,          -- Entity type (card, batch, inventory, etc.)
  aggregate_id TEXT NOT NULL,            -- Entity ID
  data TEXT NOT NULL,                    -- JSON event payload
  timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
  device_id TEXT NOT NULL,               -- Device that created event
  user_id TEXT,                          -- User ID (future: multi-user)
  vector_clock TEXT,                     -- JSON: { deviceId: counter } for sync

  -- Constraints
  CHECK (length(type) > 0),
  CHECK (length(aggregate_type) > 0),
  CHECK (length(aggregate_id) > 0),
  CHECK (json_valid(data) = 1),
  CHECK (vector_clock IS NULL OR json_valid(vector_clock) = 1)
);

-- Indices (critical for performance)
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_device_id ON events(device_id);

-- Composite index for common queries (dashboard: today's scans)
CREATE INDEX idx_events_type_timestamp ON events(type, timestamp DESC);

-- Trigger: Prevent updates/deletes (append-only)
CREATE TRIGGER events_immutable BEFORE UPDATE ON events BEGIN
  SELECT RAISE(FAIL, 'Events table is append-only (no updates allowed)');
END;

CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN
  SELECT RAISE(FAIL, 'Events table is append-only (no deletes allowed)');
END;
```

**Common Event Types:**
```typescript
// Scanner events
'card_scanned'          // Card scanned and added to batch
'batch_started'         // New batch created
'batch_posted'          // Batch posted to inventory

// Inventory events
'card_added'            // Card added to inventory
'card_removed'          // Card sold/removed
'card_adjusted'         // Qty/price adjusted
'price_updated'         // Price changed

// Buylist events
'buylist_target_added'  // Card added to buylist
'buy_in_completed'      // Customer buy-in transaction

// System events
'database_migrated'     // Schema migration applied
'backup_created'        // Backup created
'settings_changed'      // Settings updated
```

---

### 6. `prices` - Historical Pricing Data
**Purpose**: Track price changes over time (for charts)
**Source**: TCGPlayer API, manual adjustments

```sql
CREATE TABLE prices (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  card_id TEXT NOT NULL REFERENCES cards(product_id) ON DELETE CASCADE,
  condition TEXT NOT NULL DEFAULT 'NM',
  market_price REAL,                     -- TCGPlayer market price
  low_price REAL,                        -- Lowest available
  high_price REAL,                       -- Highest available
  recorded_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Constraints
  CHECK (condition IN ('NM', 'LP', 'MP', 'HP', 'DMG')),
  CHECK (market_price IS NULL OR market_price >= 0),
  CHECK (low_price IS NULL OR low_price >= 0),
  CHECK (high_price IS NULL OR high_price >= 0)
);

-- Indices
CREATE INDEX idx_prices_card_id ON prices(card_id, recorded_at DESC);
CREATE INDEX idx_prices_recorded_at ON prices(recorded_at DESC);

-- Keep last 90 days only (performance)
CREATE TRIGGER prices_cleanup AFTER INSERT ON prices BEGIN
  DELETE FROM prices WHERE recorded_at < unixepoch() - (90 * 86400);
END;
```

---

### 7. `buylist_targets` - Cards Shop Wants to Buy
**Purpose**: Define which cards shop is buying and at what price
**Usage**: Buylist mode in scanner

```sql
CREATE TABLE buylist_targets (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  card_id TEXT NOT NULL REFERENCES cards(product_id) ON DELETE CASCADE,
  buy_price REAL NOT NULL,               -- Price shop pays
  max_qty INTEGER NOT NULL DEFAULT 1,    -- Max quantity to buy
  min_condition TEXT NOT NULL DEFAULT 'LP', -- Minimum acceptable condition
  notes TEXT,
  active INTEGER NOT NULL DEFAULT 1,     -- 1 = active, 0 = inactive
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Constraints
  CHECK (buy_price >= 0),
  CHECK (max_qty > 0),
  CHECK (min_condition IN ('NM', 'LP', 'MP', 'HP', 'DMG')),
  CHECK (active IN (0, 1)),

  -- One target per card
  UNIQUE (card_id)
);

-- Indices
CREATE INDEX idx_buylist_targets_active ON buylist_targets(active) WHERE active = 1;
CREATE INDEX idx_buylist_targets_card_id ON buylist_targets(card_id);
```

---

### 8. `settings` - App Configuration
**Purpose**: Store user preferences, feature flags, config
**Scope**: Single device (not synced)

```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,                  -- Setting key (e.g., "theme", "feature_flags")
  value TEXT NOT NULL,                   -- JSON value
  updated_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Constraints
  CHECK (json_valid(value) = 1)
);

-- Common settings
INSERT INTO settings (key, value) VALUES
  ('theme', '"dark"'),
  ('feature_flags', '{"multiPageNavigation": false, "cloudSync": false}'),
  ('scanner_config', '{"multiFrame": false, "confidenceThreshold": 0.75}'),
  ('pricing_rules', '{"marginPercent": 30, "rounding": 0.5}'),
  ('tcg_game', '"one-piece"');
```

---

### 9. `devices` - Multi-Device Sync (Future)
**Purpose**: Track devices for cloud sync (vector clocks)
**Usage**: Cloud sync only (Phase 9+)

```sql
CREATE TABLE devices (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), -- UUID
  name TEXT NOT NULL,                    -- Device name (e.g., "Shop Computer 1")
  last_sync INTEGER,                     -- Last successful sync timestamp
  vector_clock TEXT NOT NULL,            -- JSON: { deviceId: counter }
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),

  -- Constraints
  CHECK (json_valid(vector_clock) = 1)
);

-- Insert current device on first run
INSERT INTO devices (id, name, vector_clock)
VALUES (
  lower(hex(randomblob(16))),
  'Primary Device',
  '{}'
);
```

---

### 10. `migrations` - Schema Version Tracking
**Purpose**: Track applied migrations (Kysely managed)
**Managed by**: Kysely migration system

```sql
CREATE TABLE migrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,             -- Migration file name
  timestamp INTEGER NOT NULL,            -- When applied
  checksum TEXT NOT NULL,                -- SHA256 of migration SQL
  applied_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Index
CREATE INDEX idx_migrations_timestamp ON migrations(timestamp);
```

---

## Seed Data

### Initial Migration (001_initial_schema.ts)
```typescript
import { Kysely, sql } from 'kysely';

export async function up(db: Kysely<any>): Promise<void> {
  // Enable WAL mode (CRITICAL for performance + safety)
  await sql`PRAGMA journal_mode = WAL`.execute(db);
  await sql`PRAGMA synchronous = NORMAL`.execute(db);
  await sql`PRAGMA foreign_keys = ON`.execute(db);
  await sql`PRAGMA busy_timeout = 5000`.execute(db);

  // Create tables (all CREATE TABLE statements above)
  // ... (full schema creation)

  // Seed settings
  await db.insertInto('settings').values([
    { key: 'theme', value: JSON.stringify('dark') },
    { key: 'feature_flags', value: JSON.stringify({
      multiPageNavigation: false,
      batchPersistence: false,
      eventSourcing: true,
      inventoryPage: false,
      dashboardPage: false,
      buylistPage: false,
      cloudSync: false,
    })},
    { key: 'scanner_config', value: JSON.stringify({
      multiFrame: false,
      confidenceThreshold: 0.75,
      topK: 20,
      useGeometric: true,
    })},
    { key: 'tcg_game', value: JSON.stringify('one-piece') },
  ]).execute();

  // Seed current device
  await db.insertInto('devices').values({
    id: sql`lower(hex(randomblob(16)))`,
    name: 'Primary Device',
    vector_clock: JSON.stringify({}),
  }).execute();
}

export async function down(db: Kysely<any>): Promise<void> {
  // Drop all tables in reverse order
  await db.schema.dropTable('migrations').ifExists().execute();
  await db.schema.dropTable('devices').ifExists().execute();
  await db.schema.dropTable('settings').ifExists().execute();
  await db.schema.dropTable('buylist_targets').ifExists().execute();
  await db.schema.dropTable('prices').ifExists().execute();
  await db.schema.dropTable('events').ifExists().execute();
  await db.schema.dropTable('batch_lines').ifExists().execute();
  await db.schema.dropTable('batches').ifExists().execute();
  await db.schema.dropTable('inventory').ifExists().execute();
  await db.schema.dropTable('cards_fts').ifExists().execute();
  await db.schema.dropTable('cards').ifExists().execute();
}
```

---

## Common Queries (Performance Targets)

### 1. Scanner: Add Card to Batch (<10ms)
```sql
INSERT INTO batch_lines (batch_id, card_id, condition, scanned_price, confidence, sequence)
VALUES (?, ?, ?, ?, ?, (SELECT COALESCE(MAX(sequence), 0) + 1 FROM batch_lines WHERE batch_id = ?));
```

### 2. Inventory: Search by Name (<200ms with FTS)
```sql
SELECT c.*, i.qty, i.condition, i.sell_price
FROM cards_fts
JOIN cards c ON c.rowid = cards_fts.rowid
LEFT JOIN inventory i ON i.card_id = c.product_id
WHERE cards_fts MATCH ?
ORDER BY rank
LIMIT 50;
```

### 3. Dashboard: Today's Stats (<100ms)
```sql
-- Pre-aggregated from events table
SELECT
  COUNT(*) FILTER (WHERE type = 'card_scanned') as scans_today,
  COALESCE(SUM(json_extract(data, '$.price')), 0) as total_value,
  COUNT(DISTINCT json_extract(data, '$.batchId')) as batches_today
FROM events
WHERE DATE(timestamp, 'unixepoch') = DATE('now')
  AND type = 'card_scanned';
```

### 4. Inventory: Top 10 SKUs by Velocity (<200ms)
```sql
-- Velocity = sales in last 30 days
SELECT
  c.name,
  c.product_id,
  COUNT(*) as sales_count,
  SUM(json_extract(e.data, '$.price')) as revenue
FROM events e
JOIN cards c ON c.product_id = json_extract(e.data, '$.cardId')
WHERE e.type = 'card_removed'
  AND e.timestamp > unixepoch() - (30 * 86400)
GROUP BY c.product_id
ORDER BY sales_count DESC
LIMIT 10;
```

### 5. Buylist: Get Active Targets (<50ms)
```sql
SELECT bt.*, c.name, c.set_name
FROM buylist_targets bt
JOIN cards c ON c.product_id = bt.card_id
WHERE bt.active = 1
ORDER BY c.name;
```

---

## Backup Strategy

### Automatic Backups
```typescript
// Run daily at 2 AM
const scheduleBackup = () => {
  setInterval(async () => {
    const hour = new Date().getHours();
    if (hour === 2) {
      await createBackup();
    }
  }, 60 * 60 * 1000); // Check every hour
};

const createBackup = async () => {
  // 1. Close WAL checkpoint
  db.pragma('wal_checkpoint(TRUNCATE)');

  // 2. Copy database file
  const backupPath = path.join(
    app.getPath('userData'),
    'backups',
    `cardflux-${Date.now()}.db`
  );
  fs.copyFileSync(dbPath, backupPath);

  // 3. Encrypt (AES-256)
  const encrypted = await encryptFile(backupPath);

  // 4. Keep last 7 backups only
  await cleanupOldBackups(7);

  // 5. Log event
  await eventLog.publish('backup_created', {
    path: backupPath,
    size: fs.statSync(encrypted).size,
  });
};
```

### Manual Backup/Restore (Settings Page)
```typescript
// Backup
const exportBackup = async (destination: string) => {
  await createBackup();
  // Copy to user-selected location
  fs.copyFileSync(latestBackup, destination);
};

// Restore
const importBackup = async (source: string) => {
  // 1. Verify integrity
  const checksum = await verifyChecksum(source);
  if (!checksum.valid) throw new Error('Corrupted backup');

  // 2. Backup current state (safety)
  await createBackup();

  // 3. Close database
  db.close();

  // 4. Decrypt and restore
  const decrypted = await decryptFile(source);
  fs.copyFileSync(decrypted, dbPath);

  // 5. Restart app
  app.relaunch();
  app.exit(0);
};
```

---

## Migration Safety

### Pre-Migration Backup
```typescript
// Before running migrations
const runMigrations = async () => {
  // 1. Create safety backup
  await createBackup();

  // 2. Run migrations in transaction
  await db.transaction(async (trx) => {
    const migrator = new Migrator({ db: trx });
    const { error, results } = await migrator.migrateToLatest();

    if (error) {
      throw error; // Rollback transaction
    }

    logger.info('Migrations applied', { results });
  });

  // 3. Verify schema
  const version = await getCurrentSchemaVersion();
  if (version !== EXPECTED_VERSION) {
    throw new Error('Schema version mismatch');
  }
};
```

### Rollback on Failure
```typescript
// If migration fails, restore from pre-migration backup
try {
  await runMigrations();
} catch (error) {
  logger.error('Migration failed, restoring backup', error);

  // Close database
  db.close();

  // Restore pre-migration backup
  const preMigrationBackup = await getLatestBackup();
  fs.copyFileSync(preMigrationBackup, dbPath);

  // Restart app
  app.relaunch();
  app.exit(1);
}
```

---

## Performance Tuning

### WAL Mode (CRITICAL)
```sql
-- Enable WAL (Write-Ahead Logging) for performance + safety
PRAGMA journal_mode = WAL;        -- Concurrent reads during write
PRAGMA synchronous = NORMAL;      -- Faster writes (safe in WAL mode)
PRAGMA foreign_keys = ON;         -- Enforce referential integrity
PRAGMA busy_timeout = 5000;       -- Wait 5s for lock before error
PRAGMA cache_size = -64000;       -- 64 MB cache (negative = KB)
PRAGMA temp_store = MEMORY;       -- Temp tables in RAM
```

**Benefits:**
- **Concurrent reads**: Scanner can read while batch posts write
- **Faster writes**: No fsync on every transaction
- **Crash-safe**: WAL ensures durability

### Indices (Already Defined)
- All foreign keys indexed
- Common query patterns indexed (name search, timestamp DESC)
- Composite indices for JOIN queries

### Query Plan Analysis
```typescript
// Check query performance
const explainQuery = (sql: string) => {
  const plan = db.prepare(`EXPLAIN QUERY PLAN ${sql}`).all();
  console.log(plan);
  // Look for "SCAN" (bad) vs "SEARCH" using index (good)
};
```

---

## Schema Version History

### v1.0 (Week 1) - Initial Schema
- All tables defined
- WAL enabled
- Seed data
- FTS for card search

### v1.1 (Week 3) - Inventory Enhancements
- Add `location` column to inventory
- Add `notes` column to inventory
- Add index on `qty > 0`

### v1.2 (Week 5) - Dashboard Optimizations
- Add composite index `(type, timestamp)` on events
- Add `prices` cleanup trigger (keep 90 days)

### v1.3 (Week 8) - Cloud Sync Prep
- Add `vector_clock` column to events
- Add `devices` table
- Add `device_id` column to events

---

## Next Steps

1. **Review schema** - Any missing fields or tables?
2. **Approve design** - Ready for implementation?
3. **Next deliverable**: Dependency plan (Kysely, better-sqlite3, etc.)

**Ready for Phase 1 implementation?** Let me know if any schema changes needed!
