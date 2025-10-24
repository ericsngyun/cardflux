# Production Readiness Roadmap - Complete Implementation Plan

**Date**: 2025-10-22
**Goal**: Make CardFlux production-ready with cloud data pipeline
**Timeline**: 2-3 weeks

---

## 🎯 Overview

### Current State:
✅ **Core identification working** (47% HIGH confidence, 778ms avg)
✅ **Card detection** (100% success rate)
✅ **Desktop app** (v0.2.2)
✅ **Data pipeline infrastructure** (TCGPlayer scraping, embeddings, FAISS)
✅ **DataManager with CDN sync** (already implemented!)

### Target State:
🎯 **90%+ HIGH confidence** (production-grade accuracy)
🎯 **Cloud-based data pipeline** (prevent API blacklisting)
🎯 **Automatic daily updates** (sync from cloud)
🎯 **Flawless identification** (<1% error rate)

---

## 📋 Implementation Plan

### **Phase 1: Critical Identification Improvements** (Week 1)

#### 1.1 Confidence Calibration System ⚠️ **HIGHEST PRIORITY**

**Current Problem**:
- Thresholds are arbitrary (0.75 HIGH, 0.62 MODERATE)
- Don't know if HIGH = 95% accurate or 70% accurate
- No statistical basis for confidence levels

**Solution**: Build calibration curve from real data

**Implementation**:
```python
# scripts/identification/core/confidence_calibrator.py

class ConfidenceCalibrator:
    """
    Calibrate confidence scores based on historical accuracy.
    """

    def __init__(self, calibration_data_path: str):
        self.calibration_curve = self._load_calibration_data(calibration_data_path)

    def calibrate(self, raw_score: float, margin: float, geometric_score: float,
                  quality_tier: str) -> Dict:
        """
        Convert raw score to calibrated confidence with expected accuracy.

        Returns:
            {
                'confidence': 'HIGH' | 'MODERATE' | 'LOW' | 'AMBIGUOUS',
                'expected_accuracy': float (0-1),
                'calibrated_score': float (0-1)
            }
        """
        # Use lookup table built from test data
        # Example:
        # raw_score=0.85, margin=0.15, geometric>0.15 → HIGH, 96% accuracy
        # raw_score=0.75, margin=0.05 → AMBIGUOUS (too close), 80% accuracy
        # raw_score=0.65, margin=0.10, geometric=0 → MODERATE, 85% accuracy

        key = (
            round(raw_score, 2),
            'high_margin' if margin > 0.10 else 'low_margin',
            'good_geom' if geometric_score > 0.15 else 'weak_geom'
        )

        calibration = self.calibration_curve.get(key, DEFAULT_CALIBRATION)

        return {
            'confidence': calibration['level'],
            'expected_accuracy': calibration['accuracy'],
            'calibrated_score': raw_score * calibration['adjustment']
        }
```

**Test Data Collection**:
```bash
# Step 1: Collect 100-200 real shop cards
python scripts/identification/tools/collect_ground_truth.py \
    --input-dir real-shop-cards/ \
    --output ground_truth.json

# Step 2: Run identification and compare
python scripts/identification/tools/build_calibration_curve.py \
    --ground-truth ground_truth.json \
    --output calibration_data.json

# Step 3: Validate calibration
python scripts/identification/tests/test_calibration_accuracy.py
```

**Files to Create**:
- `scripts/identification/core/confidence_calibrator.py` - Calibration system
- `scripts/identification/tools/collect_ground_truth.py` - Ground truth collection
- `scripts/identification/tools/build_calibration_curve.py` - Build calibration
- `scripts/identification/tests/test_calibration_accuracy.py` - Validation

**Acceptance Criteria**:
- ✅ HIGH confidence = 95%+ actual accuracy
- ✅ MODERATE confidence = 85-95% actual accuracy
- ✅ LOW confidence = <85% actual accuracy
- ✅ AMBIGUOUS flag for close matches (margin <0.05)

**Time Estimate**: 3-4 days

---

#### 1.2 Ambiguous Result Handling

**Current Problem**:
- Close matches (score difference <0.05) reported as HIGH confidence
- User doesn't know when to double-check

**Solution**: Add AMBIGUOUS confidence level

**Implementation**:
```python
# In production_card_identifier.py

def _calculate_confidence(self, best_score, second_best_score, geometric_score):
    margin = best_score - second_best_score

    # CRITICAL: Flag ambiguous matches
    if margin < 0.05:
        return {
            'level': 'AMBIGUOUS',
            'warning': 'Multiple close matches - please verify manually',
            'alternatives': [best_match, second_best_match],
            'margin': margin
        }

    # Use calibrator for other cases
    return self.calibrator.calibrate(best_score, margin, geometric_score, quality_tier)
```

**UI Changes**:
- Show yellow warning badge for AMBIGUOUS
- Display top 3 matches side-by-side for manual selection
- Don't auto-add AMBIGUOUS to inventory (require manual confirm)

**Time Estimate**: 1 day

---

#### 1.3 Rotation Invariance

**Current Problem**:
- Cards may be oriented at different angles
- System may fail on rotated cards

**Solution**: Add rotation detection and normalization

**Implementation**:
```python
# scripts/identification/core/rotation_corrector.py

class RotationCorrector:
    """
    Detect and correct card rotation using geometric features.
    """

    def detect_rotation(self, image: np.ndarray) -> float:
        """
        Detect rotation angle using:
        1. ORB feature orientation histogram
        2. Edge detection and Hough lines
        3. Text orientation (OCR)

        Returns: angle in degrees (0-360)
        """
        pass

    def correct_rotation(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image to upright position.
        """
        # Rotate around center
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h))
        return rotated
```

**Integration**:
```python
# In production_card_identifier.py, add stage 0c:

# [Stage 0c] Rotation correction
rotation_angle = self.rotation_corrector.detect_rotation(image)
if abs(rotation_angle) > 5:  # More than 5° off
    image = self.rotation_corrector.correct_rotation(image, rotation_angle)
    logger.info(f"Corrected rotation: {rotation_angle:.1f}°")
```

**Testing**:
```python
# Test cards at 0°, 45°, 90°, 180°, 270°
python scripts/identification/tests/test_rotation_invariance.py
```

**Time Estimate**: 2-3 days

---

#### 1.4 Desktop App Integration

**Current Problem**:
- `polished_card_detector.py` not integrated into desktop app
- App doesn't use card detection before identification

**Solution**: Integrate card detector into camera workflow

**Files to Modify**:
```typescript
// apps/desktop/src/python/identification_service.py

def identify_card(image_path: str, settings: dict) -> dict:
    """
    Main identification endpoint with card detection.
    """
    # Stage 0: Card detection
    detector = PolishedCardDetector()
    detection_result = detector.detect_and_crop(image_path)

    if detection_result['status'] != 'PERFECT' and detection_result['status'] != 'GOOD':
        return {
            'success': False,
            'error': 'NO_CARD_DETECTED',
            'message': f"Card detection failed: {detection_result['status']}",
            'detection': detection_result
        }

    # Use cropped image for identification
    cropped_path = detection_result['cropped_path']

    # Stage 1-5: Identification
    identifier = ProductionCardIdentifier(game=settings['game'])
    result = identifier.identify(cropped_path, top_k=settings['top_k'])

    # Add detection info to result
    result['detection'] = detection_result

    return result
```

```typescript
// apps/desktop/src/renderer/components/CameraView.tsx

// Add visual feedback for card detection
interface CardDetectionOverlay {
  status: 'PERFECT' | 'GOOD' | 'POOR_QUALITY' | 'NO_CARD';
  confidence: number;
  boundingBox?: Rectangle;
  message?: string;
}

// Show green box when card detected, red when no card
```

**Acceptance Criteria**:
- ✅ Card detection runs before identification
- ✅ Visual feedback shows detection status
- ✅ Bad detections rejected before wasting time on identification
- ✅ Cropped image used for better accuracy

**Time Estimate**: 2 days

---

### **Phase 2: Cloud Data Pipeline** (Week 2)

#### 2.1 Cloud Architecture Design

**Current Problem**:
- Multiple desktop apps scraping TCGPlayer → API rate limits
- Risk of getting blacklisted
- Each app downloads 400MB+ of images

**Solution**: Centralized cloud pipeline

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUD PIPELINE (AWS)                      │
│                                                               │
│  ┌──────────────┐                                            │
│  │ GitHub       │                                            │
│  │ Actions      │ (Scheduled: Daily at 2 AM UTC)            │
│  │ Workflow     │                                            │
│  └───────┬──────┘                                            │
│          │                                                    │
│          ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Data Ingestion Pipeline                               │   │
│  │                                                        │   │
│  │ 1. pull_tcgcsv.ts                                     │   │
│  │    → Fetch from tcgcsv.com (ETag, rate-limited)      │   │
│  │    → Incremental updates only                         │   │
│  │                                                        │   │
│  │ 2. fetch_images.ts                                    │   │
│  │    → Download new card images                         │   │
│  │    → Incremental (only changed cards)                 │   │
│  │                                                        │   │
│  │ 3. embedder service                                   │   │
│  │    → Generate DINOv2 embeddings                       │   │
│  │    → Only for new/updated cards                       │   │
│  │                                                        │   │
│  │ 4. indexer service                                    │   │
│  │    → Build FAISS index                                │   │
│  │                                                        │   │
│  │ 5. publisher service                                  │   │
│  │    → Generate manifest.json                           │   │
│  │    → Create .tar.gz archives                          │   │
│  │    → Upload to S3                                     │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                         │
│                     ▼                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AWS S3 + CloudFront CDN                               │   │
│  │                                                        │   │
│  │ databases/                                            │   │
│  │   manifest.json (version info)                        │   │
│  │   one-piece/                                          │   │
│  │     v2025.01.22/                                      │   │
│  │       images.tar.gz (400 MB)                          │   │
│  │       index.tar.gz (7 MB)                             │   │
│  │       metadata.tar.gz (7 MB)                          │   │
│  │       manifest.json                                   │   │
│  │   pokemon/                                            │   │
│  │     v2025.01.22/                                      │   │
│  │       ...                                             │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                         │
└─────────────────────┼─────────────────────────────────────────┘
                      │
                      │ HTTPS (CloudFront)
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Desktop │  │ Desktop │  │ Desktop │
   │ App #1  │  │ App #2  │  │ App #N  │
   └─────────┘  └─────────┘  └─────────┘

   All apps sync from CDN (no direct TCGPlayer scraping)
```

**Benefits**:
- ✅ Single scraper → no API blacklisting
- ✅ Centralized updates → all users get same data
- ✅ CloudFront CDN → fast downloads worldwide
- ✅ Incremental updates → only download changed data
- ✅ Version control → rollback if needed

**Time Estimate**: 1 day design + documentation

---

#### 2.2 GitHub Actions Workflow

**Implementation**:
```yaml
# .github/workflows/data-pipeline.yml

name: Daily Data Pipeline

on:
  schedule:
    # Run daily at 2 AM UTC (low traffic time)
    - cron: '0 2 * * *'
  workflow_dispatch: # Manual trigger for testing

env:
  AWS_REGION: us-east-1
  S3_BUCKET: cardflux-databases
  CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}

jobs:
  ingest-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 120 # 2 hours max

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pnpm install --frozen-lockfile
          pip install -r requirements.txt

      - name: Download previous state from S3
        run: |
          aws s3 sync s3://${{ env.S3_BUCKET }}/state/ data/state/
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Pull TCGPlayer data (incremental)
        run: pnpm tcgplayer:pull
        env:
          RATE_LIMIT_DELAY: 1000 # 1 req/sec

      - name: Fetch card images (incremental)
        run: pnpm pipeline:fetch-images

      - name: Generate embeddings (new cards only)
        run: pnpm pipeline:embed
        env:
          BATCH_SIZE: 32
          DEVICE: cpu # GitHub Actions doesn't have GPU

      - name: Build FAISS indexes
        run: pnpm pipeline:index

      - name: Generate manifests
        run: pnpm pipeline:manifest

      - name: Package databases
        run: pnpm pipeline:package

      - name: Upload to S3
        run: pnpm pipeline:publish
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/databases/manifest.json"

      - name: Upload state to S3
        run: |
          aws s3 sync data/state/ s3://${{ env.S3_BUCKET }}/state/

      - name: Notify on failure
        if: failure()
        run: |
          # Send notification (Slack, email, etc.)
          echo "Pipeline failed! Check logs."
```

**Time Estimate**: 2-3 days implementation + testing

---

#### 2.3 Desktop App Sync Integration

**Current State**: DataManager already implemented! Just needs CDN URL

**Changes Needed**:
```typescript
// apps/desktop/src/main/core/data-manager.ts

// Update CDN URLs
const CDN_BASE_URL = 'https://d1234567890.cloudfront.net'; // CloudFront URL
const FALLBACK_CDN_URL = 'https://github.com/cardflux/cardflux-data/releases/latest/download';

// Already has:
// - Version checking
// - Download with progress
// - Retry logic
// - Checksum verification
// - Extraction
// - Update notifications
```

**Add Auto-Update Check**:
```typescript
// apps/desktop/src/main/index.ts

// On app startup
app.whenReady().then(async () => {
  // ... existing initialization ...

  // Initialize data manager
  dataManager = DataManager.getInstance();
  await dataManager.initialize();

  // Check for updates
  const currentGame = settings.get('game') || 'one-piece';

  if (dataManager.isUpdateAvailable(currentGame)) {
    const latestVersion = dataManager.getLatestVersion(currentGame);
    const installedVersion = dataManager.getInstalledVersion(currentGame);

    logger.info('DataManager', 'Update available', {
      game: currentGame,
      installed: installedVersion,
      latest: latestVersion
    });

    // Show notification to user
    mainWindow.webContents.send('update-available', {
      game: currentGame,
      installed: installedVersion,
      latest: latestVersion
    });
  }
});
```

**UI for Update Notification**:
```typescript
// apps/desktop/src/renderer/components/UpdateNotification.tsx

export function UpdateNotification({ game, installedVersion, latestVersion }) {
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpdate = async () => {
    setDownloading(true);

    // Listen for progress
    window.api.on('download-progress', (progress) => {
      setProgress(progress.percentage);
    });

    // Start download
    await window.api.downloadUpdate(game);

    setDownloading(false);
  };

  return (
    <div className="update-notification">
      <h3>Update Available</h3>
      <p>
        {game}: {installedVersion} → {latestVersion}
      </p>

      {downloading ? (
        <ProgressBar value={progress} />
      ) : (
        <button onClick={handleUpdate}>Download Update</button>
      )}
    </div>
  );
}
```

**Time Estimate**: 1-2 days

---

### **Phase 3: Additional Improvements** (Week 3)

#### 3.1 Sleeve/Glare Detection

**Problem**: Cards in sleeves often have glare reducing match quality

**Solution**: Detect glare regions and apply preprocessing

```python
# scripts/identification/core/glare_detector.py

class GlareDetector:
    """
    Detect and mitigate glare on cards in sleeves.
    """

    def detect_glare(self, image: np.ndarray) -> Dict:
        """
        Detect glare regions using:
        1. Bright spot detection (HSV V channel > threshold)
        2. Gradient analysis (sharp transitions)
        3. Specular reflection detection
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # Find very bright regions
        glare_mask = v_channel > 240
        glare_percentage = np.sum(glare_mask) / glare_mask.size

        return {
            'has_glare': glare_percentage > 0.05,  # 5% of image
            'glare_percentage': glare_percentage,
            'mask': glare_mask
        }

    def reduce_glare(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Reduce glare using inpainting or adaptive histogram equalization.
        """
        # Inpaint glare regions
        result = cv2.inpaint(image, mask.astype(np.uint8), 3, cv2.INPAINT_TELEA)
        return result
```

**Time Estimate**: 2-3 days

---

#### 3.2 Performance Monitoring

**Add telemetry to track system performance**:

```python
# scripts/identification/core/telemetry.py

class IdentificationTelemetry:
    """
    Track identification metrics for monitoring.
    """

    def __init__(self, log_path: str):
        self.log_path = log_path

    def log_identification(self, result: Dict):
        """
        Log identification event with metrics.
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'image_path': result['image_path'],
            'confidence': result['confidence'],
            'final_score': result['final_score'],
            'visual_score': result['visual_score'],
            'geometric_score': result['geometric_score'],
            'time_ms': result['time_ms'],
            'card_detected': result.get('detection', {}).get('status'),
            'quality_tier': result.get('quality_tier'),
            'foil_detected': result.get('foil', False)
        }

        # Append to JSONL log
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(event) + '\n')
```

**Dashboard** (optional):
- Grafana dashboard showing:
  - Confidence distribution over time
  - Average identification time
  - Error rate
  - Card detection success rate

**Time Estimate**: 1-2 days

---

## 📊 Success Metrics

### Production-Ready Criteria:

**Accuracy**:
- ✅ HIGH confidence = 95%+ actual accuracy (calibrated)
- ✅ Overall accuracy ≥ 90%
- ✅ Error rate < 1%

**Performance**:
- ✅ Average identification time < 1000ms
- ✅ Card detection time < 100ms
- ✅ 99% uptime (system stability)

**User Experience**:
- ✅ Clear confidence indicators
- ✅ AMBIGUOUS flag for uncertain matches
- ✅ Automatic updates from cloud
- ✅ Visual feedback for card detection

**Infrastructure**:
- ✅ Centralized cloud pipeline running
- ✅ Daily automatic updates
- ✅ No direct TCGPlayer API access from apps
- ✅ CloudFront CDN serving data globally

---

## 🚀 Implementation Timeline

### Week 1: Critical Identification
- **Days 1-3**: Confidence calibration (collect data, build curve, test)
- **Day 4**: Ambiguous result handling
- **Days 5-6**: Rotation invariance
- **Day 7**: Desktop app integration (card detector)

### Week 2: Cloud Pipeline
- **Day 1**: Architecture design + documentation
- **Days 2-3**: GitHub Actions workflow implementation
- **Day 4**: AWS S3 + CloudFront setup
- **Day 5**: Desktop app sync integration
- **Days 6-7**: End-to-end testing

### Week 3: Polish & Monitoring
- **Days 1-2**: Sleeve/glare detection
- **Day 3**: Performance monitoring/telemetry
- **Days 4-5**: Documentation + user guides
- **Days 6-7**: Beta testing with real shop

---

## 💰 Cost Estimates

### AWS Infrastructure:
- **S3 Storage**: ~$10/month (100 GB @ $0.023/GB)
- **CloudFront**: ~$10/month (100 GB transfer @ $0.085/GB)
- **GitHub Actions**: Free (2000 minutes/month, ~30 min/day = 900 min/month)

**Total**: ~$20/month for unlimited users

---

## 📝 Next Steps

1. **Review this roadmap** - Adjust priorities/timeline as needed
2. **Collect ground truth data** - Start collecting shop cards for calibration
3. **Set up AWS account** - If not already done
4. **Begin Week 1 implementation** - Confidence calibration first

---

**Ready to start?** Let me know which phase you want to tackle first!
