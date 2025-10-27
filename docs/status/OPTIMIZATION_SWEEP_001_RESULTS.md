# Optimization Sweep #001: Results & Analysis

**Date**: 2025-10-27
**Sweep**: Geometric Verification Boost
**Status**: ❌ NO IMPROVEMENT - Revert to Baseline

---

## 🎯 Hypothesis

**Problem**: Angled/poor lighting images fail (0% accuracy on sanji.jpg, bonneyleader.png, radicalbeam.png)

**Hypothesis**: Geometric matching is weak - boost ORB features and verification depth

**Expected**: +20-30% accuracy on challenging images

---

## 🔬 Experimental Design

**Parameters Tested**:
- `orb_nfeatures`: [1000, 1500, 2000]
- `orb_verify_top_n`: [10, 15, 20]
- `orb_lowe_ratio`: [0.75, 0.80, 0.85]

**Configurations**: 3 × 3 × 3 = 27 configs
**Completed**: 27/27
**Baseline**: run_1761580678_baseline_1761580664 (70% accuracy)

---

## 📊 Results

**Best Configuration**: Same as baseline (70% accuracy, no improvement)

All 27 configurations tested:
- Top-1 Accuracy: **70.0%** (same as baseline)
- Average Time: 949-1006ms (slightly slower due to more ORB features)
- Same 3 failures: sanji.jpg, bonneyleader.png, radicalbeam.png

**Conclusion**: Tweaking ORB parameters had **ZERO** impact on accuracy.

---

## 💡 Key Insights

###  1. **Root Cause Identified**
The problem is NOT geometric matching. The issue is that **the correct card never appears in the top visual candidates** from FAISS search.

Looking at the failures:
- **bonneyleader.png** (Jewelry Bonney): Correct card not in top-50 visual matches
- **radicalbeam.png** (Radical Beam): Correct card at rank #2, but geometric matching weak
- **sanji.jpg** (Sanji): Correct card not in top-50 visual matches

### 2. **ORB is Already Working**
On images where the correct card IS in top-50 (like blackbeard.png, mihawk.png), ORB successfully boosts it to #1. The problem is when it's not there at all.

### 3. **Visual Embeddings are the Bottleneck**
DINOv2 embeddings with current preprocessing are not robust enough to:
- Handle extreme angles (sanji.jpg)
- Distinguish leader variants (bonneyleader.png)
- Match event cards (radicalbeam.png)

---

## 🚫 Decision: REVERT

**No improvement found** → Keep baseline configuration

Increasing ORB features from 1000 → 2000 adds 50ms with zero accuracy gain.

---

## 📋 Next Steps

### Short-Term: Fix Visual Embeddings
The real problem is DINOv2 preprocessing for challenging images.

**New Hypothesis**: Current bilateral filter + contrast enhancement is insufficient for:
1. **Angled images**: Need rotation normalization or better feature extraction
2. **Dark images**: Need stronger contrast boost
3. **Leader cards**: Need better handling of card variants

**Recommended Sweep #002**:
```python
PARAM_RANGES = {
    # Test stronger preprocessing
    "dinov2_bilateral_d": [3, 5, 7, 9],  # Larger filter = more smoothing
    "dinov2_bilateral_sigma_color": [30, 50, 70, 90],  # Color smoothing
    "dinov2_contrast_alpha": [1.0, 1.05, 1.10, 1.15, 1.20],  # Contrast boost

    # Test retrieving more candidates
    "faiss_top_k": [50, 75, 100, 150],  # Maybe we're filtering out correct card too early
}
```

### Medium-Term: Alternative Approaches
1. **Fine-tune DINOv2** on TCG cards (requires labeled dataset)
2. **Add rotation augmentation** during embedding generation
3. **Test different vision models** (CLIP, EfficientNet, ResNet)
4. **Ensemble multiple models** for robustness

### Long-Term: Architectural Changes
1. **Two-stage identification**:
   - Stage 1: Coarse visual search (current DINOv2)
   - Stage 2: Fine-grained variant classifier
2. **Add OCR-first strategy** for text-heavy cards
3. **Build card-specific classifiers** (leaders vs characters vs events)

---

## 📝 Lessons Learned

1. **Hypothesis Testing Works**: We proved ORB tuning doesn't help → Now know to focus elsewhere

2. **Small Test Set Limitations**: 10 images makes it hard to see small improvements. Need 50-100 for better signal.

3. **Root Cause Analysis Critical**: Don't optimize the wrong component. Always check where the failure actually occurs.

4. **Baseline Comparison Essential**: Framework made it easy to see "no improvement" immediately.

---

## ✅ Action Items

- [ ] Revert to baseline configuration (no code changes needed - baseline still best)
- [ ] Design Sweep #002 focusing on preprocessing/top-K
- [ ] Expand test set to 50+ images for better validation
- [ ] Analyze individual failure cases more deeply

---

**Sweep #001 Complete**: 2025-10-27
**Result**: No improvement, valuable learning
**Time Invested**: ~30 minutes
**Next**: Focus on visual embedding quality, not geometric matching

