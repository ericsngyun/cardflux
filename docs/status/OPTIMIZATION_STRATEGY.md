# Optimization Strategy - Data-Driven Approach

**Date**: 2025-10-27
**Current Status**: Running Sweep #003 (Focused High-Impact)

---

## 🎯 Problem Statement

**Current Performance**: 70% accuracy (7/10 correct)

**Failures**:
1. `bonneyleader.png` - Jewelry Bonney (OP05-046) → Predicted Carrot (OP08-023)
2. `radicalbeam.png` - Radical Beam (OP03-057) → Predicted Divine Departure (OP10-019) [GT at rank #2!]
3. `sanji.jpg` - Sanji (OP04-104) → Predicted Come On!! (OP09-020)

---

## 📊 Root Cause Analysis

### Sweep #001: ORB Tuning (FAILED)
**Hypothesis**: Geometric matching too weak
**Test**: Varied orb_nfeatures (1000-2000), orb_verify_top_n (10-20), orb_lowe_ratio (0.75-0.85)
**Result**: 27/27 configs = 70% accuracy (ZERO improvement)
**Learning**: **ORB is NOT the bottleneck**

### Deep Dive: Where Are The Failures?
Analyzed the actual failure modes:

**bonneyleader.png**:
- Ground truth (OP05-046) **NOT in top-50** visual candidates
- System predicted OP08-023 instead
- Issue: **Visual search** failing to retrieve correct card

**radicalbeam.png**:
- Ground truth (OP03-057) **at rank #2** in visual search!
- But geometric matching scored it lower than #1
- Issue: **Score fusion** or geometric matching

**sanji.jpg**:
- Ground truth (OP04-104) **NOT in top-50** visual candidates
- Very low score (0.5442) - marked as LOW confidence
- Issue: **Preprocessing** - image is angled and dark

---

## 💡 Strategic Insights

### 1. Visual Search is the Primary Bottleneck
**2 out of 3 failures** have correct card not in top-50 candidates.

If DINOv2 doesn't put the card in top-50, no amount of ORB tuning will help.

**Solution**:
- Increase `faiss_top_k` from 50 → 100-150
- Improve preprocessing for better embeddings

### 2. Preprocessing Needs Improvement
**sanji.jpg** is angled and dark - current preprocessing insufficient.

Current:
```python
bilateral_filter(d=5, sigma=50, 50)
contrast(alpha=1.05, beta=3)
```

**Solution**:
- Increase contrast boost: `alpha=1.10-1.20`
- Test stronger filtering

### 3. Confidence Thresholds May Be Too Conservative
Currently:
- HIGH threshold: 0.65
- MODERATE threshold: 0.55

**60% HIGH confidence rate** is good, but could be higher.

**Solution**:
- Lower HIGH threshold to 0.60-0.62
- More cards marked HIGH = better user experience

---

## 🔬 Sweep #003: Focused High-Impact Design

**Strategy**: Multi-pronged attack on the actual root causes

**Parameters**:
```python
"faiss_top_k": [75, 100, 150],          # Baseline: 50
"dinov2_contrast_alpha": [1.10, 1.15, 1.20],  # Baseline: 1.05
"threshold_high": [0.60, 0.62, 0.65],    # Baseline: 0.65
```

**Expected Impact**:
- `faiss_top_k=150`: +10-20% accuracy (correct cards now in candidates)
- `contrast_alpha=1.20`: +5-10% on dark images
- `threshold_high=0.60`: +10-20% HIGH confidence rate

**Target**: 70% → 80-90% accuracy (8-9 out of 10 correct)

---

## 📈 Success Metrics

**Minimum Success** (Deploy):
- Top-1 accuracy ≥ 80% (+10% improvement)
- No regression on currently correct images
- Speed ≤ 1200ms (acceptable slowdown for accuracy)

**Ideal Success** (Celebrate):
- Top-1 accuracy ≥ 90% (+20% improvement)
- HIGH confidence rate ≥ 70%
- Speed ≤ 1100ms

**Failure** (Revert):
- Top-1 accuracy < 75% (<5% improvement)
- Keep baseline configuration
- Try different strategy

---

## 🚀 If Sweep #003 Succeeds

1. **Deploy Best Config**: Apply to production identifier
2. **Validate on More Images**: Test on 50-100 card set
3. **Document Changes**: Update production docs
4. **Commit to Git**: Clean commit with results

---

## 🔄 If Sweep #003 Fails

**Next Strategies** (in order of priority):

### Strategy A: Fine-Tune DINOv2
- Fine-tune dinov2-small on TCG cards
- Requires labeled dataset (500-1000 cards)
- Expected: +20-30% accuracy

### Strategy B: Ensemble Approach
- Combine DINOv2 + CLIP embeddings
- Vote or weighted average
- Expected: +10-20% accuracy

### Strategy C: Architectural Change
- Two-stage: Coarse search → Fine-grained classifier
- Build variant-specific classifiers
- Expected: +15-25% accuracy

### Strategy D: Data Quality
- Expand test set to 50-100 images
- Verify ground truth labels
- May discover labeling errors

---

## 🎓 Optimization Philosophy

1. **Test One Hypothesis at a Time**: Sweep #001 proved ORB isn't the issue
2. **Follow the Data**: Failures told us where to focus
3. **Small, Focused Sweeps**: 27 configs = manageable + interpretable
4. **Always Have a Revert Plan**: Baseline is safe, can rollback anytime
5. **Document Everything**: Git + reports = full reproducibility

---

## 📊 Current Optimization Pipeline

```
Baseline (70%)
    ↓
Sweep #001: ORB Tuning
    ├─ Result: No improvement
    ├─ Learning: ORB not bottleneck
    └─ Decision: Focus on visual search
        ↓
Sweep #003: Focused (TOP-K + Contrast + Thresholds) [RUNNING]
    ├─ Expected: 80-90% accuracy
    ├─ If Success: Deploy to production
    └─ If Failure: Try Strategy A/B/C
```

---

**Status**: Sweep #003 running (27 configs, ~30 min)
**Next Update**: After sweep completion
**Decision Point**: Deploy best config or revert to baseline

