#!/bin/bash
# CardFlux Cloud Sync Script (Linux/Mac)
# Pulls latest database updates from GitHub (cloud updates)

set -e

echo "========================================"
echo "CardFlux Cloud Sync"
echo "========================================"
echo ""

# Check if we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Not a git repository"
    echo "Please run this from the cardflux root directory"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted local changes:"
    git status --short
    echo ""
    read -p "Stash changes and continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Sync cancelled"
        exit 1
    fi
    git stash push -m "Auto-stash before cloud sync $(date '+%Y-%m-%d %H:%M:%S')"
    echo "✅ Changes stashed"
fi

# Fetch latest from origin
echo "🔄 Fetching latest updates from GitHub..."
git fetch origin

# Check what will be updated
BEHIND=$(git rev-list --count HEAD..origin/main)
if [ "$BEHIND" -eq 0 ]; then
    echo "✅ Already up to date!"
    exit 0
fi

echo "📦 $BEHIND new commit(s) available"
echo ""
echo "Changes to be pulled:"
git log --oneline HEAD..origin/main | head -10
echo ""

# Pull changes
echo "⬇️  Pulling updates..."
git pull origin main --rebase

echo ""
echo "✅ Sync complete!"
echo ""

# Show what was updated
echo "📊 Updated files:"
git diff --stat HEAD@{1} HEAD | head -20

# Check if artifacts were updated
echo ""
echo "🔍 Checking for database updates..."

ARTIFACTS_UPDATED=$(git diff --name-only HEAD@{1} HEAD | grep "artifacts/" || true)
if [ -n "$ARTIFACTS_UPDATED" ]; then
    echo "✅ Database artifacts updated:"
    echo "$ARTIFACTS_UPDATED" | sed 's/^/  - /'
    echo ""
    echo "⚠️  Restart the desktop app to use the new data!"
else
    echo "ℹ️  No database changes in this update"
fi

echo ""
echo "Next sync: Run this script again or use 'git pull'"
echo ""
