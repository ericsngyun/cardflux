# CardFlux Dependencies & Version Control Strategy
**Date**: 2025-10-31
**Target**: Electron 39 / Node 22 LTS
**Package Manager**: pnpm 8.x

---

## Core Dependencies (Production)

### Electron & Node
```json
{
  "electron": "^39.0.0",
  "node": "22.11.0"
}
```
**Rationale:**
- Electron 39 = latest stable (security patches, performance)
- Node 22 = LTS with native SQLite support (`node:sqlite`)
- Chromium 132 (modern web APIs, good performance)

---

### Database (SQLite)

#### Option A: `better-sqlite3` (RECOMMENDED)
```json
{
  "better-sqlite3": "^11.5.0"
}
```
**Pros:**
- ✅ Synchronous API (simpler code, no async/await overhead)
- ✅ Fastest SQLite binding for Node
- ✅ Pre-built binaries (no compilation on install)
- ✅ Mature (6+ years, battle-tested)
- ✅ WAL mode support
- ✅ Prepared statements (SQL injection safe)

**Cons:**
- ⚠️ Native dependency (rebuilds needed for Electron)
- ⚠️ ~2 MB binary size

**Electron Compatibility:**
```bash
# Rebuild for Electron (automated in package.json)
pnpm add -D @electron/rebuild
# postinstall script handles rebuild
```

#### Option B: `node:sqlite` (Native Module)
```json
{
  "node": ">=22.5.0"
}
```
**Pros:**
- ✅ No external dependencies
- ✅ Built into Node 22.5+
- ✅ No rebuild needed

**Cons:**
- ⚠️ Experimental API (may change)
- ⚠️ Limited features vs better-sqlite3
- ⚠️ Requires Node 22.5+ (Electron 39 has Node 22.11 ✅)

**Recommendation**: Use `better-sqlite3` for stability and features. Switch to `node:sqlite` in 2026 when stable.

---

### Migration Tool: Kysely
```json
{
  "kysely": "^0.27.4"
}
```
**Rationale:**
- ✅ Type-safe query builder (TypeScript first-class)
- ✅ Migration system built-in
- ✅ Works with better-sqlite3
- ✅ No ORM overhead (raw SQL control)
- ✅ Excellent for event sourcing patterns

**Alternative Considered**: Knex (older, less type-safe)

**Usage:**
```typescript
import { Kysely, SqliteDialect } from 'kysely';
import Database from 'better-sqlite3';

const db = new Kysely<DatabaseSchema>({
  dialect: new SqliteDialect({
    database: new Database('cardflux.db'),
  }),
});

// Type-safe queries
const cards = await db
  .selectFrom('cards')
  .where('tcg_game', '=', 'one-piece')
  .selectAll()
  .execute();
```

---

### State Management: Zustand
```json
{
  "zustand": "^4.5.0"
}
```
**Rationale:**
- ✅ Lightweight (1 KB gzipped)
- ✅ No boilerplate (vs Redux)
- ✅ React 18 compatible
- ✅ DevTools support
- ✅ Perfect for multi-page app state

**Usage:**
```typescript
import create from 'zustand';

interface AppStore {
  currentBatch: Batch | null;
  inventory: InventoryItem[];
  setCurrentBatch: (batch: Batch) => void;
}

export const useStore = create<AppStore>((set) => ({
  currentBatch: null,
  inventory: [],
  setCurrentBatch: (batch) => set({ currentBatch: batch }),
}));
```

**Why Not Redux?** Too much boilerplate for simple state needs

---

### Routing: React Router v6
```json
{
  "react-router-dom": "^6.28.0"
}
```
**Rationale:**
- ✅ Industry standard
- ✅ v6 = simplified API
- ✅ Lazy loading built-in
- ✅ TypeScript support

**Usage:**
```typescript
import { createHashRouter, RouterProvider } from 'react-router-dom';

const router = createHashRouter([
  { path: '/', element: <DashboardPage /> },
  { path: '/scanner', element: <ScannerPage /> },
  { path: '/inventory', element: <InventoryPage /> },
  { path: '/buylist', element: <BuylistPage /> },
  { path: '/settings', element: <SettingsPage /> },
]);

<RouterProvider router={router} />;
```

**Why Hash Router?** Works with `file://` protocol in Electron (no server needed)

---

### Validation: Zod
```json
{
  "zod": "^3.23.8"
}
```
**Rationale:**
- ✅ Runtime type checking (security for IPC)
- ✅ TypeScript inference
- ✅ Excellent error messages
- ✅ Lightweight

**Usage:**
```typescript
import { z } from 'zod';

// IPC payload validation
const ScannerPayload = z.object({
  imagePath: z.string().min(1),
  options: z.object({
    topK: z.number().min(1).max(100),
    confidenceThreshold: z.number().min(0).max(1),
  }).optional(),
});

// Validate in IPC handler
ipcMain.handle('scanner:identify', async (event, payload) => {
  const validated = ScannerPayload.parse(payload); // Throws if invalid
  // ... safe to use validated.imagePath
});
```

---

### Storage: electron-store
```json
{
  "electron-store": "^10.0.0"
}
```
**Rationale:**
- ✅ Simple key-value store for settings
- ✅ JSON schema validation
- ✅ Encryption support
- ✅ Observable (watch for changes)

**Usage:**
```typescript
import Store from 'electron-store';

interface StoreSchema {
  theme: 'dark' | 'light';
  featureFlags: FeatureFlags;
  scannerConfig: ScannerConfig;
}

const store = new Store<StoreSchema>({
  defaults: {
    theme: 'dark',
    featureFlags: { cloudSync: false },
  },
  encryptionKey: 'obfuscation', // Not true security, just obfuscation
});

// Get/set
const theme = store.get('theme');
store.set('theme', 'light');
```

**Why Not Database?** Settings are device-specific (not synced), fast access needed

---

### Logging: winston
```json
{
  "winston": "^3.15.0"
}
```
**Rationale:**
- ✅ Flexible (file, console, remote transports)
- ✅ Log levels (debug, info, warn, error)
- ✅ JSON formatting
- ✅ Rotation built-in

**Usage:**
```typescript
import winston from 'winston';

export const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({
      filename: 'cardflux.log',
      maxsize: 10 * 1024 * 1024, // 10 MB
      maxFiles: 7,
    }),
  ],
});
```

**Already Implemented**: Custom logger in `apps/desktop/src/main/core/logger.ts` (keep it, works great)

---

### UI Components: Radix UI
```json
{
  "@radix-ui/react-dialog": "^1.1.2",
  "@radix-ui/react-select": "^2.1.2",
  "@radix-ui/react-tabs": "^1.1.1",
  "@radix-ui/react-toast": "^1.2.2"
}
```
**Rationale:**
- ✅ Headless components (full style control)
- ✅ Accessibility built-in (ARIA, keyboard nav)
- ✅ No CSS framework lock-in
- ✅ Tree-shakeable (only import what you use)

**Why Not Material UI?** Too heavy (~500 KB), opinionated styling

---

### Charts: Recharts
```json
{
  "recharts": "^2.12.7"
}
```
**Rationale:**
- ✅ React-first (composable)
- ✅ Responsive
- ✅ Built on D3 (powerful)
- ✅ TypeScript support

**Usage (Dashboard):**
```typescript
import { LineChart, Line, XAxis, YAxis } from 'recharts';

<LineChart data={dailyStats}>
  <XAxis dataKey="date" />
  <YAxis />
  <Line type="monotone" dataKey="revenue" stroke="#8884d8" />
</LineChart>
```

---

### CSV: papaparse
```json
{
  "papaparse": "^5.4.1"
}
```
**Rationale:**
- ✅ CSV parsing + generation
- ✅ Large file support (streaming)
- ✅ Type detection

**Usage:**
```typescript
import Papa from 'papaparse';

// Import CSV
const result = Papa.parse(csvString, { header: true });
// result.data = [{ name: '...', price: '...' }, ...]

// Export CSV
const csv = Papa.unparse(inventoryData);
fs.writeFileSync('inventory.csv', csv);
```

---

## Development Dependencies

### TypeScript
```json
{
  "typescript": "^5.6.3",
  "@types/node": "^22.9.0",
  "@types/react": "^18.3.12",
  "@types/react-dom": "^18.3.1",
  "@types/better-sqlite3": "^7.6.12"
}
```

### Build Tools
```json
{
  "webpack": "^5.102.0",
  "webpack-cli": "^5.1.4",
  "ts-loader": "^9.5.1",
  "electron-builder": "^25.1.8"
}
```

### Testing
```json
{
  "jest": "^29.7.0",
  "@types/jest": "^29.5.14",
  "playwright": "^1.49.0",
  "@playwright/test": "^1.49.0",
  "ts-jest": "^29.2.5"
}
```

### Linting & Formatting
```json
{
  "eslint": "^8.57.1",
  "@typescript-eslint/parser": "^7.18.0",
  "@typescript-eslint/eslint-plugin": "^7.18.0",
  "prettier": "^3.3.3"
}
```

### Electron Tools
```json
{
  "@electron/rebuild": "^3.7.0",
  "electron-devtools-installer": "^3.2.0",
  "electron-updater": "^6.3.9"
}
```

---

## Complete package.json
```json
{
  "name": "@cardflux/desktop",
  "version": "0.3.0",
  "description": "CardFlux - TCG Shop Management",
  "main": "dist/main/index.js",
  "scripts": {
    "start": "electron .",
    "dev": "concurrently \"pnpm build:watch\" \"pnpm start\"",
    "build": "pnpm build:main && pnpm build:renderer",
    "build:main": "webpack --config webpack.main.config.js",
    "build:renderer": "webpack --config webpack.renderer.config.js",
    "build:watch": "concurrently \"pnpm build:main --watch\" \"pnpm build:renderer --watch\"",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test",
    "migrate": "kysely migrate:latest",
    "migrate:down": "kysely migrate:down",
    "migrate:make": "kysely migrate:make",
    "package": "electron-builder",
    "postinstall": "electron-rebuild"
  },
  "dependencies": {
    "better-sqlite3": "^11.5.0",
    "kysely": "^0.27.4",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^4.5.0",
    "zod": "^3.23.8",
    "electron-store": "^10.0.0",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-select": "^2.1.2",
    "@radix-ui/react-tabs": "^1.1.1",
    "@radix-ui/react-toast": "^1.2.2",
    "recharts": "^2.12.7",
    "papaparse": "^5.4.1"
  },
  "devDependencies": {
    "electron": "^39.0.0",
    "typescript": "^5.6.3",
    "@types/node": "^22.9.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/better-sqlite3": "^7.6.12",
    "@types/papaparse": "^5.3.15",
    "webpack": "^5.102.0",
    "webpack-cli": "^5.1.4",
    "ts-loader": "^9.5.1",
    "electron-builder": "^25.1.8",
    "@electron/rebuild": "^3.7.0",
    "jest": "^29.7.0",
    "@types/jest": "^29.5.14",
    "ts-jest": "^29.2.5",
    "playwright": "^1.49.0",
    "@playwright/test": "^1.49.0",
    "eslint": "^8.57.1",
    "@typescript-eslint/parser": "^7.18.0",
    "@typescript-eslint/eslint-plugin": "^7.18.0",
    "prettier": "^3.3.3",
    "concurrently": "^9.1.0"
  },
  "engines": {
    "node": ">=22.0.0",
    "pnpm": ">=8.0.0"
  }
}
```

---

## Version Control Strategy

### Branch Structure
```
main              # Production-ready code (v0.2.2)
  ├── feature/database-foundation    # Week 1-2
  ├── feature/inventory-page         # Week 3-4
  ├── feature/dashboard              # Week 5
  ├── feature/buylist                # Week 6
  ├── feature/settings-polish        # Week 7
  └── feature/cloud-ready            # Week 8
```

### Tagging Strategy
```bash
# Tag stable releases
git tag -a v0.2.2 -m "Scanner MVP (pre-multi-page)"  # Baseline
git tag -a v0.3.0 -m "Multi-page foundation + database"
git tag -a v0.4.0 -m "Inventory management"
git tag -a v0.5.0 -m "Dashboard + buylist"
git tag -a v0.6.0 -m "Production-ready multi-page"

# Tag before risky changes
git tag -a v0.2.2-pre-migration -m "Before database migration"
```

### Commit Conventions (Conventional Commits)
```bash
feat: Add database schema and migrations
fix: Correct batch posting transaction
refactor: Extract IPC handlers to separate files
test: Add integration tests for batch posting
docs: Update architecture diagrams
chore: Update dependencies
perf: Optimize dashboard query performance
```

### Branch Protection Rules
```yaml
# main branch
- Require pull request reviews (1 approver)
- Require status checks (CI tests pass)
- Require branches to be up to date
- No force push
- No delete

# feature/* branches
- Allow force push (for rebasing)
- Delete after merge
```

### Workflow
```bash
# Week 1: Database Foundation
git checkout -b feature/database-foundation

# Incremental commits (build working state)
git commit -m "feat: Add SQLite database initialization"
git commit -m "feat: Add Kysely migration system"
git commit -m "test: Add database integration tests"
git commit -m "feat: Add event log publisher"

# Merge to main when tests pass
git checkout main
git merge --no-ff feature/database-foundation
git tag -a v0.3.0 -m "Multi-page foundation"
git push origin main --tags

# Week 2: Inventory Page
git checkout -b feature/inventory-page
# ... repeat
```

### Safety Net (Revert Strategy)
```bash
# If feature branch breaks something
git checkout main
git revert <bad-commit-hash>
git push origin main

# If need to rollback to previous tag
git checkout v0.2.2
git checkout -b hotfix/rollback-to-scanner-only
# ... fix critical issue
git checkout main
git merge hotfix/rollback-to-scanner-only
git tag -a v0.2.3 -m "Hotfix: Rollback to scanner-only"
```

### Pre-Merge Checklist
```markdown
## Feature Branch Merge Checklist

- [ ] All tests pass (unit + integration + e2e)
- [ ] TypeScript compiles with no errors
- [ ] Lint and format clean
- [ ] Scanner page still works (regression test)
- [ ] Database migrations tested (up + down)
- [ ] Documentation updated (if architecture changed)
- [ ] CHANGELOG.md updated
- [ ] Tag created (if release)
- [ ] Backup created before merge (safety)
```

---

## CI/CD Pipeline (GitHub Actions)

### .github/workflows/ci.yml
```yaml
name: CI

on:
  push:
    branches: [main, feature/*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [22]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Typecheck
        run: pnpm typecheck

      - name: Lint
        run: pnpm lint

      - name: Unit tests
        run: pnpm test

      - name: Build
        run: pnpm build

      - name: E2E tests
        run: pnpm test:e2e

      - name: Upload artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.os }}
          path: test-results/

  release:
    needs: test
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Setup pnpm
        uses: pnpm/action-setup@v2

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Package app
        run: pnpm package

      - name: Upload release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*.{exe,dmg,AppImage,deb,rpm}
```

---

## Dependency Security

### Audit Schedule
```bash
# Run weekly
pnpm audit

# Update dependencies monthly (test first)
pnpm update --interactive --latest
```

### Known Vulnerabilities (As of 2025-10-31)
- None (all dependencies up to date)

### Lockfile
```bash
# Commit pnpm-lock.yaml (deterministic builds)
git add pnpm-lock.yaml
git commit -m "chore: Update lockfile"
```

---

## Bundle Size Targets

### Current (v0.2.2)
- main.js: 682 KB
- react-vendor.js: 2.77 MB
- Total: ~3.5 MB (acceptable for desktop app)

### Target (v0.6.0)
- main.js: <1 MB (with code splitting)
- react-vendor.js: 2.77 MB (unchanged)
- database: +2 MB (better-sqlite3 binary)
- **Total: <6 MB** (still acceptable)

### Optimization Strategies
1. **Code splitting**: Dynamic imports for routes
2. **Tree shaking**: Radix UI (import only used components)
3. **Externalize**: Electron APIs (don't bundle)
4. **Minify**: Production builds with Terser

---

## Compatibility Matrix

| Dependency | Version | Electron 39 | Node 22 | Windows | macOS | Linux |
|------------|---------|-------------|---------|---------|-------|-------|
| better-sqlite3 | 11.5.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| kysely | 0.27.4 | ✅ | ✅ | ✅ | ✅ | ✅ |
| React | 18.3.1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| zustand | 4.5.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| zod | 3.23.8 | ✅ | ✅ | ✅ | ✅ | ✅ |
| electron-store | 10.0.0 | ✅ | ✅ | ✅ | ✅ | ✅ |

**No platform-specific dependencies** = Easy cross-platform support

---

## Next Steps

1. **Install dependencies** (Week 1, Day 1)
   ```bash
   cd apps/desktop
   pnpm add better-sqlite3 kysely zustand zod react-router-dom
   pnpm add -D @types/better-sqlite3 ts-jest playwright
   ```

2. **Configure Kysely** (Week 1, Day 1)
3. **Write first migration** (Week 1, Day 2)
4. **Test database init** (Week 1, Day 2)

**Ready to start Phase 1 implementation?**
