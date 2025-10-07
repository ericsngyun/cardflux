#!/bin/bash
# Rebuild the full One Piece identification pipeline
# Run this after filtering sealed products

set -e  # Exit on error

echo "=================================================="
echo "Rebuilding One Piece Identification Pipeline"
echo "=================================================="

# Step 1: Generate embeddings
echo -e "\n[1/3] Generating embeddings..."
python services/embedder/bin/embed_onepiece.py

# Step 2: Build FAISS index
echo -e "\n[2/3] Building FAISS index..."
python services/indexer/bin/build_faiss_onepiece.py

# Step 3: Build reprint map
echo -e "\n[3/3] Building reprint detection map..."
python scripts/build_reprint_map.py

echo -e "\n=================================================="
echo "Pipeline rebuild complete!"
echo "=================================================="
echo ""
echo "Test with:"
echo "  python scripts/identify_card.py data/images/one-piece/288230.jpg"
