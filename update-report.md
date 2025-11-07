# CardFlux Update Report

**Date:** $(date)
**Status:** success
**Game:** one-piece
**Price Scraping:** failed

## Changes

$(git diff --stat || echo "No changes detected")

## New Files

$(git status --short || echo "No new files")

## Artifacts Status

$(ls -lh artifacts/faiss/*/index.faiss 2>/dev/null || echo "No index files found")
$(ls -lh artifacts/metadata/embeddings/*/metadata.jsonl 2>/dev/null || echo "No metadata files found")
$(ls -lh artifacts/keypoints/*/orb_keypoints.npz 2>/dev/null || echo "No keypoints files found")

## Card Counts

$(find data/curated -name "*.jsonl" -exec sh -c 'echo "{}: $(wc -l < {})" cards' \; 2>/dev/null || echo "No JSONL files found")

## Price Data

$(if [ -d "data/prices/historical/one-piece" ]; then
    echo "Total price snapshots: $(ls -1 data/prices/historical/one-piece/*.jsonl 2>/dev/null | wc -l)"
    echo "Latest: $(ls -1t data/prices/historical/one-piece/*.jsonl 2>/dev/null | head -1)"
  else
    echo "No price data collected yet"
  fi)

## System Info

- Node: $(node --version)
- Python: $(python --version)
- Disk: $(df -h . | tail -1)
- pnpm: $(pnpm --version)

