# Geometric Matching Improvements

> **Analysis Date**: 2025-10-21
> **Current Performance**: ORB geometric scoring at 300-665ms
> **Goal**: Improve accuracy and/or speed of geometric verification

---

## Current ORB Implementation Analysis

### Current Setup (production_card_identifier.py:665-748)

```python
orb = cv2.ORB_create(
    nfeatures=1000,      # Max keypoints
    scaleFactor=1.2,     # Pyramid scale
    nlevels=8,           # Pyramid levels
    edgeThreshold=15     # Edge threshold
)

# Lowe's ratio test: 0.80 threshold
# Scoring: match_ratio*0.5 + coverage*0.3 + distance_quality*0.2
# Amplification: score * 2.2
```

**Performance**:
- Good: Handles watermarks well
- Good: Works on angled images
- **Problem**: Fails on compressed images (0.0 score on Discord screenshots)
- **Problem**: Sometimes too sensitive (rejects valid matches)

---

## Proposed Improvements

### 🔥 Priority 1: SIFT as Alternative to ORB (Highest Impact)

**Why**: SIFT is more robust than ORB for TCG cards

| Feature | ORB | SIFT |
|---------|-----|------|
| **Speed** | Fast (~50-100ms) | Slower (~100-200ms) |
| **Accuracy** | Good | **Better** |
| **Rotation** | Good | **Excellent** |
| **Scale** | Good | **Excellent** |
| **Compressed Images** | **Poor** | Better |
| **Lighting Changes** | Good | **Excellent** |

**Expected Improvement**: +10-15% geometric scores on difficult images

**Implementation**: Hybrid approach - try ORB first, fallback to SIFT if low score

```python
def _compute_geometric_similarity_hybrid(self, query_img, candidate_img):
    """Try ORB first (fast), fallback to SIFT if needed (accurate)."""

    # Try ORB first (fast)
    orb_score = self._compute_orb_similarity(query_img, candidate_img)

    # If ORB works well, use it
    if orb_score > 0.15:
        return {
            'score': orb_score,
            'method': 'ORB',
            'fallback': False
        }

    # If ORB failed, try SIFT (more robust)
    sift_score = self._compute_sift_similarity(query_img, candidate_img)

    return {
        'score': sift_score,
        'method': 'SIFT',
        'fallback': True
    }
```

**Pros**:
- ✅ Best of both worlds (ORB speed + SIFT accuracy)
- ✅ Better on compressed images
- ✅ Better on lighting variations
- ✅ Only ~10-20% slower (SIFT used sparingly)

**Cons**:
- ⚠️ SIFT is patented (free for non-commercial, check licensing)
- ⚠️ Slightly more complex

---

### 🔥 Priority 2: AKAZE (Patent-Free SIFT Alternative)

**Why**: AKAZE is as good as SIFT, faster, and patent-free

**Performance**:
- Speed: ~80-120ms (between ORB and SIFT)
- Accuracy: ~95% of SIFT performance
- **No patent issues**

```python
akaze = cv2.AKAZE_create()
kp1, des1 = akaze.detectAndCompute(img1_gray, None)
kp2, des2 = akaze.detectAndCompute(img2_gray, None)
```

**Expected Improvement**: +8-12% on difficult images

**Pros**:
- ✅ Patent-free (can use commercially)
- ✅ Better than ORB on compressed images
- ✅ Good balance of speed and accuracy

---

### 🔥 Priority 3: Multi-Scale Geometric Matching

**Why**: Card photos often have different scales (camera distance varies)

**Current Problem**:
- Query image: 1080x720 (phone photo)
- Reference image: 600x600 (database)
- Scale mismatch reduces matches

**Solution**: Match at multiple scales

```python
def _compute_orb_multiscale(self, query_img, ref_img):
    """Match at multiple scales to handle distance variations."""

    scales = [1.0, 0.8, 1.2]  # Original, 80%, 120%
    best_score = 0

    for scale in scales:
        # Resize query to different scales
        h, w = query_img.shape[:2]
        scaled = cv2.resize(query_img, (int(w*scale), int(h*scale)))

        # Match at this scale
        score = self._compute_orb_similarity(scaled, ref_img)
        best_score = max(best_score, score)

    return best_score
```

**Expected Improvement**: +5-10% on real-world photos

**Overhead**: ~2-3x slower (but still <200ms)

---

### 🔥 Priority 4: RANSAC Geometric Verification

**Why**: Filter outliers from matches (more reliable scoring)

**Current Problem**: All matches treated equally, even bad ones

**Solution**: Use RANSAC to find geometric transformation

```python
def _compute_orb_with_ransac(self, query_img, ref_img):
    """Use RANSAC to verify geometric consistency."""

    # Get matches (same as before)
    good_matches = self._get_good_matches(kp1, des1, kp2, des2)

    if len(good_matches) < 4:
        return 0.0

    # Extract matched keypoint locations
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches])
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches])

    # Find homography with RANSAC
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if H is None:
        return 0.0

    # Count inliers (matches that fit the geometric transformation)
    inliers = np.sum(mask)
    inlier_ratio = inliers / len(good_matches)

    # Penalize if too few inliers
    if inlier_ratio < 0.5:
        return 0.0

    # Score based on inlier ratio and count
    score = (inlier_ratio * 0.6) + (inliers / len(kp1) * 0.4)

    return min(score * 1.5, 1.0)
```

**Expected Improvement**: +15-20% accuracy (fewer false positives)

**Pros**:
- ✅ Filters outlier matches
- ✅ More reliable scores
- ✅ Can detect if card is rotated/skewed

---

### 🔥 Priority 5: Pre-Computed Reference Keypoints (FAISS-style)

**Why**: ORB on reference images is slow and redundant

**Current**: Compute ORB for every reference image on every query (wasteful)

**Solution**: Pre-compute and store reference keypoints

```python
# During embedding phase (one-time)
def precompute_reference_keypoints():
    """Pre-compute ORB features for all reference images."""

    orb = cv2.ORB_create(nfeatures=1000)
    keypoints_db = {}

    for card_id in all_cards:
        img_path = f"data/images/one-piece/{card_id}.jpg"
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

        kp, des = orb.detectAndCompute(img, None)

        # Store in efficient format
        keypoints_db[card_id] = {
            'keypoints': [(k.pt, k.size, k.angle) for k in kp],
            'descriptors': des
        }

    # Save to file
    np.savez('artifacts/keypoints/one-piece-orb.npz', **keypoints_db)
```

**Expected Improvement**:
- Speed: 30-40% faster (300-665ms → 180-400ms)
- Accuracy: Same (no change)

**Pros**:
- ✅ Huge speed improvement
- ✅ No accuracy loss
- ✅ Works with any feature detector (ORB, SIFT, AKAZE)

**Cons**:
- ⚠️ Need to rebuild keypoints database when new cards added
- ⚠️ Storage: ~50-100 MB for keypoints

---

### 🔥 Priority 6: Adaptive Geometric Verification (Smart Skipping)

**Why**: Don't waste time on candidates that won't match

**Current**: Geometric verification on all top 20 candidates

**Solution**: Skip geometric if visual score is too low

```python
# In Stage 3 geometric verification
for candidate in top_20_candidates:
    visual_score = candidate['visual_score']

    # Skip geometric if visual score is too low
    # (No point verifying if visual already failed)
    if visual_score < 0.40:
        candidate['geometric_score'] = 0.0
        continue

    # Run geometric verification
    geom_score = self._compute_orb_similarity(...)
    candidate['geometric_score'] = geom_score
```

**Expected Improvement**:
- Speed: 20-30% faster (skip ~5-10 candidates)
- Accuracy: Same or better (don't waste time on junk)

---

### 🔥 Priority 7: Keypoint Region Weighting (Card-Specific)

**Why**: Not all parts of a card are equally important

**Insight**: Character faces and art are more distinctive than borders/text

```python
def _compute_orb_with_region_weights(self, query_img, ref_img):
    """Weight matches by importance of region."""

    # Get matches
    good_matches = self._get_good_matches(kp1, des1, kp2, des2)

    h, w = query_img.shape[:2]

    # Define important regions (card art area)
    # For TCG cards, center 60% contains character art
    center_x_min, center_x_max = w * 0.2, w * 0.8
    center_y_min, center_y_max = h * 0.2, h * 0.8

    weighted_score = 0
    total_weight = 0

    for m in good_matches:
        kp_query = kp1[m.queryIdx]
        x, y = kp_query.pt

        # Weight based on region
        if center_x_min < x < center_x_max and center_y_min < y < center_y_max:
            weight = 1.5  # Center region (art) more important
        else:
            weight = 0.8  # Border/text less important

        match_quality = 1.0 - (m.distance / 100.0)
        weighted_score += match_quality * weight
        total_weight += weight

    return weighted_score / total_weight if total_weight > 0 else 0.0
```

**Expected Improvement**: +5-8% on cards with similar borders

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)

**1. Pre-Computed Reference Keypoints** (Priority 5)
- Biggest speed improvement (30-40% faster)
- No accuracy trade-off
- Easy to implement

**2. Adaptive Geometric Verification** (Priority 6)
- Skip low-visual-score candidates
- 20-30% faster
- Simple change

**Combined Phase 1**: **50-70% faster geometric matching** (300-665ms → 150-350ms)

---

### Phase 2: Accuracy Improvements (2-3 days)

**3. AKAZE Hybrid** (Priority 2)
- Add AKAZE as fallback when ORB fails
- +8-12% accuracy on compressed images
- Patent-free

**4. RANSAC Verification** (Priority 4)
- Filter outlier matches
- +15-20% accuracy (fewer false positives)
- More reliable confidence scores

**Combined Phase 2**: **~20-30% accuracy improvement** on difficult images

---

### Phase 3: Advanced (Optional, 3-5 days)

**5. Multi-Scale Matching** (Priority 3)
- Handle scale variations better
- +5-10% on real-world photos

**6. Region Weighting** (Priority 7)
- Focus on important card regions
- +5-8% on similar cards

---

## Expected Overall Impact

### After Phase 1 (Speed Focused):
```
Geometric verification time: 300-665ms → 150-350ms (50-70% faster)
Total identification time: 500-835ms → 350-520ms (30-40% faster)
Accuracy: No change (maintained)
```

### After Phase 2 (Accuracy Focused):
```
Geometric scores on compressed images: 0.00 → 0.05-0.15 (+10-15%)
HIGH confidence rate: 28.6% → 40-50% (+11-21%)
False positive rate: Reduced by ~15-20%
```

### After Phase 3 (Polished):
```
Overall accuracy: +5-10% additional improvement
Robustness: Better on edge cases (angles, scale, lighting)
```

---

## Code Changes Required

### 1. Pre-Compute Keypoints Script

Create `scripts/identification/precompute_keypoints.py`:
```python
#!/usr/bin/env python3
"""Pre-compute ORB/AKAZE keypoints for all reference images."""

import cv2
import numpy as np
from pathlib import Path
import json
from tqdm import tqdm

def precompute_keypoints(game='one-piece', method='ORB'):
    """Pre-compute keypoints for all cards."""

    images_dir = Path(f'data/images/{game}')
    cards_jsonl = Path(f'data/curated/{game}.jsonl')
    output_dir = Path(f'artifacts/keypoints/{game}')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create detector
    if method == 'ORB':
        detector = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, nlevels=8)
    elif method == 'AKAZE':
        detector = cv2.AKAZE_create()

    # Load card IDs
    card_ids = []
    with open(cards_jsonl, 'r') as f:
        for line in f:
            card = json.loads(line)
            card_ids.append(str(card['productId']))

    # Compute keypoints
    keypoints_db = {}

    for card_id in tqdm(card_ids, desc=f"Computing {method} keypoints"):
        img_path = images_dir / f"{card_id}.jpg"

        if not img_path.exists():
            continue

        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        kp, des = detector.detectAndCompute(img, None)

        if des is not None:
            # Store keypoints and descriptors
            keypoints_db[card_id] = {
                'num_keypoints': len(kp),
                'descriptors': des
            }

    # Save
    output_file = output_dir / f'{method.lower()}_keypoints.npz'
    np.savez_compressed(str(output_file), **keypoints_db)

    print(f"\nSaved {len(keypoints_db)} card keypoints to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    precompute_keypoints(method='ORB')
    precompute_keypoints(method='AKAZE')
```

### 2. Update Identifier to Use Pre-Computed Keypoints

Modify `production_card_identifier.py`:
```python
def __init__(self, ...):
    # Load pre-computed keypoints
    keypoints_path = Path(f'artifacts/keypoints/{game}/orb_keypoints.npz')
    if keypoints_path.exists():
        self.precomputed_keypoints = np.load(keypoints_path, allow_pickle=True)
        print(f"  Loaded pre-computed keypoints for {len(self.precomputed_keypoints.files)} cards")
    else:
        self.precomputed_keypoints = None

def _compute_orb_similarity(self, query_path, ref_card_id):
    """Use pre-computed reference keypoints if available."""

    # Query image (compute on-the-fly)
    query_img = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
    orb = cv2.ORB_create(nfeatures=1000)
    kp1, des1 = orb.detectAndCompute(query_img, None)

    # Reference image (use pre-computed if available)
    if self.precomputed_keypoints and ref_card_id in self.precomputed_keypoints:
        ref_data = self.precomputed_keypoints[ref_card_id].item()
        des2 = ref_data['descriptors']
    else:
        # Fallback: compute on-the-fly
        ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        kp2, des2 = orb.detectAndCompute(ref_img, None)

    # Match (same as before)
    ...
```

---

## Testing Plan

1. **Implement Phase 1** (pre-computed keypoints + adaptive skipping)
2. **Run test suite**: `python test_production_suite.py`
3. **Compare**: V1 baseline vs V1+Phase1
4. **If successful**: Deploy Phase 1
5. **Implement Phase 2** (AKAZE + RANSAC)
6. **Test again**
7. **Deploy if improved**

---

## Bottom Line

**Quick wins available**:
- Pre-compute keypoints: **50-70% faster** (1 day work)
- Adaptive skipping: **20-30% faster** (2 hours work)
- AKAZE hybrid: **+10-15% accuracy** on compressed images (1-2 days)

**Combined**: Geometric matching goes from **300-665ms → 150-350ms** while improving accuracy on difficult images by **~20-30%**.

This complements fine-tuning nicely:
- **Fine-tuning**: Improves visual similarity (+15-25%)
- **Geometric improvements**: Improves verification (+20-30% on difficult cases)
- **Combined**: Could reach **80-90% HIGH confidence** rate

---

**Status**: Analysis complete, ready to implement
**Recommendation**: Start with Phase 1 (speed) while model trains

_Analysis Date: 2025-10-21_
_Author: Senior Principal Engineer via Claude Code_
