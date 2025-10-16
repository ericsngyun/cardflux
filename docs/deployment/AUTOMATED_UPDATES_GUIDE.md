# CardFlux Automated Database Updates Guide

## Overview

The CardFlux automated update system keeps your card database, prices, and indices fresh by running daily incremental updates. This ensures you always have the latest card data and accurate market prices from TCGPlayer.

**Key Features:**
- ✅ Scheduled daily updates (configurable time)
- ✅ Automatic backup before updates
- ✅ Rollback capability on failures
- ✅ Health checks before/after updates
- ✅ Notifications (Slack, Discord, Email, Logs)
- ✅ Multi-game support
- ✅ Monitoring dashboard
- ✅ Resume from interruption

---

## Quick Start

### 1. Configure the Scheduler

Edit `config/update-scheduler.json`:

```json
{
  "enabled": true,
  "schedule": {
    "dailyUpdateTime": "03:00",  // 3 AM daily
    "timezone": "America/New_York",
    "retryAttempts": 3
  },
  "games": {
    "one-piece": {
      "enabled": true,
      "priority": 1
    }
  }
}
```

### 2. Set Up Scheduled Task

**Windows:**
```powershell
# Run as Administrator
cd scripts/automation
.\setup-windows-task.ps1
```

**Linux/Mac:**
```bash
# Run as root
cd scripts/automation
sudo ./setup-systemd.sh
```

### 3. Test the Update

```bash
# Run update immediately (test mode)
node scripts/automation/update-orchestrator.mjs

# Dry run (no changes)
node scripts/automation/update-orchestrator.mjs --dry-run
```

### 4. Monitor Status

```bash
# View dashboard
node scripts/automation/monitor.mjs

# View recent logs
node scripts/automation/monitor.mjs --logs

# Live monitoring
node scripts/automation/monitor.mjs --watch
```

---

## Configuration Reference

### Schedule Settings

```json
{
  "schedule": {
    "timezone": "America/New_York",      // IANA timezone
    "dailyUpdateTime": "03:00",          // HH:MM (24-hour)
    "retryAttempts": 3,                  // Retry on failure
    "retryDelayMinutes": 30,             // Wait between retries
    "maxDurationHours": 4,               // Kill if exceeds
    "skipWeekends": false                // Skip Sat/Sun
  }
}
```

### Game Configuration

```json
{
  "games": {
    "one-piece": {
      "enabled": true,        // Enable/disable game
      "priority": 1,          // Lower = higher priority
      "updateSteps": [
        "scrape",             // Scrape TCGPlayer
        "normalize",          // Normalize data
        "fetch-images",       // Download images
        "embed",              // Generate embeddings
        "index"               // Build FAISS index
      ]
    }
  }
}
```

### Notifications

```json
{
  "notifications": {
    "enabled": true,
    "onSuccess": true,       // Notify on success
    "onFailure": true,       // Notify on failure
    "channels": {
      "slack": {
        "enabled": true,
        "webhookUrl": "https://hooks.slack.com/services/YOUR/WEBHOOK"
      },
      "discord": {
        "enabled": true,
        "webhookUrl": "https://discord.com/api/webhooks/YOUR/WEBHOOK"
      },
      "log": {
        "enabled": true,
        "directory": "logs/updates"
      }
    }
  }
}
```

### Rollback Settings

```json
{
  "rollback": {
    "enabled": true,
    "keepBackups": 3,                // Keep last 3 backups
    "backupBeforeUpdate": true,      // Always backup first
    "autoRollbackOnFailure": false   // Manual rollback only
  }
}
```

### Monitoring

```json
{
  "monitoring": {
    "enabled": true,
    "healthCheck": {
      "beforeUpdate": true,          // Check before update
      "afterUpdate": true,           // Check after update
      "checkIndexIntegrity": true,   // Verify FAISS index
      "checkImageCount": true,       // Verify images
      "checkEmbeddingCount": true    // Verify embeddings
    },
    "alertThresholds": {
      "maxDurationMinutes": 240,     // Alert if > 4 hours
      "minNewCards": 0,              // Alert if no new cards
      "maxFailedImages": 100         // Alert if too many failures
    }
  }
}
```

---

## How It Works

### Update Pipeline

```
1. Pre-Update Health Check
   ├─ Verify indices exist
   ├─ Verify metadata exists
   └─ Check directory structure

2. Create Backup
   ├─ Backup FAISS indices
   ├─ Backup metadata
   └─ Backup curated data

3. Run Update Steps (per game)
   ├─ Scrape: Fetch latest data from TCGPlayer
   ├─ Normalize: Filter sealed products, normalize data
   ├─ Fetch Images: Download new card images
   ├─ Embed: Generate DINOv2 embeddings (incremental)
   └─ Index: Rebuild FAISS index with new embeddings

4. Post-Update Health Check
   ├─ Verify new indices work
   ├─ Check card counts
   └─ Validate metadata

5. Send Notifications
   ├─ Success: Report stats (games updated, duration)
   └─ Failure: Report error, suggest rollback
```

### Incremental Updates

The system uses **incremental updates** to minimize processing time:

- **Scraping**: Only fetches new/changed products
- **Images**: Only downloads missing images
- **Embeddings**: Only generates embeddings for new cards
- **Index**: Rebuilds entire index (fast with FAISS)

**Typical Duration:**
- Full initial build: 2-4 hours
- Daily incremental update: 10-30 minutes

---

## Platform-Specific Setup

### Windows Task Scheduler

**Setup:**
```powershell
cd scripts/automation
.\setup-windows-task.ps1
```

**Management:**
```powershell
# Start task now
Start-ScheduledTask -TaskName "CardFlux-DailyUpdate"

# View status
Get-ScheduledTask -TaskName "CardFlux-DailyUpdate"

# Disable
Disable-ScheduledTask -TaskName "CardFlux-DailyUpdate"

# Enable
Enable-ScheduledTask -TaskName "CardFlux-DailyUpdate"

# Remove
Unregister-ScheduledTask -TaskName "CardFlux-DailyUpdate"
```

**View Logs:**
```powershell
# Task Scheduler logs
Get-EventLog -LogName "Microsoft-Windows-TaskScheduler/Operational"

# CardFlux logs
Get-Content logs\updates\update-*.log -Tail 50
```

### Linux systemd Service

**Setup:**
```bash
cd scripts/automation
sudo ./setup-systemd.sh
```

**Management:**
```bash
# Start service
sudo systemctl start cardflux-update

# Stop service
sudo systemctl stop cardflux-update

# Status
sudo systemctl status cardflux-update

# View logs (live)
sudo journalctl -u cardflux-update -f

# Enable on boot
sudo systemctl enable cardflux-update

# Disable
sudo systemctl disable cardflux-update
```

**View Logs:**
```bash
# systemd logs
sudo journalctl -u cardflux-update --since "1 hour ago"

# CardFlux logs
tail -f logs/updates/update-*.log
```

### macOS Launchd (Alternative)

Create `~/Library/LaunchAgents/com.cardflux.update.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cardflux.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/node</string>
        <string>/path/to/cardflux/scripts/automation/update-orchestrator.mjs</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/path/to/cardflux</string>
    <key>StandardOutPath</key>
    <string>/path/to/cardflux/logs/update.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/cardflux/logs/update-error.log</string>
</dict>
</plist>
```

```bash
# Load service
launchctl load ~/Library/LaunchAgents/com.cardflux.update.plist

# Unload service
launchctl unload ~/Library/LaunchAgents/com.cardflux.update.plist
```

---

## Monitoring Dashboard

### View Status

```bash
node scripts/automation/monitor.mjs
```

**Output:**
```
═══════════════════════════════════════════════════════════
  📊 CardFlux Update Monitor
═══════════════════════════════════════════════════════════

⚙️  Configuration:
  Status: ✅ Enabled
  Schedule: Daily at 03:00
  Games: one-piece

🔄 Update Status:
  Last Update: 2025-10-13 03:15:22 (5h ago)
  Log File: update-2025-10-13T03-00-05.log
  Next Update: 2025-10-14 03:00:00 (in 18h 45m)

💚 System Health:
  Backups: 3
  Log Files: 7

  one-piece:
    Index: ✅  Metadata: ✅  Cards: 4,813
    Last Modified: 2025-10-13 03:14:58
```

### View Logs

```bash
node scripts/automation/monitor.mjs --logs
```

### Live Monitoring

```bash
node scripts/automation/monitor.mjs --watch
```

Refreshes every 30 seconds. Press Ctrl+C to exit.

---

## Rollback Guide

### List Available Backups

```bash
node scripts/automation/rollback.mjs
```

**Output:**
```
📦 Available Backups:

─────────────────────────────────────────────────────────────
ID                            Game       Created             Size
─────────────────────────────────────────────────────────────
one-piece-2025-10-13T03-00-05 one-piece  10/13/2025 3:00 AM  1.2 GB
one-piece-2025-10-12T03-00-12 one-piece  10/12/2025 3:00 AM  1.1 GB
one-piece-2025-10-11T03-00-08 one-piece  10/11/2025 3:00 AM  1.1 GB
─────────────────────────────────────────────────────────────
Total: 3 backup(s)
```

### Rollback to Specific Backup

```bash
node scripts/automation/rollback.mjs one-piece-2025-10-13T03-00-05
```

**Process:**
1. Confirms with user
2. Creates safety backup of current state
3. Restores from specified backup
4. Reports completion

### Rollback to Latest Backup

```bash
node scripts/automation/rollback.mjs --latest
```

---

## Troubleshooting

### Update Failed

**Symptom:** Update stops with error

**Solutions:**
1. Check logs: `node scripts/automation/monitor.mjs --logs`
2. Verify configuration: `config/update-scheduler.json`
3. Check disk space: Ensure 10GB+ free
4. Verify network: TCGPlayer API must be accessible
5. Rollback if needed: `node scripts/automation/rollback.mjs --latest`

### Health Check Failed

**Symptom:** "Health check failed" error

**Solutions:**
1. Check if indices exist: `ls artifacts/faiss/*/index.faiss`
2. Check if metadata exists: `ls artifacts/metadata/embeddings/*/metadata.jsonl`
3. Rebuild if corrupt: `pnpm pipeline:all` (full rebuild)

### Update Runs Too Long

**Symptom:** Update exceeds `maxDurationHours`

**Solutions:**
1. Increase timeout in config: `"maxDurationHours": 6`
2. Check for stuck processes: `ps aux | grep python`
3. Reduce Top-K in identifier: `top_k: 20` (from 30)
4. Disable OCR if not needed: `skip_ocr: true`

### Notifications Not Working

**Symptom:** No Slack/Discord notifications

**Solutions:**
1. Verify webhook URL is correct
2. Test webhook manually:
   ```bash
   curl -X POST YOUR_WEBHOOK_URL -H 'Content-Type: application/json' -d '{"text":"test"}'
   ```
3. Check firewall/proxy settings
4. Enable log notifications as fallback

### Backup Directory Full

**Symptom:** Disk space low, backups consuming space

**Solutions:**
1. Reduce `keepBackups`: `"keepBackups": 2` (from 3)
2. Enable cleanup: `"cleanupOldBackups": true`
3. Enable compression: `"compressBackups": true` (future feature)
4. Manually delete old backups: `rm -rf backups/old-*`

---

## Best Practices

### 1. Test Before Production

```bash
# Dry run (no changes)
node scripts/automation/update-orchestrator.mjs --dry-run

# Run once manually
node scripts/automation/update-orchestrator.mjs

# Check results
node scripts/automation/monitor.mjs
```

### 2. Schedule During Off-Hours

- **Shops:** 3-4 AM (before opening)
- **Personal:** 2-3 AM (overnight)
- Avoid peak hours to prevent resource contention

### 3. Monitor Regularly

```bash
# Daily check
node scripts/automation/monitor.mjs

# Weekly log review
node scripts/automation/monitor.mjs --logs
```

### 4. Keep Multiple Backups

```json
{
  "rollback": {
    "keepBackups": 3  // Recommended: 3-7 days
  }
}
```

### 5. Set Up Notifications

Configure at least one notification channel:
- **Email:** For important alerts
- **Slack/Discord:** For team visibility
- **Logs:** Always enabled as fallback

### 6. Plan for Failures

- Enable `backupBeforeUpdate: true`
- Keep `autoRollbackOnFailure: false` (manual control)
- Test rollback process monthly

### 7. Monitor Disk Space

Typical storage requirements:
- **Images:** 500MB - 2GB per game
- **Embeddings:** 100MB - 500MB per game
- **Indices:** 50MB - 200MB per game
- **Backups:** 3x the above
- **Total:** Plan for 5-10GB per game

---

## Upgrade Guide

### Updating the Update System

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pnpm install
pip install -r services/embedder/requirements.txt

# Test new version
node scripts/automation/update-orchestrator.mjs --dry-run

# Restart service (systemd)
sudo systemctl restart cardflux-update

# Or restart task (Windows)
Stop-ScheduledTask -TaskName "CardFlux-DailyUpdate"
Start-ScheduledTask -TaskName "CardFlux-DailyUpdate"
```

### Migrating Configuration

If config schema changes:

1. Backup current config: `cp config/update-scheduler.json config/update-scheduler.json.bak`
2. Compare with new schema: `config/update-scheduler.schema.json`
3. Update config with new fields
4. Validate: `node scripts/automation/update-orchestrator.mjs --dry-run`

---

## FAQ

**Q: How long does an update take?**
A: First run: 2-4 hours. Daily incremental: 10-30 minutes.

**Q: What happens if my computer is off during scheduled time?**
A: Windows Task Scheduler will run when computer starts (`StartWhenAvailable`). systemd will skip and run next day.

**Q: Can I run updates manually?**
A: Yes: `node scripts/automation/update-orchestrator.mjs`

**Q: How much disk space do I need?**
A: 5-10GB per TCG game (including backups).

**Q: What if an update fails?**
A: Check logs, fix issue, run manually or wait for next scheduled run. Rollback if needed.

**Q: Can I update multiple games?**
A: Yes, enable multiple games in config. They update sequentially by priority.

**Q: How do I disable updates temporarily?**
A: Set `"enabled": false` in config or disable the scheduled task/service.

**Q: Can I change the update time?**
A: Yes, edit `dailyUpdateTime` in config and restart the service/task.

**Q: What if I delete a backup by accident?**
A: System keeps multiple backups. Rollback to an earlier one.

**Q: How do I know if an update succeeded?**
A: Check monitor dashboard: `node scripts/automation/monitor.mjs`

---

## Support

### Get Help

1. Check logs: `node scripts/automation/monitor.mjs --logs`
2. View dashboard: `node scripts/automation/monitor.mjs`
3. Read troubleshooting section above
4. Check GitHub issues: https://github.com/yourusername/cardflux/issues

### Report Issues

Include in your report:
- Config file: `config/update-scheduler.json`
- Recent log: `logs/updates/update-*.log`
- System info: OS, Node version, Python version
- Error message and stack trace

---

## Summary

The automated update system ensures your CardFlux database stays fresh with:
- ✅ Daily scheduled updates
- ✅ Automatic backups
- ✅ Health monitoring
- ✅ Rollback capability
- ✅ Notifications
- ✅ Easy management

**Set it and forget it!** The system runs autonomously, keeping your card data and prices up-to-date.
