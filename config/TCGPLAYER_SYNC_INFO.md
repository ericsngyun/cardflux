# TCGPlayer API Sync Configuration

## TCGPlayer Update Schedule

**TCGPlayer (tcgcsv.com) API Update Time:**
- **Daily at 1:00 PM PDT (Pacific Daylight Time)**
- This is when they refresh their database with:
  - New card releases
  - Updated market prices
  - Inventory changes
  - Set releases

## Our Update Schedule

**CardFlux Update Time:**
- **Daily at 2:00 PM PDT (Pacific)**
- **1 hour buffer** after TCGPlayer updates
- Ensures we get the freshest data

### Configuration

```json
{
  "schedule": {
    "timezone": "America/Los_Angeles",
    "dailyUpdateTime": "14:00"  // 2 PM PDT
  }
}
```

## Time Zone Reference

| Timezone | Update Time | TCGPlayer Buffer |
|----------|-------------|------------------|
| **PDT (Pacific Daylight)** | 2:00 PM | +1 hour |
| **PST (Pacific Standard)** | 2:00 PM | +1 hour |
| **MDT (Mountain)** | 3:00 PM | +2 hours |
| **CDT (Central)** | 4:00 PM | +3 hours |
| **EDT (Eastern)** | 5:00 PM | +4 hours |

**Note:** Using `America/Los_Angeles` automatically handles PDT/PST transitions.

## Why 2 PM PDT?

1. **Fresh Data:** TCGPlayer finishes updating by 1 PM PDT
2. **Safety Buffer:** 1-hour window for TCGPlayer to complete
3. **Business Hours:** Most shops are open, computers are on
4. **Price Changes:** Same-day price updates reflected in shop scanner

## What Gets Updated

### Daily (2 PM PDT)
- ✅ New card releases
- ✅ Market price updates (all cards)
- ✅ New product listings
- ✅ Rarity changes
- ✅ Set information

### Our Process (2:00 PM - 2:30 PM PDT)
```
2:00 PM - Start update
2:01 PM - Scrape TCGPlayer API (new data)
2:05 PM - Download new card images
2:12 PM - Generate embeddings for new cards
2:15 PM - Rebuild FAISS index
2:18 PM - Update complete
```

**Total Duration:** ~15-20 minutes

## Benefits of This Schedule

### For Card Shops
- **Price Updates:** New prices available same day
- **New Releases:** New cards searchable within hours of release
- **Business Hours:** Update runs while shop is open
- **Computer Available:** Desktop computers typically on during shop hours

### Timing Example
```
1:00 PM PDT - TCGPlayer updates their database
              (New One Piece set released)

2:00 PM PDT - CardFlux starts update
2:18 PM PDT - CardFlux update complete
              (New set now scannable!)

2:30 PM PDT - Customer walks in with new cards
              ✅ Cards identify correctly
              ✅ Prices are fresh (updated 1.5 hours ago)
```

## What If Computer Is Off?

**Windows Task Scheduler handles this:**

### Scenario 1: Shop Closed at 2 PM
```
2:00 PM - Update scheduled (shop closed, computer off)
9:00 AM next day - Computer boots
9:01 AM - Task sees missed schedule → Runs immediately
9:20 AM - Update complete
```

**Result:** 19 hours old data (still very fresh)

### Scenario 2: Shop Open at 2 PM
```
2:00 PM - Update scheduled (computer on)
2:00 PM - Update starts immediately
2:18 PM - Update complete
```

**Result:** 1-hour old data (optimal!)

## Adjusting the Time

If you want to change when updates run:

**Edit `config/update-scheduler.json`:**
```json
{
  "schedule": {
    "dailyUpdateTime": "15:00"  // Change to 3 PM PDT
  }
}
```

**Then restart the scheduled task:**
```powershell
# Windows
Stop-ScheduledTask -TaskName "CardFlux-DailyUpdate"
Start-ScheduledTask -TaskName "CardFlux-DailyUpdate"

# Or just reinstall
cd scripts/automation
.\setup-windows-task.ps1
```

## Monitoring

Check if updates are running on schedule:

```bash
# View update history
pnpm update:monitor

# See last update time
pnpm update:logs
```

**Expected output:**
```
Last Update: 2025-10-13 14:18:32 PDT (2h ago)
Next Update: 2025-10-14 14:00:00 PDT (in 21h 42m)
```

## Daylight Saving Time

**Using `America/Los_Angeles` timezone:**
- ✅ Automatically handles PDT ↔ PST transitions
- ✅ Spring forward: Update stays at 2 PM PDT
- ✅ Fall back: Update stays at 2 PM PST
- ✅ Always 1 hour after TCGPlayer (1 PM PDT/PST)

**No manual adjustment needed!**

## Production Checklist

Before deploying:

- [x] Timezone set to `America/Los_Angeles`
- [x] Update time set to `14:00` (2 PM)
- [x] Buffer of 1 hour after TCGPlayer update (1 PM)
- [x] Scheduled task installed
- [x] Test run completed successfully
- [ ] Monitor first few days to verify timing

## Support

If you need to change the sync timing:
1. Edit `config/update-scheduler.json`
2. Adjust `dailyUpdateTime` (24-hour format)
3. Reinstall scheduled task: `.\setup-windows-task.ps1`
4. Test: `pnpm update:now`

---

**Summary:** CardFlux updates daily at 2 PM PDT, 1 hour after TCGPlayer's 1 PM PDT update, ensuring fresh prices and new cards are available same-day.
