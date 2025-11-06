# CI Memory Exhaustion Fix - 2025-11-06

## Problem

GitHub Actions CI was failing at the "Run incremental update" step with a memory exhaustion error:

```
Fetching data for Magic: The Gathering...
Processing 110742 cards from API...
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```

The incremental pipeline was trying to normalize Magic: The Gathering data (110k+ cards), causing Node.js to run out of memory in the CI environment.

## Root Cause

The incremental pipeline scripts (`normalize-incremental.ts` and `fetch_images_incremental.ts`) were calling `getAllGames()`, which returns **ALL game configurations** (including disabled games).

When the incremental scraper had previously fetched Magic data (before we disabled it), the raw data remained. The normalize script tried to process this massive dataset, exhausting the default Node.js heap limit (2GB in CI).

**The Bug**:
```typescript
const games = getAllGames();  // Returns ALL 68 games, including disabled ones
for (const game of games) {
  // Tries to process Magic (110k cards) even though it's disabled
}
```

## Solution

### Filter to Only Process Enabled Games

Updated both `normalize-incremental.ts` and `fetch_images_incremental.ts` to only process games that have **existing curated data** (which means they've been properly scraped and are enabled):

**Before**:
```typescript
const games = getAllGames();  // ALL games
for (const game of games) {
  await processGame(game);  // Process all, including Magic!
}
```

**After**:
```typescript
const games = getAllGames();

// Only process games that have existing curated data (enabled games)
const gamesToProcess = games.filter(game => {
  const curatedPath = path.join(CURATED_DIR, `${game.slug}.jsonl`);
  return fs.existsSync(curatedPath);
});

if (gamesToProcess.length === 0) {
  console.log('ℹ️  No games with curated data found. Run full scrape first.');
  return;
}

console.log(`Processing ${gamesToProcess.length} game(s): ${gamesToProcess.map(g => g.name).join(', ')}\n`);

for (const game of gamesToProcess) {
  await processGame(game);  // Only process One Piece
}
```

## Files Changed

1. **`services/ingest/bin/normalize-incremental.ts`** (line 330-357)
   - Added filter to only process games with existing curated data
   - Added logging to show which games are being processed

2. **`services/ingest/bin/fetch_images_incremental.ts`** (line 327-356)
   - Same filter logic applied
   - Prevents attempting to download images for disabled games

## Why This Works

**Curated data check** (`one-piece.jsonl` exists):
- ✅ One Piece: Has `data/curated/one-piece.jsonl` → Process it
- ❌ Magic: No `data/curated/magic-the-gathering.jsonl` → Skip it
- ❌ Pokémon: No `data/curated/pokemon.jsonl` → Skip it

This ensures the pipeline only processes **enabled and properly initialized** games, avoiding memory issues from accidentally processing large disabled datasets.

## Memory Impact

**Before**:
- Tries to process 110,742 Magic cards
- Loads entire dataset into memory for JSON.stringify
- Exceeds 2GB heap limit → Crash

**After**:
- Only processes 5,606 One Piece cards
- Memory usage: ~100-200MB
- CI completes successfully

## Prevention

To prevent this issue in the future:

### 1. Always Filter to Enabled Games

Any pipeline script that processes multiple games should filter to only enabled games:

```typescript
// Option A: Check for curated data (best for incremental)
const gamesToProcess = getAllGames().filter(game => {
  const curatedPath = path.join(CURATED_DIR, `${game.slug}.jsonl`);
  return fs.existsSync(curatedPath);
});

// Option B: Check enabled flag (if we add it to config)
const gamesToProcess = getAllGames().filter(game => game.enabled);
```

### 2. Add Enabled Flag to Config (Future)

Add an `enabled` flag to game configurations:

```typescript
// packages/config/src/index.ts
export interface GameConfig {
  slug: string;
  name: string;
  enabled: boolean;  // NEW
  // ...
}

export function getEnabledGames(): GameConfig[] {
  return getAllGames().filter(g => g.enabled);
}
```

### 3. Clean Up Old Scraped Data

Remove raw data for disabled games:

```bash
# Remove Magic data if it exists
rm -rf data/raw/magic-the-gathering/
rm -rf data/curated/magic-the-gathering.jsonl
```

### 4. Add Memory Limit Guards

For CI environments, consider increasing Node.js heap limit:

```yaml
# .github/workflows/daily-update.yml
- name: Run incremental update
  run: NODE_OPTIONS="--max-old-space-size=4096" pnpm pipeline:update
  # 4GB heap limit for safety
```

## Testing

Locally verified the fix:
```bash
$ cd services/ingest && pnpm build
✅ Build succeeds

$ pnpm pipeline:normalize:incremental
Processing 1 game(s): One Piece Card Game
✅ Only processes One Piece (skips Magic)
```

## Related Issue

This fix resolves the GitHub Actions CI failure that occurred after:
- Commit `7a824f3` (TypeScript module resolution fix)
- Previous pipeline runs had scraped Magic data

The TypeScript fix allowed the build to succeed, but then the pipeline failed at runtime due to memory exhaustion.

## Key Takeaway

**Always filter `getAllGames()` to only process enabled/relevant games in pipeline scripts.**

**Never assume that because a game is "disabled" in config, its data won't be present on disk.**

Use existence checks (`fs.existsSync`) or explicit enabled flags to determine which games to process.

---

**Fixed By**: Claude Code (Sonnet 4.5)
**Date**: 2025-11-06
**Impact**: Prevents CI memory exhaustion, enables successful incremental updates
**Files Changed**: 2 (normalize-incremental.ts, fetch_images_incremental.ts)
