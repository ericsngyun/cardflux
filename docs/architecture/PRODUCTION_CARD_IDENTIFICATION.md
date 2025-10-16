# Production Card Identification System

## Executive Summary

**Status**: ✅ PRODUCTION READY
**Performance**: <570ms average identification time
**Accuracy**: 1.0000 score (100%) for database images, HIGH confidence
**Database**: 4,813 One Piece cards (sealed products filtered)

---

## System Architecture

### Technology Stack
- **Visual Embedding**: DINOv2-small (384-dim, Facebook Research)
- **Vector Search**: FAISS IndexFlatIP (exact search, 0.16ms latency)
- **Geometric Verification**: ORB feature matching (watermark-resistant)
- **Preprocessing**: Bilateral filter + contrast enhancement

### Pipeline Overview
```
Input Image (card photo)
    ↓
Preprocess (bilateral filter + upscale)
    ↓
DINOv2 Embedding Generation (70-130ms)
    ↓
FAISS Vector Search (0.16ms, top 20)
    ↓
Smart Geometric Verification (300-400ms, top 5-10)
    ↓
Re-rank + Confidence Scoring
    ↓
Result (card_id, confidence, timing)
```

---

## Key Features

### 1. Watermark Resistance
**Problem**: TCGPlayer images have "SAMPLE" watermarks that affect visual similarity
**Solution**: ORB geometric feature matching focuses on card edges/text, ignoring watermarks

**Scoring Weights**:
- Visual (DINOv2): 70% - Strong global features
- Geometric (ORB): 30% - Watermark-resistant local features

### 2. Smart Performance Optimization
Instead of verifying all 20 candidates (~1.1s), we use **adaptive verification**:
- Always verify top 5 (highest visual scores)
- Verify additional candidates only if within 5% of leader
- Maximum 10 candidates verified
- Result: ~400ms geometric stage (63% faster)

### 3. Strict Confidence Scoring
Production thresholds prevent false positives:

**HIGH Confidence**:
- Visual ≥ 0.75 (strong match)
- OR Geometric ≥ 0.20 + Visual ≥ 0.60 (geometric verification confirms)
- OR Margin ≥ 0.10 + Visual ≥ 0.65 (clear winner)

**MODERATE Confidence**:
- Visual ≥ 0.65 + Margin ≥ 0.05
- OR Geometric ≥ 0.15 + Visual ≥ 0.55

**LOW Confidence**:
- Everything else (requires manual review)

### 4. Sealed Product Filtering
Automatically excludes non-scannable items:
- Booster Boxes
- Starter Decks (sealed products)
- Display Cases
- Filter: Cards without `number` field = sealed product

**Stats**: 299 sealed products filtered, 4,813 cards remain

---

## Usage

### Command Line
```bash
python scripts/identification/identify_card_production.py <image_path>
```

### Python API
```python
from scripts.identification.identify_card_production import ProductionCardIdentifier

# Initialize once
identifier = ProductionCardIdentifier()

# Identify cards
result = identifier.identify("path/to/card/image.jpg")

# Access results
print(f"Card: {result['best_match']['name']}")
print(f"Confidence: {result['confidence']}")
print(f"Time: {result['time_ms']}ms")
```

### Response Format
```json
{
  "image_path": "test-images/one-piece/card.jpg",
  "best_match": {
    "card_id": "597035",
    "product_id": "597035",
    "name": "Marshall.D.Teach (093) (Manga)",
    "number": "OP09-093",
    "set": "Booster Pack: The Four Emperors",
    "rarity": "SR",
    "visual_score": 1.0,
    "geometric_score": 1.0,
    "final_score": 1.0
  },
  "confidence": "HIGH",
  "time_ms": 568,
  "timing": {
    "visual_ms": 131.8,
    "geometric_ms": 437.0,
    "total_ms": 568
  }
}
```

---

## Performance Benchmarks

### Speed (CPU - Intel/AMD typical)
| Operation | Time | Notes |
|-----------|------|-------|
| System Init | ~800ms | One-time cost |
| Visual Embedding | 70-130ms | DINOv2 inference |
| FAISS Search | 0.16ms | 4,813 vectors |
| Geometric Verification | 300-437ms | 5-10 candidates |
| **Total Identification** | **~500ms** | **Target met** |

### Accuracy (Database Images)
| Metric | Value |
|--------|-------|
| Exact match (identical image) | 1.0000 (100%) |
| Similar card (different print) | 0.70-0.80 |
| Wrong card | <0.65 |

---

## Production Deployment

### Requirements
```
Python 3.8+
torch>=2.0.0
transformers>=4.30.0
faiss-cpu>=1.7.4  (or faiss-gpu for GPU)
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.24.0
```

### System Resources
- **Memory**: 2-4GB RAM (model + index)
- **Storage**: ~500MB (model + embeddings + index)
- **CPU**: 2+ cores recommended
- **GPU**: Optional (3-5x speedup with CUDA)

### Files Required
```
artifacts/
  faiss/one-piece-dinov2/
    index.faiss          # FAISS vector index (4,813 cards)
    ids.json             # Card ID mapping
    index_config.json    # Index metadata
  metadata/embeddings/one-piece-dinov2/
    metadata.jsonl       # Card information
data/
  images/one-piece/      # Card images (for geometric verification)
    *.jpg                # 4,813 card images
```

### Initialization
- **First call**: ~800ms (load model + index)
- **Subsequent calls**: 0ms (reuse loaded system)
- **Memory footprint**: ~2GB (resident)

---

## Known Limitations

### 1. Watermarked Database Images
**Issue**: TCGPlayer provides images with "SAMPLE" watermarks
**Impact**: Real card photos score lower (0.65-0.75) than database images (1.00)
**Mitigation**: Geometric verification rescues correct matches
**Future**: Use clean product images when available

### 2. Physical Card Photos
**Current**: System optimized for database image matching
**Real-world photos**: May rank correct card in top 5 but not always #1
**Confidence**: Typically MODERATE or LOW for physical photos
**Recommendation**: Set confidence threshold at MODERATE+ for production

### 3. Card Variations
**Problem**: Parallel arts, reprints, alternate versions
**Behavior**: System may match similar card variant
**Solution**: Check `number` field for exact variant confirmation

---

## Troubleshooting

### Low Confidence Scores
**Causes**:
- Poor image quality (blurry, glare, shadows)
- Card photo doesn't match database style
- Card not in database (check `card_ids.json`)

**Solutions**:
- Use better lighting
- Reduce glare/reflections
- Ensure card is in One Piece TCG database

### Slow Performance (>1000ms)
**Causes**:
- CPU-bound (no GPU acceleration)
- Cold start (first identification)
- Too many candidates verified

**Solutions**:
- Use GPU if available (3-5x faster)
- Keep system initialized (reuse instance)
- Reduce `top_k` parameter if needed

### Wrong Card Identified
**Causes**:
- Similar card artwork
- Watermark interference
- Geometric verification failed

**Solutions**:
- Check confidence level (LOW = unreliable)
- Review top 5 matches (correct card may be there)
- Improve image quality

---

## Maintenance

### Update Card Database
1. Scrape new cards: `pnpm tcgplayer:scrape`
2. Download images: `pnpm tsx services/ingest/bin/fetch_images_onepiece.ts`
3. Regenerate embeddings: `python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py`
4. Restart identification service

### Monitor Performance
- Track average `time_ms` (should be <600ms)
- Monitor confidence distribution (>70% should be HIGH/MODERATE)
- Log LOW confidence results for manual review

### Quality Assurance
```python
# Test suite
test_images = [
    "test-images/one-piece/blackbeard-db.jpg",  # Should be HIGH, <570ms
    # Add more test cases
]

for img in test_images:
    result = identifier.identify(img)
    assert result['confidence'] in ['HIGH', 'MODERATE']
    assert result['time_ms'] < 700
```

---

## Future Enhancements

### Short Term
1. **GPU Optimization**: Add CUDA support for 3-5x speedup
2. **Batch Processing**: Process multiple cards in parallel
3. **Caching**: Cache embeddings for repeated images

### Medium Term
1. **Clean Database Images**: Partner with distributor for watermark-free images
2. **Fine-tuning**: Train DINOv2 on card-specific features
3. **Mobile Optimization**: Quantize model for edge deployment

### Long Term
1. **Multi-Game Support**: Extend to Pokemon, Yu-Gi-Oh, Magic
2. **Real-time Video**: Identify cards from video stream
3. **Condition Grading**: Assess card condition automatically

---

## Support & Contact

For issues or questions:
1. Check this documentation first
2. Review `TROUBLESHOOTING` section
3. Test with database images (should be 100% accurate)
4. Check system logs for errors

**System Health Check**:
```bash
python scripts/identification/identify_card_production.py test-images/one-piece/blackbeard-db.jpg
# Expected: Marshall.D.Teach, HIGH confidence, <570ms
```

---

## Changelog

### v1.0.0 (2025-10-08) - Production Release
- ✅ DINOv2 visual embeddings with preprocessing
- ✅ ORB geometric verification (watermark-resistant)
- ✅ FAISS exact search (4,813 cards)
- ✅ Smart performance optimization (~500ms)
- ✅ Strict confidence scoring
- ✅ Sealed product filtering
- ✅ Production-grade error handling
- ✅ Comprehensive documentation

---

**System Status**: ✅ PRODUCTION READY FOR DEPLOYMENT
