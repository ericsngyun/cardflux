# CardFlux Cloud Updates Guide

## Overview

CardFlux can run database updates in the cloud via GitHub Actions, eliminating the need for your local computer to be on at the scheduled time.

**How it works:**
1. GitHub Actions runs daily at 2 PM PDT (in the cloud)
2. Updates scrape TCGPlayer, generate embeddings, rebuild indices
3. Changes are committed back to the repository
4. Your local machine pulls the updates when convenient

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           GitHub Actions (Cloud)                │
│                                                 │
│  Runs Daily at 2 PM PDT                        │
│  ├─ Scrapes TCGPlayer API                      │
│  ├─ Downloads new card images                  │
│  ├─ Generates embeddings (DINOv2)             │
│  ├─ Builds FAISS indices                       │
│  └─ Commits artifacts to repository            │
│                                                 │
└──────────────────┬──────────────────────────────┘
                   │ git push (automated)
                   ▼
┌─────────────────────────────────────────────────┐
│           GitHub Repository                     │
│                                                 │
│  ├─ artifacts/faiss/                           │
│  ├─ artifacts/metadata/                        │
│  ├─ data/curated/                              │
│  └─ .github/workflows/daily-update.yml         │
│                                                 │
└──────────────────┬──────────────────────────────┘
                   │ git pull (manual or scheduled)
                   ▼
┌─────────────────────────────────────────────────┐
│           Your Local Machine                    │
│                                                 │
│  Shop Computer (Windows)                        │
│  ├─ Pulls updates: pnpm update:sync            │
│  ├─ Desktop app uses fresh data                │
│  └─ Scanner identifies cards with new prices   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Setup (5 Minutes)

### 1. Enable GitHub Actions

The workflow is already created at `.github/workflows/daily-update.yml`.

GitHub Actions should be enabled by default, but verify:

1. Go to your GitHub repository
2. Click "Actions" tab
3. If disabled, click "Enable Actions"

### 2. Configure Git LFS (Large File Storage)

Since we're storing embeddings and indices in git:

```bash
# Install Git LFS
# Windows: Download from https://git-lfs.github.com/
# Mac: brew install git-lfs
# Linux: sudo apt-get install git-lfs

# Initialize LFS in your repo
git lfs install

# Track large files
git lfs track "artifacts/**/*.faiss"
git lfs track "artifacts/**/*.npy"
git lfs track "data/images/**/*.jpg"
git lfs track "data/images/**/*.png"

# Commit .gitattributes
git add .gitattributes
git commit -m "chore: Configure Git LFS for large artifacts"
git push
```

### 3. Test the Workflow

**Trigger manually:**

1. Go to GitHub → Actions → "Daily Card Database Update"
2. Click "Run workflow"
3. Select branch: `main`
4. Click "Run workflow"

**Monitor progress:**
- Click on the running workflow
- Watch logs in real-time
- Typical duration: 15-30 minutes

### 4. Set Up Local Sync

**Add npm script** (already done):
```json
{
  "scripts": {
    "update:sync": "pwsh -File scripts/automation/sync-from-cloud.ps1"
  }
}
```

**Windows (PowerShell):**
```powershell
# Pull latest updates from cloud
pnpm update:sync

# Or manually
cd scripts/automation
.\sync-from-cloud.ps1
```

**Linux/Mac:**
```bash
# Make script executable
chmod +x scripts/automation/sync-from-cloud.sh

# Pull latest updates
./scripts/automation/sync-from-cloud.sh
```

---

## Daily Workflow

### Morning Routine (Shop Opening)

```bash
# 1. Pull latest updates from GitHub
pnpm update:sync

# 2. Check what changed
git log -1 --stat

# 3. Start desktop app
cd apps/desktop
pnpm start
```

**What this does:**
- Downloads fresh card data from last night's cloud update
- Syncs new FAISS indices
- Updates metadata and prices
- Takes ~30 seconds

### Automated Local Sync (Optional)

**Windows Task Scheduler:**

Create a task that runs at shop opening (e.g., 9 AM):

```powershell
# Run this to set up
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-File C:\path\to\cardflux\scripts\automation\sync-from-cloud.ps1" `
    -WorkingDirectory "C:\path\to\cardflux"

$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "CardFlux-CloudSync" `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Description "Pull CardFlux updates from GitHub"
```

---

## GitHub Actions Schedule

The workflow runs daily at **2 PM PDT** (1 hour after TCGPlayer's 1 PM update).

**Cron schedules in the workflow:**
```yaml
on:
  schedule:
    - cron: '0 21 * * *'  # 2 PM PDT (9 PM UTC, summer)
    - cron: '0 22 * * *'  # 2 PM PST (10 PM UTC, winter)
```

**Why two schedules?**
- GitHub Actions uses UTC time
- 2 PM PDT = 9 PM UTC (daylight saving)
- 2 PM PST = 10 PM UTC (standard time)
- Both schedules ensure updates run at 2 PM Pacific year-round

---

## What Gets Updated

### Daily (Cloud)
1. **Scrape TCGPlayer** (~2 minutes)
   - New card releases
   - Price updates
   - Set information

2. **Download Images** (~3 minutes)
   - Only new images
   - Skips existing

3. **Generate Embeddings** (~5 minutes)
   - DINOv2 embeddings for new cards
   - Incremental processing

4. **Build Indices** (~2 minutes)
   - FAISS index rebuilt
   - Metadata updated

5. **Commit & Push** (~1 minute)
   - Artifacts committed to git
   - Automated commit message

**Total time:** ~15 minutes

### Local Sync
1. **Pull from GitHub** (~30 seconds)
   - Downloads only changed files
   - Git LFS handles large files efficiently

2. **Verify artifacts** (automatic)
   - Script checks if database changed
   - Notifies if restart needed

---

## Monitoring Cloud Updates

### View Workflow Status

**GitHub Web UI:**
1. Go to repository → Actions tab
2. See "Daily Card Database Update" workflow
3. Green checkmark = Success
4. Red X = Failed

**Email Notifications:**
GitHub sends emails on workflow failures (enable in Settings → Notifications).

### View Logs

**Recent runs:**
```bash
# Via GitHub CLI (if installed)
gh run list --workflow="daily-update.yml"

# View specific run
gh run view <run-id>
```

**Web UI:**
1. Actions → Daily Card Database Update
2. Click on a run
3. Expand steps to see detailed logs

### Check Last Update

```bash
# See last automated commit
git log --grep="Automated database update" -1

# Check what changed
git show HEAD --stat
```

---

## Cost Analysis

### GitHub Actions Free Tier
- **2,000 minutes/month** free
- Our update takes ~15 minutes
- **133 updates/month** possible (way more than daily)

**Cost:** $0 (well within free tier)

### Git LFS Free Tier
- **1 GB storage** free
- **1 GB bandwidth/month** free

**Typical usage:**
- FAISS indices: ~50-200 MB per game
- Embeddings: ~100-500 MB per game
- Images: ~500 MB - 2 GB per game

**For One Piece only:** ~1-2 GB total (may need paid LFS)

**Git LFS pricing (if needed):**
- $5/month for 50 GB storage + 50 GB bandwidth
- More than enough for multiple games

### Alternative: GitHub Releases

Instead of Git LFS, we can use GitHub Releases:

```yaml
# In workflow, upload artifacts as release
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    tag_name: daily-${{ github.run_number }}
    files: |
      artifacts/faiss/**/*
      artifacts/metadata/**/*
```

**Benefits:**
- Unlimited storage (within reason)
- Free
- Easier to download specific versions

**Trade-off:**
- Manual download (not git pull)
- More complex sync script

---

## Troubleshooting

### Workflow Failed

**Check logs:**
1. Actions → Failed workflow → Click on run
2. Expand failed step
3. Read error message

**Common issues:**
- **Out of disk space:** GitHub runners have 14 GB disk
- **Timeout:** Increase `timeout-minutes` in workflow
- **Python error:** Update dependencies in workflow
- **Git push failed:** Check repository permissions

**Fix and retry:**
1. Fix the issue
2. Go to Actions → Failed run
3. Click "Re-run jobs"

### Local Sync Failed

**Error: "Not a git repository"**
- Run from cardflux root directory

**Error: "Uncommitted changes"**
- Commit or stash your changes first
- Or let script auto-stash

**Error: "Merge conflict"**
- Resolve conflicts manually: `git status`
- Or reset local changes: `git reset --hard origin/main`

### Artifacts Not Updating

**Check if workflow ran:**
```bash
git log --oneline | grep "Automated database update"
```

**If no recent commits:**
- Check Actions tab for failures
- Verify schedule in workflow file
- Manually trigger workflow to test

**If commits exist but not pulled:**
```bash
# Force pull
git fetch origin
git reset --hard origin/main
```

---

## Best Practices

### 1. Regular Syncs

**Recommended schedule:**
- **Shop opening:** Morning sync (9 AM)
- **Midday:** Optional (if expecting new releases)
- **Shop closing:** Evening sync (9 PM)

```powershell
# Quick check for updates
git fetch origin
git log HEAD..origin/main --oneline

# If updates available
pnpm update:sync
```

### 2. Monitor Workflow Health

**Weekly check:**
- Review Actions tab for failures
- Check update-report artifacts
- Verify card counts are increasing

### 3. Backup Strategy

**Cloud backups:**
GitHub keeps full git history (free unlimited backup!)

**Local backups:**
```bash
# Before major changes
git tag backup-$(date +%Y%m%d)
git push origin --tags
```

### 4. Resource Management

**Keep Git LFS usage low:**
- Only track necessary files
- Use `.gitignore` for temporary files
- Clean up old images periodically

**Monitor Actions usage:**
- GitHub Settings → Billing → Actions usage
- Should stay well under 2,000 minutes/month

---

## Migration from Local Updates

### If You Were Using Task Scheduler

**Option 1: Disable local updates (recommended)**
```powershell
Disable-ScheduledTask -TaskName "CardFlux-DailyUpdate"
```

**Option 2: Keep as backup**
- Cloud updates run at 2 PM PDT
- Local runs at different time (e.g., 3 AM)
- Redundancy if cloud fails

### Transition Period

**Week 1: Both systems**
- Cloud updates daily at 2 PM
- Local updates daily at 3 AM
- Compare results to verify cloud works

**Week 2+: Cloud only**
- Disable local updates
- Use `pnpm update:sync` for local refresh

---

## Advanced: Custom Workflows

### Update Specific Game

```bash
# Trigger workflow with inputs
gh workflow run daily-update.yml -f game=pokemon
```

### Dry Run (Test Without Committing)

```bash
gh workflow run daily-update.yml -f dry_run=true
```

### Manual Update (Emergency)

```bash
# On your local machine
pnpm pipeline:update

# Commit and push
git add -A
git commit -m "chore: Manual database update - $(date)"
git push
```

---

## Summary

**Cloud updates with GitHub Actions:**
- ✅ Free (within generous free tier)
- ✅ Runs even when computer is off
- ✅ Reliable (GitHub infrastructure)
- ✅ Automatic commits
- ✅ Full history/backups
- ✅ Easy monitoring
- ✅ No local maintenance

**Local sync:**
- ✅ Fast (30 seconds)
- ✅ Simple (`pnpm update:sync`)
- ✅ Automatic or manual
- ✅ Verifies changes

**Result:** Fresh card data daily, zero local overhead!

---

## Quick Reference

```bash
# Cloud management
gh workflow run daily-update.yml           # Trigger update now
gh run list --workflow=daily-update.yml    # View recent runs
gh run view <run-id>                       # View specific run

# Local sync
pnpm update:sync                           # Pull latest updates
git log -1 --stat                          # See what changed
git log HEAD..origin/main                  # Check pending updates

# Monitoring
# GitHub: https://github.com/[your-repo]/actions
# View workflow runs and logs
```

---

**You're now set up for fully automated cloud updates!** 🎉
