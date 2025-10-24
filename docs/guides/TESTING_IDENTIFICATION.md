# Testing Card Identification - User Guide

> **Quick Start**: Run identification tests on your card images
> **Time**: ~1-2 minutes for 10 images
> **Skill Level**: Beginner-friendly

---

## Quick Start (TL;DR)

```bash
# Navigate to project root
cd C:\Users\rayno\eric\cardflux

# Run the test
python scripts/identification/tests/test_all_production_images.py
```

That's it! The test will automatically:
- ✅ Find all images in `test-images/one-piece/`
- ✅ Identify each card
- ✅ Show detailed results
- ✅ Save results to JSON file

---

## What This Test Does

The test script (`test_all_production_images.py`) will:

1. **Load the identifier** (one-time, ~4 seconds)
2. **Process each image** in `test-images/one-piece/` (~1 second each)
3. **Show results** for each card:
   - Card name and number
   - Confidence level (HIGH/MODERATE/LOW)
   - Scores (visual, geometric, final)
   - Processing time
   - Top 3 matches
4. **Generate summary statistics**:
   - Confidence distribution
   - Average scores
   - Performance metrics
5. **Save results** to `scripts/identification/tests/test_all_production_results.json`

---

## Step-by-Step Instructions

### Step 1: Prepare Your Images

**Option A: Use Existing Test Images**
```
test-images/one-piece/
  ├── bege.png
  ├── blackbeard.png
  ├── mihawk.png
  └── ... (7 more images)
```

**Option B: Add Your Own Images**
1. Place your card images in `test-images/one-piece/`
2. Supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`
3. Any filename works (e.g., `my-card.jpg`, `test-1.png`)

### Step 2: Run the Test

**Open PowerShell/Command Prompt**:
```powershell
# Navigate to project root
cd C:\Users\rayno\eric\cardflux

# Run the test script
python scripts/identification/tests/test_all_production_images.py
```

**Expected Output**:
```
================================================================================
PRODUCTION CARD IDENTIFIER - COMPREHENSIVE TEST SUITE
================================================================================

Test Directory: C:\Users\rayno\eric\cardflux\test-images\one-piece
Total Images: 10

[1/3] Initializing identifier...
[OK] Identifier ready (4238ms)

[2/3] Testing all images...
================================================================================

[1/10] bege.png
--------------------------------------------------------------------------------
  Card: Capone"Gang"Bege
  Number: ST02-004
  Confidence: HIGH
  Final Score: 0.9232
    - Visual: 0.8976
    - Geometric: 1.0000
  Quality:
    - Sharpness: 1941.0
    - Quality Tier: unknown
  Time: 615ms
  Top 3:
    1. Capone"Gang"Bege (ST02-004) - Final: 0.9232 (V:0.898 G:1.000)
    2. Capone"Gang"Bege (ST02-004) (Jolly Roger Foil) - Final: 0.8624 (V:0.855 G:0.000)
    3. Capone"Gang"Bege (ST02-004) - Final: 0.8313 (V:0.875 G:0.000)

... (9 more images)

================================================================================
[3/3] RESULTS SUMMARY
================================================================================

Confidence Distribution:
  HIGH:     6/10 (60.0%)
  MODERATE: 3/10 (30.0%)
  LOW:      1/10 (10.0%)

Average Scores:
  Final:     0.6992
  Visual:    0.7136
  Geometric: 0.3977

Performance:
  Average: 992ms
  Min:     615ms
  Max:     1370ms

System Performance: GOOD
  HIGH confidence rate: 60.0%
  Average final score: 0.6992
  Average speed: 992ms

[OK] Results saved to: C:\Users\rayno\eric\cardflux\scripts\identification\tests\test_all_production_results.json
================================================================================
```

### Step 3: Review Results

**Console Output**: Detailed results for each image (see above)

**JSON File**: Complete results saved to:
```
scripts/identification/tests/test_all_production_results.json
```

**JSON Structure**:
```json
{
  "results": [
    {
      "image": "bege.png",
      "card_name": "Capone\"Gang\"Bege",
      "card_number": "ST02-004",
      "confidence": "HIGH",
      "final_score": 0.9232,
      "visual_score": 0.8976,
      "geometric_score": 1.0,
      "time_ms": 615,
      "top_3_matches": [...]
    },
    ...
  ],
  "statistics": {
    "total_images": 10,
    "high_confidence": 6,
    "moderate_confidence": 3,
    "low_confidence": 1,
    "avg_final_score": 0.6992,
    "avg_time_ms": 992
  }
}
```

---

## Understanding Results

### Confidence Levels

| Level | Meaning | Shop Action | Score Range |
|-------|---------|-------------|-------------|
| **HIGH** | Very confident match | ✅ Auto-accept | ≥0.65 or ≥0.55 with margin ≥0.05 |
| **MODERATE** | Likely correct, review recommended | ⚠️ Manual review | ≥0.55 |
| **LOW** | Uncertain, needs verification | ❌ Manual review | <0.55 |

### Score Breakdown

**Final Score** (0.0 - 1.0):
- Combined score from visual + geometric + bonuses
- Higher = more confident match

**Visual Score** (DINOv2 similarity):
- 0.90-1.00: Excellent visual match
- 0.75-0.89: Good visual match
- 0.60-0.74: Decent visual match
- <0.60: Weak visual match

**Geometric Score** (ORB/AKAZE matching):
- 0.50-1.00: Excellent geometric match
- 0.20-0.49: Good geometric match
- 0.05-0.19: Weak geometric match
- 0.00-0.04: No geometric match (or match failed)

**Bonuses**:
- **Foil Boost**: +0.05 if foil detected
- **Card# Boost**: +0.12 if OCR matches card number

### Quality Tiers

- **High**: Sharp, large images (>800x800, sharpness >2000)
- **Medium**: Acceptable quality (>400x400, sharpness >1000)
- **Low**: Compressed/small/blurry (<400x400 or sharpness <1000)

### Performance Metrics

- **<500ms**: Excellent (simple geometric match)
- **500-1000ms**: Good (typical performance)
- **1000-1500ms**: Acceptable (complex geometric matching)
- **>1500ms**: Slow (may indicate quality issues)

---

## Testing Your Own Images

### Best Practices

1. **Image Quality**:
   - Use good lighting (natural light or bright LED)
   - Avoid glare (tilt card slightly if needed)
   - Keep camera steady (clear, sharp image)
   - Minimum 400x400 pixels (larger is better)

2. **Card Positioning**:
   - Fill frame with card (card should be 50-80% of image)
   - Straight-on angle (not too skewed)
   - Avoid shadows across card

3. **Testing Strategy**:
   - Start with 5-10 cards
   - Include variety (characters, events, different sets)
   - Include challenging cases (foils, alternate arts, older cards)

### Adding Your Images

```powershell
# Copy your images to test directory
cp my-card-photos/*.jpg test-images/one-piece/

# Run test
python scripts/identification/tests/test_all_production_images.py
```

---

## Interpreting Test Results

### Excellent Results
```
HIGH confidence rate: 80-100%
Average final score: >0.75
Average speed: <1000ms
```
**Action**: System ready for production use

### Good Results
```
HIGH confidence rate: 60-79%
Average final score: 0.65-0.75
Average speed: <1500ms
```
**Action**: Deploy with manual review workflow for MODERATE/LOW

### Needs Improvement
```
HIGH confidence rate: <60%
Average final score: <0.65
Average speed: >1500ms
```
**Action**: Review image quality, check for compressed reference images, consider fine-tuning

---

## Troubleshooting

### Issue: "ModuleNotFoundError"
```
ModuleNotFoundError: No module named 'production_card_identifier'
```

**Solution**: Make sure you're in the project root directory:
```powershell
cd C:\Users\rayno\eric\cardflux
python scripts/identification/tests/test_all_production_images.py
```

### Issue: "Test directory not found"
```
ERROR: Test directory not found: test-images/one-piece
```

**Solution**: Create the directory or add images:
```powershell
mkdir test-images\one-piece
# Add images to this directory
```

### Issue: Slow Performance (>2000ms per image)
**Possible Causes**:
- First run (model loading overhead)
- Large images (>2000x2000 pixels)
- Low-end CPU

**Solutions**:
- First run is always slower (~4s initialization)
- Resize images to 800-1200 pixels
- Consider GPU acceleration (see `docs/guides/WINDOWS_SETUP_GUIDE.md`)

### Issue: Low Confidence on All Images
**Possible Causes**:
- Poor image quality (blurry, small, low resolution)
- Different game (not One Piece TCG)
- Reference images missing or corrupted

**Solutions**:
- Check image quality (sharpness score should be >1000)
- Verify game: `identifier.game` should be "one-piece"
- Re-download artifacts: `pnpm update:sync`

### Issue: Wrong Card Identified
**Possible Causes**:
- Variant/alternate art (system identifies base card)
- Similar artwork (different cards look alike)
- Watermarked reference images

**Solutions**:
- Check Top 3 matches (correct card might be #2 or #3)
- Review geometric score (should be >0.15 for good match)
- Report false positives for future improvements

---

## Advanced Usage

### Test Specific Directory
```python
# Edit test_all_production_images.py
# Or run with custom directory:
python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / "scripts/identification/core"))
from production_card_identifier import ProductionCardIdentifier

identifier = ProductionCardIdentifier(game="one-piece", verbose=True)
result = identifier.identify("path/to/my/card.jpg")
print(result)
```

### Single Image Test
```python
python scripts/identification/core/production_card_identifier.py test-images/one-piece/bege.png
```

### Verbose Mode
Edit `test_all_production_images.py` line 56:
```python
# Change verbose=False to verbose=True
identifier = ProductionCardIdentifier(game="one-piece", verbose=True)
```

This will show detailed processing steps for each image.

---

## Expected Test Results (Current System)

**Baseline Performance** (10 test images, as of 2025-10-24):

```
Confidence Distribution:
  HIGH:     60% (6/10)
  MODERATE: 30% (3/10)
  LOW:      10% (1/10)

Average Scores:
  Final:     0.6992
  Visual:    0.7136
  Geometric: 0.3977

Performance:
  Average: 992ms
  Min:     615ms
  Max:     1370ms
```

If your results are significantly different, check:
- ✅ Latest code version (run `git pull`)
- ✅ Up-to-date artifacts (run `pnpm update:sync`)
- ✅ Python dependencies installed (run `pip install -r requirements.txt`)

---

## Next Steps

After testing:

1. **Good Results?**
   - ✅ Test with real shop inventory (50-100 cards)
   - ✅ Deploy desktop app for production use
   - ✅ Monitor false positive rate

2. **Need Improvement?**
   - 📸 Review image quality (lighting, camera, positioning)
   - 🔧 Check reference images (re-download if needed)
   - 📊 Analyze which cards fail (report patterns)
   - 🎯 Consider fine-tuning (see `docs/guides/FINETUNING_GUIDE.md`)

3. **Want to Contribute?**
   - 📝 Report test results (share your JSON file)
   - 🐛 Report false positives/negatives
   - 💡 Suggest improvements
   - 🔬 Help with fine-tuning dataset

---

## Summary

**Run Test**:
```bash
python scripts/identification/tests/test_all_production_images.py
```

**Review Results**:
- Console output (detailed results)
- `test_all_production_results.json` (complete data)

**Target Performance**:
- HIGH: ≥60%
- Average score: ≥0.65
- Speed: <1500ms

**Questions?** Check `docs/guides/WINDOWS_SETUP_GUIDE.md` or report issues on GitHub.

---

**Last Updated**: 2025-10-24
**Maintained By**: CardFlux Development Team
