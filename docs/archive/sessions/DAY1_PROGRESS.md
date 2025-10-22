# Day 1: 800x800 Resolution Upgrade - Progress Tracker

**Date**: 2025-10-21  
**Branch**: `feature/week1-accuracy-improvements`  
**Goal**: Upgrade from 600x600 to 800x800 reference images

---

## Status: 🔄 IN PROGRESS

### ✅ Completed Steps

1. **Created feature branch** (`feature/week1-accuracy-improvements`)
2. **Updated transformImageUrl()** to use 800x800
   - File: `packages/config/src/tcgplayer-config.ts`
   - Commit: `fc7d27d` - feat: upgrade reference images to 800x800 resolution
3. **Backed up existing data**
   - Location: `data/backup_600x600_20251021_104129/`
   - Baseline: 5,113 images, 307.41 MB
4. **Started 800x800 download** (in progress...)

### 🔄 Current Step

**Downloading images at 800x800 resolution**
- Expected: ~450-500 MB
- Expected time: 5-10 minutes
- Progress log: `data/backup_600x600_20251021_104129/download_log.txt`

### ⏳ Remaining Steps

5. **Verify download** 
   - Check image count: should be ~5,113
   - Check total size: should be ~450-500 MB  
   - Verify images are 800x800 (not 600x600)

6. **Regenerate embeddings**
   - Script: `embed_onepiece_dinov2_with_preprocessing.py`
   - Expected time: 5-7 minutes
   - This uses the preprocessing pipeline (critical!)

7. **Rebuild FAISS index**
   - Script: `build_faiss_onepiece_dinov2.py`
   - Expected time: 1-2 minutes

8. **Test accuracy improvements**
   - Run tests on: blackbeard.png, yellow_event.png
   - Compare before/after scores
   - Expected: +20-30% accuracy

9. **Commit changes**
   - Commit message: "chore: regenerate embeddings with 800x800 images"
   - Include test results in commit message

---

## Expected Improvements

| Metric | Before (600x600) | After (800x800) | Improvement |
|--------|------------------|-----------------|-------------|
| **Image Size** | 60-65 KB avg | 90-100 KB avg | +58% |
| **OCR Accuracy** | 85% | 95% | +10% |
| **Geometric Matching** | Baseline | +50% | +50% |
| **HIGH Confidence Rate** | 50% (2/4) | 70%+ (3/4+) | +40% |

### Test Cases to Validate

1. `blackbeard.png` - Currently MODERATE (0.69), expect HIGH (0.75+)
2. `yellow_event.png` - Currently MODERATE (0.57), expect MODERATE-HIGH (0.65+)
3. `bege.png` - Currently HIGH (0.93), expect HIGH (maintained or better)
4. `blackbeard-db.jpg` - Currently HIGH (1.00), expect HIGH (maintained)

---

## Rollback Plan (If Needed)

If accuracy doesn't improve or gets worse:

```bash
# 1. Restore 600x600 images
Copy-Item -Path "data/backup_600x600_20251021_104129/images_one-piece/*" -Destination "data/images/one-piece/" -Recurse

# 2. Restore old embeddings (if backed up)
Copy-Item -Path "data/backup_600x600_20251021_104129/metadata/*" -Destination "artifacts/metadata/embeddings/one-piece-dinov2/" -Recurse

# 3. Revert code changes
git revert fc7d27d

# 4. Rebuild index with old embeddings
python services/indexer/bin/build_faiss_onepiece_dinov2.py
```

---

## Notes

- ✅ Using `embed_onepiece_dinov2_with_preprocessing.py` (has preprocessing!)
- ✅ Backup includes all original 600x600 data
- ✅ Download script only downloads missing images (safe to retry)
- ⚠️ Total download size: ~150 MB additional (450 MB - 307 MB)
- ⚠️ Embeddings regeneration will take ~5-7 minutes on CPU

---

**Last Updated**: 2025-10-21 10:41 AM  
**Next Check**: After download completes (~10:50 AM)

