# CardFlux Cloud Sync Script
# Pulls latest database updates from GitHub (cloud updates)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CardFlux Cloud Sync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in a git repo
if (-not (Test-Path .git)) {
    Write-Host "❌ Not a git repository" -ForegroundColor Red
    Write-Host "Please run this from the cardflux root directory" -ForegroundColor Yellow
    exit 1
}

# Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  You have uncommitted local changes:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    $response = Read-Host "Stash changes and continue? (y/n)"
    if ($response -ne "y") {
        Write-Host "❌ Sync cancelled" -ForegroundColor Red
        exit 1
    }
    git stash push -m "Auto-stash before cloud sync $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "✅ Changes stashed" -ForegroundColor Green
}

# Fetch latest from origin
Write-Host "🔄 Fetching latest updates from GitHub..." -ForegroundColor Cyan
git fetch origin

# Check what will be updated
$behind = git rev-list --count HEAD..origin/main
if ($behind -eq 0) {
    Write-Host "✅ Already up to date!" -ForegroundColor Green
    exit 0
}

Write-Host "📦 $behind new commit(s) available" -ForegroundColor Yellow
Write-Host ""
Write-Host "Changes to be pulled:" -ForegroundColor Cyan
git log --oneline HEAD..origin/main | Select-Object -First 10
Write-Host ""

# Pull changes
Write-Host "⬇️  Pulling updates..." -ForegroundColor Cyan
git pull origin main --rebase

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Pull failed!" -ForegroundColor Red
    Write-Host "You may need to resolve conflicts manually" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "✅ Sync complete!" -ForegroundColor Green
Write-Host ""

# Show what was updated
Write-Host "📊 Updated files:" -ForegroundColor Cyan
git diff --stat HEAD@{1} HEAD | Select-Object -First 20

# Check if artifacts were updated
Write-Host ""
Write-Host "🔍 Checking for database updates..." -ForegroundColor Cyan

$artifactsUpdated = git diff --name-only HEAD@{1} HEAD | Where-Object { $_ -match "artifacts/" }
if ($artifactsUpdated) {
    Write-Host "✅ Database artifacts updated:" -ForegroundColor Green
    $artifactsUpdated | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "⚠️  Restart the desktop app to use the new data!" -ForegroundColor Yellow
} else {
    Write-Host "ℹ️  No database changes in this update" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next sync: Run this script again or use 'git pull'" -ForegroundColor Cyan
Write-Host ""
