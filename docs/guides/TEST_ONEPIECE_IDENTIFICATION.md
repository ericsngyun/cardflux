# Testing One Piece Card Identification

This guide walks through testing the card identification pipeline with One Piece TCG cards only.

## Phase 1: Build the Index

### Step 1: Download One Piece Card Images

```bash
tsx services/ingest/bin/fetch_images_onepiece.ts
```

**What it does**: Downloads ~5,000 One Piece card images (~500MB)
**Time**: ~15-20 minutes
**Output**: `data/images/one-piece/*.jpg`

### Step 2: Install Python Dependencies

```bash
pip install torch transformers faiss-cpu pillow numpy tqdm
```

**What it does**: Installs ML libraries for embeddings and search
**Time**: ~5 minutes
**Size**: ~2GB download

### Step 3: Generate Embeddings

```bash
python services/embedder/bin/embed_onepiece.py
```

**What it does**: Uses CLIP model to convert images to 512-dimensional vectors
**Time**:
- CPU: ~30-60 minutes
- GPU (CUDA): ~5-10 minutes

**Output**:
- `artifacts/metadata/embeddings/one-piece/embeddings.npy` (vector data)
- `artifacts/metadata/embeddings/one-piece/metadata.jsonl` (card info)

### Step 4: Build FAISS Index

```bash
python services/indexer/bin/build_faiss_onepiece.py
```

**What it does**: Creates fast similarity search index
**Time**: <1 minute
**Output**:
- `artifacts/faiss/one-piece/index.faiss` (search index)
- `artifacts/faiss/one-piece/ids.json` (card ID mapping)

---

## Phase 2: Test Identification

### Option A: Test with Reference Images

Use images that are already in your database:

```bash
python scripts/test_identification.py data/images/one-piece/[CARD_ID].jpg
```

**Expected result**: Should match with ~0.99+ similarity (nearly perfect)

### Option B: Test with Phone Photos

1. Take a photo of a One Piece card with your phone
2. Transfer to your computer (e.g., save as `test_card.jpg`)
3. Run identification:

```bash
python scripts/test_identification.py test_card.jpg
```

**Expected result**:
- Good photo: 0.85-0.95 similarity
- Angled/lit photo: 0.70-0.85 similarity
- Poor photo: 0.50-0.70 similarity

### Get Top 10 Matches

```bash
python scripts/test_identification.py test_card.jpg 10
```

Shows the 10 most similar cards to see if correct card is in top results.

---

## Phase 3: Understand Results

### Similarity Scores

The test script outputs a similarity score (0.0 to 1.0):

- **0.90 - 1.00**: High confidence match ✅
  - Near-perfect image or same artwork
  - Safe to auto-identify

- **0.70 - 0.89**: Moderate confidence ⚠️
  - Good photo but different angle/lighting
  - Should show user for confirmation

- **0.50 - 0.69**: Low confidence ❌
  - Poor quality photo or wrong card
  - Needs user to manually select

- **< 0.50**: No match ❌
  - Not a One Piece card
  - Not in database
  - Image too blurry

### Example Output

```
================================================================================
IDENTIFICATION RESULTS
================================================================================

#1 - Similarity: 0.9234 (92.3%)
  Card ID: op01-001-en
  Name: Monkey D. Luffy
  Set: OP01 - Romance Dawn
  Rarity: L
  Type: Leader

#2 - Similarity: 0.7821 (78.2%)
  Card ID: op01-025-en
  Name: Monkey D. Luffy
  Set: OP01 - Romance Dawn
  Rarity: SR
  Type: Character

================================================================================
✅ HIGH CONFIDENCE MATCH: Monkey D. Luffy
```

---

## Phase 4: Tuning Thresholds

Based on testing, adjust confidence thresholds:

### Recommended Thresholds

```typescript
const IDENTIFICATION_THRESHOLDS = {
  AUTO_ACCEPT: 0.85,    // Auto-identify without confirmation
  SHOW_MATCH: 0.65,     // Show as potential match, ask user
  NO_MATCH: 0.65,       // Below this, don't show
  TOP_K: 5,             // Show top 5 candidates
};
```

Test with various scenarios:
- ✅ Perfect lighting, straight angle
- ✅ Slight angle (10-20 degrees)
- ✅ Different lighting (shadow, bright)
- ✅ Phone camera vs webcam
- ✅ Sleeved vs unsleeved cards
- ✅ Foil vs non-foil (if both exist)

---

## Troubleshooting

### "FAISS index not found"
Run Step 4 to build the index.

### "No embeddings found"
Run Step 3 to generate embeddings.

### "No images found"
Run Step 1 to download images.

### "Low similarity for correct card"
- Try better lighting
- Hold card straight (not angled)
- Ensure card fills most of frame
- Check if card is actually in database

### "Wrong card matched with high confidence"
- Check if cards have similar artwork
- May need to tune embedding model or add OCR

---

## Next Steps After Validation

Once identification works well:

1. ✅ Integrate into desktop app UI
2. ✅ Add manual image upload for testing
3. ✅ Combine with camera detection
4. ✅ Expand to other card games
5. ✅ Add OCR for additional validation

---

## Performance Notes

- **CLIP Model**: ~500MB download (cached after first use)
- **Index Size**: ~10MB per 5,000 cards
- **Search Speed**: <10ms for top-5 results
- **Memory**: ~1GB for loaded model + index

---

## Files Created

```
services/ingest/bin/
  └── fetch_images_onepiece.ts       # Download One Piece images

services/embedder/bin/
  └── embed_onepiece.py              # Generate One Piece embeddings

services/indexer/bin/
  └── build_faiss_onepiece.py        # Build One Piece search index

scripts/
  └── test_identification.py         # Test CLI for identification
```

---

**Ready to start?** Run Step 1 to download images!
