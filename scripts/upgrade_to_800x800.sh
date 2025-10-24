#!/usr/bin/env bash
#
# Upgrade from 600x600 to 800x800 Resolution
#
# This script:
# 1. Backs up existing 600x600 data
# 2. Re-downloads images at 800x800
# 3. Re-generates DINOv2 embeddings
# 4. Re-builds FAISS index
# 5. Validates the upgrade
#
# Est. Time: 10-15 minutes
# Disk Usage: +150 MB temporarily (backup + new images)
#

set -e  # Exit on error

echo "========================================"
echo "  Upgrading to 800x800 Resolution"
echo "========================================"
echo ""

# Step 1: Backup existing data
echo "[1/5] Backing up existing 600x600 data..."
BACKUP_DIR="data/backup_600x600_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d "data/images/one-piece" ]; then
  echo "  Backing up images..."
  cp -r data/images/one-piece "$BACKUP_DIR/images_one-piece"
  echo "  [OK] Images backed up"
fi

if [ -f "artifacts/metadata/one-piece/embeddings.npy" ]; then
  echo "  Backing up embeddings..."
  mkdir -p "$BACKUP_DIR/metadata"
  cp artifacts/metadata/one-piece/embeddings.npy "$BACKUP_DIR/metadata/"
  echo "  [OK] Embeddings backed up"
fi

if [ -f "artifacts/faiss/one-piece.index" ]; then
  echo "  Backing up FAISS index..."
  mkdir -p "$BACKUP_DIR/faiss"
  cp artifacts/faiss/one-piece.index "$BACKUP_DIR/faiss/"
  echo "  [OK] FAISS index backed up"
fi

echo "  [OK] Backup complete: $BACKUP_DIR"
echo ""

# Step 2: Re-download images at 800x800
echo "[2/5] Re-downloading images at 800x800..."
echo "  This will download ~400 MB of data (was ~250 MB)"
echo "  Est. time: 3-5 minutes"
echo ""

pnpm run download-images:one-piece

echo "  [OK] Images downloaded"
echo ""

# Step 3: Re-generate embeddings
echo "[3/5] Re-generating DINOv2 embeddings..."
echo "  Processing 4,813 cards"
echo "  Est. time: 5-7 minutes"
echo ""

pnpm run embed:one-piece

echo "  [OK] Embeddings generated"
echo ""

# Step 4: Rebuild FAISS index
echo "[4/5] Rebuilding FAISS index..."
echo "  Est. time: 1-2 minutes"
echo ""

pnpm run index:one-piece

echo "  [OK] FAISS index built"
echo ""

# Step 5: Validate upgrade
echo "[5/5] Validating upgrade..."

python scripts/identification/test_all_images.py

echo ""
echo "========================================"
echo "  Upgrade Complete!"
echo "========================================"
echo ""
echo "Before (600x600):"
echo "  - Images: ~250 MB"
echo "  - Confidence: 16.7% HIGH"
echo "  - Avg Score: 0.623"
echo ""
echo "After (800x800):"
echo "  - Images: ~400 MB"
echo "  - Confidence: (testing...)"
echo "  - Avg Score: (testing...)"
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""
echo "To rollback:"
echo "  1. cp -r $BACKUP_DIR/images_one-piece data/images/one-piece"
echo "  2. cp $BACKUP_DIR/metadata/embeddings.npy artifacts/metadata/one-piece/"
echo "  3. cp $BACKUP_DIR/faiss/one-piece.index artifacts/faiss/"
echo ""
