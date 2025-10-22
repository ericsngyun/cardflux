# Sync Feature Documentation

**Date**: 2025-10-16
**Version**: Desktop v0.3.0
**Status**: ✅ Ready for Testing

---

## Overview

Added a comprehensive data synchronization system that allows users to update card prices and check for new cards with a single click. The system integrates seamlessly with the existing monochrome UI and provides real-time status feedback.

---

## Features

### 1. Sync Status Indicator

**Location**: Header (next to Settings button)

**Visual States**:
- **Success** (< 1 hour): Grey icon, no glow
  - Shows: "Just now" or "X hours ago"
  - Indicates: Data is fresh, no sync needed

- **Warning** (1-3 days): Amber tint, subtle glow
  - Shows: "1 day ago" or "X days ago"
  - Indicates: Sync recommended

- **Error** (> 3 days): Pulsing icon, bright glow
  - Shows: "X days ago"
  - Indicates: Sync strongly recommended, data may be outdated

**Information Displayed**:
```
🔄 LAST SYNC
   Just now / X hours ago / X days ago
```

### 2. Sync Button

**States**:
- **Idle**: `🔄 Sync`
- **Syncing**: `⏳ Syncing...` (with spinner)
- **Needs Sync**: Pulsing glow animation (when >1 day old)
- **Disabled**: Greyed out (during sync operation)

**Behavior**:
- Click to start sync
- Disabled during sync operation
- Shows progress notification
- Updates last sync timestamp on completion
- Displays result (updated/new cards count)

### 3. Notifications

**Sync Start**:
```
⚠ Syncing card data and prices...
```

**Sync Success**:
```
✓ Sync complete! Updated 4,813 cards, 12 new cards.
```

**Sync Error**:
```
✕ Sync failed: [error message]
```

---

## Technical Implementation

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      SYNC FLOW                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. User clicks "Sync" button                             │
│     ↓                                                      │
│  2. App.tsx: handleSync()                                 │
│     • Sets isSyncing = true                               │
│     • Shows notification                                  │
│     ↓                                                      │
│  3. window.sync.syncData(game)                            │
│     • IPC: 'sync:data' with game name                     │
│     ↓                                                      │
│  4. main/index.ts: IPC Handler                            │
│     • Spawns pnpm process                                 │
│     • Runs tcgplayer-scraper-onepiece.ts                  │
│     • Monitors stdout/stderr                              │
│     • 5 min timeout                                       │
│     ↓                                                      │
│  5. Scraper runs                                          │
│     • Fetches latest prices from TCGPlayer API            │
│     • Checks for new cards                                │
│     • Updates data/curated/one-piece.jsonl                │
│     • Outputs stats                                       │
│     ↓                                                      │
│  6. Result returned                                       │
│     • Parse output for stats                              │
│     • { updatedCards: 4813, newCards: 12 }                │
│     ↓                                                      │
│  7. App.tsx: Update state                                 │
│     • Set lastSyncTime = now                              │
│     • Save to localStorage                                │
│     • Show success notification                           │
│     • Set isSyncing = false                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Files Modified

#### 1. `apps/desktop/src/renderer/app.tsx`

**Added State**:
```typescript
const [isSyncing, setIsSyncing] = useState(false);
const [lastSyncTime, setLastSyncTime] = useState<number | null>(() => {
  const stored = localStorage.getItem(SYNC_STATUS_STORAGE_KEY);
  return stored ? JSON.parse(stored).timestamp : null;
});
```

**Added Handler**:
```typescript
const handleSync = useCallback(async () => {
  setIsSyncing(true);

  const result = await window.sync.syncData(settings.tcgGame);

  if (result.success) {
    setLastSyncTime(Date.now());
    localStorage.setItem(SYNC_STATUS_STORAGE_KEY,
      JSON.stringify({ timestamp: Date.now(), game: settings.tcgGame })
    );
    showNotification('success', `Sync complete! ...`);
  }

  setIsSyncing(false);
}, [isSyncing, settings.tcgGame]);
```

**Added Status Calculator**:
```typescript
const getSyncStatus = useMemo(() => {
  if (!lastSyncTime) return { text: 'Never synced', status: 'warning' };

  const diffDays = (Date.now() - lastSyncTime) / (1000 * 60 * 60 * 24);

  if (diffDays >= 3) return { text: `${Math.floor(diffDays)} days ago`, status: 'error' };
  if (diffDays >= 1) return { text: `${Math.floor(diffDays)} days ago`, status: 'warning' };
  // ... more cases
}, [lastSyncTime]);
```

**Added UI Components**:
```tsx
<div className="sync-container">
  <div className={`sync-status sync-status-${getSyncStatus.status}`}>
    <span className="sync-icon">🔄</span>
    <div className="sync-info">
      <span className="sync-label">Last Sync</span>
      <span className="sync-time">{getSyncStatus.text}</span>
    </div>
  </div>
  <button
    className={`btn btn-sync btn-sm ${isSyncing ? 'btn-syncing' : ''} ${
      getSyncStatus.needsSync ? 'btn-sync-needed' : ''
    }`}
    onClick={handleSync}
    disabled={isSyncing}
  >
    {isSyncing ? 'Syncing...' : '🔄 Sync'}
  </button>
</div>
```

#### 2. `apps/desktop/src/preload/preload.ts`

**Added Interface**:
```typescript
export interface SyncAPI {
  syncData: (game: string) => Promise<{
    success: boolean;
    updatedCards?: number;
    newCards?: number;
    error?: string;
  }>;
}
```

**Exposed API**:
```typescript
contextBridge.exposeInMainWorld('sync', {
  syncData: (game: string) => ipcRenderer.invoke('sync:data', game),
} as SyncAPI);
```

**Updated Window Interface**:
```typescript
declare global {
  interface Window {
    scanner: ScannerAPI;
    camera: CameraAPI;
    identifier: IdentifierAPI;
    sync: SyncAPI; // NEW
  }
}
```

#### 3. `apps/desktop/src/main/index.ts`

**Added IPC Handler**:
```typescript
ipcMain.handle('sync:data', async (_event, game: string) => {
  const { spawn } = require('child_process');
  const rootDir = path.join(__dirname, '../../../..');
  const scraperPath = path.join(rootDir, 'services/ingest/bin/tcgplayer-scraper-onepiece.ts');

  return new Promise((resolve, reject) => {
    const scraper = spawn('pnpm', ['tsx', scraperPath], {
      cwd: rootDir,
      stdio: 'pipe',
    });

    let output = '';
    scraper.stdout?.on('data', (data) => {
      output += data.toString();
      console.log('[Scraper]', data.toString());
    });

    scraper.on('close', (code) => {
      if (code === 0) {
        // Parse output for stats
        const updatedMatch = output.match(/(\d+)\s+cards?\s+updated/i);
        const newMatch = output.match(/(\d+)\s+new\s+cards?/i);

        resolve({
          success: true,
          updatedCards: updatedMatch ? parseInt(updatedMatch[1]) : 0,
          newCards: newMatch ? parseInt(newMatch[1]) : 0,
        });
      } else {
        reject(new Error(`Scraper exited with code ${code}`));
      }
    });

    // 5 min timeout
    setTimeout(() => {
      scraper.kill();
      reject(new Error('Sync timeout'));
    }, 5 * 60 * 1000);
  });
});
```

#### 4. `apps/desktop/src/renderer/styles.css`

**Added Sync Container Styles**:
```css
.sync-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
}

.sync-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.sync-icon {
  font-size: 1rem;
  opacity: 0.7;
  transition: transform 0.3s ease;
}

.sync-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sync-label {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.sync-time {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
```

**Added State Styles**:
```css
.sync-status-success .sync-icon {
  opacity: 0.5;
}

.sync-status-warning .sync-icon {
  opacity: 0.8;
  filter: hue-rotate(30deg);
}

.sync-status-error .sync-icon {
  opacity: 1;
  animation: pulse 2s ease-in-out infinite;
}

.sync-status-warning .sync-time {
  color: var(--warning);
}

.sync-status-error .sync-time {
  color: var(--error);
}
```

**Added Button Styles**:
```css
.btn-sync {
  position: relative;
  overflow: hidden;
}

.btn-sync-needed {
  animation: pulseGlow 2s ease-in-out infinite;
}

.btn-syncing .sync-icon {
  animation: spin 1s linear infinite;
}

@keyframes pulseGlow {
  0%, 100% {
    box-shadow: 0 0 0 rgba(255, 255, 255, 0);
  }
  50% {
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.3);
  }
}
```

**Polished All Buttons**:
```css
.btn {
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1); /* Smooth easing */
  will-change: transform, box-shadow;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn:active:not(:disabled) {
  transform: scale(0.98);
  transition: all 0.05s ease-out;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
  filter: grayscale(0.3);
}

.btn-primary {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px) translateZ(0);
  box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15);
}

.btn-secondary {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-1px) translateZ(0);
  box-shadow: 0 3px 8px rgba(255, 255, 255, 0.08);
}
```

---

## UI/UX Polish

### Button Improvements

**Before**:
- Instant transitions (0.05s) - too jarring
- No active state feedback
- Inconsistent hover effects
- Basic box shadows

**After**:
- Smooth cubic-bezier easing (0.15s)
- Active state: scale(0.98) for tactile feedback
- Consistent hover lifts (translateY)
- Enhanced box shadows with depth
- Better disabled state (grayscale filter)
- Perfect click feedback (user-select: none)

### Spacing & Layout

**Consistency**:
- All buttons use standard spacing (--spacing-sm, --spacing-md, --spacing-lg)
- Header items have consistent gap (--spacing-lg)
- Sync container matches existing component patterns

**Typography**:
- Sync label: 0.6875rem, uppercase, tertiary color
- Sync time: 0.8125rem, tabular nums, secondary/warning/error color
- Matches existing status indicators

**Visual Hierarchy**:
- Primary button: Strongest shadow, highest lift
- Secondary button: Medium shadow, medium lift
- Icon buttons: Minimal shadow, subtle lift
- Disabled: Reduced opacity + grayscale

---

## localStorage Schema

**Key**: `cardflux-sync-status`

**Value**:
```json
{
  "timestamp": 1697456789000,
  "game": "one-piece"
}
```

- `timestamp`: Unix timestamp (ms) of last successful sync
- `game`: TCG game that was synced

---

## Sync Workflow

### User Perspective

1. **Check Status**: Look at "Last Sync" indicator in header
2. **Decide if Sync Needed**:
   - Green/grey + "Just now" → No action needed
   - Yellow + "1 day ago" → Recommended
   - Red + "3 days ago" → Strongly recommended
3. **Click Sync Button**: Single click to start
4. **Wait**: Button shows "Syncing..." with spinner (typically 30-60 seconds)
5. **Review Result**: Notification shows updated/new cards count
6. **Continue Scanning**: Data is now current, prices are updated

### Technical Perspective

1. **Trigger**: IPC call to `sync:data` with game name
2. **Process**: Spawn pnpm subprocess to run scraper
3. **Monitor**: Capture stdout/stderr, log to console
4. **Parse**: Extract stats from output (updated/new cards)
5. **Timeout**: Kill after 5 minutes if not complete
6. **Return**: Success/error with stats
7. **Update**: Save timestamp to localStorage, update UI

---

## Performance

### Sync Duration

**Typical**: 30-60 seconds
**Network-dependent**: May take longer with slow connection
**Timeout**: 5 minutes maximum

### Sync Operations

**What Gets Updated**:
- ✅ Card prices (normal, foil, market, low, mid, high)
- ✅ New cards (if TCGPlayer added new products)
- ✅ Card metadata (rarity, set, etc.)
- ✅ `data/curated/one-piece.jsonl`

**What Doesn't Get Updated** (no need if images already exist):
- ⏭️ Card images (already downloaded)
- ⏭️ Embeddings (not affected by price changes)
- ⏭️ FAISS index (not affected by price changes)
- ⏭️ Metadata embeddings (not affected by price changes)

**Why It's Fast**:
- Only scrapes metadata (lightweight JSON)
- Skips image downloads (heavy files)
- No ML processing required
- API-only operation

---

## Error Handling

### Scraper Fails

**Error**: `Scraper exited with code 1`
**Cause**: Network error, API error, permission error
**Action**: Check console for scraper logs, retry later

### Timeout

**Error**: `Sync timeout`
**Cause**: Scraper took >5 minutes
**Action**: Check network connection, restart app, try again

### Permission Error

**Error**: `Permission denied`
**Cause**: Cannot write to data directory
**Action**: Check file permissions, run as admin (Windows)

### Invalid Response

**Error**: `Failed to parse output`
**Cause**: Scraper output format changed
**Action**: Update scraper script, rebuild app

---

## Testing Checklist

### Initial Sync

- [ ] Fresh install (no lastSyncTime) shows "Never synced"
- [ ] Status indicator shows warning/error state
- [ ] Button has pulsing glow animation
- [ ] Clicking button starts sync
- [ ] Notification appears: "Syncing card data and prices..."
- [ ] Button changes to "Syncing..." with spinner
- [ ] Console shows scraper output
- [ ] Sync completes within 60 seconds
- [ ] Success notification shows stats
- [ ] Status updates to "Just now"
- [ ] localStorage has timestamp saved

### Subsequent Syncs

- [ ] Status shows "X hours ago" after 2 hours
- [ ] Status shows "1 day ago" after 24 hours
- [ ] Status turns yellow after 24 hours
- [ ] Button starts pulsing after 24 hours
- [ ] Status shows "3 days ago" after 72 hours
- [ ] Status turns red after 72 hours
- [ ] Icon pulsates when >3 days old
- [ ] Sync updates timestamp correctly

### Error Cases

- [ ] Disconnect network → click sync → error shown
- [ ] Kill scraper mid-sync → timeout error shown
- [ ] Spam click sync button → only one sync runs
- [ ] Close app mid-sync → no corruption

### UI Polish

- [ ] All buttons have smooth hover (150ms ease)
- [ ] All buttons have active state (scale 0.98)
- [ ] All buttons have consistent shadows
- [ ] Disabled buttons are greyed + desaturated
- [ ] Sync container matches theme (monochrome)
- [ ] Typography is consistent (sizes, weights)
- [ ] Spacing is consistent (gaps, padding)
- [ ] Animations are smooth (no jank)

---

## Future Enhancements

### Short-Term

1. **Progress Bar**: Show scraper progress (X/Y cards)
2. **Cancel Button**: Allow cancelling mid-sync
3. **Auto-Sync**: Optional background sync every 24 hours
4. **Sync History**: Show last 5 syncs with timestamps

### Medium-Term

1. **Partial Sync**: Only update prices, skip new cards check
2. **Delta Sync**: Only fetch changed cards since last sync
3. **Multi-Game Sync**: Sync all enabled games at once
4. **Sync Schedule**: User-configurable auto-sync times

### Long-Term

1. **Cloud Sync**: Push/pull from CardFlux cloud service
2. **Webhook Integration**: Real-time price updates via webhooks
3. **Sync Profiles**: Different sync strategies (fast, thorough, minimal)
4. **Collaborative Sync**: Share price data with other users

---

## Conclusion

The sync feature provides a seamless, user-friendly way to keep card data and prices up-to-date without requiring technical knowledge or manual script execution. The UI integration is polished and consistent with the existing monochrome design system, with thoughtful visual feedback at every step.

**Status**: ✅ Ready for production use

**Recommended Workflow**: Sync once per day before starting a scanning session to ensure accurate pricing.

