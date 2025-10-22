# Distance Detection Improvements - 1 Foot Challenge

> **Goal**: Enable reliable card identification from ~1 foot (30cm) camera distance
> **Current**: 100% accuracy at close range, LOW confidence (0.48-0.60) at distance
> **Target**: 80%+ HIGH confidence at 1-foot distance

---

## Problem Analysis

### Current Test Results (from distance/compressed images):

| Image | Resolution | Score | Confidence | Geometric | Issue |
|-------|-----------|-------|------------|-----------|-------|
| Screenshot_20251021_085328 | 251x192 | 0.519 | LOW | 0.00 | Too small, compressed |
| Screenshot_20251021_085344 | 251x192 | 0.484 | LOW | 0.318 | Too small, compressed |
| Screenshot_20251021_085357 | 259x185 | 0.605 | LOW | 0.00 | Too small, compressed |

### Close-up Test Results (baseline):

| Image | Resolution | Score | Confidence | Geometric | Status |
|-------|-----------|-------|------------|-----------|--------|
| bege.png | ~600x800 | 0.871 | HIGH | 0.834 | ✅ Perfect |
| blackbeard.png | 148x215 | 0.690 | MODERATE | 0.436 | ⚠️ Small but works |
| yellow_event.png | ~600x800 | 0.573 | LOW | 0.00 | ⚠️ Text-heavy card |

### Root Causes:

1. **Resolution Loss**: 1-foot distance → 200-300px captures vs 600x600px references
2. **Motion Blur**: Natural hand shake at distance
3. **Focus Issues**: Camera autofocus struggles with cards at 30cm
4. **Compression**: Real captures have JPEG artifacts
5. **Geometric Failure**: ORB can't find enough features at low resolution (0.0 score)

---

## Solution Strategy

### Phase 1: Camera & Capture Quality (Immediate Impact)
**Goal**: Get higher resolution captures from 1-foot distance

#### 1.1 Force High-Resolution Capture
**Location**: `apps/desktop/src/renderer/components/CameraView.tsx:56-69`

**Current**:
```typescript
video: {
  width: { ideal: 1920, min: 1280 },
  height: { ideal: 1080, min: 720 },
  focusDistance: { ideal: 0.3 }, // 30cm
}
```

**Improvement**: Add **digital zoom** to capture cards at higher effective resolution

```typescript
video: {
  width: { ideal: 3840, min: 1920 },  // Request 4K if available
  height: { ideal: 2160, min: 1080 }, // Request 4K if available
  focusDistance: { ideal: 0.3 },      // Keep 30cm focus
  zoom: { ideal: 2.0 },                // 2x digital zoom for card focus
}
```

**Expected**: Card at 1-foot becomes 400-600px effective resolution (2-3x improvement)

#### 1.2 Add Capture Sharpness Filter
**Location**: `apps/desktop/src/renderer/components/CameraView.tsx` (capture function)

**Add**: Real-time sharpness detection to guide user

```typescript
// After capture, check if sharp enough
const sharpness = await window.electron.checkImageSharpness(imagePath);

if (sharpness < 50) {
  showWarning("Hold camera steady - image blurry");
  return; // Don't send to identifier
}
```

**Expected**: Reject blurry captures, encourage better positioning

#### 1.3 Multi-Frame Burst Capture
**Location**: `apps/desktop/src/main/index.ts` (capture handler)

**Current**: Single frame capture
**Improvement**: Capture 3 frames in 0.5s, pick sharpest

```typescript
async function captureBurst(): Promise<string> {
  const frames = [];

  // Capture 3 frames over 0.5s
  for (let i = 0; i < 3; i++) {
    const frame = await captureFrame();
    const sharpness = await checkSharpness(frame);
    frames.push({ path: frame, sharpness });
    await sleep(167); // 167ms = 0.5s / 3 frames
  }

  // Return sharpest frame
  frames.sort((a, b) => b.sharpness - a.sharpness);
  return frames[0].path;
}
```

**Expected**: Always get the sharpest moment, compensate for hand shake

---

### Phase 2: Preprocessing Pipeline (High Impact)
**Goal**: Enhance low-resolution captures before identification

#### 2.1 Super-Resolution Upscaling
**Location**: `scripts/identification/production_card_identifier.py:646-676`

**Add before DINOv2 embedding**:

```python
def _preprocess_query_image(self, image_path: str) -> np.ndarray:
    """Enhanced preprocessing for distance captures."""

    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # 1. Super-resolution upscaling if too small
    if min(h, w) < 400:
        # Use EDSR (Enhanced Deep Super-Resolution) or simple bicubic
        scale_factor = 400 / min(h, w)
        image = cv2.resize(
            image,
            None,
            fx=scale_factor,
            fy=scale_factor,
            interpolation=cv2.INTER_CUBIC  # Better than LANCZOS for small->large
        )

        # Optional: Apply EDSR model for AI upscaling (if available)
        # sr_model = cv2.dnn_superres.DnnSuperResImpl_create()
        # sr_model.readModel("EDSR_x2.pb")
        # image = sr_model.upsample(image)

    # 2. Aggressive sharpening for distance blur
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    image = cv2.filter2D(image, -1, kernel)

    # 3. Bilateral filter (already present, keep it)
    filtered = cv2.bilateralFilter(image, 5, 50, 50)

    # 4. Contrast enhancement (already present, keep it)
    enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)

    # 5. JPEG artifact removal (for compressed images)
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)

    return denoised
```

**Expected**:
- 200px capture → 400px effective resolution
- Remove blur and compression artifacts
- +10-15% visual similarity on distance captures

#### 2.2 Adaptive Preprocessing Based on Quality
**Location**: Same function, add quality detection

```python
def _preprocess_query_image(self, image_path: str) -> np.ndarray:
    """Adaptive preprocessing based on image quality."""

    image = cv2.imread(image_path)
    quality = self._check_image_quality(image_path)

    # Low quality (distance/compressed) - aggressive enhancement
    if quality['sharpness_score'] < 100 or quality['brightness'] < 80:
        image = self._enhance_low_quality(image)  # Super-res + sharpening

    # High quality (close-up) - minimal processing
    else:
        image = self._enhance_high_quality(image)  # Just bilateral + contrast

    return image
```

**Expected**: Don't over-process good images, focus on bad ones

---

### Phase 3: Geometric Matching Overhaul (Highest Impact)
**Goal**: Fix 0.0 geometric scores on distance captures

#### 3.1 Pre-Computed Keypoints (ALREADY EXISTS!)
**Location**: `scripts/identification/precompute_keypoints.py`

**Action**: Run this script to generate keypoints database

```bash
python scripts/identification/precompute_keypoints.py
```

**Expected**:
- 50-70% faster geometric matching (300-665ms → 150-350ms)
- More consistent results

#### 3.2 AKAZE Hybrid Fallback
**Location**: `scripts/identification/production_card_identifier.py:678-786`

**Current**: ORB only (fails on compressed/small images)
**Improvement**: Try AKAZE if ORB fails

```python
def _compute_geometric_similarity(self, query_path, ref_path):
    """Hybrid ORB → AKAZE fallback."""

    # Try ORB first (fast)
    orb_score = self._compute_orb_similarity(query_path, ref_path)

    # If ORB works, use it
    if orb_score > 0.10:
        return orb_score

    # If ORB failed (0.0 score), try AKAZE (more robust)
    akaze_score = self._compute_akaze_similarity(query_path, ref_path)

    return akaze_score

def _compute_akaze_similarity(self, query_path, ref_path):
    """AKAZE matching (better for low-res/compressed images)."""

    img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)

    # Create AKAZE detector
    akaze = cv2.AKAZE_create()
    kp1, des1 = akaze.detectAndCompute(img1, None)
    kp2, des2 = akaze.detectAndCompute(img2, None)

    if des1 is None or des2 is None or len(des1) < 8:
        return 0.0

    # Match with BFMatcher (AKAZE uses binary descriptors like ORB)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Lowe's ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    if len(good_matches) < 8:
        return 0.0

    # Score (same logic as ORB)
    match_ratio = len(good_matches) / max(len(kp1), len(kp2))
    coverage_ratio = len(good_matches) / min(len(kp1), len(kp2))
    avg_distance = np.mean([m.distance for m in good_matches])
    distance_quality = 1.0 / (1.0 + avg_distance / 40.0)

    score = (match_ratio * 0.5 + coverage_ratio * 0.3 + distance_quality * 0.2) * 2.2

    return min(score, 1.0)
```

**Expected**:
- Rescue 0.0 geometric scores → 0.10-0.25 scores
- +15-20% overall accuracy on distance captures

#### 3.3 Multi-Scale Matching
**For distance variations** (card closer/farther than expected)

```python
def _compute_geometric_similarity_multiscale(self, query_img, ref_img):
    """Try matching at multiple scales (handles distance variation)."""

    scales = [1.0, 0.7, 1.3]  # Original, 70%, 130%
    best_score = 0

    for scale in scales:
        # Resize query image
        h, w = query_img.shape[:2]
        scaled = cv2.resize(query_img, (int(w*scale), int(h*scale)))

        # Try ORB at this scale
        score = self._compute_orb_similarity(scaled, ref_img)
        best_score = max(best_score, score)

        if best_score > 0.3:  # Early exit if good match found
            break

    return best_score
```

**Expected**: +5-10% on cards at varying distances

---

### Phase 4: Confidence & Scoring Adjustments
**Goal**: Better confidence assignment for distance captures

#### 4.1 Adjust Thresholds for Low-Res Images
**Location**: `production_card_identifier.py:589-615`

**Current**:
```python
THRESHOLD_HIGH = 0.70
THRESHOLD_MODERATE = 0.55
```

**Improvement**: Adaptive thresholds based on image quality

```python
def _determine_confidence(self, best_match, quality_check):
    """Adaptive confidence based on image quality."""

    score = best_match['final_score']
    margin = best_match['final_score'] - second_best['final_score']

    # For low-quality images (distance captures), be more lenient
    if quality_check['sharpness_score'] < 100:
        THRESHOLD_HIGH = 0.65      # Lower from 0.70
        THRESHOLD_MODERATE = 0.50  # Lower from 0.55
    else:
        THRESHOLD_HIGH = 0.70
        THRESHOLD_MODERATE = 0.55

    # Apply confidence logic with adjusted thresholds
    if score >= THRESHOLD_HIGH:
        return "HIGH"
    elif score >= THRESHOLD_MODERATE and margin >= 0.08:
        return "HIGH"
    elif score >= THRESHOLD_MODERATE:
        return "MODERATE"
    else:
        return "LOW"
```

**Expected**: More realistic confidence on distance captures

---

## Implementation Plan

### Week 2: Distance Detection Sprint

#### Day 1 (Monday): Camera Quality
- [ ] Upgrade camera resolution to 4K (1 hour)
- [ ] Add digital zoom for card focus (1 hour)
- [ ] Implement burst capture mode (2 hours)
- [ ] Test with real 1-foot distance captures (1 hour)

**Expected**: 2-3x higher resolution captures

#### Day 2 (Tuesday): Preprocessing Pipeline
- [ ] Add super-resolution upscaling (2 hours)
- [ ] Implement aggressive sharpening (1 hour)
- [ ] Add JPEG artifact removal (1 hour)
- [ ] Test on current distance captures (1 hour)

**Expected**: +10-15% visual similarity improvement

#### Day 3 (Wednesday): Geometric Overhaul
- [ ] Run precompute_keypoints.py (10 minutes)
- [ ] Implement AKAZE hybrid fallback (3 hours)
- [ ] Add multi-scale matching (2 hours)
- [ ] Test geometric scores on distance captures (1 hour)

**Expected**: 0.0 → 0.10-0.25 geometric scores

#### Day 4 (Thursday): Integration & Testing
- [ ] Wire up adaptive thresholds (1 hour)
- [ ] Full end-to-end testing (3 hours)
- [ ] Create test suite with distance captures (2 hours)

**Expected**: Full system working at 1-foot distance

#### Day 5 (Friday): Version Control & Release
- [ ] Create version 1.1.0 with semantic versioning (1 hour)
- [ ] Update documentation (1 hour)
- [ ] Build desktop app v0.3.0 (1 hour)
- [ ] Final validation testing (2 hours)

**Expected**: Production-ready v1.1.0 release

---

## Expected Results

### Before (Current State):
```
Distance captures (200-300px):
- Visual similarity: 0.48-0.60
- Geometric score: 0.0-0.32
- Confidence: LOW
- Accuracy: ~20-40% (unusable)
```

### After (Week 2 Complete):
```
Distance captures (400-600px effective):
- Visual similarity: 0.65-0.80 (+20-35%)
- Geometric score: 0.15-0.40 (+15-40%)
- Confidence: MODERATE-HIGH
- Accuracy: 70-85% (usable!)
```

---

## Versioning Strategy

### v1.0.0 (Current)
- 100% accuracy at close range
- Visual-heavy weighting (75/25-95/05)
- Lowered thresholds (0.70/0.55)
- Fails at distance (LOW confidence)

### v1.1.0 (Week 2 Target)
- **NEW**: 4K camera + digital zoom
- **NEW**: Super-resolution preprocessing
- **NEW**: AKAZE hybrid geometric matching
- **NEW**: Adaptive confidence thresholds
- **IMPROVED**: 70-85% accuracy at 1-foot distance

### v1.2.0 (Future - Week 3)
- Multi-frame fusion in production
- Fine-tuned DINOv2 model
- 90%+ accuracy at 1-foot distance

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| 4K camera not available | HIGH | Fallback to 1080p + aggressive upscaling |
| AKAZE slower than ORB | MEDIUM | Use hybrid (ORB first, AKAZE fallback) |
| Over-sharpening artifacts | LOW | Adaptive preprocessing based on quality |
| Threshold changes affect close-up | LOW | Adaptive thresholds (separate for distance/close) |

---

## Testing Checklist

### Must Pass (90% required):
- [  ] 6 existing test images maintain HIGH/MODERATE confidence
- [  ] 10 new 1-foot distance captures: ≥7 MODERATE-HIGH confidence
- [  ] Geometric scores improve from 0.0 to ≥0.10 on distance captures
- [  ] No regression on close-up captures
- [  ] Total identification time ≤1000ms (no worse than current)

### Nice to Have:
- [  ] 1-foot captures reach 80%+ HIGH confidence
- [  ] Geometric matching <400ms with pre-computed keypoints
- [  ] Multi-frame burst capture working in desktop app

---

## Files to Modify

1. `apps/desktop/src/renderer/components/CameraView.tsx` - Camera resolution + zoom
2. `apps/desktop/src/main/index.ts` - Burst capture mode
3. `scripts/identification/production_card_identifier.py` - Preprocessing + AKAZE
4. `scripts/identification/test_distance_detection.py` - New test suite
5. `package.json` - Version bump to 1.1.0
6. `apps/desktop/package.json` - Desktop version to 0.3.0

---

**Status**: Plan ready, awaiting approval to implement
**Estimated Time**: 5 days (Week 2)
**Expected Outcome**: 70-85% accuracy at 1-foot distance

**Last Updated**: 2025-10-22
**Author**: Senior Principal Engineer via Claude Code
