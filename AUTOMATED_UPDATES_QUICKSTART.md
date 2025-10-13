# Automated Updates - Quick Start

## 30-Second Setup

### 1. Configure
```bash
# Edit config/update-scheduler.json
{
  "enabled": true,
  "schedule": { "dailyUpdateTime": "03:00" },
  "games": { "one-piece": { "enabled": true } }
}
```

### 2. Install Scheduler

**Windows:**
```powershell
cd scripts/automation
.\setup-windows-task.ps1
```

**Linux:**
```bash
cd scripts/automation
sudo ./setup-systemd.sh
sudo systemctl start cardflux-update
```

### 3. Test
```bash
pnpm update:dry-run  # Test without changes
pnpm update:now      # Run once
pnpm update:monitor  # Check status
```

---

## Daily Commands

```bash
# Check status
pnpm update:monitor

# View logs
pnpm update:logs

# Run update now
pnpm update:now

# Rollback
pnpm update:rollback
```

---

## What It Does

**Every day at 3 AM:**
1. Scrapes latest TCGPlayer data
2. Downloads new card images
3. Generates embeddings
4. Rebuilds FAISS index
5. Creates backup
6. Sends notification

**Result:** Fresh prices and card data automatically!

---

## Troubleshooting

**Update failed?**
```bash
pnpm update:logs        # Check what went wrong
pnpm update:rollback    # Restore previous version
```

**Need to change time?**
Edit `config/update-scheduler.json` → `dailyUpdateTime`

**Want to disable?**
Edit `config/update-scheduler.json` → `"enabled": false`

---

## Read More

See [AUTOMATED_UPDATES_GUIDE.md](./AUTOMATED_UPDATES_GUIDE.md) for complete documentation.
