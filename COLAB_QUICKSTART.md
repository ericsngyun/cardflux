# Google Colab Fine-Tuning - Quick Start Guide

> **Total Time**: 4-5 hours (mostly automated)
> **Cost**: Free (using Colab's free T4 GPU)

---

## Step-by-Step Instructions

### 1. Prepare Your Files (5 minutes)

**Option A: Upload to Google Drive (Recommended)**

Upload these to your Google Drive:
```
MyDrive/
  cardflux/
    data/
      curated/
        one-piece.jsonl          (4,813 cards, ~2 MB)
      images/
        one-piece/
          288227.jpg
          288228.jpg
          ...                     (5,113 images, ~400 MB)
```

**How to get these files:**
- Already on your computer at: `C:\Users\rayno\eric\cardflux\data\`
- Zip the `data` folder and upload to Google Drive
- Or upload `curated` and `images` folders separately

---

### 2. Open Google Colab (1 minute)

1. Go to https://colab.research.google.com
2. Sign in with Google account
3. Click **"New Notebook"**
4. **Enable GPU**:
   - Click **Runtime** → **Change runtime type**
   - Hardware accelerator: **GPU** (T4)
   - Click **Save**

---

### 3. Copy Code into Colab (5 minutes)

Open the file: `scripts/identification/colab_finetune_notebook.py`

The file has 13 cells marked as:
```python
# ============================================================================
# CELL 1: Setup and Install Dependencies
# ============================================================================
```

**For each cell**:
1. Copy everything between the cell markers
2. Paste into a new code cell in Colab (click "+ Code")
3. Repeat for all 13 cells

**Quick tip**: You can copy multiple cells at once and paste - Colab will create separate cells automatically.

---

### 4. Update File Paths (1 minute)

In **CELL 3**, update these paths to match where you uploaded files:

```python
# If you uploaded to MyDrive/cardflux/
CARDS_JSONL = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
IMAGES_DIR = "/content/drive/MyDrive/cardflux/data/images/one-piece"
OUTPUT_DIR = "/content/finetuned-models"
```

---

### 5. Run All Cells (3-4 hours)

Click **Runtime** → **Run all**

Or run cells one by one by clicking the play button.

**What happens:**
- ✅ Cell 1: Check GPU, install dependencies (~1 min)
- ✅ Cell 2: Mount Google Drive (~30 sec)
- ✅ Cell 3: Verify files exist (~5 sec)
- ✅ Cells 4-9: Setup code (~10 sec)
- ⏱️  **Cell 10: TRAINING (~3-4 hours)** ☕
- ✅ Cell 11: Save history and plot (~10 sec)
- ✅ Cell 12: Download model (~1 min)
- ✅ Cell 13: Copy to Drive (~10 sec)

**During training (Cell 10)**, you'll see:
```
Epoch 1/15
Epoch 1/15:  45%|████████████████████                     | 130/287 [02:15<02:43,  0.96it/s, loss=0.2847]

Epoch 1 Summary:
  Train Loss: 0.2847
  Val Loss: 0.2134
  Learning Rate: 0.000015
  ✅ [BEST] Model saved: /content/finetuned-models/dinov2-onepiece-best.pt

Epoch 2/15
...
```

**Leave the tab open** - Colab will disconnect after ~12 hours of inactivity, but training will complete in ~3-4 hours.

---

### 6. Download Trained Model (1 minute)

After training completes, **Cell 12** will automatically download:
- `dinov2-onepiece-best.pt` (~86 MB)

Save this file to:
```
C:\Users\rayno\eric\cardflux\artifacts\finetuned-models\dinov2-onepiece-best.pt
```

**Alternative**: Cell 13 copies to Google Drive if download fails.

---

### 7. Test the Fine-Tuned Model (2 minutes)

Back on your local machine:

```bash
cd C:\Users\rayno\eric\cardflux
python scripts/identification/test_finetuned_model.py
```

This compares V1 baseline vs fine-tuned on all test images.

**Expected output:**
```
VERDICT
------------------------------------------------------------------------------------
[+] Fine-tuned significantly improves scores: +0.1467 (+21.7%)
[+] Fine-tuned improved confidence on 3 image(s)
[+] Fine-tuned increased HIGH confidence count: 2 -> 5

[RECOMMENDATION] Deploy fine-tuned model - significant improvements!
```

---

## Troubleshooting

### "No GPU detected"
- Go to **Runtime → Change runtime type → GPU**
- Restart runtime
- Re-run Cell 1

### "Cannot find JSONL or images"
- Check paths in Cell 3
- Verify files uploaded to Google Drive
- Run Cell 3 again after fixing paths

### "Out of Memory (OOM)"
In Cell 6, change:
```python
'batch_size': 8,  # Reduce from 16
```
Restart runtime and re-run from Cell 7.

### "Colab disconnected during training"
- Training checkpoints are saved every 5 epochs
- Models saved in `/content/finetuned-models/`
- If disconnected, you can resume from last checkpoint (advanced)

### "Download fails"
Use Cell 13 to copy to Google Drive instead:
- Files saved to: `/content/drive/MyDrive/cardflux-finetuned/`
- Download from Google Drive web interface

---

## Summary

**Total Steps**:
1. Upload data to Google Drive (5 min)
2. Create Colab notebook, enable GPU (1 min)
3. Copy 13 code cells (5 min)
4. Update paths (1 min)
5. Run all cells (3-4 hours automated)
6. Download model (1 min)
7. Test locally (2 min)

**Total active time**: ~15 minutes
**Total wait time**: ~3-4 hours (training)

**Cost**: $0 (free Colab GPU)

---

## After Fine-Tuning

If tests show improvement:

1. **Integrate into production**:
   - Fine-tuned model automatically detected in `production_card_identifier.py`
   - Just place `.pt` file in `artifacts/finetuned-models/`

2. **Rebuild embeddings**:
   ```bash
   pnpm run embed:cards
   pnpm run build:faiss
   ```

3. **Update desktop app**:
   - Include fine-tuned model in next release
   - Shops get automatic accuracy improvement

---

**Ready to start?** Open Colab and paste the cells!

_Created: 2025-10-21_
_Estimated completion: Your fine-tuned model will be ready in ~4 hours_
