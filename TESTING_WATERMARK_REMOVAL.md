# Testing Watermark Removal - Quick Guide

> **Status**: Re-embedding in progress (~2-3 min remaining)
> **Your Task**: Run tests once complete, review results, decide to keep or revert

---

## Once Re-Embedding Completes

### Step 1: Test Radical Beam (Your Specific Issue)

```bash
python scripts/identification/core/production_card_identifier.py test-images/one-piece/radicalbeam.png
```

**What to look for**:
- ✅ **GOOD**: Identified as "Radical Beam!!" (OP01-029) with HIGH confidence
- ❌ **BAD**: Still identified as "Divine Departure" or wrong card

---

### Step 2: Run Comprehensive Comparison Test

```bash
python scripts/identification/tests/test_watermark_removal_impact.py
```

**This script will**:
1. Load baseline results (before watermark removal)
2. Test all 10 images with new watermark-removed embeddings
3. Compare confidence distribution, scores, and identifications
4. Give you a **VERDICT**: Keep, Review, or Revert

**Expected output**:
```
VERDICT
================================================================================

✅ WATERMARK REMOVAL IS BENEFICIAL - KEEP CHANGES

Reasons:
  ✅ HIGH confidence improved: 6 → 8 (+2)
  ✅ Average score improved: 0.6992 → 0.7450 (+0.0458)
  ✅ No confidence downgrades
```

---

### Step 3: Review Results

**Key Metrics to Check**:

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| HIGH Confidence | 60% (6/10) | 70-80% (7-8/10) | Check report |
| Average Score | 0.6992 | 0.72+ | Check report |
| Radical Beam | ❌ Wrong ID | ✅ Correct ID | Check Step 1 |
| Confidence Downgrades | 0 | 0 | ❌ Any downgrades = concern |

---

## Decision Tree

### ✅ KEEP Watermark Removal If:
- Radical Beam now identifies correctly
- HIGH confidence improved (60% → 70%+)
- Average scores improved
- No accuracy regressions (wrong IDs)

### ⚠️ REVIEW If:
- Mixed results (some improve, some degrade)
- Radical Beam fixed but other cards broke
- Scores improved but confidence didn't change

### ❌ REVERT If:
- Radical Beam still wrong
- HIGH confidence decreased
- Multiple cards now misidentified
- Scores decreased overall

---

## How to Revert (If Needed)

If watermark removal made things worse:

### Quick Revert (Restore Backup)

```bash
# Restore original FAISS index
rm -rf artifacts/faiss/one-piece-dinov2
cp -r artifacts/faiss/one-piece-dinov2-BACKUP-before-watermark-removal artifacts/faiss/one-piece-dinov2

# Revert code changes
git checkout scripts/identification/core/production_card_identifier.py
git checkout services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py

# Test again
python scripts/identification/tests/test_all_production_images.py
```

---

## Alternative Approach (If Watermark Removal Fails)

### Option 1: Adjust Watermark Detection Thresholds

Try more conservative watermark detection:

```python
# In both embedder and identifier, change:
watermark_mask[gray > 200] = 255  # Current threshold

# To:
watermark_mask[gray > 210] = 255  # More conservative (only very bright pixels)
```

### Option 2: Different Inpainting Algorithm

Try alternative inpainting method:

```python
# Current:
img_array = cv2.inpaint(img_array, watermark_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

# Alternative (slower but better quality):
img_array = cv2.inpaint(img_array, watermark_mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
```

### Option 3: Blur Instead of Inpaint

Less aggressive approach:

```python
# Instead of inpainting, blur the watermark region
if watermark_ratio > 0.01:
    blurred = cv2.GaussianBlur(img_array, (15, 15), 0)
    img_array[watermark_mask > 0] = blurred[watermark_mask > 0]
```

### Option 4: Source Clean Images

Long-term solution:
- Find alternative image sources without watermarks
- Community contributions of clean photos
- Use TCGPlayer API (if they provide unwatermarked images)

---

## Expected Results

### Baseline (Before Watermark Removal)
```
radicalbeam.png:
  Card: Divine Departure (Parallel) ❌
  Number: OP10-019
  Confidence: MODERATE (0.6008)

Overall:
  HIGH: 60% (6/10)
  Avg Score: 0.6992
```

### Expected (After Watermark Removal)
```
radicalbeam.png:
  Card: Radical Beam!! (Textured Foil) ✅
  Number: OP01-029
  Confidence: HIGH (0.75+)

Overall:
  HIGH: 70-80% (7-8/10)
  Avg Score: 0.72-0.75
```

---

## Files Involved

### Modified Code
1. `services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py`
2. `scripts/identification/core/production_card_identifier.py`

### Backups
1. `artifacts/faiss/one-piece-dinov2-BACKUP-before-watermark-removal/` ← Restore from here if needed

### Test Scripts
1. `scripts/identification/tests/test_watermark_removal_impact.py` ← Run this for comparison
2. `scripts/identification/tests/test_all_production_images.py` ← Standard test

---

## Summary

**Your Job**: Run tests → Review results → Keep or revert

**Commands**:
```bash
# 1. Test Radical Beam specifically
python scripts/identification/core/production_card_identifier.py test-images/one-piece/radicalbeam.png

# 2. Run comprehensive comparison
python scripts/identification/tests/test_watermark_removal_impact.py

# 3. If good: Commit changes
git add -A
git commit -m "fix: Add watermark removal to improve visual similarity matching"

# 4. If bad: Revert
rm -rf artifacts/faiss/one-piece-dinov2
cp -r artifacts/faiss/one-piece-dinov2-BACKUP-before-watermark-removal artifacts/faiss/one-piece-dinov2
git checkout scripts/identification/core/production_card_identifier.py services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
```

**I'll wait for re-embedding to complete and help you interpret results!**
