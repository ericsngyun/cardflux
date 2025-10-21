# V1 Accuracy Improvement Opportunities

> **Date**: 2025-10-21
> **Current Performance**: 16.7% HIGH confidence (1/6 images)
> **Goal**: Identify realistic ways to improve accuracy significantly

---

## Current V1 Performance Analysis

### Confidence Distribution

| Confidence | Count | Percentage | Avg Score | Gap to HIGH (0.75) |
|------------|-------|------------|-----------|-------------------|
| **HIGH** | 1/6 | 16.7% | 0.8721 | ✅ Already HIGH |
| **MODERATE** | 2/6 | 33.3% | 0.6304 | **+0.1196 (+19%)** |
| **LOW** | 3/6 | 50.0% | 0.5346 | **+0.2154 (+40%)** |

### Key Insight

- **50% of images are LOW confidence** (compressed Discord screenshots)
- **MODERATE images need +19% boost** to reach HIGH
- **LOW images need +40% boost** (likely not achievable)

---

## Realistic Improvement Strategies

### ✅ Strategy 1: Fine-Tuned DINOv2 Model ⭐⭐⭐⭐⭐

**Impact**: **VERY HIGH** (+15-25% accuracy)
**Effort**: HIGH (requires GPU, training data, 1-2 weeks)
**Cost**: Moderate (GPU compute)

**What is it?**

Fine-tune the DINOv2 vision model specifically on One Piece TCG cards.

**Why it works:**
- Current DINOv2 is a **general-purpose** vision model
- Fine-tuning teaches it **TCG-specific features**:
  - Character faces and poses
  - Card borders and text layout
  - Foil patterns and textures
  - Artwork styles unique to One Piece

**Expected improvements:**
- Visual similarity scores: +0.10 to +0.20 boost
- MODERATE (0.63) → HIGH (0.83) ✅
- Better differentiation of similar cards
- More robust to watermarks, angles, lighting

**Implementation:**
```python
# 1. Prepare training data
#    - 4,813 One Piece cards (we have these!)
#    - 600x600 reference images
#    - Augment: rotation, brightness, crop variations

# 2. Fine-tune DINOv2
from transformers import Trainer, TrainingArguments

training_args = TrainingArguments(
    output_dir="./dinov2-one-piece-finetuned",
    num_train_epochs=10,
    per_device_train_batch_size=16,
    learning_rate=2e-5,
    warmup_steps=500,
)

# 3. Train for 10-20 epochs (~8-16 hours on GPU)

# 4. Replace model in production_card_identifier.py
```

**Pros:**
- ✅ Addresses root cause (visual similarity)
- ✅ Works for ALL image types (clean, compressed, real photos)
- ✅ One-time effort, permanent improvement
- ✅ We already have perfect training data (4,813 cards)

**Cons:**
- ⚠️ Requires GPU (can rent from AWS/Google Cloud)
- ⚠️ 1-2 weeks development time
- ⚠️ Need to test thoroughly before deployment
- ⚠️ Model file size increases (~400MB → ~450MB)

**Expected Results:**
- MODERATE images (0.63) → HIGH (0.75-0.85) ✅
- LOW clean images (yellow_event 0.57) → MODERATE/HIGH (0.70-0.75) ✅
- Compressed images (0.53) → still LOW (fundamental limits)

**This is the #1 highest-impact improvement we can make.**

---

### ✅ Strategy 2: Larger Reference Image Database ⭐⭐⭐⭐

**Impact**: **HIGH** (+10-15% accuracy for variants)
**Effort**: MEDIUM (scrape additional sources, 2-3 days)
**Cost**: Low (storage only)

**What is it?**

Expand the reference database with multiple images per card:
- Different angles
- Different lighting
- Different foil patterns
- Alt-art variants explicitly tagged

**Why it works:**
- Current: 1 reference image per card (600x600)
- Problem: If reference has watermark or different angle, match fails
- Solution: 3-5 reference images per card with variations

**Implementation:**
```python
# Scrape additional sources:
# 1. TCGPlayer alternate images (many cards have 2-3 images)
# 2. OnePieceTCG.com official images
# 3. Community-submitted high-quality scans

# Store multiple references per card:
# data/images/one-piece/{card_id}/
#   - ref_1.jpg (600x600 official)
#   - ref_2.jpg (600x600 alternate angle)
#   - ref_3.jpg (600x600 foil variant)

# Update identifier to search against all references
# Return best match across all reference images
```

**Pros:**
- ✅ Handles watermarked references better
- ✅ Better variant detection (alt-art, foil)
- ✅ More robust to angle/lighting differences
- ✅ Low complexity (just more data)

**Cons:**
- ⚠️ 3-5x storage (400 MB → 1.2-2 GB)
- ⚠️ 3-5x embedding time (5 min → 15-25 min)
- ⚠️ 3-5x slower searches (need to check multiple refs)

**Expected Results:**
- Variant/alt-art detection: +20-30% accuracy
- Watermarked cards: +10-15% accuracy
- Overall: +5-10% average score

---

### ✅ Strategy 3: Ensemble Model Approach ⭐⭐⭐

**Impact**: **MEDIUM** (+5-10% accuracy)
**Effort**: MEDIUM (3-5 days)
**Cost**: Low

**What is it?**

Use multiple vision models and combine their predictions:
- DINOv2 (current)
- CLIP (OpenAI's model)
- ResNet50 (classic CNN)

**Why it works:**
- Different models have different strengths
- DINOv2: Great for textures, patterns
- CLIP: Great for semantic understanding
- ResNet50: Fast, good for basic features

**Implementation:**
```python
class EnsembleIdentifier:
    def __init__(self):
        self.dinov2 = load_dinov2()
        self.clip = load_clip()
        self.resnet = load_resnet50()

    def identify(self, image_path):
        # Get embeddings from all 3 models
        dinov2_emb = self.dinov2.embed(image_path)
        clip_emb = self.clip.embed(image_path)
        resnet_emb = self.resnet.embed(image_path)

        # Search with each model
        dinov2_matches = faiss_search(dinov2_emb, k=10)
        clip_matches = faiss_search(clip_emb, k=10)
        resnet_matches = faiss_search(resnet_emb, k=10)

        # Vote: weighted combination
        combined_scores = {}
        for card_id in all_candidates:
            score = (
                0.6 * dinov2_matches.get(card_id, 0) +  # DINOv2 weighted higher
                0.3 * clip_matches.get(card_id, 0) +
                0.1 * resnet_matches.get(card_id, 0)
            )
            combined_scores[card_id] = score

        return best_match(combined_scores)
```

**Pros:**
- ✅ More robust (different models see different features)
- ✅ Better for edge cases
- ✅ Can tune weights per model

**Cons:**
- ⚠️ 3x slower (3 model forwards)
- ⚠️ 3x storage (3 FAISS indexes)
- ⚠️ More complex

**Expected Results:**
- Borderline cases: +10-15% accuracy
- Overall: +5-7% average score

---

### ✅ Strategy 4: Query Image Augmentation ⭐⭐⭐⭐

**Impact**: **MEDIUM-HIGH** (+8-12% accuracy)
**Effort**: LOW (1-2 days)
**Cost**: None

**What is it?**

Generate multiple augmented versions of the query image and vote:
- Original
- Rotated ±5°
- Brightness adjusted ±10%
- Contrast adjusted
- Slightly cropped

**Why it works:**
- Handles angle/lighting variations
- Small transformations can push borderline matches over threshold
- Similar to test-time augmentation (TTA) in ML

**Implementation:**
```python
def identify_with_augmentation(self, image_path, n_augmentations=5):
    augmented_images = []

    # Original
    augmented_images.append(load_image(image_path))

    # Rotation
    augmented_images.append(rotate(load_image(image_path), angle=3))
    augmented_images.append(rotate(load_image(image_path), angle=-3))

    # Brightness
    augmented_images.append(adjust_brightness(load_image(image_path), +0.1))
    augmented_images.append(adjust_brightness(load_image(image_path), -0.1))

    # Get predictions for all
    predictions = []
    for aug_img in augmented_images:
        pred = self.identify(aug_img)
        predictions.append(pred)

    # Vote
    return vote_best_match(predictions)
```

**Pros:**
- ✅ Low effort, high reward
- ✅ No retraining needed
- ✅ Handles angle/lighting robustly

**Cons:**
- ⚠️ 5x slower (5 forward passes)
- ⚠️ Can be mitigated with parallel processing

**Expected Results:**
- Real photos: +10-15% accuracy
- Angled/lit images: +15-20% accuracy
- Overall: +8-12% average score

---

### ✅ Strategy 5: Better Reference Images from Official Sources ⭐⭐⭐⭐⭐

**Impact**: **HIGH** (+10-20% accuracy)
**Effort**: LOW-MEDIUM (1 week scraping)
**Cost**: None

**What is it?**

Replace TCGPlayer images with higher-quality official images:
- OnePieceTCG.com official card database
- Bandai official images (if available)
- Community high-res scans

**Why it works:**
- TCGPlayer images have watermarks ("SAMPLE")
- TCGPlayer images may be lower quality
- Official images are watermark-free, higher quality

**Current TCGPlayer issues:**
- "SAMPLE" watermarks reduce similarity
- Some images are product photos (in packaging)
- Compression artifacts

**Implementation:**
```bash
# 1. Scrape OnePieceTCG.com
python scrape_official_images.py

# 2. Match official images to our card database by number
python match_official_to_tcgplayer.py

# 3. Replace reference images
python replace_reference_images.py

# 4. Re-generate embeddings
python embed_cards.py

# 5. Rebuild FAISS index
python build_faiss.py
```

**Pros:**
- ✅ No algorithm changes needed
- ✅ Better quality = better matches
- ✅ No watermark issues
- ✅ One-time effort

**Cons:**
- ⚠️ Need to find official source
- ⚠️ May not exist for all cards
- ⚠️ Need to match by card number

**Expected Results:**
- Watermarked cards: +15-25% accuracy
- Overall: +10-15% average score

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 weeks)

1. **✅ Better Reference Images** (Strategy 5)
   - Scrape official sources
   - Replace watermarked images
   - Re-embed and re-index
   - **Expected: +10-15% overall**

2. **✅ Query Image Augmentation** (Strategy 4)
   - Implement TTA (test-time augmentation)
   - 5x forward passes with voting
   - **Expected: +8-12% overall**

**Combined Phase 1: +18-27% improvement** ⭐

### Phase 2: Major Improvements (2-4 weeks)

3. **✅ Fine-Tuned DINOv2** (Strategy 1)
   - Rent GPU (AWS/Google Cloud)
   - Fine-tune on 4,813 One Piece cards
   - Train for 10-20 epochs
   - **Expected: +15-25% overall**

**Combined Phase 1 + 2: +33-52% improvement** ⭐⭐⭐

### Phase 3: Advanced (if needed, 4-8 weeks)

4. **✅ Multiple References per Card** (Strategy 2)
   - Scrape alternate images
   - Store 3-5 refs per card
   - **Expected: +5-10% on variants**

5. **✅ Ensemble Models** (Strategy 3)
   - Add CLIP + ResNet50
   - Weighted voting
   - **Expected: +5-7% overall**

---

## Expected Results After All Phases

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| **Avg Score** | 0.6228 | **0.73-0.76** | **0.80-0.85** | **0.85-0.90** |
| **HIGH Confidence** | 16.7% (1/6) | **50-67%** (3-4/6) | **83-100%** (5-6/6) | **100%** (6/6) |
| **MODERATE** | 33.3% (2/6) | **33-50%** | **0-17%** | **0%** |
| **LOW** | 50.0% (3/6) | **0-17%** | **0%** | **0%** |

---

## My #1 Recommendation

**Start with Phase 1**: Better reference images + query augmentation

**Why?**
- ✅ Low effort (1-2 weeks)
- ✅ No GPU required
- ✅ No retraining
- ✅ Expected +18-27% improvement
- ✅ Low risk

**Then, if Phase 1 works well:**
- Move to **Phase 2: Fine-tuned DINOv2** for massive gains

**This would transform:**
- Current: 16.7% HIGH confidence
- After Phase 1: **50-67% HIGH confidence**
- After Phase 2: **83-100% HIGH confidence**

That's a **3-6x improvement in HIGH confidence rate!**

---

## What NOT to Do

❌ **Super-resolution** - Tested, minimal benefit
❌ **More ORB features** - Tested, made it worse
❌ **Higher resolution references (800x800)** - Tested, actually worse
❌ **Compressed image preprocessing (V3)** - Tested, too slow for minimal gain

---

## Bottom Line

**The biggest lever we have is:**

1. **Better reference images** (official sources without watermarks)
2. **Fine-tuned DINOv2** (teach it One Piece TCG specifically)

These two alone could give us **+30-40% accuracy improvement**.

Would you like me to start implementing Phase 1 (better reference images + query augmentation)?

---

**Status**: Analysis Complete
**Recommendation**: Implement Phase 1 first (quick wins)
**Expected Outcome**: 16.7% → 50-67% HIGH confidence

_Date: 2025-10-21_
_Analyzed by: Senior Principal Engineer via Claude Code_
