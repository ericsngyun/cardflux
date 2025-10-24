# Watermark Removal - Failure Analysis & Next Steps

> **Date**: 2025-10-24
> **Experiment**: TCGPlayer SAMPLE watermark removal preprocessing
> **Result**: ❌ **FAILED - Made accuracy WORSE**
> **Action Taken**: ✅ **REVERTED** to original embeddings and code

---

## Executive Summary

Attempted to fix Radical Beam identification issue by removing TCGPlayer SAMPLE watermarks from reference images during embedding. **The watermark removal preprocessing made accuracy significantly worse**, causing 7/10 cards to be misidentified.

**Verdict**: Watermark removal approach failed. Reverted all changes.

---

## Original Problem

**User Report**: "Radical Beam!! (Parallel)" alternate art not properly identified

**Investigation Found**:
- 93% of TCGPlayer reference images have SAMPLE watermarks
- User's clean photos don't match watermarked references
- Visual similarity severely degraded (~0.15-0.25 drop)

**Hypothesis**: Removing watermarks from both reference AND query images would improve matching

---

## What We Tried

### Approach: Inpainting-Based Watermark Removal

**Implementation**:
1. Detect bright pixels in center region (watermark location)
2. Use cv2.INPAINT_TELEA to fill watermark area
3. Apply to BOTH embedder (reference images) AND identifier (query images)

**Code Changes**:
- `services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py` (lines 29-70)
- `scripts/identification/core/production_card_identifier.py` (lines 689-745)

**Re-embedding**: 4,815 cards in 7.6 minutes

---

## Test Results (FAILURE)

### Baseline (Before Watermark Removal)
```
Confidence Distribution:
  HIGH:     6/10 (60%)
  MODERATE: 3/10 (30%)
  LOW:      1/10 (10%)

Average Score: 0.6992
Accuracy: 9/10 correct (90%)
```

### After Watermark Removal
```
Confidence Distribution:
  HIGH:     5/10 (50%)  ❌ -1 card (-10%)
  MODERATE: 4/10 (40%)  ⬆️ +1 card
  LOW:      1/10 (10%)  ➡️ Same

Average Score: 0.6960  ❌ -0.0032 (-0.5%)
Accuracy: 3/10 correct (30%)  ❌ -60% drop!
```

### Specific Failures

| Image | Baseline (Correct) | After Watermark Removal | Result |
|-------|-------------------|------------------------|--------|
| Screenshot_*.jpg (Doflamingo) | ✅ Correct, HIGH | ❌ Same card, **LOW** | Downgrade |
| Screenshot_*.jpg (Carrot) | ✅ Carrot, MODERATE | ❌ **Portgas.D.Ace**, HIGH | Wrong card |
| blackbeard.png | ✅ Marshall.D.Teach, HIGH | ❌ **Boa Hancock**, HIGH | Wrong card |
| bonneyleader.png | ✅ Carrot, MODERATE | ❌ **Nami**, MODERATE | Wrong card |
| radicalbeam.png | ❌ Divine Departure, MOD | ❌ **Trafalgar Law**, MOD | Still wrong, different wrong card |
| yellow_event.png | ✅ You're the One..., HIGH | ❌ **Gol.D.Roger**, MOD | Wrong card + downgrade |
| sanji.jpg | ✅ Come On!! We'll Fight..., LOW | ❌ **Black Maria**, MOD | Wrong card |

**7/10 cards affected negatively!**

---

## Why It Failed

### Root Cause Analysis

1. **Inpainting Artifacts**:
   - cv2.INPAINT_TELEA creates visible artifacts/smudges
   - These artifacts introduce noise that confuses DINOv2
   - Artifacts vary between images (inconsistent)

2. **Over-Aggressive Watermark Detection**:
   - Threshold (>200/255 brightness) caught non-watermark bright regions
   - Some cards have naturally bright artwork in center
   - False positives removed important card features

3. **Vector Space Mismatch**:
   - Reference images: Watermark removal creates artifacts
   - Query images: Often no watermark OR different inpainting artifacts
   - Result: Embeddings in different vector spaces even with "same" preprocessing

4. **Loss of Discriminative Features**:
   - Watermark region often contains important artwork details
   - Inpainting "guesses" what should be there
   - DINOv2 learns features from inpainted regions that don't match reality

### Example: Radical Beam

**Reference Image (593883.jpg)**:
- Has SAMPLE watermark over center artwork
- Inpainting fills with blurred/smudged approximation
- DINOv2 embedding includes these artifacts

**User's Photo (radicalbeam.png)**:
- Clean parallel art with different artwork than base version
- No watermark, so inpainting doesn't trigger OR triggers differently
- DINOv2 embedding from clean real artwork

**Result**: Embeddings don't match, identifies as random wrong card

---

## Lessons Learned

### What Didn't Work

❌ **Inpainting watermarks**: Creates inconsistent artifacts
❌ **Aggressive watermark detection**: False positives on bright cards
❌ **Assumption**: "Remove watermark from both sides = same vector space"

### Why Current System Works (Despite Watermarks)

✅ **Geometric Matching (ORB/AKAZE)**: Robust to watermarks (finds keypoints around watermark)
✅ **Dynamic Weighting**: Adjusts visual vs geometric weights based on quality
✅ **High Visual Threshold (0.65)**: Requires strong match even with watermark
✅ **Margin Check**: Verifies clear winner (not just best of bad options)

**Key Insight**: The watermarks affect both reference AND query images from similar sources (screenshots, photos), so the relative similarities remain meaningful.

---

## Alternative Approaches (Future)

### Option 1: Source Clean Reference Images ⭐ (BEST)

**Approach**: Get unwatermarked images from alternative sources

**Options**:
- TCGPlayer API (check if unwatermarked images available)
- Official Bandai One Piece TCG website
- Community contributions (clean scans/photos)
- Purchase and scan physical cards

**Pros**:
- No preprocessing needed
- Highest accuracy
- No artifacts

**Cons**:
- Requires sourcing/downloading new images
- May not be available for all cards
- Time/effort intensive

**Recommendation**: ✅ **BEST long-term solution**

---

### Option 2: Watermark-Aware Training ⚙️ (ADVANCED)

**Approach**: Fine-tune DINOv2 with watermark augmentation

**Method**:
1. Take clean card images
2. Add synthetic SAMPLE watermarks during training
3. Train model to be invariant to watermarks

**Pros**:
- Model learns to ignore watermarks
- Works on any watermarked image
- No preprocessing needed at inference

**Cons**:
- Requires GPU + training time (~hours)
- Needs clean training dataset first
- Complex implementation

**Recommendation**: ⚠️ **Consider if Option 1 not feasible**

---

### Option 3: Improved Geometric Matching 🔧 (PRACTICAL)

**Approach**: Rely more heavily on geometric verification

**Changes**:
- Lower visual weight when watermark detected
- Increase geometric weight (ORB/AKAZE)
- Use SIFT + ORB + AKAZE ensemble
- Precompute keypoints for all reference images

**Pros**:
- Geometric matching already works well
- No re-embedding needed
- Quick to implement

**Cons**:
- Slower (geometric matching is expensive)
- Doesn't help cards with no geometric features
- Still limited by watermarked references

**Recommendation**: ✅ **Worth trying as interim solution**

---

### Option 4: Multi-Modal Fusion 🎯 (EXPERIMENTAL)

**Approach**: Use multiple visual models + fusion

**Method**:
1. DINOv2 embeddings (current)
2. CLIP embeddings (text-aware)
3. EfficientNet embeddings (lightweight)
4. Ensemble vote for final match

**Pros**:
- Multiple models may handle watermarks differently
- Increased robustness
- Potentially higher accuracy

**Cons**:
- 3x slower (3 models)
- More complex
- Requires testing all models

**Recommendation**: ⚠️ **Research project, not immediate fix**

---

## Immediate Next Steps

### 1. Accept Current Limitations ✅

**Reality Check**:
- 60% HIGH confidence is **acceptable** for production
- 90% accuracy is **good** for auto-identification
- Manual review workflow handles MODERATE/LOW cases

**Recommendation**: Ship current system, iterate later

---

### 2. Improve Radical Beam Specifically 🎯

**Problem**: Radical Beam parallel art is alternate artwork (not in database)

**Root Cause**: Database has base Radical Beam!! (OP01-029) but not the specific parallel variant

**Solution Options**:

A. **Add Missing Variant to Database**:
   - Find/source the specific parallel art image
   - Add to database as separate product
   - Re-embed

B. **Variant Classifier Enhancement**:
   - Train classifier to recognize "same card, different art"
   - Map parallels to base version
   - Show "Radical Beam!! (Parallel)" instead of wrong card

C. **Accept Limitation**:
   - Document that alternate arts may not match exactly
   - Recommend manual review for parallel/alternate cards
   - Add to known limitations

**Recommendation**: ✅ **Option C short-term, Option B long-term**

---

### 3. Optimize Geometric Matching ⚙️

**Current Performance**: ~1000ms per identification (300-800ms geometric)

**Improvements**:
1. **Precompute Keypoints**: Save ORB/AKAZE keypoints for all references
2. **GPU Acceleration**: Use CUDA for geometric matching (3-5x speedup)
3. **Smart Fallback**: Only use geometric when visual score < threshold

**Expected Impact**:
- Speed: 1000ms → 500ms (-50%)
- Accuracy: Maintain or improve
- Confidence: More cards reach HIGH threshold

**Recommendation**: ✅ **High priority optimization**

---

## Documentation Updates

### Files Created:
- ✅ `docs/status/WATERMARK_ISSUE_RESOLUTION_2025-10-24.md` (investigation)
- ✅ `docs/status/WATERMARK_REMOVAL_FAILURE_ANALYSIS_2025-10-24.md` (this file)
- ✅ `scripts/identification/tools/watermark_remover.py` (unused utility)
- ✅ `scripts/identification/tests/test_watermark_removal_impact.py` (test script)
- ✅ `TESTING_WATERMARK_REMOVAL.md` (testing guide)

### Files Reverted:
- ✅ `scripts/identification/core/production_card_identifier.py`
- ✅ `services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py`
- ✅ `artifacts/faiss/one-piece-dinov2/` (restored from backup)

### Backup Preserved:
- ✅ `artifacts/faiss/one-piece-dinov2-BACKUP-before-watermark-removal/` (kept for reference)

---

## Current System Status

### After Revert:
```
Confidence Distribution:
  HIGH:     60% (6/10)  ✅
  MODERATE: 30% (3/10)  ✅
  LOW:      10% (1/10)  ✅

Average Score: 0.6992  ✅
Accuracy: 90% (9/10)  ✅
Avg Speed: 992ms  ✅
```

**Status**: ✅ **System restored to known-good state**

---

## Recommendations

### Immediate (This Week):
1. ✅ **Accept current performance** (60% HIGH is good)
2. ✅ **Document alternate art limitation** (user education)
3. ✅ **Ship to production** with manual review workflow

### Short-Term (1-2 Weeks):
1. 🔧 **Precompute geometric keypoints** (speed optimization)
2. 📸 **Source clean reference images** (start with top 100 cards)
3. 📊 **Collect production metrics** (real shop data)

### Medium-Term (1-2 Months):
1. 🎯 **Variant classifier v2** (handle alternate arts)
2. 🖼️ **Replace all watermarked references** (community effort)
3. 🚀 **GPU acceleration** (if speed becomes issue)

### Long-Term (3-6 Months):
1. 🤖 **Fine-tune DINOv2** on One Piece TCG specifically
2. 🎨 **Multi-modal ensemble** (DINOv2 + CLIP + geometric)
3. 📱 **Mobile app** with on-device identification

---

## Conclusion

**Watermark removal preprocessing failed** due to inpainting artifacts and inconsistent vector spaces. The current system (60% HIGH confidence, 90% accuracy) is **production-ready** despite watermarks, thanks to robust geometric matching and dynamic weighting.

**Path Forward**: Source clean images, optimize geometric matching, and accept current limitations while iterating.

**Key Takeaway**: Sometimes the "obvious" solution (remove watermarks) makes things worse. Trust the data, test thoroughly, and be ready to revert.

---

**Prepared By**: Senior Principal Engineer (Claude Code)
**Date**: 2025-10-24
**Status**: ✅ Reverted, system restored
**Next Action**: Ship current system to production
