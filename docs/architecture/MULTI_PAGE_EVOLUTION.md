# CardFlux Multi-Page Architecture Evolution
**Date**: 2025-10-31
**Status**: Planning Phase
**Target**: Demo-ready, shop-tested multi-page application

---

## Executive Summary

**Goal**: Evolve CardFlux from single-page scanner MVP to full-featured offline-first shop management system with cloud-sync readiness, while maintaining 100% backward compatibility with existing scanner functionality.

**Strategy**: Phased implementation with feature flags, incremental database adoption, and rigorous testing at each milestone.

**Timeline**: 8 weeks to production-ready multi-page app
**Risk Level**: LOW (scanner stays functional throughout)

---

## Current State (v0.2.2)

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Main Process                     │
├─────────────────────────────────────────────────────────────┤
│  ResourceManager  │  DataManager  │  PythonBridge  │ Logger │
│                   │               │                │        │
│  • Paths          │  • Manifest   │  • Subprocess  │  • File│
│  • Validation     │  • Downloads  │  • JSON-RPC    │  • Logs│
└───────────────────┴───────────────┴────────────────┴────────┘
                              ↓ IPC (contextBridge)
┌─────────────────────────────────────────────────────────────┐
│                    Renderer Process (React)                  │
├─────────────────────────────────────────────────────────────┤
│                   CameraView Component                       │
│  • Live camera feed (getUserMedia)                          │
│  • Real-time card detection (detect_card IPC)              │
│  • SPACE to capture → identify → add to stack              │
│                                                              │
│  Stack (React State - Volatile)                             │
│  ┌────────────────────────────────────────┐                │
│  │ [Card 1] $12.50  [×]                   │                │
│  │ [Card 2] $8.00   [×]                   │                │
│  │ [Card 3] $25.00  [×]                   │                │
│  └────────────────────────────────────────┘                │
│                                                              │
│  [Clear Stack]  [Export CSV]                                │
└─────────────────────────────────────────────────────────────┘

Data Flow:
Camera → detect_card → identify → React State → CSV Export
                                    (volatile - lost on close)
```

**Strengths:**
- ✅ Fast scanning loop (500-1000ms detection)
- ✅ Secure IPC (contextBridge, rate limiting, input validation)
- ✅ Memory optimized (canvas reuse, cleanup)
- ✅ Real-time feedback (bounding boxes, confidence meters)

**Limitations:**
- ❌ No persistence (stack lost on app close)
- ❌ No inventory management
- ❌ No batch tracking
- ❌ No historical data/analytics
- ❌ No buylist functionality
- ❌ No multi-user workflows

---

## Target Architecture (v0.6.0)

```
┌───────────────────────────────────────────────────────────────────┐
│                    Electron Main Process                          │
├───────────────────────────────────────────────────────────────────┤
│  ResourceManager  │  DatabaseManager  │  EventLog  │  SyncAdapter │
│                   │                   │            │              │
│  • Paths          │  • SQLite (WAL)   │  • Events  │  • Local     │
│  • Validation     │  • Migrations     │  • Pub/Sub │  • (AWS stub)│
│                   │  • Transactions   │  • Replay  │              │
├───────────────────┴───────────────────┴────────────┴──────────────┤
│  PythonBridge  │  Logger  │  BackupService  │  HealthCheck        │
└───────────────────────────────────────────────────────────────────┘
                              ↓ IPC (typed, validated)
┌───────────────────────────────────────────────────────────────────┐
│                    Renderer Process (React Router)                │
├───────────────────────────────────────────────────────────────────┤
│  Navigation: [Dashboard] [Scanner] [Inventory] [Buylist] [Settings]
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Dashboard                                                     ││
│  │  • Today's Stats (scans, revenue, margin)                    ││
│  │  • Top 10 SKUs by velocity                                   ││
│  │  • Aging stock alerts (>90 days)                             ││
│  │  • Shrinkage warnings                                        ││
│  │  • Buy-in vs Sell chart                                      ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Scanner (existing functionality + persistence)                ││
│  │  • Camera feed (existing)                                    ││
│  │  • Detection + confidence (existing)                         ││
│  │  • Stack (now persisted to DB)                               ││
│  │  • Batch controls: [Start Batch] [Post to Inventory]        ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Inventory                                                     ││
│  │  • Search/filter (name, set, rarity, price range)            ││
│  │  • Bulk actions (adjust price, mark damaged, tag batch)      ││
│  │  • Import CSV / Export CSV                                   ││
│  │  • Quick grading (NM/LP/MP/HP/DMG)                           ││
│  │  • Stock level warnings                                      ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Buylist                                                       ││
│  │  • Target cards with qty + price bands                       ││
│  │  • Margin calculator (buy price vs market)                   ││
│  │  • Acceptance rules (min condition, max qty)                 ││
│  │  • Quick buy-in workflow (scan → accept/reject → payment)    ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ Settings                                                      ││
│  │  • TCG game selection                                        ││
│  │  • Scanner config (multi-frame, confidence thresholds)       ││
│  │  • Pricing rules (margin %, rounding)                        ││
│  │  • Backup/restore                                            ││
│  │  • Feature flags (cloud sync, multi-user)                    ││
│  │  • Accessibility (dark/light, high-contrast, font size)      ││
│  └──────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────┘
                              ↓ (persisted)
┌───────────────────────────────────────────────────────────────────┐
│                    SQLite Database (WAL Mode)                     │
├───────────────────────────────────────────────────────────────────┤
│  cards          │  Card master data (productId, name, set, etc.) │
│  inventory      │  Stock on hand (qty, condition, cost basis)    │
│  batches        │  Scan sessions (started_at, posted_at, total)  │
│  batch_lines    │  Individual scanned cards in batch             │
│  events         │  Append-only audit log (all domain events)     │
│  prices         │  Historical price data (for charts)            │
│  buylist_targets│  Cards shop wants to buy (price bands)         │
│  settings       │  App configuration (feature flags, user prefs) │
│  migrations     │  Schema version tracking                       │
└───────────────────────────────────────────────────────────────────┘
```

**Data Flow (Scanner → Inventory):**
```
1. User scans card with SPACE
2. identify IPC → Python (existing)
3. Scanner page: Add to batch stack (in-memory + DB batch_lines)
4. User clicks [Post Batch]
5. Transaction:
   - Insert/update inventory rows
   - Publish card_added events to event log
   - Mark batch as posted
6. Inventory page: Query inventory table (read model)
7. Dashboard: Aggregate from events table (metrics)
```

**Event Sourcing Flow:**
```
Domain Event → EventLog.publish()
                    ↓
            ┌───────┴───────┐
            ↓               ↓
      Event Table      Subscribers
     (append-only)    (Dashboard, Metrics)
                            ↓
                      Read Models
                   (denormalized views)
```

---

## Evolution Phases (8 Weeks)

### Phase 1: Foundation (Week 1-2) 🏗️
**Goal**: Add database + event log WITHOUT breaking scanner

**Deliverables:**
- ✅ SQLite database with migrations (Kysely)
- ✅ Event log publisher/consumer
- ✅ SyncAdapter interface + LocalOnlyAdapter
- ✅ Testing infrastructure (Jest + Playwright)
- ✅ Multi-page routing (React Router)
- ✅ Feature flags system (electron-store)
- ✅ Health check + auto-rollback logic

**Scanner Impact**: NONE (scanner page works exactly as before)

**Success Criteria:**
- Scanner app still passes all existing workflows
- Database initializes on first run (empty tables)
- Tests run in CI (unit + integration)
- Health check detects migration failures

**Git Strategy:**
```bash
# Create feature branch from main (v0.2.2 tagged)
git checkout -b feature/database-foundation
# Incremental commits:
# - Add SQLite + migrations
# - Add event log
# - Add SyncAdapter interface
# - Add testing scaffolds
# Merge to main when all tests pass
```

---

### Phase 2: Inventory Page (Week 3-4) 📦
**Goal**: Build inventory management with batch posting from scanner

**Deliverables:**
- ✅ Inventory CRUD operations (IPC + DB queries)
- ✅ Batch posting workflow (Scanner → Inventory)
- ✅ CSV import/export
- ✅ Search/filter UI
- ✅ Bulk edit actions
- ✅ Event log integration (card_added, card_updated events)

**Scanner Changes:**
- Add "Post Batch" button (saves stack to inventory)
- Optional: "Save for Later" (batch persistence)
- Stack now writes to DB on post (not just CSV export)

**Success Criteria:**
- Scan 10 cards → Post Batch → See in Inventory
- Export CSV from Inventory (includes posted cards)
- Import CSV → Cards appear in Inventory
- Bulk price adjustment works
- Events logged for all inventory changes

**Demo Scenario:**
```
Shop owner:
1. Scans 20 cards (existing workflow)
2. Clicks "Post Batch" (NEW)
3. Opens Inventory page (NEW)
4. Sees 20 cards with timestamps
5. Bulk adjusts price by 10%
6. Exports CSV for website upload
```

---

### Phase 3: Dashboard (Week 5) 📊
**Goal**: Show shop metrics from event log (read models)

**Deliverables:**
- ✅ Dashboard page with widgets
- ✅ Metrics: today's stats, top SKUs, aging stock
- ✅ Charts: buy-in vs sell, margin trends
- ✅ Alerts: shrinkage, low stock, aging inventory
- ✅ Read model builders (aggregate from events)

**Data Source**: Event log (not inventory table directly)
- Enables replayability
- Future: cloud sync can replay events to rebuild state

**Success Criteria:**
- Dashboard shows accurate counts after scanning session
- Charts update after inventory changes
- Alerts trigger for aging stock (>90 days)
- Performance: Dashboard loads <500ms

**Demo Scenario:**
```
Shop owner:
1. Opens Dashboard (sees empty state)
2. Scans 50 cards over 2 days
3. Dashboard shows:
   - "50 cards scanned"
   - "$1,250 total value"
   - "Top 10 cards by value"
   - "3 cards aging >90 days"
```

---

### Phase 4: Buylist (Week 6) 💰
**Goal**: Enable buy-in workflow with pricing rules

**Deliverables:**
- ✅ Buylist target management (add cards shop wants to buy)
- ✅ Pricing rules (% of market, min/max, condition adjustments)
- ✅ Quick buy-in workflow (scan → accept/reject → payment)
- ✅ Margin calculator (buy price vs sell price)
- ✅ Acceptance rules (min condition, max qty per card)

**Scanner Changes:**
- Add "Buylist Mode" toggle
- In buylist mode: show buy price instead of sell price
- Accept/Reject buttons for each card

**Success Criteria:**
- Add 10 cards to buylist targets
- Customer brings cards to sell
- Scan cards → see buy prices
- Accept 5 cards → total shows correct buy-in amount
- Transaction logged in events

**Demo Scenario:**
```
Customer brings collection to sell:
1. Shop owner enables "Buylist Mode"
2. Scans customer's cards
3. System shows buy prices (70% of market)
4. Owner accepts 20 cards, rejects 5 (low condition)
5. System shows total: "$180 buy-in"
6. Owner pays customer, marks transaction complete
7. Cards added to inventory with cost basis
```

---

### Phase 5: Settings + Polish (Week 7) ⚙️
**Goal**: Complete app with settings, accessibility, backup

**Deliverables:**
- ✅ Settings page (game selection, scanner config, pricing rules)
- ✅ Backup/restore with encryption
- ✅ Feature flags UI (cloud sync toggle, multi-user)
- ✅ Accessibility: dark/light themes, high-contrast, keyboard nav
- ✅ Keyboard shortcuts (global, context-aware)
- ✅ User roles/permissions scaffold (single-user now, multi-user later)

**Success Criteria:**
- Settings persist across restarts
- Backup creates encrypted ZIP
- Restore from backup works (with migration check)
- Dark/light themes switch instantly
- All pages navigable via keyboard (Tab, Arrow keys)
- High-contrast mode passes WCAG AA

**Demo Scenario:**
```
Shop owner:
1. Changes theme to dark mode (instant)
2. Adjusts scanner confidence threshold to 0.8 (stricter)
3. Creates backup (encrypted, saves to USB)
4. Restores from backup on new computer (works)
5. Enables cloud sync feature flag (shows "Coming Soon" badge)
```

---

### Phase 6: Cloud-Ready + Release (Week 8) ☁️
**Goal**: Production-ready with cloud sync stubs

**Deliverables:**
- ✅ AwsSyncAdapter stub (interface only, no network)
- ✅ Feature flag: cloud_sync (disabled by default)
- ✅ Auto-update system (electron-updater)
- ✅ Health check + auto-rollback on failure
- ✅ Release channels (canary/beta/stable)
- ✅ E2E test suite (all critical paths)
- ✅ Visual regression tests (Percy or Playwright screenshots)

**Cloud Sync Design (NOT implemented):**
```typescript
interface AwsSyncAdapter extends SyncAdapter {
  // Stub methods (throw "Not implemented")
  pushEvents(events: Event[]): Promise<void>;
  pullEvents(since: Date): Promise<Event[]>;
  resolveConflicts(local: Event[], remote: Event[]): Event[];
  authenticate(credentials: CognitoCredentials): Promise<Session>;
}

// Feature flag check in UI
if (featureFlags.cloudSync) {
  return <Badge>Cloud Sync: Coming Soon</Badge>;
}
```

**Success Criteria:**
- App auto-updates from GitHub releases
- Health check prevents broken migrations from shipping
- Rollback restores previous version on failure
- E2E tests cover: scan → post → inventory → dashboard
- Visual regression catches UI bugs
- Release process documented (CI/CD pipeline)

**Demo Scenario:**
```
Shop owner (production user):
1. App auto-updates from v0.5.0 → v0.6.0
2. Health check runs: migrations succeed
3. App starts normally with new features
4. If migration failed: auto-rollback to v0.5.0
5. Owner sees "Cloud Sync Coming Soon" badge in Settings
```

---

## Backward Compatibility Strategy

### Scanner Page (Zero Breaking Changes)
```typescript
// OLD: Scanner saves to React state only
const [cards, setCards] = useState<Card[]>([]);

// NEW: Scanner saves to React state + optional DB batch
const [cards, setCards] = useState<Card[]>([]);
const [currentBatch, setCurrentBatch] = useState<Batch | null>(null);

// Capture flow (unchanged for user)
const handleCapture = async (imagePath: string) => {
  const result = await window.identifier.identify(imagePath);

  // Existing: Add to React state (immediate UX)
  setCards(prev => [result.card, ...prev]);

  // NEW: Optionally save to batch (background)
  if (featureFlags.batchPersistence && currentBatch) {
    await window.batches.addCard(currentBatch.id, result.card);
  }

  // Event log (NEW, async)
  if (featureFlags.eventSourcing) {
    await window.events.publish('card_scanned', {
      batchId: currentBatch?.id,
      card: result.card,
      confidence: result.confidence,
    });
  }
};
```

**Key Points:**
- Scanner UX unchanged (SPACE still works)
- Stack still shows cards immediately (React state)
- Database writes are async, non-blocking
- If DB write fails, scanner keeps working (degrades gracefully)
- CSV export still works (from React state)

### Feature Flags (Gradual Rollout)
```typescript
// electron-store config
interface FeatureFlags {
  multiPageNavigation: boolean;  // Week 1: false → true
  batchPersistence: boolean;     // Week 3: false → true
  eventSourcing: boolean;        // Week 1: true (always on)
  inventoryPage: boolean;        // Week 3: false → true
  dashboardPage: boolean;        // Week 5: false → true
  buylistPage: boolean;          // Week 6: false → true
  cloudSync: boolean;            // Week 8: false (not implemented)
}

// Usage in code
if (flags.inventoryPage) {
  return <Route path="/inventory" component={InventoryPage} />;
} else {
  return <Redirect to="/scanner" />; // Fallback to scanner
}
```

---

## Data Persistence Strategy

### Immediate (React State)
```typescript
// Scanner page: cards in state (existing)
const [cards, setCards] = useState<Card[]>([]);
// ✅ Fast (0ms latency)
// ✅ No database dependency
// ❌ Lost on close (unless exported to CSV)
```

### Short-term (Batch in DB)
```typescript
// NEW: Current scanning session persisted
const currentBatch = {
  id: 'batch_1234',
  started_at: Date.now(),
  lines: [...cards], // Synced to batch_lines table
  posted: false,
};
// ✅ Survives app restart
// ✅ Can resume interrupted session
// ❌ Not yet posted to inventory
```

### Long-term (Inventory in DB)
```typescript
// NEW: Posted cards in inventory table
await window.batches.post(currentBatch.id);
// Atomically:
// - Insert/update inventory rows
// - Mark batch as posted
// - Publish events to event log
// ✅ Permanent record
// ✅ Searchable/filterable
// ✅ Audit trail in events
```

---

## Database Transaction Strategy

### ACID Guarantees
```sql
-- All batch posts are atomic transactions
BEGIN TRANSACTION;

-- 1. Insert inventory entries
INSERT INTO inventory (card_id, condition, cost_basis, qty)
VALUES (?, ?, ?, ?)
ON CONFLICT (card_id, condition) DO UPDATE SET
  qty = qty + excluded.qty,
  last_updated = CURRENT_TIMESTAMP;

-- 2. Log events
INSERT INTO events (type, aggregate_id, data, timestamp)
VALUES ('card_added', ?, ?, ?);

-- 3. Mark batch as posted
UPDATE batches SET posted_at = CURRENT_TIMESTAMP WHERE id = ?;

COMMIT; -- All or nothing
```

**Failure Handling:**
- If any step fails → ROLLBACK (no partial state)
- Show error to user: "Batch post failed, try again"
- Batch remains in "unposted" state (can retry)

---

## Event Sourcing Benefits

### Audit Trail
```typescript
// Every domain action logged
await eventLog.publish('card_scanned', {
  batchId: '1234',
  cardId: 'OP01-001',
  confidence: 'HIGH',
  price: 12.50,
  timestamp: Date.now(),
});

await eventLog.publish('price_adjusted', {
  cardId: 'OP01-001',
  oldPrice: 12.50,
  newPrice: 15.00,
  reason: 'market_update',
  timestamp: Date.now(),
});
```

**Benefits:**
- **Replay**: Rebuild inventory state from events (disaster recovery)
- **Analytics**: Dashboard queries events, not live inventory (fast)
- **Cloud Sync**: Replicate events to AWS (idempotent, commutative)
- **Debugging**: "Show me all events for card OP01-001"

### Read Models (Denormalized Views)
```typescript
// Dashboard metrics built from events (fast queries)
SELECT
  COUNT(*) as total_scans,
  SUM(price) as total_value,
  AVG(confidence) as avg_confidence
FROM events
WHERE type = 'card_scanned'
  AND DATE(timestamp) = DATE('now');

// Pre-aggregated for speed
CREATE TABLE dashboard_metrics (
  date TEXT PRIMARY KEY,
  total_scans INTEGER,
  total_value REAL,
  avg_confidence REAL
);

// Rebuilt on app start from events (fast)
```

---

## Cloud Sync Design (Future)

### SyncAdapter Interface
```typescript
interface SyncAdapter {
  // Push local events to cloud
  pushEvents(events: Event[]): Promise<SyncResult>;

  // Pull remote events from cloud
  pullEvents(since: Date): Promise<Event[]>;

  // Resolve conflicts (3-way merge)
  resolveConflicts(local: Event[], remote: Event[]): Event[];

  // Authenticate device
  authenticate(creds: Credentials): Promise<Session>;

  // Health check
  isOnline(): Promise<boolean>;
}

// LocalOnlyAdapter (Phase 1-7)
class LocalOnlyAdapter implements SyncAdapter {
  async pushEvents() { return { synced: 0 }; }
  async pullEvents() { return []; }
  resolveConflicts(local) { return local; } // No conflicts
  async authenticate() { throw new Error('Offline mode'); }
  async isOnline() { return false; }
}

// AwsSyncAdapter (Phase 8 stub, Phase 9+ implementation)
class AwsSyncAdapter implements SyncAdapter {
  constructor(
    private apiEndpoint: string,
    private cognito: CognitoClient,
  ) {}

  async pushEvents(events: Event[]): Promise<SyncResult> {
    // TODO: POST /events to API Gateway
    // TODO: Store in DynamoDB as event stream
    throw new Error('Cloud sync not yet implemented');
  }

  // ... other methods stubbed
}
```

### Conflict Resolution Strategy
```typescript
// Vector clock approach (design now, implement later)
interface Event {
  id: string;                    // UUID
  type: string;                  // 'card_scanned', 'price_adjusted'
  aggregateId: string;           // Entity ID (card, batch)
  data: any;                     // Event payload
  timestamp: number;             // Local timestamp (may have clock skew)
  vectorClock: { [device: string]: number }; // Causal ordering
  deviceId: string;              // Device that created event
}

// Last-write-wins with vector clock tie-breaking
function resolveConflicts(local: Event[], remote: Event[]): Event[] {
  const merged = [...local, ...remote];

  // Group by aggregate (e.g., same card)
  const byAggregate = groupBy(merged, e => e.aggregateId);

  // For each aggregate, resolve conflicts
  return Object.values(byAggregate).flatMap(events => {
    // Sort by vector clock (causal order)
    events.sort(vectorClockCompare);

    // Apply events in order (last write wins)
    return events;
  });
}
```

**Implementation Timeline**: Not before Week 9+

---

## Security Considerations

### Database Encryption (At Rest)
```typescript
// Phase 5: SQLCipher for encrypted database
import Database from 'better-sqlite3';
const db = new Database('cardflux.db');
db.pragma('cipher_page_size = 4096');
db.pragma('kdf_iter = 256000');
db.pragma(`key = '${await getEncryptionKey()}'`);
```

### Backup Encryption
```typescript
// Phase 5: AES-256 encrypted ZIP
import { createCipheriv, randomBytes } from 'crypto';

async function createBackup(dbPath: string): Promise<string> {
  const key = randomBytes(32); // 256-bit key
  const iv = randomBytes(16);

  const cipher = createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([
    cipher.update(fs.readFileSync(dbPath)),
    cipher.final(),
  ]);

  // Store key in keychain (electron-store with encryption)
  await keychain.setPassword('backup', backupId, key.toString('hex'));

  return encrypted;
}
```

### IPC Security (Already Implemented)
```typescript
// Existing: Origin validation in main process
ipcMain.handle('database:query', async (event, sql, params) => {
  // Validate origin
  const url = new URL(event.senderFrame.url);
  if (url.protocol !== 'file:' && url.host !== 'localhost') {
    throw new Error('Invalid IPC origin');
  }

  // Validate SQL (no DROP, DELETE without WHERE, etc.)
  if (isUnsafeSQL(sql)) {
    throw new Error('Unsafe SQL detected');
  }

  // Rate limit
  await rateLimiter.check('database:query', event.sender.id);

  // Execute
  return db.prepare(sql).all(...params);
});
```

---

## Performance Targets

### Scanner Page (Unchanged)
- ✅ Detection loop: 500-1000ms (already achieved)
- ✅ Capture feedback: <150ms (flash animation)
- ✅ Identification: 500-1500ms (Python bridge)

### New Pages
- **Inventory**: Search results <200ms (indexed queries)
- **Dashboard**: Page load <500ms (pre-aggregated metrics)
- **Buylist**: Scan loop <150ms (cached buy prices)

### Database Operations
- **Batch post**: <100ms for 50 cards (transaction)
- **CSV import**: <2s for 1000 cards (bulk insert)
- **Event log write**: <10ms (async, non-blocking)

### App Startup
- **Cold start**: <3s (database init + migrations)
- **Hot start**: <1s (cached)

---

## Testing Strategy (Detailed in TESTING_PLAN.md)

**Coverage Targets:**
- Unit tests: 80% coverage (business logic)
- Integration tests: All IPC handlers
- E2E tests: 10 critical user flows
- Visual regression: 20 key screens

**Test Pyramid:**
```
     /\        E2E (10 tests)
    /  \       - Scanner → Inventory flow
   /    \      - Batch posting
  /------\     - CSV import/export
 / Integr \    Integration (50 tests)
/   ation \    - IPC handlers
/----------\   - Database queries
/   Unit    \  Unit (200 tests)
/            \ - Event log
/  Tests      \- SyncAdapter
```

---

## Rollback Strategy

### Automatic Health Check
```typescript
// On app start (main.ts)
const healthCheck = async () => {
  try {
    // 1. Test database connection
    db.prepare('SELECT 1').get();

    // 2. Verify migrations
    const version = await getMigrationVersion();
    if (version !== EXPECTED_VERSION) {
      throw new Error('Migration mismatch');
    }

    // 3. Test renderer init
    const timeout = setTimeout(() => {
      throw new Error('Renderer init timeout');
    }, 10000);

    await waitForRendererReady();
    clearTimeout(timeout);

    // Success
    await markVersionHealthy(app.getVersion());
  } catch (error) {
    // ROLLBACK: Restore previous version
    logger.error('Health check failed, rolling back', error);
    await restorePreviousVersion();
    app.relaunch();
    app.exit(0);
  }
};
```

### Manual Rollback
```typescript
// Settings page: "Restore from Backup"
const restoreBackup = async (backupPath: string) => {
  // 1. Verify backup integrity
  const backup = await decryptBackup(backupPath);
  const checksum = await verifyChecksum(backup);

  // 2. Create current backup (safety)
  await createBackup('pre-restore-backup.zip');

  // 3. Stop database
  db.close();

  // 4. Replace database file
  fs.copyFileSync(backup.dbPath, currentDbPath);

  // 5. Restart app
  app.relaunch();
  app.exit(0);
};
```

---

## Release Channels

### Canary (Week 8)
- **Audience**: Internal testing (1-2 devices)
- **Update frequency**: Every commit to `main`
- **Auto-update**: Enabled
- **Rollback**: Automatic on health check failure

### Beta (Week 9)
- **Audience**: Friendly shops (5-10 users)
- **Update frequency**: Weekly
- **Auto-update**: Prompt user
- **Rollback**: Manual (restore from backup)

### Stable (Week 10+)
- **Audience**: All users
- **Update frequency**: Bi-weekly
- **Auto-update**: Background download, install on quit
- **Rollback**: Automatic + manual

---

## Success Metrics (Demo-Ready Checklist)

### Phase 1 (Foundation) ✅
- [ ] Scanner still works (all existing tests pass)
- [ ] Database initializes on first run
- [ ] Migrations run successfully
- [ ] Event log writes events
- [ ] Health check detects failures
- [ ] Tests run in CI (100% pass)

### Phase 2 (Inventory) ✅
- [ ] Scan 20 cards → Post Batch → See in Inventory
- [ ] Search finds cards by name
- [ ] Bulk price adjustment works
- [ ] CSV export includes all inventory
- [ ] CSV import adds cards to inventory

### Phase 3 (Dashboard) ✅
- [ ] Dashboard shows accurate scan count
- [ ] Top 10 SKUs correct
- [ ] Charts render in <500ms
- [ ] Alerts trigger for aging stock

### Phase 4 (Buylist) ✅
- [ ] Add cards to buylist targets
- [ ] Buy-in workflow: scan → accept → pay
- [ ] Margin calculator shows profit
- [ ] Cards added to inventory with cost basis

### Phase 5 (Settings) ✅
- [ ] Backup creates encrypted ZIP
- [ ] Restore from backup works
- [ ] Dark/light themes switch instantly
- [ ] Keyboard navigation works on all pages

### Phase 6 (Cloud-Ready) ✅
- [ ] Auto-update downloads and installs
- [ ] Health check prevents broken releases
- [ ] Rollback restores previous version
- [ ] E2E tests cover all critical paths
- [ ] Visual regression catches UI bugs

---

## Next Steps

1. **Review this architecture** - Does it meet your vision?
2. **Approve phasing** - Any phases to adjust?
3. **Next deliverable**: Database schema + migrations (WEEK 1)
4. **Then**: Dependency plan + version control strategy

**Ready to proceed?** Let me know if any changes needed before I design the database schema.
