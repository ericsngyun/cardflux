# Colab Fine-Tuning - Troubleshooting Guide

## ❌ Error: "Loaded 0 cards with images"

This means the dataset couldn't find your images. Here's how to fix it:

---

## Step-by-Step Fix

### 1. **Run CELL 3.5 (NEW!)**

I just added a verification cell. Run it to see what's wrong:

```python
# CELL 3.5: Verify Setup
```

This will show you exactly what's missing.

---

### 2. **Check Your Paths**

In **CELL 3**, verify these paths:

```python
# These should match YOUR Google Drive structure
CARDS_JSONL = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
IMAGES_DIR = "/content/images"  # After running CELL 2.5
```

**Common mistakes:**
- ❌ `cardflux/` vs `CardFlux/` (case sensitive!)
- ❌ `data/` vs `Data/`
- ❌ Typos in path

---

### 3. **Did You Run CELL 2.5?**

**CELL 2.5 extracts the images from your zip file.**

If you skipped it:
1. Go back to CELL 2.5
2. Update the `IMAGES_ZIP_PATH` to point to your zip
3. Run the cell
4. Wait 2-3 minutes for extraction

**Check extraction succeeded:**
```python
# Run this in a new cell:
import os
print(f"Files in /content/images: {len(os.listdir('/content/images'))}")
# Should show ~5,000 files
```

---

### 4. **Verify Files Manually**

Run this in a new Colab cell to diagnose:

```python
import os
from pathlib import Path

# Check JSONL
jsonl_path = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
print(f"JSONL exists: {Path(jsonl_path).exists()}")

if Path(jsonl_path).exists():
    with open(jsonl_path, 'r') as f:
        first_line = f.readline()
        print(f"First line: {first_line[:100]}...")

# Check images directory
images_dir = "/content/images"
print(f"\nImages dir exists: {Path(images_dir).exists()}")

if Path(images_dir).exists():
    files = os.listdir(images_dir)
    print(f"Total files: {len(files)}")
    print(f"First 10 files: {files[:10]}")
```

**What to look for:**
- JSONL should exist and have JSON data
- Images dir should have ~5,000 .jpg files
- Filenames should be numbers (product IDs): `510897.jpg`, `510898.jpg`, etc.

---

### 5. **Check File Structure in Zip**

Your zip file might have a nested structure. Check:

```python
# After running CELL 2.5, check structure
import os
for root, dirs, files in os.walk('/content/images'):
    print(f"Directory: {root}")
    print(f"  Subdirs: {dirs}")
    print(f"  Files (first 5): {files[:5]}")
    break  # Just check top level
```

**Expected:**
```
Directory: /content/images
  Subdirs: []
  Files: ['510897.jpg', '510898.jpg', '510899.jpg', ...]
```

**If you see:**
```
Directory: /content/images
  Subdirs: ['one-piece']  ← PROBLEM!
  Files: []
```

Then images are nested. CELL 2.5 should auto-fix this, but if not:
```python
import shutil
# Move files up one level
for file in os.listdir('/content/images/one-piece'):
    shutil.move(f'/content/images/one-piece/{file}', f'/content/images/{file}')
os.rmdir('/content/images/one-piece')
```

---

### 6. **Alternative: Skip Zip, Upload Directory**

If unzipping is problematic, upload images directly:

1. In Colab, click the **folder icon** (left sidebar)
2. Create folder: `/content/images`
3. Right-click → Upload
4. Select all your .jpg files (this takes 10-15 minutes)

Or use Google Drive (slower training but works):

```python
# In CELL 3, use Drive directly (no CELL 2.5 needed)
CARDS_JSONL = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
IMAGES_DIR = "/content/drive/MyDrive/cardflux/data/images/one-piece"
```

---

## ✅ Checklist Before Training

Run these checks in order:

- [ ] **CELL 1**: GPU detected (T4 or better)
- [ ] **CELL 2**: Google Drive mounted
- [ ] **CELL 2.5**: Images extracted (5,000+ files in `/content/images`)
- [ ] **CELL 3**: Paths updated and verified
- [ ] **CELL 3.5**: Verification passed ✅
- [ ] **CELL 4**: Dataset class defined (should load ~4,800 cards)

If all pass, you're good to train!

---

## 🐛 Still Stuck?

### Quick Debug Script

Paste this in a new Colab cell:

```python
import os
import json
from pathlib import Path

print("="*80)
print("COLAB DEBUGGING INFO")
print("="*80)

# 1. Check Drive
drive_mounted = Path("/content/drive/MyDrive").exists()
print(f"\n1. Google Drive: {'✅ Mounted' if drive_mounted else '❌ Not mounted'}")

# 2. Check JSONL
jsonl_candidates = [
    "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl",
    "/content/drive/MyDrive/CardFlux/data/curated/one-piece.jsonl",
    "/content/drive/MyDrive/cardflux/one-piece.jsonl",
]

jsonl_found = None
for candidate in jsonl_candidates:
    if Path(candidate).exists():
        jsonl_found = candidate
        break

print(f"\n2. JSONL file: {'✅ ' + jsonl_found if jsonl_found else '❌ Not found'}")

if jsonl_found:
    with open(jsonl_found, 'r') as f:
        line_count = sum(1 for line in f if line.strip())
    print(f"   Lines: {line_count}")

# 3. Check images
image_candidates = [
    "/content/images",
    "/content/drive/MyDrive/cardflux/data/images/one-piece",
    "/content/drive/MyDrive/CardFlux/data/images/one-piece",
]

images_found = None
for candidate in image_candidates:
    if Path(candidate).exists():
        image_count = len([f for f in os.listdir(candidate) if f.endswith(('.jpg', '.png'))])
        if image_count > 0:
            images_found = (candidate, image_count)
            break

print(f"\n3. Images: {'✅ ' + images_found[0] + f' ({images_found[1]} files)' if images_found else '❌ Not found'}")

# 4. Suggested paths
print(f"\n4. Use these paths in CELL 3:")
print(f"   CARDS_JSONL = \"{jsonl_found or 'UPDATE_THIS'}\"")
print(f"   IMAGES_DIR = \"{images_found[0] if images_found else 'UPDATE_THIS'}\"")

print("\n" + "="*80)
```

This will auto-detect your paths and tell you exactly what to use!

---

## 📊 Expected Output (When Working)

When everything is correct, CELL 7 should show:

```
Device: cuda

Loading DINOv2 model...
✅ Model loaded: facebook/dinov2-small

Creating dataset...
[DEBUG] JSONL path: /content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl
[DEBUG] JSONL exists: True
[DEBUG] Images dir: /content/images
[DEBUG] Images dir exists: True
[DEBUG] Files in images dir: 5113
[DEBUG] Sample files: ['510897.jpg', '510898.jpg', '510899.jpg', ...]
✅ Loaded 4813 cards with images  ← THIS NUMBER SHOULD BE ~4,800
⚠️  Skipped 300 cards (no image found)
✅ Dataset split: 4331 train, 482 val

✅ DataLoaders created
   Train batches: 271
   Val batches: 31
```

---

**Need more help?** Share the output of the debug script above!

