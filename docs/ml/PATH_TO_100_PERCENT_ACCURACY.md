# Path to 100% Accuracy: Multi-Game TCG Recognition System
## Achieving Near-Perfect Identification Using Renders + Active Learning

**Created**: 2025-10-23
**Goal**: 99.5%+ accuracy across Top 5 TCG games using only digital renders + self-improving feedback loop
**Timeline**: 6-12 months to production-grade multi-game system

---

## Executive Summary

**Current State**: 100% accuracy on One Piece test set (19 images), but limited to one game with 4,813 cards.

**Target State**: 99.5%+ accuracy across **all Top 5 TCG games**:
1. **Magic: The Gathering** - 27,000+ unique cards
2. **Pokémon TCG** - 15,000+ unique cards
3. **Yu-Gi-Oh!** - 12,000+ unique cards
4. **One Piece** - 4,813 cards (DONE)
5. **Lorcana** - 1,000+ cards (growing fast)

**Total TAM**: 60,000+ unique cards across 5 games

**The Challenge**: Digital renders don't match real-world camera captures (lighting, angles, glare, wear, backgrounds).

**The Solution**: Advanced ML pipeline combining:
1. **Synthetic data augmentation** (simulate real-world conditions from renders)
2. **Metric learning** (ArcFace/CosFace for robust embeddings)
3. **Active learning loop** (users validate → model improves continuously)
4. **Fine-tuned DINOv2** per game (game-specific optimizations)

---

## I. THE ACCURACY PROBLEM (Current Limitations)

### A. Why Renders ≠ Real Photos

**Digital Render Characteristics**:
- Perfect lighting (no shadows, glare, or reflections)
- Perfect centering (card fills frame exactly)
- Perfect focus (no blur)
- Clean background (usually white/transparent)
- No wear/damage (mint condition)
- No watermarks (unless intentionally added)

**Real-World Camera Capture Issues**:
- Variable lighting (overhead lights, desk lamps, sunlight)
- Glare on glossy/foil cards (75% of cards have some foiling)
- Perspective distortion (camera angle ≠ 90°)
- Busy backgrounds (desk, playmat, hand holding card)
- Card wear (scratches, edge whitening, bends)
- Motion blur (handheld camera shake)
- Partial occlusion (fingers holding card, sleeves)
- Watermarks on reference images (TCGPlayer "SAMPLE" overlay)

**The Domain Gap**:
- Model trained on perfect renders → fails on imperfect real photos
- This is the **core reason** most card scanning apps are only 70-85% accurate

### B. Current Performance Analysis

**One Piece (4,813 cards)**:
- Test accuracy: 100% (19 test images)
- Confidence: 47% HIGH / 42% MODERATE / 11% LOW
- **Why it works**: Hybrid geometric verification rescues visual failures

**Estimated Performance on New Games** (without fine-tuning):
- Magic (27K cards): 75-85% top-1 accuracy
- Pokémon (15K cards): 80-90% (simpler art styles)
- Yu-Gi-Oh! (12K cards): 70-80% (complex art, similar frames)
- Lorcana (1K cards): 85-95% (smaller dataset, newer cleaner scans)

**Failure Modes**:
1. **Alternate art variants** (10-15% of cards) - looks totally different
2. **Foil vs non-foil** (same card, different appearance)
3. **Reprint differences** (border changes, set symbols)
4. **Similar cards** (same character, different set/version)
5. **Damaged cards** (creases, fading reduce visual similarity)

---

## II. THE SOLUTION: 5-LAYER ML ARCHITECTURE

### Layer 1: Synthetic Data Augmentation Pipeline

**Objective**: Transform perfect renders into realistic camera captures

**Augmentation Categories**:

**A. Photometric Augmentations** (color/light)
```python
# Lighting variations
- Brightness: ±30% random
- Contrast: ±20% random
- Saturation: ±15% random (especially for foils)
- Hue shift: ±5° (color temperature)
- Gamma correction: 0.8-1.2 (exposure simulation)

# Glare/reflection simulation
- Specular highlights (foil cards): 20-40% opacity white overlay
- Lens flare: 5% of images
- Shadow overlay: 10-30% darkening on corners

# Noise
- Gaussian noise: σ=0.01-0.03
- ISO noise simulation (grain)
- JPEG compression artifacts: quality 60-95
```

**B. Geometric Augmentations** (perspective/shape)
```python
# Perspective distortion
- Rotation: ±15° random
- Affine transform: simulate viewing angle
- Perspective warp: simulate camera angle (up to 30° off-perpendicular)
- Scale: 0.7-1.3× (card size variation)
- Translation: ±20% of image

# Cropping
- Tight crop: card fills 95% of frame
- Loose crop: card fills 60-70% of frame
- Offset crop: card not centered (±15% shift)
```

**C. Environmental Augmentations** (background/context)
```python
# Background replacement (critical!)
- Random textures: wood, playmat, desk surface (100 backgrounds)
- Natural images: ImageNet subset (1000 backgrounds)
- Gradient backgrounds: simulate studio lighting
- Edge blending: feather card edges into background (anti-aliasing)

# Occlusion simulation
- Hand/finger overlays: 5-10% of card edge
- Sleeve edges: top 2-3% of card
- Random objects: 2% of images (simulate desk clutter)
```

**D. Defect Simulation** (wear/damage)
```python
# Card condition variations
- Edge whitening: 10-30% of cards
- Surface scratches: thin white lines (5-15 per card)
- Creases: localized brightness changes
- Dirt/smudges: Perlin noise overlays
- Fading: reduce saturation 10-20%

# Print defects
- Miscuts: shift card art ±2mm
- Off-centering: asymmetric borders
- Print lines: horizontal/vertical artifacts
```

**E. Watermark Simulation** (TCGPlayer/CardMarket)
```python
# Overlay "SAMPLE" text (matches TCGPlayer)
- Font: Arial Bold, 72pt
- Opacity: 30-50%
- Angle: ±5° from horizontal
- Color: White/Gray
- Position: Diagonal across center
```

**Implementation**:
```python
# Use Albumentations library (fast, GPU-accelerated)
import albumentations as A

transform_pipeline = A.Compose([
    # Geometric
    A.ShiftScaleRotate(shift_limit=0.2, scale_limit=0.3, rotate_limit=15, p=0.8),
    A.Perspective(scale=(0.05, 0.15), p=0.5),

    # Photometric
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.2, p=0.8),
    A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=15, val_shift_limit=10, p=0.7),
    A.RandomGamma(gamma_limit=(80, 120), p=0.5),

    # Blur/noise
    A.OneOf([
        A.MotionBlur(blur_limit=5, p=0.3),
        A.GaussianBlur(blur_limit=3, p=0.3),
        A.MedianBlur(blur_limit=3, p=0.3),
    ], p=0.4),
    A.GaussNoise(var_limit=(10, 50), p=0.3),

    # Compression
    A.ImageCompression(quality_lower=60, quality_upper=95, p=0.5),

    # Advanced
    A.CoarseDropout(max_holes=8, max_height=8, max_width=8, p=0.2),  # Occlusion
    A.RandomShadow(shadow_roi=(0, 0, 1, 1), p=0.3),
])
```

**Augmentation Multiplier**:
- Each render → 20-50 augmented variants
- 60,000 renders × 30 variants = **1.8M training images**
- Storage: ~500GB (compressed JPEGs)

---

### Layer 2: Metric Learning (ArcFace Embeddings)

**Objective**: Learn embeddings where same card = close, different card = far

**Why Not Softmax?**
- Softmax classification: N-way classifier (60,000 classes!)
- Problems:
  - Adding new card = retrain entire model
  - No notion of "similarity" (just class probabilities)
  - Poor generalization to unseen cards

**ArcFace Solution**:
- Learn 384-dim embedding space
- Same card (different photos) → cosine similarity >0.85
- Different cards → cosine similarity <0.60
- **Angular margin penalty**: enforce separation

**Architecture**:
```python
# Base model: DINOv2 ViT-S/14 (frozen or fine-tuned)
backbone = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14')

# Projection head (trainable)
class ArcFaceHead(nn.Module):
    def __init__(self, in_features=384, out_features=60000, s=64.0, m=0.50):
        super().__init__()
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.s = s  # scale
        self.m = m  # margin (0.50 = 28.6° angular margin)

    def forward(self, features, labels):
        # Normalize features and weights
        features = F.normalize(features, p=2, dim=1)
        weight = F.normalize(self.weight, p=2, dim=1)

        # Cosine similarity
        logits = F.linear(features, weight)

        # Add angular margin penalty for true class
        theta = torch.acos(torch.clamp(logits, -1.0 + 1e-7, 1.0 - 1e-7))
        target_logits = torch.cos(theta + self.m)

        # Replace true class logits
        one_hot = torch.zeros_like(logits)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        output = logits * (1 - one_hot) + target_logits * one_hot

        return output * self.s

# Full model
class CardRecognitionModel(nn.Module):
    def __init__(self, num_cards=60000):
        super().__init__()
        self.backbone = dinov2_vits14(pretrained=True)
        self.arcface = ArcFaceHead(in_features=384, out_features=num_cards)

    def forward(self, images, labels=None):
        features = self.backbone(images)  # [B, 384]
        if labels is not None:
            return self.arcface(features, labels)
        else:
            return F.normalize(features, p=2, dim=1)  # Return normalized embeddings
```

**Training Strategy**:
1. **Freeze DINOv2**: Train only ArcFace head (1 epoch, fast)
2. **Unfreeze last 2 blocks**: Fine-tune DINOv2 layers (5 epochs)
3. **Full fine-tuning**: All layers trainable (10-20 epochs)

**Hyperparameters** (critical):
- Scale (s): 64.0 (controls logit magnitude)
- Margin (m): 0.50 (28.6° angular separation)
- Learning rate: 1e-4 (backbone), 1e-3 (ArcFace head)
- Batch size: 256-512 (large batches help metric learning)
- Optimizer: AdamW (weight decay 0.01)

**Expected Performance**:
- Top-1 accuracy: 95-98% (vs 85-90% with softmax)
- Top-5 accuracy: 99.5%+ (almost always in top 5)
- Robustness: Handles foil, wear, lighting variations

---

### Layer 3: Game-Specific Fine-Tuning

**Objective**: Optimize model per game (not one-size-fits-all)

**Why Game-Specific?**
- **Magic**: Complex art, many variants → need strong variant classifier
- **Pokémon**: Simpler art, more foiling → optimize for foil detection
- **Yu-Gi-Oh!**: Similar card frames → focus on text/art details
- **One Piece**: DONE (baseline)
- **Lorcana**: New game, clean scans → fastest convergence

**Fine-Tuning Strategy (per game)**:

**Stage 1: Transfer Learning** (1-3 days training)
1. Start with DINOv2 pre-trained on ImageNet
2. Train ArcFace head on renders + augmentations
3. Target: 90-95% accuracy

**Stage 2: Domain Adaptation** (3-7 days training)
1. Mix rendered + real user photos (80/20 ratio initially)
2. Fine-tune last 4 transformer blocks
3. Target: 95-97% accuracy

**Stage 3: Active Learning Refinement** (ongoing)
1. Deploy to production
2. Collect user validations (see Layer 4)
3. Retrain weekly on corrected labels
4. Target: 98-99.5% accuracy

**Game-Specific Optimizations**:

**Magic: The Gathering** (27K cards)
```python
# Challenges: Variants, reprints, similar art
# Solution: Multi-task learning

class MagicModel(CardRecognitionModel):
    def __init__(self):
        super().__init__(num_cards=27000)
        # Additional heads
        self.foil_classifier = nn.Linear(384, 2)  # Foil vs non-foil
        self.variant_classifier = nn.Linear(384, 10)  # Art variant type
        self.set_classifier = nn.Linear(384, 150)  # Which set

    def forward(self, images, labels=None):
        features = self.backbone(images)
        card_logits = self.arcface(features, labels) if labels else features

        # Auxiliary tasks (improve feature learning)
        foil_logits = self.foil_classifier(features)
        variant_logits = self.variant_classifier(features)
        set_logits = self.set_classifier(features)

        return card_logits, foil_logits, variant_logits, set_logits
```

**Pokémon TCG** (15K cards)
```python
# Challenges: Heavy foiling, reverse holos, full arts
# Solution: Separate foil/non-foil embeddings

class PokemonModel(CardRecognitionModel):
    def __init__(self):
        super().__init__(num_cards=15000)
        # Dual embedding space
        self.foil_embedding = nn.Linear(384, 384)
        self.non_foil_embedding = nn.Linear(384, 384)

    def forward(self, images, is_foil=None):
        features = self.backbone(images)

        # Route through appropriate embedding space
        if is_foil is not None:
            foil_features = self.foil_embedding(features) * is_foil
            non_foil_features = self.non_foil_embedding(features) * (1 - is_foil)
            features = foil_features + non_foil_features

        return self.arcface(features)
```

**Yu-Gi-Oh!** (12K cards)
```python
# Challenges: Similar card frames, small text differences
# Solution: Multi-scale feature extraction

class YuGiOhModel(CardRecognitionModel):
    def __init__(self):
        super().__init__(num_cards=12000)
        # Multi-resolution processing
        self.high_res_adapter = nn.Sequential(
            nn.Conv2d(3, 3, kernel_size=1),  # Learn sharpening filter
            nn.BatchNorm2d(3),
        )

    def forward(self, images):
        # Process at 2× resolution for text clarity
        high_res = F.interpolate(images, scale_factor=2, mode='bilinear')
        high_res = self.high_res_adapter(high_res)

        features = self.backbone(high_res)
        return self.arcface(features)
```

---

### Layer 4: Active Learning Feedback Loop

**Objective**: Continuously improve model using real user validations

**The Flywheel**:
```
User scans card → Model predicts (with confidence)
    ↓
IF confidence < 0.75 (MODERATE/LOW):
    → Show top 5 predictions
    → User selects correct card (or searches manually)
    → Log: {image, correct_label, model_predictions, confidence}
    ↓
Weekly retraining:
    → Filter high-quality corrections (user confidence signals)
    → Add to training set (real photos!)
    → Retrain model
    → Deploy updated model
    ↓
Accuracy improves → Fewer LOW confidence → Less validation needed → REPEAT
```

**Active Learning Strategy**:

**1. Uncertainty Sampling**
- Flag images where model is uncertain
- Criteria:
  - Top-1 confidence <0.75
  - Top-1 and Top-2 very close (gap <0.10)
  - Multiple cards with similar embeddings (ambiguous)

**2. Diversity Sampling**
- Don't just sample uncertain images
- Also sample diverse images (different cards, conditions, lighting)
- Use clustering to ensure broad coverage

**3. Hard Negative Mining**
- Find pairs of cards model confuses frequently
- Explicitly train to separate them
- Example: Foil vs non-foil of same card

**Implementation**:
```python
# Active learning queue
class ActiveLearningQueue:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)

    def add_prediction(self, image_path, predictions, user_correction=None):
        """Log model prediction and optional user correction"""
        top1_conf = predictions[0]['confidence']
        top2_conf = predictions[1]['confidence'] if len(predictions) > 1 else 0
        gap = top1_conf - top2_conf

        # Flag for review if uncertain
        needs_review = (top1_conf < 0.75) or (gap < 0.10)

        self.db.execute("""
            INSERT INTO predictions
            (image_path, top1_card, top1_conf, top2_card, top2_conf,
             user_correction, needs_review, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_path, predictions[0]['card_id'], top1_conf,
              predictions[1]['card_id'], top2_conf,
              user_correction, needs_review, time.time()))
        self.db.commit()

    def get_retraining_batch(self, min_confidence=0.9, max_samples=10000):
        """Get high-quality user corrections for retraining"""
        # Only use corrections where user was confident
        # (clicked quickly, didn't search manually)
        cursor = self.db.execute("""
            SELECT image_path, user_correction
            FROM predictions
            WHERE user_correction IS NOT NULL
              AND needs_review = 1
              AND user_confidence > ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (min_confidence, max_samples))

        return [(row[0], row[1]) for row in cursor.fetchall()]

# Weekly retraining job
def weekly_retrain():
    queue = ActiveLearningQueue('active_learning.db')
    corrections = queue.get_retraining_batch(min_confidence=0.9, max_samples=5000)

    print(f"Retraining with {len(corrections)} user corrections")

    # Mix with original renders (80% renders, 20% real photos)
    render_dataset = load_render_dataset(sample_size=20000)
    real_dataset = corrections  # User-validated real photos

    train_dataset = CombinedDataset(render_dataset, real_dataset, mix_ratio=0.8)

    # Fine-tune model
    model = load_latest_model()
    train(model, train_dataset, epochs=3, lr=1e-5)  # Small LR, short training

    # Validate improvement
    val_accuracy = evaluate(model, val_dataset)
    print(f"New accuracy: {val_accuracy:.2%}")

    # Deploy if better
    if val_accuracy > previous_accuracy:
        deploy_model(model, version=f"v{get_next_version()}")
```

**Expected Improvement Trajectory**:
- Week 0 (launch): 90-95% accuracy (renders only)
- Week 4: 95-97% accuracy (1,000 user corrections)
- Week 12: 97-98% accuracy (5,000 corrections)
- Week 24: 98-99% accuracy (15,000 corrections)
- Week 52: 99-99.5% accuracy (50,000+ corrections, model converges)

**Key Metrics to Track**:
- User correction rate (% of scans corrected)
- Confidence distribution (% HIGH/MODERATE/LOW)
- Top-5 accuracy (should be 99.9%+)
- Hard example accuracy (foils, variants, damaged cards)

---

### Layer 5: Ensemble & Geometric Verification (Current System)

**Objective**: Use hybrid approach when visual fails

**Current Implementation** (polished_card_detector.py + production_card_identifier.py):
1. **Visual retrieval**: DINOv2 embeddings → FAISS top-50
2. **Geometric verification**: ORB + AKAZE on top-20
3. **Dynamic scoring**: 60/40 to 90/10 visual/geometric weight

**Keep This!** It's your safety net:
- Visual fails (watermark, foil, damage) → Geometric rescues
- Example: Marshall D. Teach ranked #46 visually → #1 after geometric

**Enhancement for Multi-Game**:
```python
# Per-game geometric thresholds
GEOMETRIC_THRESHOLDS = {
    'magic': {
        'min_matches': 15,  # Complex art needs more features
        'lowe_ratio': 0.75,
    },
    'pokemon': {
        'min_matches': 12,  # Simpler art, fewer features
        'lowe_ratio': 0.80,
    },
    'yugioh': {
        'min_matches': 10,  # Similar frames, focus on art region
        'roi': (0.15, 0.45, 0.85, 0.85),  # Crop to art box
        'lowe_ratio': 0.75,
    },
    'onepiece': {
        'min_matches': 12,  # Current tuning
        'lowe_ratio': 0.80,
    },
    'lorcana': {
        'min_matches': 10,  # New game, clean scans
        'lowe_ratio': 0.80,
    },
}
```

---

## III. TRAINING DATA REQUIREMENTS

### A. Per-Game Dataset Sizing

| Game | Unique Cards | Renders Needed | Augmentations/Card | Total Training Images | Storage (Compressed) |
|------|--------------|----------------|--------------------|-----------------------|----------------------|
| **Magic** | 27,000 | 27,000 | 30× | 810,000 | 220 GB |
| **Pokémon** | 15,000 | 15,000 | 30× | 450,000 | 120 GB |
| **Yu-Gi-Oh!** | 12,000 | 12,000 | 30× | 360,000 | 95 GB |
| **One Piece** | 4,813 | 4,813 | 30× | 144,390 | 40 GB |
| **Lorcana** | 1,200 | 1,200 | 30× | 36,000 | 10 GB |
| **TOTAL** | **60,013** | **60,013** | **30×** | **1,800,390** | **485 GB** |

**Additional Data**:
- Real user photos (active learning): 50K-100K over 12 months (15-30 GB)
- Validation sets: 5K per game (10% of renders, no augmentation) (2 GB)
- **Total storage**: ~500-550 GB

### B. Data Collection Strategy

**Stage 1: Render Acquisition** (Months 1-2)

**Magic: The Gathering**:
- Source: Scryfall API (100% coverage, 27K+ cards)
- Format: 488×680 PNG (official WotC scans)
- Quality: Excellent (high-res, clean)
- API: `GET https://api.scryfall.com/cards`
- Rate limit: 100ms between requests (10/sec)
- Download time: ~45 minutes (27K cards)

**Pokémon TCG**:
- Source: PokémonTCG API (https://pokemontcg.io)
- Format: Various sizes (normalize to 600×850)
- Quality: Good (official Pokémon Company images)
- Coverage: 15K+ cards
- Rate limit: No official limit (be respectful, 5/sec)
- Download time: ~50 minutes

**Yu-Gi-Oh!**:
- Source: YGOProDeck API (https://db.ygoprodeck.com/api)
- Format: Variable (small images, ~421×614)
- Quality: Moderate (may need upscaling)
- Coverage: 12K+ cards
- Rate limit: None specified
- Download time: ~40 minutes

**One Piece**:
- Source: TCGPlayer scraping (DONE)
- Format: 600×600 JPG
- Quality: Good (97.4% success rate)
- Coverage: 4,813 cards

**Lorcana**:
- Source: Lorcana API (https://lorcana-api.com)
- Format: Variable
- Quality: Excellent (new game, official scans)
- Coverage: 1,200+ cards (growing)
- Download time: ~15 minutes

**Automation Script**:
```python
import asyncio
import aiohttp
from pathlib import Path

async def download_game_renders(game='magic'):
    if game == 'magic':
        url = "https://api.scryfall.com/cards"
        cards = await fetch_scryfall_cards(url)
    elif game == 'pokemon':
        url = "https://api.pokemontcg.io/v2/cards"
        cards = await fetch_pokemon_cards(url)
    # ... etc

    # Download images concurrently
    tasks = [download_image(card['image_url'], f"data/renders/{game}/{card['id']}.jpg")
             for card in cards]
    await asyncio.gather(*tasks)

# Run all games in parallel
asyncio.run(download_all_games(['magic', 'pokemon', 'yugioh', 'lorcana']))
```

**Stage 2: Augmentation Pipeline** (Months 2-3)
- Use Albumentations library (GPU-accelerated)
- Process on 4× A100 GPUs (AWS p4d.24xlarge)
- Throughput: ~1,000 images/sec (augmentation)
- Time to process 60K cards × 30 augmentations = 1.8M images
  - Sequential: ~30 hours
  - Parallelized (4 GPUs): ~8 hours

**Stage 3: Active Learning Collection** (Ongoing)
- Start collecting from day 1 of beta launch
- Target: 1,000 user corrections/week
- Quality filter: Only use corrections where user was confident
- Storage: S3 bucket with versioning (cheap, $0.023/GB/mo)

---

## IV. MODEL TRAINING PIPELINE

### A. Infrastructure Requirements

**Hardware** (cloud-based for flexibility):

**Development/Experimentation** (Months 1-3):
- 1× AWS p3.8xlarge (4× V100 32GB GPUs)
- Cost: $12.24/hr on-demand, $3.06/hr spot (75% savings)
- Usage: 8 hrs/day × 90 days = 720 hrs
- **Cost**: $2,203 (spot pricing)

**Production Training** (Months 4-12):
- 1× AWS p4d.24xlarge (8× A100 40GB GPUs)
- Cost: $32.77/hr on-demand, $9.83/hr spot
- Usage: Weekly retraining (12 hrs/week × 48 weeks) = 576 hrs
- **Cost**: $5,662 (spot pricing)

**Total GPU Compute** (Year 1): ~$8,000

**Storage**:
- S3 Standard: 500 GB × $0.023/GB/mo × 12 mo = $138/year
- S3 Glacier (archives): 200 GB × $0.004/GB/mo × 12 mo = $10/year
- **Total Storage**: ~$150/year

**Total Infrastructure (Year 1)**: ~$8,150

### B. Training Schedule

**GAME 1: Magic (Months 1-4)**

**Month 1**: Data collection + preprocessing
- Download 27K Scryfall renders
- Generate 810K augmented images
- Split: 80% train (648K) / 10% val (81K) / 10% test (81K)
- Create FAISS index for baseline

**Month 2**: Baseline model training
- DINOv2-S/14 frozen + ArcFace head
- Training: 3 days (10 epochs, batch 512)
- Expected accuracy: 85-90% (renders only)

**Month 3**: Fine-tuning + domain adaptation
- Unfreeze last 4 DINOv2 blocks
- Mix in first user photos (if available)
- Training: 7 days (20 epochs)
- Expected accuracy: 92-95%

**Month 4**: Active learning iteration 1
- Collect 2,000 user corrections
- Retrain with mixed dataset
- Deploy v1.1
- Expected accuracy: 95-97%

**GAME 2: Pokémon (Months 3-6)** [Parallel start]

**Month 3**: Data collection
- Download 15K Pokémon cards
- Generate 450K augmented images

**Month 4-5**: Training
- Transfer learning from Magic model (shared backbone)
- Pokémon-specific ArcFace head
- Training: 2 days (faster due to transfer learning)
- Expected accuracy: 88-92%

**Month 6**: Fine-tuning
- Add user corrections
- Deploy Pokémon v1.0
- Expected accuracy: 93-96%

**GAME 3-5: Yu-Gi-Oh!, Lorcana** (Months 5-8)

Similar process, accelerated by:
- Transfer learning from Magic/Pokémon backbones
- Shared infrastructure (pipelines already built)
- Smaller datasets (12K, 1.2K cards)

**Timeline**:
- Yu-Gi-Oh!: Months 5-7
- Lorcana: Month 6-8
- All games live by Month 8

### C. Training Configuration

**Baseline Training** (renders only):
```python
# config/training_config.yaml
model:
  backbone: dinov2_vits14
  embedding_dim: 384
  num_classes: 27000  # Per game
  arcface_scale: 64.0
  arcface_margin: 0.50

training:
  batch_size: 512  # Large batches help metric learning
  num_epochs: 20
  learning_rate:
    backbone: 1e-4
    arcface: 1e-3
  optimizer: AdamW
  weight_decay: 0.01
  scheduler: cosine_annealing
  warmup_epochs: 2

data:
  image_size: 224  # DINOv2 default
  augmentation: heavy  # See Layer 1
  num_workers: 16
  prefetch_factor: 2

hardware:
  gpus: 4
  precision: mixed  # FP16 for speed, FP32 for stability
  strategy: ddp  # Distributed Data Parallel
```

**Fine-Tuning Configuration** (with user photos):
```python
finetuning:
  freeze_backbone: false
  freeze_first_n_blocks: 8  # Only train last 4 blocks

  dataset_mixing:
    renders_weight: 0.7  # 70% renders
    real_photos_weight: 0.3  # 30% user photos
    oversample_hard_examples: true

  learning_rate: 5e-5  # Lower LR for stability
  num_epochs: 10
  early_stopping_patience: 3
```

**Expected Training Times** (4× V100 GPUs):

| Phase | Dataset Size | Epochs | Batch Size | Time per Epoch | Total Time |
|-------|--------------|--------|------------|----------------|------------|
| Baseline (Magic) | 648K | 10 | 512 | 45 min | 7.5 hrs |
| Fine-tuning (Magic) | 648K + 2K | 20 | 512 | 45 min | 15 hrs |
| Pokémon (transfer) | 360K | 10 | 512 | 30 min | 5 hrs |
| Yu-Gi-Oh! (transfer) | 288K | 10 | 512 | 25 min | 4 hrs |
| Weekly retrain | 50K new | 3 | 512 | 8 min | 24 min |

---

## V. EVALUATION & VALIDATION STRATEGY

### A. Metrics to Track

**Primary Metrics**:
1. **Top-1 Accuracy**: % where top prediction is correct
   - Target: 95%+ (baseline), 98%+ (fine-tuned), 99%+ (active learning)

2. **Top-5 Accuracy**: % where correct card is in top 5
   - Target: 99%+ (baseline), 99.5%+ (fine-tuned), 99.9%+ (active learning)

3. **Confidence-Stratified Accuracy**:
   - HIGH (≥0.75): Should be 99%+ accurate
   - MODERATE (0.62-0.75): Should be 95%+ accurate
   - LOW (<0.62): Manual review required

**Secondary Metrics**:
4. **Embedding Quality**:
   - Intra-class similarity: Same card, different photos → cosine >0.85
   - Inter-class separation: Different cards → cosine <0.60

5. **Failure Mode Analysis**:
   - Foil accuracy (separate metric)
   - Variant accuracy (alternate art)
   - Damaged card accuracy (NM vs HP)

### B. Test Sets

**Render Test Set** (synthetic, easy):
- 10% of renders held out (never seen during training)
- Purpose: Sanity check (should be 99%+ accurate)

**Real-World Test Set** (critical):
- Source: Hand-curated from different sources
  - 100 cards photographed in-house (controlled conditions)
  - 100 cards from beta users (real conditions)
  - 50 challenging cards (foils, damaged, variants)
- Total: 250 cards per game = 1,250 cards (5 games)
- Purpose: Real performance estimate

**Adversarial Test Set** (stress test):
- Intentionally difficult cases:
  - Heavy glare on foils
  - Severe damage (creases, fading)
  - Partial occlusion (fingers, sleeves)
  - Extreme lighting (dark, overexposed)
  - Watermarked reference images
- Total: 50 cards per game = 250 cards
- Purpose: Find failure modes, guide improvements

### C. Continuous Monitoring (Production)

**Dashboard Metrics** (update every 5 minutes):
```
┌─────────────────────────────────────────┐
│  CardFlux Model Performance Dashboard   │
├─────────────────────────────────────────┤
│ Last Hour:                              │
│   Total Scans: 1,247                    │
│   Avg Confidence: 0.81 (▲0.02)         │
│   User Corrections: 37 (3.0%)           │
│                                         │
│ Confidence Distribution:                │
│   HIGH (≥0.75):    68% ██████████▓▓▓▓  │
│   MODERATE:        24% ███████▓▓▓▓▓▓▓  │
│   LOW (<0.62):      8% ██▓▓▓▓▓▓▓▓▓▓▓▓  │
│                                         │
│ Per-Game Accuracy (Top-1):              │
│   Magic:      96.2% ██████████████▓▓  │
│   Pokémon:    97.8% ███████████████▓  │
│   Yu-Gi-Oh!:  94.5% █████████████▓▓▓  │
│   One Piece:  98.1% ███████████████▓  │
│   Lorcana:    99.2% ████████████████  │
│                                         │
│ Active Learning Queue: 143 pending      │
│ Next Retrain: 4 days, 17 hours         │
└─────────────────────────────────────────┘
```

**Alerting** (automated):
- Accuracy drops >2% from baseline → Email alert
- Confidence distribution shifts (more LOW) → Investigate
- Specific card frequently corrected → Add to hard examples
- New failure mode detected → Flag for manual review

---

## VI. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Months 1-3)

**Month 1: Data + Infrastructure**
- [ ] Set up AWS infrastructure (S3, EC2, SageMaker)
- [ ] Download all game renders (Magic, Pokémon, Yu-Gi-Oh!, Lorcana)
- [ ] Build augmentation pipeline (Albumentations)
- [ ] Generate 1.8M training images
- [ ] Create baseline FAISS indexes (one per game)

**Month 2: Baseline Models**
- [ ] Implement ArcFace training pipeline
- [ ] Train Magic model (DINOv2 frozen + ArcFace)
- [ ] Validate on render test set (target: 90%+)
- [ ] Train Pokémon model (transfer learning)
- [ ] Document training configs, hyperparameters

**Month 3: Fine-Tuning + Integration**
- [ ] Unfreeze DINOv2, fine-tune Magic model
- [ ] Integrate multi-game models into desktop app
- [ ] Add game selector UI
- [ ] Deploy to 10 beta testers (Magic + Pokémon only)
- [ ] Start collecting user corrections

**Deliverables**:
- 5 trained models (one per game)
- Desktop app with multi-game support
- Active learning pipeline (logging only, no retraining yet)
- Baseline accuracy: 90-95% (renders), 85-90% (real photos)

---

### Phase 2: Active Learning Loop (Months 4-6)

**Month 4: Active Learning Infrastructure**
- [ ] Build correction UI (show top 5, user selects)
- [ ] Implement confidence-based flagging (LOW → require validation)
- [ ] Set up PostgreSQL database (predictions + corrections)
- [ ] Create retraining pipeline (weekly cron job)
- [ ] Deploy to 50 beta users

**Month 5: First Retraining Cycle**
- [ ] Collect 2,000+ user corrections (across all games)
- [ ] Filter high-quality corrections (confidence signals)
- [ ] Retrain models with mixed renders + real photos
- [ ] A/B test new vs old models
- [ ] Deploy improved models (v1.1)
- [ ] Target accuracy: 95-97%

**Month 6: Optimization**
- [ ] Train Yu-Gi-Oh! + Lorcana models (catch up to Magic/Pokémon)
- [ ] Implement hard negative mining (confusing pairs)
- [ ] Add foil/variant-specific models (if needed)
- [ ] Expand to 200 beta users
- [ ] Target accuracy: 96-98%

**Deliverables**:
- Automated weekly retraining
- 5,000+ validated user photos in training set
- Accuracy: 95-98% across all games
- Confidence distribution: 60% HIGH / 30% MODERATE / 10% LOW

---

### Phase 3: Production Scale (Months 7-12)

**Month 7-8: Production Hardening**
- [ ] Migrate to production infrastructure (load balancers, CDN)
- [ ] Set up model serving (TorchServe or ONNX Runtime)
- [ ] Implement model versioning (A/B testing framework)
- [ ] Add monitoring dashboards (Grafana + Prometheus)
- [ ] Launch to 1,000 users

**Month 9-10: Advanced Features**
- [ ] Condition grading model (NM/LP/MP/HP)
- [ ] Foil detection model (separate classifier)
- [ ] Variant classifier (alternate art types)
- [ ] Multi-modal fusion (text + image for rare cards)

**Month 11-12: Convergence**
- [ ] Continuous retraining (now with 50K+ user photos)
- [ ] Model compression (ONNX quantization for mobile)
- [ ] Geographic-specific models (if regional differences)
- [ ] Achieve 98-99% production accuracy
- [ ] Launch publicly

**Deliverables**:
- 99%+ accuracy on Top-1 (real-world test set)
- 99.9%+ accuracy on Top-5
- <2% user correction rate
- Production-grade system serving 5,000+ users

---

## VII. COST BREAKDOWN (12-Month Budget)

### A. Infrastructure Costs

| Category | Description | Monthly | Annual |
|----------|-------------|---------|--------|
| **GPU Compute** | Training (spot instances) | $670 | $8,000 |
| **Storage** | S3 (renders, models, photos) | $50 | $600 |
| **Database** | PostgreSQL (RDS t3.medium) | $80 | $960 |
| **Serving** | Inference (g4dn.xlarge GPU) | $360 | $4,320 |
| **Networking** | Data transfer, CDN | $50 | $600 |
| **Monitoring** | Grafana Cloud, logging | $30 | $360 |
| **TOTAL** | | **$1,240/mo** | **$14,840/yr** |

**Notes**:
- GPU compute uses spot instances (75% cheaper)
- Serving costs scale with users (5K users = ~$4K/mo)
- Can optimize with ONNX Runtime (2-3× cheaper inference)

### B. Tooling & Services

| Tool | Purpose | Cost |
|------|---------|------|
| Weights & Biases | Experiment tracking | $50/mo (team plan) |
| Label Studio | Active learning UI (self-hosted) | $0 (open-source) |
| Albumentations | Augmentation library | $0 (open-source) |
| PyTorch | ML framework | $0 (open-source) |
| FAISS | Vector search | $0 (open-source) |
| **TOTAL** | | **$600/yr** |

### C. Human Labor (if outsourcing validation)

**Option 1: Community-Driven** (RECOMMENDED)
- Users validate their own scans (free)
- Gamify with badges, leaderboards
- Cost: $0

**Option 2: Paid Labeling** (if needed)
- Platform: Scale AI, Labelbox, Amazon MTurk
- Task: Validate model predictions (5-10 sec/card)
- Rate: $0.05-0.10 per validation
- Volume: 10K validations/month
- Cost: $500-1,000/month = $6K-12K/year

**Recommendation**: Use Option 1 (community), only pay for Option 2 if struggling to get enough data.

### D. Total Year 1 Budget

| Category | Cost |
|----------|------|
| Infrastructure | $14,840 |
| Tooling | $600 |
| Labeling (optional) | $0-12,000 |
| **TOTAL** | **$15,440 - $27,440** |

**With seed funding ($2M)**: This is only **0.77% - 1.37%** of budget. Very affordable.

---

## VIII. RISK MITIGATION

### Risk 1: Synthetic-to-Real Domain Gap Too Large

**Symptom**: Model trained on renders performs poorly on real photos (75-80% accuracy).

**Likelihood**: MEDIUM (30-40%)

**Mitigation**:
1. **Enhanced augmentation**: Add more aggressive photometric augmentations (glare, shadows)
2. **Real photo bootstrapping**: Manually photograph 500 cards per game (2,500 total) to seed real data
3. **Domain adaptation techniques**: CycleGAN to translate renders → realistic photos
4. **Hybrid approach**: Keep geometric verification as safety net

**Contingency**: If accuracy <90% after 3 months, pivot to semi-supervised learning with 10K manually labeled real photos (~$500-1K labeling cost).

---

### Risk 2: Active Learning Doesn't Improve Models

**Symptom**: User corrections don't lead to accuracy gains (stuck at 90-92%).

**Likelihood**: LOW (10-20%)

**Mitigation**:
1. **Quality filtering**: Only use corrections where user was confident (clicked quickly)
2. **Hard example mining**: Focus retraining on frequently confused pairs
3. **Curriculum learning**: Start with easy examples, gradually add harder ones
4. **Ensemble models**: Train multiple models, combine predictions

**Contingency**: Hire professional labelers to validate 10K images per game (~$5K-10K).

---

### Risk 3: New Cards Released (Data Drift)

**Symptom**: Accuracy degrades as new sets release (model doesn't know new cards).

**Likelihood**: HIGH (100% certainty - new sets release quarterly)

**Mitigation**:
1. **Automated scraping**: Daily cron job to check for new cards (Scryfall API has webhooks)
2. **Incremental learning**: Add new cards to model without retraining from scratch
3. **Hot-swapping**: Update FAISS index in real-time (no downtime)
4. **User flagging**: "This is a new card not in database" button

**Implementation**:
```python
# Daily job
def check_for_new_cards():
    for game in ['magic', 'pokemon', 'yugioh', 'lorcana']:
        latest_set = get_latest_set(game)
        if latest_set not in database:
            print(f"New set detected: {latest_set}")
            download_renders(latest_set)
            augment_renders(latest_set)
            update_faiss_index(latest_set)  # Add to existing index
            schedule_retrain()  # Light retrain (just new cards)
```

---

### Risk 4: Compute Costs Explode

**Symptom**: GPU bills exceed $5K/month as users scale.

**Likelihood**: MEDIUM (40-50% if not optimized)

**Mitigation**:
1. **ONNX optimization**: Convert to ONNX Runtime (2-3× faster, 50% cheaper)
2. **Model quantization**: INT8 instead of FP32 (4× smaller, 2× faster)
3. **Batching**: Process 10 scans at once (amortize GPU cost)
4. **CPU fallback**: Use CPU for HIGH confidence (GPU only for MODERATE/LOW)
5. **Edge deployment**: Run models on user's device (desktop app already does this!)

**Cost Savings**:
- Current: $0.10 per 1000 inferences (GPU)
- ONNX + quantization: $0.03 per 1000 inferences (70% reduction)
- Edge deployment: $0 per inference (no cloud cost!)

**Recommendation**: Keep desktop app GPU-free (CPU inference), only use cloud GPUs for web/mobile.

---

## IX. SUCCESS CRITERIA

### Month 3 (Baseline)
- ✅ 5 game models trained and deployed
- ✅ 90%+ accuracy on render test set
- ✅ 85%+ accuracy on real-world test set
- ✅ Active learning pipeline collecting data

### Month 6 (Fine-Tuned)
- ✅ 95%+ accuracy on render test set
- ✅ 92%+ accuracy on real-world test set
- ✅ 5,000+ user corrections collected
- ✅ Weekly retraining operational
- ✅ 200+ beta users

### Month 12 (Production)
- ✅ **98%+ accuracy on real-world test set**
- ✅ **99.5%+ Top-5 accuracy**
- ✅ <2% user correction rate
- ✅ 50K+ validated photos in training set
- ✅ <500ms average inference time
- ✅ Deployed to 5,000+ users

### Ultimate Goal (Month 18-24)
- ✅ **99%+ Top-1 accuracy**
- ✅ **99.9%+ Top-5 accuracy**
- ✅ <1% user correction rate
- ✅ Industry-leading performance (better than any competitor)

---

## X. COMPETITIVE ADVANTAGE (Why This Works)

### What Makes This Strategy Defensible?

**1. Data Flywheel** (Compounding Moat)
- More users → More corrections → Better model → Higher accuracy → More users
- Impossible for competitors to replicate without user base
- 6-12 month head start = 50K-100K labeled photos = insurmountable data advantage

**2. Multi-Game Excellence** (Not One-Trick Pony)
- Most competitors focus on one game (Magic) or generic CV
- We'll be best-in-class for ALL top 5 games
- Network effects: Magic user brings Pokémon collection → lock-in

**3. Continuous Improvement** (Living Model)
- Weekly retraining = always getting better
- Competitors with static models = stale, degrading accuracy
- New sets handled automatically (we're always up-to-date)

**4. Hybrid Approach** (Best of Both Worlds)
- Visual (DINOv2) + Geometric (ORB/AKAZE) = redundancy
- When one fails, other rescues
- 5-10% accuracy boost vs pure visual methods

**5. Production-Grade System** (Not Research Project)
- Desktop app already built (immediate deployment)
- Cloud sync, POS integration, marketplace sync (ecosystem lock-in)
- Not just "better AI" — better product

---

## XI. NEXT STEPS (Start TODAY)

### Week 1: Setup
- [ ] Set up AWS account, configure S3/EC2
- [ ] Download Scryfall data (Magic - 27K cards)
- [ ] Install Albumentations, PyTorch, FAISS
- [ ] Create augmentation pipeline (test with 100 cards)

### Week 2: Baseline Training
- [ ] Generate 3K augmented images (100 cards × 30 variants)
- [ ] Implement ArcFace training loop
- [ ] Train baseline model on 100-card subset
- [ ] Validate approach (should get 95%+ on this small set)

### Week 3-4: Scale Up
- [ ] Download all 5 games' renders (60K cards)
- [ ] Generate full 1.8M augmented dataset (parallelize on 4 GPUs)
- [ ] Train Magic model (full 27K cards)
- [ ] Integrate into desktop app (replace current DINOv2 model)

### Month 2: Expansion
- [ ] Train Pokémon, Yu-Gi-Oh!, Lorcana models
- [ ] Add game selector to desktop app UI
- [ ] Deploy to 10 beta users (start active learning)
- [ ] Collect first 500 user corrections

### Month 3+: Iterate
- [ ] Follow roadmap in Section VI
- [ ] Weekly retraining with user data
- [ ] Monitor accuracy improvements
- [ ] Scale to 50 → 200 → 1,000 users

---

## XII. APPENDIX

### A. Key Papers & References

**Vision Transformers**:
- DINOv2: "DINOv2: Learning Robust Visual Features without Supervision" (Meta AI, 2023)
- CLIP: "Learning Transferable Visual Models From Natural Language Supervision" (OpenAI, 2021)

**Metric Learning**:
- ArcFace: "ArcFace: Additive Angular Margin Loss for Deep Face Recognition" (2019)
- CosFace: "CosFace: Large Margin Cosine Loss for Deep Face Recognition" (2018)

**Active Learning**:
- "Human-in-the-Loop Label Generation with Active Learning and Weak Supervision" (ODSC, 2023)
- "A survey of active learning for quantifying vegetation traits" (Nature, 2024)

**Synthetic Data**:
- "A survey of synthetic data augmentation methods in computer vision" (arXiv:2403.10075, 2024)
- "Synthetic Data for Computer Vision" (Edge AI Alliance, 2025)

### B. Code Repository Structure

```
cardflux/
├── scripts/
│   └── ml/
│       ├── data/
│       │   ├── download_renders.py          # Scrape APIs
│       │   ├── augmentation_pipeline.py     # Albumentations
│       │   └── create_faiss_index.py        # Build indexes
│       ├── training/
│       │   ├── train_arcface.py             # ArcFace training
│       │   ├── finetune_dinov2.py           # Fine-tuning
│       │   └── evaluate_model.py            # Validation
│       ├── active_learning/
│       │   ├── collect_corrections.py       # Log user data
│       │   ├── weekly_retrain.py            # Automated retraining
│       │   └── hard_example_mining.py       # Find confusing pairs
│       └── deployment/
│           ├── export_to_onnx.py            # Optimize for prod
│           └── benchmark_latency.py         # Speed testing
├── models/
│   ├── magic_v1.0.pth
│   ├── pokemon_v1.0.pth
│   └── ...
├── data/
│   ├── renders/
│   │   ├── magic/
│   │   ├── pokemon/
│   │   └── ...
│   ├── augmented/
│   └── user_photos/
└── config/
    ├── training_config.yaml
    └── augmentation_config.yaml
```

### C. Sample Training Command

```bash
# Train Magic model with ArcFace
python scripts/ml/training/train_arcface.py \
  --game magic \
  --data_dir data/augmented/magic \
  --num_classes 27000 \
  --batch_size 512 \
  --num_epochs 20 \
  --learning_rate 1e-4 \
  --arcface_margin 0.50 \
  --arcface_scale 64.0 \
  --gpus 4 \
  --precision mixed \
  --output_dir models/magic_v1.0

# Fine-tune with user photos
python scripts/ml/training/finetune_dinov2.py \
  --checkpoint models/magic_v1.0/best.pth \
  --render_data data/augmented/magic \
  --real_data data/user_photos/magic \
  --mix_ratio 0.7 \
  --num_epochs 10 \
  --learning_rate 5e-5 \
  --output_dir models/magic_v1.1

# Export to ONNX for production
python scripts/ml/deployment/export_to_onnx.py \
  --checkpoint models/magic_v1.1/best.pth \
  --output models/magic_v1.1.onnx \
  --quantize int8 \
  --optimize
```

---

## CONCLUSION

**You can reach 99%+ accuracy using only renders + active learning.**

The key insights:
1. **Synthetic data can close the domain gap** with aggressive augmentation
2. **Metric learning (ArcFace) is superior** to softmax for card recognition
3. **Active learning creates a compounding advantage** that competitors can't replicate
4. **Hybrid visual + geometric** provides redundancy for edge cases

**Timeline**: 12 months from renders to 99% production accuracy
**Cost**: $15K-27K (affordable on $2M seed round)
**Feasibility**: HIGH (proven techniques, existing infrastructure)

This is not theoretical. Every component has been proven:
- DINOv2: State-of-the-art vision transformer (Meta AI)
- ArcFace: Industry-standard for face recognition (99.8% accuracy)
- Active learning: Used by Facebook, Google, Edelman (proven to work)
- Synthetic data: Used in autonomous driving, robotics (domain adaptation works)

**The only variable is execution.**

You have the opportunity to build the most accurate card recognition system in the world — not by 5%, but by 15-20% over competitors.

That's your moat. That's your $100M company.

Now go build it.
