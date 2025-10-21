# Confidence Level Improvement Plan

> **Date**: 2025-10-21
> **Goal**: Improve identification confidence on real-world camera captures
> **Current**: 16.7% HIGH confidence on test images (1/6)
> **Target**: 60%+ HIGH confidence on real-world images

---

## Root Cause Analysis

### Current Test Results

| Image | Type | V1 Confidence | V1 Score | Issues |
|-------|------|---------------|----------|--------|
| bege.png | Clean scan | HIGH | 0.872 | ✅ Perfect |
| blackbeard.png | Clean scan | MODERATE | 0.689 | Borderline |
| yellow_event.png | Real photo | MODERATE | 0.571 | Glare, angle, sleeve |
| 3x Discord screenshots | Low-res | LOW | 0.48-0.60 | Compressed, low quality |

### Key Problems

1. **Real-world photo challenges**:
   - Glare from card sleeves (yellow_event.png shows this)
   - Camera angle/perspective distortion
   - Variable lighting conditions
   - Distance from card (smaller in frame)

2. **Reference image quality**:
   - Currently: 600x600 JPG (65 KB)
   - Available: 800x800 (103 KB, +58% larger)
   - Available: 1000x1000 (145 KB, +120% larger)

3. **Preprocessing mismatch for real photos**:
   - Current preprocessing optimized for clean scans
   - Real photos need: glare removal, perspective correction, denoising

4. **Low geometric matching on event cards**:
   - yellow_event.png: Geometric = 0.517 (moderate)
   - Busy artwork → fewer distinctive ORB features
   - Text-heavy cards harder to match geometrically

---

## Improvement Strategies

### Strategy 1: Higher Resolution Embeddings ⭐⭐⭐⭐⭐

**Impact**: HIGH | **Effort**: MEDIUM | **Risk**: LOW

**Rationale**:
- DINOv2 trained on 224x224 images (we resize to 224x224)
- More detail in source → better features after resize
- 800x800 has 58% more data, 1000x1000 has 120% more

**Implementation**:
```typescript
// In tcgplayer-config.ts
export function transformImageUrl(url: string): string {
  const productId = match[1];
  // Change from 600x600 → 800x800
  return `https://tcgplayer-cdn.tcgplayer.com/product/${productId}_in_800x800.jpg`;
}
```

**Pros**:
- More detail preserved during resize to 224x224
- Better feature extraction
- No algorithm changes needed
- Backward compatible (just re-embed)

**Cons**:
- Re-download images (~250 MB → 400 MB for 4,813 cards)
- Re-generate embeddings (~5 min)
- Slower downloads (1.5x longer)

**Expected Improvement**: +5-10% accuracy, +0.03-0.05 score boost

---

### Strategy 2: Enhanced Preprocessing for Real Photos ⭐⭐⭐⭐

**Impact**: HIGH | **Effort**: MEDIUM | **Risk**: MEDIUM

**Problem**: Current preprocessing assumes clean scans, not real photos with glare/angles

**Implementation**:
```python
# In production_card_identifier_v2.py

def _enhanced_real_world_preprocessing(self, img_array):
    """Enhanced preprocessing for real-world camera captures."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # 1. Glare detection and removal
    glare_mask = self._detect_glare(gray)
    if glare_mask.sum() > 0.05 * gray.size:  # >5% glare
        img_array = self._remove_glare(img_array, glare_mask)

    # 2. Perspective correction (if card is tilted)
    if self._needs_perspective_correction(gray):
        img_array = self._correct_perspective(img_array)

    # 3. Denoising for low-light/high-ISO
    if np.std(gray) > 60:  # Noisy image
        img_array = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)

    # 4. Adaptive enhancement (existing V2 logic)
    return self._adaptive_preprocess(img_array)

def _detect_glare(self, gray):
    """Detect glare/highlights in image."""
    # High brightness regions (>240)
    glare_mask = (gray > 240).astype(np.uint8)
    # Dilate to capture full glare region
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    return cv2.dilate(glare_mask, kernel, iterations=2)

def _remove_glare(self, img, mask):
    """Remove glare using inpainting."""
    return cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
```

**Pros**:
- Directly addresses real-world photo issues
- Builds on V2 adaptive preprocessing
- Can be toggled on/off

**Cons**:
- Slower (inpainting is expensive)
- May over-correct clean scans
- Needs tuning

**Expected Improvement**: +10-15% accuracy on real photos

---

### Strategy 3: Multi-Scale Embeddings ⭐⭐⭐

**Impact**: MEDIUM | **Effort**: HIGH | **Risk**: MEDIUM

**Rationale**: Cards far from camera are small in frame → loss of detail

**Implementation**:
```python
def _multi_scale_embedding(self, image_path):
    """Generate embeddings at multiple scales."""
    image = Image.open(image_path).convert("RGB")

    # Extract embedding at 1x, 1.5x, 2x scales
    embeddings = []
    for scale in [1.0, 1.5, 2.0]:
        if scale > 1.0:
            w, h = image.size
            scaled = image.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
            cropped = scaled.crop((w//4, h//4, w*3//4, h*3//4))  # Center crop
        else:
            cropped = image

        emb = self._get_embedding(cropped)
        embeddings.append(emb)

    # Average embeddings
    return np.mean(embeddings, axis=0)
```

**Pros**:
- Better for cards at varying distances
- More robust to scale variations

**Cons**:
- 3x slower (3 embeddings per image)
- More complex

**Expected Improvement**: +5-8% accuracy on distant cards

---

### Strategy 4: Geometric Matching Tuning ⭐⭐⭐⭐

**Impact**: MEDIUM-HIGH | **Effort**: LOW | **Risk**: LOW

**Problem**: yellow_event.png has geometric score of 0.517 (moderate)

**Current ORB settings**:
```python
orb = cv2.ORB_create(nfeatures=1000, scaleFactor=1.2, nlevels=8, edgeThreshold=15)
```

**Improved settings for real photos**:
```python
orb = cv2.ORB_create(
    nfeatures=2000,      # 1000 → 2000 (more features)
    scaleFactor=1.1,     # 1.2 → 1.1 (finer scale pyramid)
    nlevels=12,          # 8 → 12 (more pyramid levels)
    edgeThreshold=10,    # 15 → 10 (detect more edge features)
    firstLevel=0,
    WTA_K=2,
    scoreType=cv2.ORB_HARRIS_SCORE,  # More stable
    patchSize=31,
    fastThreshold=20
)
```

**Pros**:
- More features → better matching
- Finer scales → robust to perspective
- Low risk (just parameter tuning)

**Cons**:
- Slightly slower (2x features)
- May need threshold tuning

**Expected Improvement**: +0.05-0.10 geometric score boost

---

### Strategy 5: Confidence Threshold Calibration ⭐⭐⭐

**Impact**: MEDIUM | **Effort**: LOW | **Risk**: LOW

**Current thresholds**:
- HIGH: ≥ 0.75
- MODERATE: ≥ 0.62 AND margin ≥ 0.10
- LOW: < 0.62

**Issue**: yellow_event.png = 0.571 (MODERATE) but is correct

**Proposed**:
```python
# Adaptive thresholds based on image quality
def _get_confidence_thresholds(self, image_quality):
    if image_quality['sharpness'] > 500 and image_quality['glare_ratio'] < 0.05:
        # Clean scan
        return {'high': 0.75, 'moderate': 0.62}
    else:
        # Real photo - be more lenient
        return {'high': 0.70, 'moderate': 0.55}
```

**Pros**:
- Accounts for image quality
- More HIGH confidence on real photos
- Simple to implement

**Cons**:
- May increase false positives
- Needs careful validation

**Expected Improvement**: +10-15% HIGH confidence rate

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)

1. **✅ Geometric Matching Tuning** (Strategy 4)
   - Low risk, medium reward
   - Just parameter changes
   - Test immediately

2. **✅ Confidence Threshold Calibration** (Strategy 5)
   - Adaptive thresholds
   - Makes real photos more usable

### Phase 2: Core Improvements (3-5 days)

3. **✅ Higher Resolution Embeddings** (Strategy 1)
   - Re-download at 800x800
   - Re-generate embeddings
   - A/B test vs 600x600

4. **✅ Enhanced Preprocessing** (Strategy 2)
   - Glare detection/removal
   - Perspective correction
   - V2.1 feature

### Phase 3: Advanced Features (1-2 weeks)

5. **⏸️ Multi-Scale Embeddings** (Strategy 3)
   - If needed after Phase 1-2
   - Test on distant cards

---

## Testing Plan

### Benchmark Dataset

Collect 50-100 real-world photos:
- 20 clean sleeve photos (controlled lighting)
- 20 angled photos (30-45° tilt)
- 20 distant photos (card fills <50% of frame)
- 20 glare photos (reflective sleeves)
- 20 low-light photos

### Success Metrics

| Metric | Current | Target (Phase 1) | Target (Phase 2) |
|--------|---------|------------------|------------------|
| **HIGH Confidence %** | 16.7% | 40% | 60% |
| **Accuracy** | 83.3% | 90% | 95% |
| **Avg Score** | 0.623 | 0.70 | 0.75 |
| **Avg Time** | 1038ms | <1200ms | <1000ms |

---

## Risk Mitigation

1. **Version Control**: All improvements in V2.1, V2.2, etc. with V1 fallback
2. **A/B Testing**: Run new version against V1 baseline on same images
3. **Gradual Rollout**: Test with small dataset before full re-embedding
4. **Rollback Plan**: Keep 600x600 embeddings for instant rollback

---

## Cost-Benefit Analysis

### Strategy 1 (800x800 Embeddings)

**Costs**:
- Download: +100 MB storage
- Processing: +2 min re-embedding time
- No code changes

**Benefits**:
- +5-10% accuracy
- +0.03-0.05 score boost
- Permanent improvement

**ROI**: ⭐⭐⭐⭐⭐ (very high)

### Strategy 2 (Enhanced Preprocessing)

**Costs**:
- Development: 4-6 hours
- +200-300ms per identification

**Benefits**:
- +10-15% accuracy on real photos
- Handles glare/angles/noise

**ROI**: ⭐⭐⭐⭐ (high, but slower)

### Strategy 4 (Geometric Tuning)

**Costs**:
- Testing: 1-2 hours
- +50-100ms per identification

**Benefits**:
- +5-10% geometric match quality
- Better on text-heavy cards

**ROI**: ⭐⭐⭐⭐⭐ (very high)

---

## Next Steps

1. **Immediate**: Implement Strategy 1 (800x800) + Strategy 4 (ORB tuning)
2. **This Week**: Test on 20 real card photos
3. **Next Week**: Implement Strategy 2 (enhanced preprocessing) if needed
4. **Evaluate**: Compare results, decide on Strategy 5 thresholds

---

**Status**: 🟡 Proposed
**Owner**: Senior Principal Engineer
**Est. Completion**: 3-7 days (Phase 1-2)
