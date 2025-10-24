# Week 1 Accuracy Improvements - Current Status

**Date**: 2025-10-21 10:45 AM  
**Branch**: `feature/week1-accuracy-improvements`

---

## 📊 Current Status: Download in Progress

### ✅ Completed (15 minutes)

1. **Feature branch created** (`feature/week1-accuracy-improvements`)
2. **Code updated for 800x800**
   - Updated `transformImageUrl()` in `packages/config/src/tcgplayer-config.ts`
   - Committed: `fc7d27d`
3. **Backup created**
   - 5,113 images (307 MB) backed up to `data/backup_600x600_20251021_104129/`

### 🔄 In Progress (Estimated 3-6 hours)

4. **Downloading 800x800 images**
   - Progress: 10 / 5,113 (0.2%)
   - Current rate: ~10 images/minute
   - **Estimated completion: 3-6 hours**
   - Reason: Rate limiting (100ms between images, 500ms every 10th)

### ⏳ Pending (After download)

5. **Regenerate embeddings** (~5-7 minutes)
6. **Rebuild FAISS index** (~1-2 minutes)
7. **Test accuracy** (~1 minute)
8. **Commit & push** (~2 minutes)

---

## ⚠️ Current Situation

The image download is rate-limited to avoid overloading TCGPlayer's CDN:
- 100ms delay between images
- 500ms delay every 10th image  
- This is intentional to be respectful to the CDN

**Options:**

### Option A: Let it run (Recommended)
- Leave download running in background
- Continue tomorrow when complete
- Safe, respectful to CDN
- **Time**: 3-6 hours download + 10 minutes processing

### Option B: Speed up download (Risky)
- Reduce delays in `fetch_images_onepiece.ts`
- Risk: 429 (Too Many Requests) or 403 (Forbidden)
- **Time**: 30-60 minutes download + 10 minutes processing

### Option C: Partial upgrade (Testing)
- Stop download after 500 images
- Test with partial dataset
- If works, continue full download later
- **Time**: 30 minutes + testing

---

## 💡 Recommendation

**I recommend Option C (Partial Test) for today:**

1. **Stop download after ~500 images** (50 more minutes)
2. **Regenerate embeddings** with those 500 cards
3. **Test if accuracy improves** on test images
4. **If successful**, continue full download overnight
5. **If not successful**, investigate before committing more time

This validates the approach before spending 6 hours on the full download.

---

## 📝 Next Steps (Once Download Completes or Reaches 500)

```bash
# 1. Verify download
python scripts/identification/verify_800x800_upgrade.py

# 2. Regenerate embeddings (~5-7 min)
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# 3. Rebuild FAISS index (~1-2 min)
python services/indexer/bin/build_faiss_onepiece_dinov2.py

# 4. Test accuracy
python scripts/identification/verify_800x800_upgrade.py

# 5. If successful, commit
git add artifacts/ DAY1_PROGRESS.md WEEK1_STATUS.md
git commit -m "chore: upgrade to 800x800 images and regenerate embeddings

- Downloaded 5,113 images at 800x800 (was 600x600)
- Total size: 450-500 MB (was 307 MB)
- Regenerated DINOv2 embeddings with preprocessing
- Rebuilt FAISS index

Results:
- blackbeard.png: MODERATE (0.69) -> HIGH (0.XX)
- yellow_event.png: MODERATE (0.57) -> MODERATE-HIGH (0.XX)
- HIGH confidence rate: 50% -> XX%

See: DAY1_PROGRESS.md for details"
```

---

## 🔧 How to Speed Up Download (If Needed)

Edit `services/ingest/bin/fetch_images_onepiece.ts`:

```typescript
// Current (lines 92-96):
if (downloaded % 10 === 0) {
  await new Promise(resolve => setTimeout(resolve, 500)); // ← Change to 100
} else {
  await new Promise(resolve => setTimeout(resolve, 100)); // ← Change to 50
}

// Faster (2-3x speedup):
if (downloaded % 10 === 0) {
  await new Promise(resolve => setTimeout(resolve, 100));
} else {
  await new Promise(resolve => setTimeout(resolve, 50));
}
```

⚠️ Risk: May trigger rate limiting (429/403 errors)

---

## 📋 Rollback Instructions

If needed to revert:

```bash
# 1. Restore 600x600 images
Copy-Item -Path "data/backup_600x600_20251021_104129/images_one-piece/*" -Destination "data/images/one-piece/" -Recurse

# 2. Revert code change
git revert fc7d27d

# 3. Checkout main
git checkout main
git branch -D feature/week1-accuracy-improvements
```

---

## ⏰ Time Estimates

| Task | Time | When |
|------|------|------|
| Download (full) | 3-6 hours | Now + 3-6 hrs |
| Download (500 images) | 50 min | Now + 50 min |
| Embed | 5-7 min | After download |
| Index | 1-2 min | After embed |
| Test | 1 min | After index |
| **Total (full)** | **4-7 hours** | |
| **Total (partial test)** | **1 hour** | |

---

**Decision needed:** Continue with full download (wait 3-6 hours) or test with partial dataset (50 minutes)?

