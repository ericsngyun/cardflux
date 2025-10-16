# Shop Setup Quick-Start Guide
**CardFlux Card Identification System - One Piece TCG**

This guide will help you set up the card identification system at your friend's shop in ~15-30 minutes.

---

## Overview

**What You'll Need:**
- ✅ Your friend's laptop (Windows/Mac/Linux)
- ✅ Document scanner webcam (USB)
- ✅ Internet connection (for initial setup only)
- ✅ This GitHub repository
- ✅ ~30 minutes for setup

**What You'll Get:**
- Real-time card identification (1-2 seconds per card)
- 95%+ accuracy
- 4,813 One Piece cards in database
- Simple capture-and-identify workflow

---

## Step 1: System Requirements Check

### Minimum Requirements
```
Operating System: Windows 10/11, macOS 10.15+, or Linux
RAM: 8GB minimum (16GB recommended)
Storage: 2GB free space
Internet: Required for initial setup only
```

### Check Your Friend's Laptop

**Windows:**
```bash
# Check RAM
systeminfo | findstr "Total Physical Memory"

# Check Python
python --version
# Should be Python 3.8 or higher
```

**Mac/Linux:**
```bash
# Check RAM
free -h

# Check Python
python3 --version
# Should be Python 3.8 or higher
```

**If Python is not installed:**
- Windows: Download from https://www.python.org/downloads/ (get Python 3.11 or 3.12)
- Mac: `brew install python3` or download from python.org
- Linux: `sudo apt install python3 python3-pip` (Ubuntu/Debian)

---

## Step 2: Clone Repository to Shop Laptop

### Option A: Using Git (Recommended)

```bash
# Install Git first if not installed
# Windows: https://git-scm.com/download/win
# Mac: brew install git
# Linux: sudo apt install git

# Clone the repository
cd /path/to/where/you/want/it
git clone https://github.com/your-username/cardflux.git
cd cardflux
```

### Option B: Download ZIP (No Git)

1. Go to GitHub repository page
2. Click green "Code" button
3. Click "Download ZIP"
4. Extract ZIP to shop laptop (e.g., `C:\cardflux\` or `~/cardflux/`)
5. Open terminal/command prompt in that folder

---

## Step 3: Install Dependencies

### Install Python Packages

**All Platforms:**
```bash
# Navigate to cardflux directory
cd cardflux

# Install required packages
pip install numpy opencv-python pillow torch transformers faiss-cpu easyocr

# This will take 5-10 minutes and download ~2GB of packages
```

**Alternative (if requirements.txt exists):**
```bash
pip install -r requirements.txt
```

### Verify Installation

```bash
python -c "import cv2, numpy, torch, transformers, faiss, easyocr; print('All dependencies installed successfully!')"
```

You should see: `All dependencies installed successfully!`

**If you get errors:**
- Make sure `pip` is up to date: `pip install --upgrade pip`
- Use `pip3` instead of `pip` on Mac/Linux: `pip3 install ...`
- On Windows, use `python -m pip install ...`

---

## Step 4: Verify Database Files

The repository should already contain the pre-built database. Let's verify:

```bash
# Check if FAISS index exists
ls artifacts/faiss/one-piece-dinov2/

# You should see:
#   index.faiss (7.1 MB)
#   ids.json (52 KB)
#   index_config.json (615 bytes)

# Check if metadata exists
ls artifacts/metadata/embeddings/one-piece-dinov2/

# You should see:
#   embeddings.npy (7.4 MB)
#   metadata.jsonl (2.8 MB)
```

**If files are missing:**
- The database files might not be in Git (too large)
- Contact me to provide database files separately
- Or rebuild from scratch (takes ~30-60 minutes, see rebuild guide)

---

## Step 5: Test the System (Before Hardware Setup)

Let's verify everything works with a test image first:

```bash
# Navigate to identification directory
cd scripts/identification

# Run test with included sample image
python production_card_identifier.py ../../test-images/one-piece/bege.png --tcg one-piece
```

**Expected Output:**
```
======================================================================
PRODUCTION CARD IDENTIFICATION SYSTEM
======================================================================
Initializing for game: one-piece

[1/5] Loading DINOv2 vision model...
  [OK] Model loaded on cpu (2.2s)

[2/5] Loading FAISS index for one-piece...
  [OK] Loaded 4813 cards (0.0s)

[3/5] Loading metadata...
  [OK] Loaded metadata (0.1s)

[4/5] Loading ORB feature matcher...
  [OK] ORB matcher ready (0.0s)

[5/5] Loading extractors...
  [OK] All systems ready (1.8s)

======================================================================
IDENTIFICATION RESULT
======================================================================

Best Match: Capone"Gang"Bege
  Product ID: 288252
  Card Number: ST02-004
  Confidence: HIGH

Time: 1787ms
======================================================================
```

**If this works, you're 90% done!** ✅

**If you get errors:**
- Check error message carefully
- See Troubleshooting section below
- Common issues: missing dependencies, wrong Python version

---

## Step 6: Hardware Setup (Document Camera)

### Physical Setup

```
      [Document Camera/Webcam]
              |
              | (USB cable)
              |
      [Laptop USB Port]


    Scanning Area Layout:
    ┌─────────────────────┐
    │   [Camera mount]    │
    │         │           │
    │         ▼           │
    │   ┌─────────┐       │
    │   │ CARD    │       │ <-- Place card here
    │   │ HERE    │       │
    │   └─────────┘       │
    │                     │
    │  [Table/Mat]        │
    └─────────────────────┘
```

### Mounting Tips

1. **Height:** 12-18 inches above table
   - Too high: Card details hard to see
   - Too low: Limited field of view

2. **Angle:** Straight down (90 degrees)
   - Camera should point directly down at card
   - Avoid angled shots

3. **Background:** Plain dark mat (black or dark blue recommended)
   - Helps with card edge detection
   - Reduces glare

4. **Lighting:** Good overhead lighting
   - Avoid harsh shadows
   - Avoid direct sunlight (creates glare)
   - LED desk lamp works well

5. **Card Placement Zone:**
   - Mark area with tape (optional)
   - Ensures cards are always centered
   - Improves consistency

### Camera Connection

```bash
# 1. Plug document camera into USB port

# 2. Verify camera is detected
# Windows: Check Device Manager > Cameras
# Mac: Check System Preferences > Camera
# Linux: lsusb

# 3. Test camera with Python
python -c "
import cv2
cap = cv2.VideoCapture(0)  # Try 0 first
if cap.isOpened():
    print('Camera 0 detected!')
    cap.release()
else:
    print('Camera 0 not found, try index 1')
    cap = cv2.VideoCapture(1)
    if cap.isOpened():
        print('Camera 1 detected!')
        cap.release()
"
```

**Camera Index:**
- Usually `0` (built-in webcam) or `1` (USB camera)
- If laptop has built-in webcam, document camera will likely be index `1`
- We'll configure this in the next step

---

## Step 7: Create Capture Script for Shop

Let's create a simple capture-and-identify script for your friend:

```bash
# Still in scripts/identification/ directory
```

Create file: `shop_scanner.py`

```python
#!/usr/bin/env python3
"""
Shop Card Scanner - Simple workflow for document camera
Press SPACE to capture, ESC to exit
"""
import cv2
import sys
import subprocess
from pathlib import Path
import time

# ============== CONFIGURATION ==============
CAMERA_INDEX = 1  # Change to 0 if document camera doesn't work
TCG_GAME = "one-piece"
# ===========================================

def main():
    print("=" * 70)
    print("SHOP CARD SCANNER - One Piece TCG")
    print("=" * 70)
    print()
    print("Initializing camera...")

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {CAMERA_INDEX}")
        print("Try changing CAMERA_INDEX in script (0 or 1)")
        return

    print(f"[OK] Camera {CAMERA_INDEX} ready")
    print()
    print("=" * 70)
    print("CONTROLS:")
    print("  SPACE - Capture and identify card")
    print("  ESC   - Exit")
    print("=" * 70)
    print()

    card_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Cannot read from camera")
            break

        # Display preview
        cv2.imshow('Shop Card Scanner (SPACE=capture, ESC=exit)', frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            print("\nExiting...")
            break

        elif key == 32:  # SPACE
            card_count += 1
            print(f"\n[Card #{card_count}] Captured! Identifying...")

            # Save image
            output_path = "captured_card.jpg"
            cv2.imwrite(output_path, frame)

            # Close preview window temporarily
            cv2.destroyAllWindows()

            # Run identification
            start = time.time()
            result = subprocess.run([
                sys.executable,
                "production_card_identifier.py",
                output_path,
                "--tcg", TCG_GAME
            ], capture_output=False)
            elapsed = time.time() - start

            print(f"\nIdentification took {elapsed:.1f} seconds")
            print("\n" + "=" * 70)
            print("Place next card and press SPACE")
            print("=" * 70)
            print()

            # Reopen preview window
            cv2.imshow('Shop Card Scanner (SPACE=capture, ESC=exit)', frame)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal cards scanned: {card_count}")

if __name__ == "__main__":
    main()
```

Save this file as: `scripts/identification/shop_scanner.py`

---

## Step 8: Test the Complete Workflow

### Run the Shop Scanner

```bash
# Make sure you're in scripts/identification/
cd scripts/identification

# Run shop scanner
python shop_scanner.py
```

**What Should Happen:**
1. Camera preview window opens
2. You see live feed from document camera
3. Place a card under the camera
4. Press SPACE
5. System identifies card (1-2 seconds)
6. Results displayed in terminal
7. Repeat for next card

### Test with Real Cards

**Grab 3-5 One Piece cards from shop inventory and test:**

1. Place first card under camera
2. Press SPACE
3. Check result:
   - ✅ Correct card name?
   - ✅ Correct card number?
   - ✅ HIGH confidence?
4. Repeat with other cards

**Expected Performance:**
- Most cards: HIGH confidence (score 0.70-0.90)
- Some cards: MODERATE confidence (still correct)
- Very few: LOW confidence (may need manual check)

---

## Step 9: Troubleshooting Common Issues

### Issue: "Cannot open camera"

**Solutions:**
1. Change `CAMERA_INDEX` in `shop_scanner.py`:
   ```python
   CAMERA_INDEX = 0  # Try 0 instead of 1
   ```
2. Check camera is plugged in and powered
3. Close other apps using camera (Zoom, Skype, etc.)
4. Try different USB port

### Issue: Camera feed is upside down

**Solution:** Add rotation in `shop_scanner.py`:
```python
# After: ret, frame = cap.read()
frame = cv2.rotate(frame, cv2.ROTATE_180)
```

### Issue: Slow identification (>5 seconds)

**Solutions:**
1. Close other applications (free up RAM/CPU)
2. Make sure laptop is plugged in (not on battery saver)
3. Reduce candidate count:
   ```python
   # In shop_scanner.py, add --top-k flag:
   "--tcg", TCG_GAME,
   "--top-k", "20"  # Add this line
   ```

### Issue: Low confidence on correct cards

**Solutions:**
1. Improve lighting (add desk lamp)
2. Ensure card fills 60-80% of frame
3. Use plain dark background
4. Make sure camera is focused
5. Clean camera lens

### Issue: Wrong card identified

**Solutions:**
1. Check if card is in database:
   ```bash
   python -c "
   import json
   from pathlib import Path

   search = input('Enter card name to search: ')

   with open('../../artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl') as f:
       found = False
       for line in f:
           card = json.loads(line)
           if search.lower() in card['name'].lower():
               print(f\"Found: {card['name']} ({card.get('number', 'N/A')})\")
               found = True
       if not found:
           print('Card not found in database')
   "
   ```
2. If not in database, card may be too new (database needs update)
3. Take better photo (better lighting, less glare)

---

## Step 10: Training Your Friend

### Quick Operation Guide (Print This)

```
═══════════════════════════════════════════════════════════════
              CARD SCANNER - QUICK GUIDE
═══════════════════════════════════════════════════════════════

1. START THE SCANNER
   → Open terminal in: cardflux/scripts/identification/
   → Run: python shop_scanner.py
   → Wait for camera preview window

2. SCAN A CARD
   → Place card flat under camera (centered)
   → Press SPACE on keyboard
   → Wait 1-2 seconds
   → Read result in terminal window

3. INTERPRET RESULTS
   ✓ HIGH confidence → Trust the result
   ? MODERATE/LOW confidence → Double-check manually

4. COMMON ISSUES
   • Wrong card? → Check lighting, try again
   • Slow? → Close other programs
   • Camera not working? → Check USB cable, try restarting

5. EXIT
   → Press ESC key
   → Close terminal window

═══════════════════════════════════════════════════════════════
```

### Tips for Your Friend

1. **Keep laptop plugged in** - Better performance
2. **Consistent lighting** - Same time of day, same lights
3. **Clean camera lens** - Weekly cleaning recommended
4. **Center cards** - Use tape marks for placement zone
5. **Remove thick sleeves** - Matte sleeves OK, glossy may cause glare

---

## Step 11: Production Checklist

Before leaving the shop, verify:

- [ ] Python installed (3.8+)
- [ ] All dependencies installed
- [ ] Database files present (FAISS index, metadata)
- [ ] Test identification successful
- [ ] Camera connected and working
- [ ] Camera mounted at correct height
- [ ] Good lighting setup
- [ ] Shop scanner script created
- [ ] Tested with 5-10 real cards
- [ ] Results are accurate (95%+ correct)
- [ ] Your friend knows how to run scanner
- [ ] Quick guide printed/saved

---

## Ongoing Maintenance

### Daily
- Keep laptop plugged in during scanning sessions
- Close unnecessary programs before scanning

### Weekly
- Clean camera lens with microfiber cloth
- Check for new card releases (database updates)

### Monthly
- Update database with new sets:
  ```bash
  # Pull latest code + database
  git pull origin main
  ```

### When New Sets Release
- Contact you to rebuild database with new cards
- Or follow rebuild guide (takes 30-60 minutes)

---

## Advanced: Batch Processing Mode

If your friend wants to scan many cards at once (e.g., 100+ cards):

1. Take photos of all cards first (manual batch capture)
2. Save all photos to folder: `cards_to_scan/`
3. Run batch script:

```bash
cd scripts/identification

# Process all images in folder
for img in ../../cards_to_scan/*.jpg; do
    python production_card_identifier.py "$img" --tcg one-piece --quiet
done
```

Or create `batch_scan.sh` / `batch_scan.bat` for easier use.

---

## Getting Help

### If You Run Into Issues

1. **Check error messages** - Read carefully
2. **Try troubleshooting section** - Most issues covered
3. **Test with sample images** - Verify system still works
4. **Contact me** with:
   - Error message (screenshot or copy-paste)
   - System info (OS, RAM, Python version)
   - What you were doing when error occurred

### Logs for Debugging

```bash
# Run with verbose output
python shop_scanner.py > shop_log.txt 2>&1

# Send me shop_log.txt if issues occur
```

---

## Summary - Complete Setup Steps

1. ✅ Check system requirements (Python 3.8+, 8GB RAM)
2. ✅ Clone repository to shop laptop
3. ✅ Install dependencies (`pip install ...`)
4. ✅ Verify database files exist
5. ✅ Test with sample image
6. ✅ Set up document camera (mount, lighting, background)
7. ✅ Create shop scanner script
8. ✅ Test with real cards from inventory
9. ✅ Train your friend on operation
10. ✅ Complete production checklist

**Total Time:** 15-30 minutes (assuming Python already installed)

---

## Quick Commands Reference

```bash
# Navigate to project
cd /path/to/cardflux

# Install dependencies
pip install numpy opencv-python pillow torch transformers faiss-cpu easyocr

# Test system
cd scripts/identification
python production_card_identifier.py ../../test-images/one-piece/bege.png --tcg one-piece

# Run shop scanner
python shop_scanner.py

# Check database
ls artifacts/faiss/one-piece-dinov2/
ls artifacts/metadata/embeddings/one-piece-dinov2/
```

---

**Ready to deploy!** 🚀

Any questions during setup, just ask!
