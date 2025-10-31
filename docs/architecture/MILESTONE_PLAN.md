# CardFlux Milestone Plan with Definition of Done
**Timeline**: 8 weeks (Nov 2025 - Jan 2026)
**Goal**: Demo-ready multi-page shop management app
**Quality**: Production-grade, shop-tested

---

## Milestone 0: Planning Complete ✅ (Week 0)
**Date**: 2025-10-31
**Status**: DONE

### Deliverables
- ✅ Architecture evolution plan (MULTI_PAGE_EVOLUTION.md)
- ✅ Database schema design (DATABASE_SCHEMA.md)
- ✅ Dependency plan (DEPENDENCIES_AND_VERSIONS.md)
- ✅ Milestone plan (this document)
- ✅ Version control strategy
- ✅ Comprehensive audit report (COMPREHENSIVE_AUDIT_2025-10-31.md)

### Definition of Done
- [x] All planning documents reviewed and approved
- [x] Team aligned on phasing strategy
- [x] Baseline tagged (v0.2.2-pre-migration)

---

## Milestone 1: Foundation (Week 1-2)
**Goal**: Add database + testing WITHOUT breaking scanner
**Branch**: `feature/database-foundation`
**Release**: v0.3.0

### Week 1: Database + Migrations

#### Day 1-2: Database Setup
**Tasks:**
- [ ] Install dependencies (better-sqlite3, kysely, zod)
- [ ] Configure Kysely with SQLite dialect
- [ ] Create database manager module in main process
- [ ] Write initial migration (001_initial_schema.ts)
- [ ] Test database initialization on first run
- [ ] Add WAL mode configuration (PRAGMA statements)

**Definition of Done:**
- [ ] Database file created on first run (`cardflux.db`)
- [ ] WAL mode enabled (`PRAGMA journal_mode = WAL`)
- [ ] All tables created from migration
- [ ] Seed data inserted (settings, devices)
- [ ] Migration tracked in `migrations` table
- [ ] No errors in console on startup
- [ ] Scanner page still works (unchanged)

**Acceptance Criteria:**
```bash
# Test script
pnpm test:db-init

# Manual test
1. Delete cardflux.db (if exists)
2. Start app
3. Check: cardflux.db created
4. Check: tables exist (run SELECT * FROM sqlite_master)
5. Check: settings populated
6. Scanner page works (scan 1 card)
```

#### Day 3-4: Event Log System
**Tasks:**
- [ ] Create EventLog service in main process
- [ ] Implement publish() method (insert into events table)
- [ ] Add IPC handler: `events:publish`
- [ ] Add event types enum (card_scanned, batch_posted, etc.)
- [ ] Test event publishing (unit tests)
- [ ] Add event to scanner: publish card_scanned (optional, feature flag)

**Definition of Done:**
- [ ] EventLog.publish() writes to events table
- [ ] Events include: id, type, aggregate_id, data, timestamp, device_id
- [ ] Events immutable (triggers prevent UPDATE/DELETE)
- [ ] IPC handler validates payloads with zod
- [ ] Unit tests cover event publishing
- [ ] Scanner can optionally publish events (doesn't block UX)

**Acceptance Criteria:**
```typescript
// Test
await eventLog.publish('card_scanned', {
  batchId: 'test-batch',
  cardId: 'OP01-001',
  confidence: 'HIGH',
});

// Verify
const events = db.selectFrom('events').selectAll().execute();
expect(events).toHaveLength(1);
expect(events[0].type).toBe('card_scanned');
```

#### Day 5-7: Testing Infrastructure
**Tasks:**
- [ ] Configure Jest for unit tests
- [ ] Configure Playwright for E2E tests
- [ ] Write database integration tests
- [ ] Write IPC contract tests
- [ ] Write E2E test: scanner still works
- [ ] Add CI workflow (GitHub Actions)

**Definition of Done:**
- [ ] Unit tests run with `pnpm test` (Jest)
- [ ] E2E tests run with `pnpm test:e2e` (Playwright)
- [ ] Test coverage report generated
- [ ] CI runs on every commit (GitHub Actions)
- [ ] All tests pass (100% green)
- [ ] Test commands documented in README.md

**Acceptance Criteria:**
```bash
# Unit tests
pnpm test
# Expected: 20+ tests pass, 0 fail

# E2E tests
pnpm test:e2e
# Expected: Scanner flow works (scan → add to stack → export CSV)

# CI
git push origin feature/database-foundation
# Expected: CI runs, all checks pass
```

### Week 2: Multi-Page Routing + SyncAdapter

#### Day 8-9: React Router Setup
**Tasks:**
- [ ] Install react-router-dom
- [ ] Create HashRouter configuration
- [ ] Add route definitions (/, /scanner, /inventory, /buylist, /settings)
- [ ] Create placeholder pages (empty components)
- [ ] Add navigation menu
- [ ] Preserve scanner page functionality (exact copy)
- [ ] Add feature flag: `multiPageNavigation` (default: false)

**Definition of Done:**
- [ ] Routes defined for all 5 pages
- [ ] Navigation menu renders (top bar)
- [ ] Scanner page accessible at /scanner
- [ ] Scanner page works exactly as before (no regressions)
- [ ] Other pages show "Coming Soon" placeholder
- [ ] Feature flag toggles multi-page navigation
- [ ] Keyboard shortcuts work (S → settings, etc.)

**Acceptance Criteria:**
```typescript
// Test routing
render(<App />);
expect(screen.getByText(/Dashboard/)).toBeInTheDocument();

fireEvent.click(screen.getByText(/Scanner/));
expect(window.location.hash).toBe('#/scanner');

// Test scanner unchanged
// (run existing scanner tests)
```

#### Day 10-11: SyncAdapter Interface
**Tasks:**
- [ ] Define SyncAdapter TypeScript interface
- [ ] Implement LocalOnlyAdapter (no-op methods)
- [ ] Add feature flag: `cloudSync` (default: false)
- [ ] Add IPC handler: `sync:push`, `sync:pull` (stubs)
- [ ] Create AwsSyncAdapter stub (throws "Not implemented")
- [ ] Document sync strategy (vector clocks, conflict resolution)

**Definition of Done:**
- [ ] SyncAdapter interface complete (TypeScript)
- [ ] LocalOnlyAdapter implements interface (returns empty)
- [ ] AwsSyncAdapter stub exists (throws error)
- [ ] Feature flag controls sync behavior
- [ ] Documentation written (CLOUD_SYNC_DESIGN.md)
- [ ] No network calls in LocalOnlyAdapter

**Acceptance Criteria:**
```typescript
// Test LocalOnlyAdapter
const adapter = new LocalOnlyAdapter();
await adapter.pushEvents([]); // Returns { synced: 0 }
const remote = await adapter.pullEvents(new Date()); // Returns []

// Test feature flag
if (featureFlags.cloudSync) {
  throw new Error('Should be disabled');
}
```

#### Day 12-14: Health Check + Rollback
**Tasks:**
- [ ] Create HealthCheck service
- [ ] Add startup health check (database, migrations, renderer)
- [ ] Implement auto-rollback logic (restore previous version)
- [ ] Test health check failure scenario
- [ ] Add pre-migration backup
- [ ] Document rollback procedure

**Definition of Done:**
- [ ] Health check runs on app startup
- [ ] Tests: database connection, migration version, renderer init
- [ ] Auto-rollback triggers on failure (restores backup)
- [ ] Pre-migration backup created automatically
- [ ] Health check timeout: 10 seconds
- [ ] Rollback tested (manual + automated)

**Acceptance Criteria:**
```bash
# Test health check
1. Corrupt database file (invalidate schema)
2. Start app
3. Expect: Health check fails
4. Expect: Auto-rollback restores backup
5. Expect: App starts successfully with old version

# Test migration backup
1. Run migration
2. Check: backup file created (pre-migration-<timestamp>.db)
3. Migration fails (simulate)
4. Check: backup restored
```

### Milestone 1 Definition of Done

#### Functional Requirements
- [x] Database initializes on first run
- [x] Migrations run successfully
- [x] Event log publishes events
- [x] Multi-page routing works (feature flag)
- [x] Scanner page unchanged (100% backward compatible)
- [x] Health check prevents broken releases
- [x] Auto-rollback restores on failure

#### Technical Requirements
- [x] All tests pass (unit + integration + E2E)
- [x] TypeScript compiles with 0 errors
- [x] Lint clean (0 warnings)
- [x] CI runs on every commit
- [x] Code coverage ≥ 70% (excluding UI)
- [x] Documentation complete (architecture + API)

#### Quality Gates
- [x] Scanner regression test passes (existing workflow works)
- [x] Database performance: init <500ms, query <50ms
- [x] No memory leaks (run for 1 hour, check heap)
- [x] Startup time ≤ 3 seconds (cold start)

#### Release Checklist
- [x] Tag baseline: `v0.2.2-pre-multi-page`
- [x] Create feature branch: `feature/database-foundation`
- [x] Merge to main (squash commits)
- [x] Tag release: `v0.3.0`
- [x] Create GitHub release with changelog
- [x] Update CHANGELOG.md

---

## Milestone 2: Inventory Page (Week 3-4)
**Goal**: Build inventory management + batch posting
**Branch**: `feature/inventory-page`
**Release**: v0.4.0

### Week 3: Batch Persistence + Posting

#### Day 15-17: Batch CRUD Operations
**Tasks:**
- [ ] Add IPC handlers: `batches:create`, `batches:addCard`, `batches:post`
- [ ] Implement batch creation (insert into batches table)
- [ ] Implement add card to batch (insert into batch_lines)
- [ ] Update scanner page: "Start Batch" button
- [ ] Update scanner page: "Post Batch" button
- [ ] Test batch persistence (survives app restart)
- [ ] Add batch state to Zustand store

**Definition of Done:**
- [ ] Batch created on "Start Batch" click
- [ ] Cards added to batch_lines table on scan
- [ ] Batch totals update (card_count, total_value)
- [ ] Batch persists across app restarts
- [ ] "Post Batch" button enabled when batch has cards
- [ ] Transaction ensures atomicity (all or nothing)

**Acceptance Criteria:**
```typescript
// Test batch creation
const batch = await window.batches.create();
expect(batch.id).toBeDefined();
expect(batch.card_count).toBe(0);

// Test add card
await window.batches.addCard(batch.id, card);
const updated = await window.batches.get(batch.id);
expect(updated.card_count).toBe(1);

// Test persistence
// Restart app
const persisted = await window.batches.get(batch.id);
expect(persisted).toBeDefined();
```

#### Day 18-19: Batch Posting Transaction
**Tasks:**
- [ ] Implement `batches.post()` transaction
- [ ] Insert/update inventory rows (UPSERT logic)
- [ ] Publish events (card_added, batch_posted)
- [ ] Mark batch as posted (set posted_at)
- [ ] Test transaction rollback on error
- [ ] Add error handling + user feedback

**Definition of Done:**
- [ ] Post batch runs in single transaction (ACID)
- [ ] Inventory rows created/updated correctly
- [ ] Events published to event log
- [ ] Batch marked as posted (posted_at set)
- [ ] Transaction rolls back on error (no partial state)
- [ ] User sees success/error notification

**Acceptance Criteria:**
```sql
-- After posting batch with 3 cards
SELECT COUNT(*) FROM inventory; -- Expected: 3 rows
SELECT COUNT(*) FROM events WHERE type = 'card_added'; -- Expected: 3
SELECT posted_at FROM batches WHERE id = ?; -- Expected: NOT NULL

-- Test rollback
-- Simulate error mid-transaction
-- Expected: inventory unchanged, batch still unposted
```

#### Day 20-21: Inventory Query API
**Tasks:**
- [ ] Add IPC handlers: `inventory:search`, `inventory:getAll`, `inventory:update`
- [ ] Implement search with FTS (full-text search)
- [ ] Implement filters (tcg_game, condition, qty > 0)
- [ ] Implement pagination (limit + offset)
- [ ] Add indices for common queries
- [ ] Test query performance (<200ms)

**Definition of Done:**
- [ ] Search by name works (FTS)
- [ ] Filters applied correctly (condition, game, qty)
- [ ] Pagination returns correct pages
- [ ] Query time <200ms for 1000 cards
- [ ] IPC handlers validate inputs (zod)
- [ ] Error handling complete

**Acceptance Criteria:**
```typescript
// Test search
const results = await window.inventory.search('Luffy', { game: 'one-piece' });
expect(results.length).toBeGreaterThan(0);
expect(results[0].name).toContain('Luffy');

// Test filters
const nmCards = await window.inventory.getAll({ condition: 'NM' });
expect(nmCards.every(c => c.condition === 'NM')).toBe(true);

// Test pagination
const page1 = await window.inventory.getAll({ limit: 10, offset: 0 });
const page2 = await window.inventory.getAll({ limit: 10, offset: 10 });
expect(page1[0].id).not.toBe(page2[0].id);
```

### Week 4: Inventory UI + CSV Import/Export

#### Day 22-24: Inventory Page UI
**Tasks:**
- [ ] Create InventoryPage component
- [ ] Add search bar with filters
- [ ] Add data table (card list)
- [ ] Add pagination controls
- [ ] Add bulk action toolbar (select all, adjust price)
- [ ] Add empty state (no inventory)
- [ ] Test keyboard navigation (Tab, Arrow keys)

**Definition of Done:**
- [ ] Search bar filters results
- [ ] Table shows: name, condition, qty, price, set
- [ ] Pagination works (next/prev buttons)
- [ ] Bulk actions enabled when rows selected
- [ ] Empty state shown when no inventory
- [ ] Keyboard navigation works (accessibility)
- [ ] Loading states shown during queries

**Acceptance Criteria:**
```tsx
// Test rendering
render(<InventoryPage />);
expect(screen.getByPlaceholderText(/Search cards/)).toBeInTheDocument();

// Test search
fireEvent.change(searchInput, { target: { value: 'Luffy' } });
await waitFor(() => {
  expect(screen.getByText(/Monkey.D.Luffy/)).toBeInTheDocument();
});

// Test pagination
fireEvent.click(screen.getByText(/Next/));
// Expect: New cards loaded
```

#### Day 25-26: CSV Import/Export
**Tasks:**
- [ ] Add "Export CSV" button (inventory page)
- [ ] Implement CSV generation (papaparse)
- [ ] Add "Import CSV" button + file picker
- [ ] Implement CSV parsing + validation
- [ ] Add bulk insert for import (transaction)
- [ ] Add progress indicator for large imports
- [ ] Test with 1000+ row CSV

**Definition of Done:**
- [ ] Export CSV downloads file (name, number, qty, price, condition)
- [ ] Import CSV validates format (required columns)
- [ ] Import runs in transaction (all or nothing)
- [ ] Progress bar shows during import
- [ ] Import handles duplicates (update existing)
- [ ] Error handling for invalid CSV

**Acceptance Criteria:**
```typescript
// Test export
const csv = await window.inventory.exportCSV();
expect(csv).toContain('Card Name,Number,Condition,Qty,Price');

// Test import
const result = await window.inventory.importCSV(csvString);
expect(result.imported).toBe(100);
expect(result.errors).toHaveLength(0);

// Test duplicate handling
// Import same CSV twice
// Expect: Qty updated, not duplicated
```

#### Day 27-28: Testing + Polish
**Tasks:**
- [ ] Write E2E test: scan → post → inventory page
- [ ] Write E2E test: CSV import/export roundtrip
- [ ] Add visual regression tests (screenshots)
- [ ] Fix bugs found during testing
- [ ] Add loading skeletons for async operations
- [ ] Performance testing (1000+ inventory items)

**Definition of Done:**
- [ ] E2E test covers full workflow (scan → inventory)
- [ ] CSV roundtrip test passes (export → import → verify)
- [ ] Visual regression tests baseline captured
- [ ] No critical bugs remaining
- [ ] Performance acceptable (queries <200ms)
- [ ] All tests pass (unit + integration + E2E)

**Acceptance Criteria:**
```bash
# E2E test
pnpm test:e2e --grep "scan to inventory"
# Expected: Pass

# Visual regression
pnpm test:visual
# Expected: No differences from baseline

# Performance
# Load 1000 cards in inventory
# Search: <200ms
# Scroll: 60fps
```

### Milestone 2 Definition of Done

#### Functional Requirements
- [x] Batch creation + persistence
- [x] Batch posting to inventory (transaction)
- [x] Inventory search (FTS)
- [x] Inventory filters (condition, game, qty)
- [x] CSV import/export
- [x] Bulk actions (price adjustment)

#### Technical Requirements
- [x] All tests pass (30+ new tests)
- [x] Transaction safety (ACID guarantees)
- [x] Performance: queries <200ms, import <2s for 1000 cards
- [x] Code coverage ≥ 75%
- [x] Documentation updated (API, user guide)

#### Quality Gates
- [x] Full workflow test: scan 20 cards → post → see in inventory
- [x] CSV roundtrip test: export → import → verify
- [x] Batch rollback test: error during post → no partial state
- [x] Scanner still works (no regressions)

#### Release Checklist
- [x] Merge to main
- [x] Tag release: `v0.4.0`
- [x] Create GitHub release
- [x] Update CHANGELOG.md
- [x] Demo video (scan → post → inventory)

---

## Milestone 3: Dashboard (Week 5)
**Goal**: Show shop metrics from event log
**Branch**: `feature/dashboard`
**Release**: v0.5.0

### Week 5: Dashboard Page

#### Day 29-30: Dashboard Metrics API
**Tasks:**
- [ ] Create DashboardService (aggregate from events)
- [ ] Add IPC handlers: `dashboard:getStats`, `dashboard:getTopSKUs`
- [ ] Implement today's stats query (scans, revenue, margin)
- [ ] Implement top 10 SKUs query (by velocity)
- [ ] Implement aging stock query (>90 days)
- [ ] Test query performance (<100ms)

**Definition of Done:**
- [ ] Dashboard queries run <100ms
- [ ] Stats accurate (match event log)
- [ ] Top SKUs sorted correctly
- [ ] Aging stock detection works
- [ ] IPC handlers tested

**Acceptance Criteria:**
```typescript
// Test stats
const stats = await window.dashboard.getStats();
expect(stats.scansToday).toBeGreaterThan(0);
expect(stats.revenue).toBeGreaterThan(0);

// Test top SKUs
const topSKUs = await window.dashboard.getTopSKUs();
expect(topSKUs).toHaveLength(10);
expect(topSKUs[0].salesCount).toBeGreaterThan(topSKUs[1].salesCount);
```

#### Day 31-32: Dashboard UI
**Tasks:**
- [ ] Create DashboardPage component
- [ ] Add stat cards (scans, revenue, margin, inventory value)
- [ ] Add chart: daily scans (last 30 days)
- [ ] Add chart: buy-in vs sell (last 30 days)
- [ ] Add top 10 SKUs table
- [ ] Add aging stock alerts
- [ ] Add empty state (no data yet)

**Definition of Done:**
- [ ] Stat cards show correct values
- [ ] Charts render correctly (Recharts)
- [ ] Charts load <500ms
- [ ] Top SKUs table sortable
- [ ] Alerts highlighted (red for aging stock)
- [ ] Empty state shown for new users

**Acceptance Criteria:**
```tsx
// Test rendering
render(<DashboardPage />);
expect(screen.getByText(/Today's Stats/)).toBeInTheDocument();
expect(screen.getByText(/Top 10 SKUs/)).toBeInTheDocument();

// Test chart
// Expect: LineChart renders with data points
```

#### Day 33-35: Polish + Testing
**Tasks:**
- [ ] Add refresh button (reload metrics)
- [ ] Add date range selector (7d, 30d, 90d)
- [ ] Add export dashboard data (CSV)
- [ ] Write E2E test: dashboard after scanning
- [ ] Visual regression tests
- [ ] Performance testing (fast metrics)

**Definition of Done:**
- [ ] Refresh updates all metrics
- [ ] Date range filters work
- [ ] Export CSV includes all data
- [ ] E2E test passes
- [ ] Visual regression baseline
- [ ] Dashboard loads <500ms

**Acceptance Criteria:**
```bash
# E2E test
1. Scan 50 cards
2. Navigate to dashboard
3. Expect: "50 cards scanned" shown
4. Expect: Charts populated
5. Expect: Top SKUs table filled
```

### Milestone 3 Definition of Done

#### Functional Requirements
- [x] Dashboard shows today's stats (scans, revenue, margin)
- [x] Charts display historical data (7d, 30d, 90d)
- [x] Top 10 SKUs by velocity
- [x] Aging stock alerts (>90 days)
- [x] Export dashboard data (CSV)

#### Technical Requirements
- [x] Query performance <100ms (pre-aggregated)
- [x] Charts render <500ms
- [x] All tests pass
- [x] Code coverage ≥ 75%

#### Quality Gates
- [x] Dashboard accurate after 100+ scans
- [x] Charts responsive (resize smoothly)
- [x] Alerts trigger correctly (aging stock)

#### Release Checklist
- [x] Merge to main
- [x] Tag release: `v0.5.0`
- [x] Update CHANGELOG.md
- [x] Demo video (dashboard walkthrough)

---

## Milestone 4: Buylist (Week 6)
**Goal**: Enable buy-in workflow
**Branch**: `feature/buylist`
**Release**: v0.5.5

### Week 6: Buylist Page

#### Day 36-37: Buylist API
**Tasks:**
- [ ] Add IPC handlers: `buylist:addTarget`, `buylist:getTargets`, `buylist:buyIn`
- [ ] Implement buylist target CRUD
- [ ] Implement buy-in transaction (add to inventory with cost basis)
- [ ] Add pricing rules (% of market, min/max)
- [ ] Test buy-in workflow

**Definition of Done:**
- [ ] Targets stored in buylist_targets table
- [ ] Buy-in transaction adds to inventory
- [ ] Pricing rules applied correctly
- [ ] Cost basis tracked for margin calc
- [ ] All IPC handlers tested

**Acceptance Criteria:**
```typescript
// Test target
await window.buylist.addTarget({
  cardId: 'OP01-001',
  buyPrice: 10.00,
  maxQty: 4,
  minCondition: 'LP',
});

// Test buy-in
const result = await window.buylist.buyIn([
  { cardId: 'OP01-001', condition: 'NM', qty: 2 },
]);
expect(result.totalCost).toBe(20.00);

// Verify inventory
const inventory = await window.inventory.get('OP01-001');
expect(inventory.qty).toBe(2);
expect(inventory.cost_basis).toBe(10.00);
```

#### Day 38-40: Buylist UI + Scanner Integration
**Tasks:**
- [ ] Create BuylistPage component
- [ ] Add target management UI (add/edit/delete targets)
- [ ] Add "Buylist Mode" toggle in scanner
- [ ] Update scanner to show buy prices in buylist mode
- [ ] Add accept/reject buttons per card
- [ ] Add buy-in summary (total, qty)
- [ ] Test scanner buylist mode

**Definition of Done:**
- [ ] Buylist targets shown in table
- [ ] Scanner shows buy prices in buylist mode
- [ ] Accept/reject buttons work
- [ ] Buy-in summary accurate
- [ ] Buylist mode toggle works
- [ ] All tests pass

**Acceptance Criteria:**
```bash
# E2E test: buy-in workflow
1. Add 5 cards to buylist targets
2. Enable "Buylist Mode" in scanner
3. Scan customer's cards (10 cards)
4. Accept 5 cards (in targets), reject 5 (not in targets)
5. Confirm buy-in ($50 total)
6. Expect: Inventory updated with cost basis
7. Expect: Event logged (buy_in_completed)
```

#### Day 41-42: Testing + Polish
**Tasks:**
- [ ] E2E test: buylist workflow
- [ ] Add margin calculator (buy vs sell price)
- [ ] Add condition adjustment (% discount for LP/MP)
- [ ] Visual regression tests
- [ ] Bug fixes

**Definition of Done:**
- [ ] E2E test passes
- [ ] Margin calculator accurate
- [ ] Condition adjustments work
- [ ] Visual regression baseline
- [ ] No critical bugs

---

## Milestone 5: Settings + Polish (Week 7)
**Goal**: Complete app with settings + accessibility
**Branch**: `feature/settings-polish`
**Release**: v0.5.8

### Week 7: Settings Page + Accessibility

#### Day 43-44: Settings Page
**Tasks:**
- [ ] Create SettingsPage component
- [ ] Add TCG game selector
- [ ] Add scanner config (thresholds, multi-frame)
- [ ] Add pricing rules (margin %, rounding)
- [ ] Add theme selector (dark/light/high-contrast)
- [ ] Add feature flags UI (toggles)
- [ ] Test settings persistence

**Definition of Done:**
- [ ] All settings persist across restarts
- [ ] Settings sync with electron-store
- [ ] Feature flags toggle correctly
- [ ] Theme changes apply instantly
- [ ] Scanner config updates scanner behavior

#### Day 45-46: Backup/Restore
**Tasks:**
- [ ] Add "Create Backup" button (Settings page)
- [ ] Implement backup creation (encrypted ZIP)
- [ ] Add "Restore from Backup" button + file picker
- [ ] Implement restore logic (verify integrity, restart app)
- [ ] Add automatic daily backups (2 AM)
- [ ] Test backup/restore roundtrip

**Definition of Done:**
- [ ] Backup creates encrypted ZIP
- [ ] Restore verifies integrity (checksum)
- [ ] Automatic backups run daily
- [ ] Keep last 7 backups only
- [ ] Restore restarts app successfully

#### Day 47-49: Accessibility + Keyboard Nav
**Tasks:**
- [ ] Add keyboard shortcuts (global + context-aware)
- [ ] Add focus management (Tab order, focus traps)
- [ ] Add ARIA labels (all interactive elements)
- [ ] Add high-contrast theme
- [ ] Test with screen reader (NVDA/JAWS)
- [ ] Test keyboard-only navigation

**Definition of Done:**
- [ ] All pages navigable via keyboard
- [ ] Focus visible (outline on focused elements)
- [ ] ARIA labels on all buttons/inputs
- [ ] High-contrast mode passes WCAG AA
- [ ] Screen reader announces state changes
- [ ] Keyboard shortcuts documented (Help dialog)

---

## Milestone 6: Cloud-Ready + Release (Week 8)
**Goal**: Production-ready with auto-update + cloud stubs
**Branch**: `feature/cloud-ready`
**Release**: v0.6.0

### Week 8: Auto-Update + E2E Testing

#### Day 50-52: Auto-Update System
**Tasks:**
- [ ] Configure electron-updater
- [ ] Add auto-update logic (background download)
- [ ] Add update notification (prompt user)
- [ ] Add release channels (canary/beta/stable)
- [ ] Test update flow (mock server)
- [ ] Document release process

**Definition of Done:**
- [ ] Auto-update checks on startup
- [ ] Downloads update in background
- [ ] Prompts user to install on quit
- [ ] Release channels configurable
- [ ] Rollback on health check failure
- [ ] Release process documented

#### Day 53-54: E2E Test Suite
**Tasks:**
- [ ] Write E2E test: full scan workflow (scan → post → inventory → dashboard)
- [ ] Write E2E test: buy-in workflow
- [ ] Write E2E test: CSV import/export
- [ ] Write E2E test: backup/restore
- [ ] Write E2E test: settings changes
- [ ] Add visual regression tests (all pages)

**Definition of Done:**
- [ ] 10+ E2E tests cover critical paths
- [ ] All E2E tests pass
- [ ] Visual regression baseline captured
- [ ] E2E tests run in CI
- [ ] Test reports generated (HTML)

#### Day 55-56: Final Polish + Release
**Tasks:**
- [ ] Fix all remaining bugs
- [ ] Update all documentation (README, CHANGELOG, user guide)
- [ ] Create demo video (YouTube)
- [ ] Package app for all platforms (Windows/macOS/Linux)
- [ ] Test installers on clean machines
- [ ] Create GitHub release (v0.6.0)

**Definition of Done:**
- [ ] Zero critical bugs
- [ ] All documentation complete
- [ ] Demo video published
- [ ] Installers tested on Windows/macOS/Linux
- [ ] GitHub release created with assets
- [ ] CHANGELOG.md complete

### Milestone 6 Definition of Done

#### Functional Requirements
- [x] Auto-update system works
- [x] All 5 pages functional (Dashboard, Scanner, Inventory, Buylist, Settings)
- [x] Backup/restore works
- [x] Accessibility complete (WCAG AA)
- [x] Cloud sync stubs in place (disabled by default)

#### Technical Requirements
- [x] 100+ tests pass (unit + integration + E2E)
- [x] Code coverage ≥ 80%
- [x] Visual regression tests baseline
- [x] Performance targets met (all queries <200ms)
- [x] Bundle size <6 MB

#### Quality Gates
- [x] Full workflow test: scan → post → inventory → dashboard → export
- [x] Buy-in workflow test: add targets → scan → buy-in → inventory
- [x] Backup/restore test: backup → restore → verify
- [x] Auto-update test: download → install → health check → success

#### Release Checklist
- [x] Tag release: `v0.6.0`
- [x] Create installers (NSIS, DMG, AppImage, Deb, RPM)
- [x] Publish GitHub release
- [x] Update CHANGELOG.md
- [x] Publish demo video
- [x] Update documentation site (if exists)
- [x] Announce to beta testers

---

## Success Metrics (Demo-Ready)

### Shop Owner Acceptance Criteria
**Scenario 1: Daily Buy-In Session**
```
1. Owner opens app (startup <3s)
2. Customer brings 50 cards to sell
3. Owner enables "Buylist Mode"
4. Scans all 50 cards (<5 min)
5. System shows buy prices, owner accepts 30 cards ($200 total)
6. Owner confirms buy-in, pays customer
7. Cards added to inventory with cost basis
8. Owner closes app (data persisted)

Expected: Smooth, fast, no errors
```

**Scenario 2: Inventory Management**
```
1. Owner opens Inventory page
2. Searches for "Luffy" (results <200ms)
3. Selects 10 cards, bulk adjusts price (+10%)
4. Exports CSV for website upload
5. Imports CSV from supplier (1000 cards, <2s)
6. Reviews aging stock alerts (>90 days)

Expected: Fast, responsive, accurate
```

**Scenario 3: Dashboard Review**
```
1. Owner opens Dashboard
2. Reviews today's stats (scans, revenue, margin)
3. Checks top 10 SKUs by velocity
4. Exports dashboard data (CSV)
5. Adjusts pricing rules based on insights

Expected: Actionable insights, fast loading
```

### Technical Acceptance Criteria
- [ ] Startup time ≤ 3 seconds (cold start)
- [ ] Query time ≤ 200ms (inventory search, dashboard)
- [ ] Scanning loop ≤ 1 second (detect + identify)
- [ ] Batch post ≤ 100ms (50 cards, transaction)
- [ ] CSV import ≤ 2 seconds (1000 cards)
- [ ] Zero crashes (run 8 hours continuously)
- [ ] Zero data loss (test backup/restore)
- [ ] Memory stable (no leaks after 1 hour)

### Quality Acceptance Criteria
- [ ] All E2E tests pass (100%)
- [ ] Code coverage ≥ 80%
- [ ] Visual regression tests pass (0 differences)
- [ ] Accessibility audit passes (WCAG AA)
- [ ] Security audit passes (no vulnerabilities)
- [ ] Performance audit passes (Lighthouse score >90)

---

## Risk Mitigation

### High Risk Items
1. **Database migrations fail in production**
   - **Mitigation**: Pre-migration backup, health check, auto-rollback
   - **Test**: Corrupt database, verify rollback works

2. **Scanner breaks during refactor**
   - **Mitigation**: Feature flags, keep original code, extensive E2E tests
   - **Test**: Run scanner tests on every commit

3. **Performance degrades with large datasets**
   - **Mitigation**: Indexed queries, pagination, lazy loading
   - **Test**: Load 10,000 inventory items, verify <200ms

4. **User data loss**
   - **Mitigation**: Automatic backups, transaction safety, event sourcing
   - **Test**: Power off during batch post, verify recovery

### Medium Risk Items
1. **Multi-page navigation confuses users**
   - **Mitigation**: Clear navigation menu, keyboard shortcuts, help dialog
   - **Test**: User testing with shop owners

2. **CSV import/export issues (encoding, format)**
   - **Mitigation**: Validation, error messages, sample CSV
   - **Test**: Import malformed CSV, verify error handling

3. **Auto-update breaks on some machines**
   - **Mitigation**: Release channels (canary → beta → stable), health check
   - **Test**: Test on clean Windows/macOS/Linux installs

---

## Next Steps (Week 1 Kickoff)

**Day 1 (Monday):**
- [ ] Review milestone plan with team
- [ ] Approve architecture + schema
- [ ] Tag baseline: `v0.2.2-pre-multi-page`
- [ ] Create feature branch: `feature/database-foundation`
- [ ] Install dependencies (better-sqlite3, kysely, zod)

**Day 2 (Tuesday):**
- [ ] Configure Kysely + SQLite
- [ ] Write initial migration (001_initial_schema.ts)
- [ ] Test database initialization
- [ ] Commit: "feat: Add database initialization"

**Day 3 (Wednesday):**
- [ ] Implement EventLog service
- [ ] Add IPC handler for event publishing
- [ ] Test event log (unit tests)
- [ ] Commit: "feat: Add event log system"

**Day 4 (Thursday):**
- [ ] Configure Jest (unit tests)
- [ ] Configure Playwright (E2E tests)
- [ ] Write first integration test (database init)
- [ ] Commit: "test: Add testing infrastructure"

**Day 5 (Friday):**
- [ ] Write E2E test: scanner still works
- [ ] Run full test suite (unit + integration + E2E)
- [ ] Fix any failures
- [ ] Review week 1 progress

---

## Approval Checklist

**Before starting Week 1:**
- [ ] Architecture evolution plan approved
- [ ] Database schema approved
- [ ] Dependency plan approved
- [ ] Milestone plan approved (this document)
- [ ] Team aligned on success criteria
- [ ] Risk mitigation strategies reviewed
- [ ] Timeline agreed upon (8 weeks realistic)

**Ready to proceed?** 🚀
