# Capture Feedback System - Design Document

**Purpose**: Automatically capture and store card images during demos/usage to improve model accuracy over time

**Date**: 2025-10-23
**Status**: 🚧 **IN DEVELOPMENT**

---

## 🎯 **System Goals**

1. **Automatic Data Collection**: Capture every card scanned during demos
2. **Rich Metadata**: Store identification results, confidence, user feedback
3. **Training Ready**: Organize data for easy model fine-tuning
4. **Privacy Compliant**: User consent, no PII, can be disabled
5. **Git-Friendly**: Compress, deduplicate, sync-ready

---

## 📁 **Directory Structure**

```
data/
├── captures/                          # Captured card images (NOT in Git)
│   ├── one-piece/                     # Per-game organization
│   │   ├── 2025-10-23/               # Date-based folders
│   │   │   ├── capture_001/          # Individual capture session
│   │   │   │   ├── original.jpg      # Original photo (high-res)
│   │   │   │   ├── preprocessed.jpg  # After preprocessing
│   │   │   │   ├── cropped.jpg       # Auto-cropped card only
│   │   │   │   └── metadata.json     # Capture metadata
│   │   │   ├── capture_002/
│   │   │   └── ...
│   │   └── captures_index.jsonl      # All captures index
│   └── pokemon/
│       └── ...
│
├── curated/                           # Verified/cleaned captures → training
│   ├── one-piece.jsonl               # Existing curated data
│   └── one-piece-captured.jsonl      # Captured data (verified)
│
└── training/                          # Training-ready datasets
    ├── one-piece-v2/                 # Version-controlled datasets
    │   ├── train/                    # 80% training
    │   ├── val/                      # 10% validation
    │   ├── test/                     # 10% testing
    │   └── manifest.json             # Dataset manifest
    └── ...
```

---

## 📝 **Metadata Schema**

### **capture_metadata.json**
```json
{
  "capture_id": "20251023_143052_abc123",
  "timestamp": "2025-10-23T14:30:52.123Z",
  "game": "one-piece",

  "images": {
    "original": "original.jpg",
    "preprocessed": "preprocessed.jpg",
    "cropped": "cropped.jpg"
  },

  "identification": {
    "predicted_id": 123456,
    "predicted_name": "Monkey.D.Luffy",
    "predicted_number": "ST01-012",
    "confidence": "HIGH",
    "final_score": 0.8817,
    "visual_score": 0.8754,
    "geometric_score": 0.2200,
    "top_3_matches": [
      {"id": 123456, "name": "Monkey.D.Luffy", "score": 0.8817},
      {"id": 123457, "name": "Monkey.D.Luffy (Alternate Art)", "score": 0.8581},
      {"id": 123458, "name": "Monkey.D.Luffy (Full Art)", "score": 0.8258}
    ]
  },

  "features": {
    "ocr_detected": true,
    "ocr_number": "ST01-012",
    "ocr_confidence": 0.92,
    "foil_detected": false,
    "quality_score": 0.95,
    "sharpness": 1941.0
  },

  "user_feedback": {
    "correct": null,         // User can mark correct/incorrect
    "true_id": null,         // If incorrect, user can specify correct card
    "notes": null            // Optional notes
  },

  "capture_conditions": {
    "lighting": "good",      // Auto-detected from brightness
    "distance": "close_up",  // Auto-detected from card size
    "orientation": "upright" // Auto-detected rotation
  },

  "version": {
    "app_version": "0.2.2",
    "model_version": "dinov2-small-v1",
    "identifier_version": "v3.1"
  }
}
```

---

## 🔧 **Implementation Components**

### **1. CaptureManager** (Python)
Handles saving captures with metadata:

```python
# services/capture/capture_manager.py

class CaptureManager:
    """
    Manages capture storage and metadata.
    """

    def save_capture(
        self,
        image_path: str,
        identification_result: dict,
        game: str = "one-piece"
    ) -> str:
        """
        Save captured image with full metadata.

        Returns:
            capture_id: Unique ID for this capture
        """
        # Create unique capture ID
        capture_id = self._generate_capture_id()

        # Create directory structure
        capture_dir = self._create_capture_dir(game, capture_id)

        # Save images (original, preprocessed, cropped)
        self._save_images(image_path, capture_dir)

        # Generate and save metadata
        metadata = self._create_metadata(
            capture_id=capture_id,
            game=game,
            identification_result=identification_result,
            # ...
        )
        self._save_metadata(metadata, capture_dir)

        # Update captures index
        self._update_index(game, capture_id, metadata)

        return capture_id
```

### **2. Desktop App Integration**
Modify identification flow to save captures:

```typescript
// apps/desktop/src/main/index.ts

ipcMain.handle('identifier:identify', async (_event, imagePath: string, options: any = {}) => {
  try {
    // Run identification
    const result = await identificationService.identifyCard(imagePath, options);

    // AUTO-SAVE: Save capture if enabled in settings
    if (settings.enableCaptureSaving) {
      await identificationService.saveCapture(imagePath, result);
    }

    return { success: true, result };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
});
```

### **3. User Feedback Interface**
Add feedback UI to desktop app:

```tsx
// apps/desktop/src/renderer/components/CardStack.tsx

<div className="card-item">
  <div className="card-info">
    {card.name} - {card.confidence}
  </div>

  {/* Feedback buttons */}
  <div className="card-feedback">
    <button onClick={() => markCorrect(card.captureId)}>
      ✓ Correct
    </button>
    <button onClick={() => markIncorrect(card.captureId)}>
      ✗ Wrong Card
    </button>
  </div>
</div>
```

### **4. Training Data Pipeline**
Convert captures to training data:

```python
# scripts/training/prepare_training_data.py

def prepare_captures_for_training(
    captures_dir: str,
    output_dir: str,
    min_confidence: float = 0.85,
    require_user_verification: bool = True
):
    """
    Convert captures to training-ready dataset.

    Filters:
    - Only HIGH confidence captures (or user-verified)
    - Only user-marked correct (if require_user_verification)
    - Deduplicate by card ID
    - Balance dataset (max N per card)
    """
    pass
```

---

## 🚀 **Features**

### **Automatic Features**:
1. ✅ **Auto-save every scan** (optional, can be disabled)
2. ✅ **Multiple image formats** (original, preprocessed, cropped)
3. ✅ **Rich metadata** (ID results, confidence, OCR, foil)
4. ✅ **Date-organized** (easy to find demo sessions)
5. ✅ **Duplicate detection** (avoid storing same card twice)

### **User Feedback Features**:
1. ✅ **Mark correct/incorrect** (validate predictions)
2. ✅ **Specify correct card** (if misidentified)
3. ✅ **Add notes** (lighting issues, damage, etc.)
4. ✅ **Export feedback** (for manual review)

### **Training Features**:
1. ✅ **Auto-filter high quality** (confidence > 0.85)
2. ✅ **User-verified only** (optional strict mode)
3. ✅ **Balanced sampling** (prevent over-representation)
4. ✅ **Train/Val/Test split** (80/10/10)
5. ✅ **Augmentation pipeline** (brightness, rotation, crop variations)

---

## 🔒 **Privacy & Settings**

### **User Settings** (Desktop App):
```typescript
interface CaptureSettings {
  enabled: boolean;              // Enable/disable capture saving
  saveOriginal: boolean;         // Save high-res original (large files)
  savePreprocessed: boolean;     // Save preprocessed image
  saveCropped: boolean;          // Save cropped card only (smallest)
  requestFeedback: boolean;      // Ask user to verify after each scan
  autoSync: boolean;             // Auto-sync to cloud (future)
}
```

### **Privacy Compliance**:
- No PII collected (just card images)
- User can disable at any time
- Clear disclosure: "Help improve CardFlux by sharing scanned cards"
- Data stays local (not synced without consent)

---

## 📊 **Usage Statistics**

Track capture metrics for monitoring:

```json
// data/captures/statistics.json
{
  "total_captures": 1523,
  "by_game": {
    "one-piece": 1234,
    "pokemon": 289
  },
  "by_confidence": {
    "high": 712,
    "moderate": 634,
    "low": 177
  },
  "user_verified": {
    "correct": 456,
    "incorrect": 34,
    "unverified": 1033
  },
  "storage_size_mb": 2341.5,
  "last_updated": "2025-10-23T14:30:52Z"
}
```

---

## 🔄 **Sync Strategy**

### **Local → Git (Developer)**
```bash
# Prepare captures for commit
python scripts/training/prepare_captures_for_commit.py

# This will:
# 1. Filter to user-verified correct
# 2. Compress images
# 3. Deduplicate
# 4. Create manifest
# 5. Move to data/training/one-piece-v2/

git add data/training/one-piece-v2/
git commit -m "feat: Add captured training data (123 cards)"
```

### **Git → Local (Other Developers)**
```bash
# Pull latest training data
git pull origin main

# Rebuild FAISS index with new captures
python services/embedder/bin/embed_cards.py --game one-piece --include-captures
python services/indexer/bin/build_faiss.py --game one-piece
```

---

## 🎯 **Roadmap**

### **Phase 1: Basic Capture** (This PR) ✅
- [ ] CaptureManager implementation
- [ ] Desktop app integration (auto-save)
- [ ] Metadata schema
- [ ] Directory structure

### **Phase 2: User Feedback** (Next Week)
- [ ] Feedback UI in desktop app
- [ ] Mark correct/incorrect
- [ ] Notes/comments
- [ ] Export feedback CSV

### **Phase 3: Training Pipeline** (Week After)
- [ ] Prepare training data script
- [ ] Augmentation pipeline
- [ ] Train/val/test split
- [ ] Fine-tuning script

### **Phase 4: Cloud Sync** (Future)
- [ ] Optional cloud backup
- [ ] Multi-device sync
- [ ] Collaborative training data
- [ ] Privacy controls

---

## 💡 **Benefits**

### **For Model Improvement**:
1. **Real-world data**: Actual user photos (lighting, angles, conditions)
2. **Diversity**: Different cameras, environments, card conditions
3. **Edge cases**: Captures difficult cards that need more training
4. **Continuous learning**: Model improves with every demo

### **For Validation**:
1. **Ground truth from users**: "Was this correct?" = instant validation
2. **Confidence calibration**: Track HIGH confidence accuracy over time
3. **Failure analysis**: Study incorrect predictions

### **For Product**:
1. **Engagement**: Users see they're contributing
2. **Transparency**: Show how data improves system
3. **Trust**: User control over data sharing

---

## 🚨 **Important Considerations**

### **Storage Management**:
- Captures can grow to **GB/TB** over time
- Implement cleanup policy: delete after 30 days (configurable)
- Or compress old captures (90% smaller)

### **Git LFS**:
- Don't commit raw captures to Git (too large)
- Only commit curated/verified training data
- Use `.gitignore` for `data/captures/`

### **Deduplication**:
- Same card scanned multiple times = waste
- Use perceptual hashing (pHash) to detect duplicates
- Keep best quality version

---

## 📖 **Documentation**

### **For Users**:
```markdown
## Help Improve CardFlux

Every card you scan helps make CardFlux more accurate!

**What we capture**:
- Card images (anonymous)
- Identification results
- Your feedback (if you choose to provide it)

**What we DON'T capture**:
- Your name or personal info
- Location data
- Any data outside the app

**You control your data**:
- Disable capture in Settings
- Delete captures anytime
- Choose what to share
```

### **For Developers**:
```markdown
## Working with Captures

### View captures:
ls data/captures/one-piece/$(date +%Y-%m-%d)/

### Export captures for review:
python scripts/training/export_captures.py --date 2025-10-23 --format csv

### Prepare for training:
python scripts/training/prepare_training_data.py \
  --captures-dir data/captures/one-piece/ \
  --output data/training/one-piece-v2/ \
  --verified-only
```

---

**Next Steps**:
1. Implement CaptureManager
2. Integrate with desktop app
3. Test during demo
4. Collect 100+ captures
5. Fine-tune model with captured data

This creates a flywheel: **More demos → More data → Better model → Better demos**

**Status**: Ready to implement ✅
