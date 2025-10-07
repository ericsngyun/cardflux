#!/bin/bash
# Rebuild One Piece identification pipeline with hybrid approach
# Uses DINOv2 + PaddleOCR + ORB for maximum accuracy

set -e  # Exit on error

echo "=========================================="
echo "One Piece Hybrid Pipeline Rebuild"
echo "=========================================="
echo ""

# Check if data exists
if [ ! -f "data/curated/one-piece.jsonl" ]; then
    echo "ERROR: No curated data found at data/curated/one-piece.jsonl"
    echo "Run scraper first: pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts"
    exit 1
fi

# Check if images exist
if [ ! -d "data/images/one-piece" ] || [ -z "$(ls -A data/images/one-piece)" ]; then
    echo "ERROR: No images found in data/images/one-piece/"
    echo "Run image fetcher first: pnpm tsx services/ingest/bin/fetch_images_onepiece.ts"
    exit 1
fi

echo "Step 1: Generate DINOv2 embeddings"
echo "------------------------------------------"
python services/embedder/bin/embed_onepiece_dinov2.py
if [ $? -ne 0 ]; then
    echo "ERROR: Embedding generation failed"
    exit 1
fi
echo ""

echo "Step 2: Build FAISS index"
echo "------------------------------------------"
python services/indexer/bin/build_faiss_onepiece_dinov2.py
if [ $? -ne 0 ]; then
    echo "ERROR: Index building failed"
    exit 1
fi
echo ""

echo "=========================================="
echo "Pipeline rebuild complete!"
echo "=========================================="
echo ""
echo "Test the hybrid identifier with:"
echo "  python scripts/identification/identify_card_hybrid.py test-images/one-piece/your-card.jpg"
echo ""
echo "Components:"
echo "  - DINOv2-small embeddings (384-dim)"
echo "  - FAISS IndexFlatIP (cosine similarity)"
echo "  - PaddleOCR text extraction"
echo "  - ORB geometric verification"
echo ""
