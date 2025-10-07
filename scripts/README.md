# Scripts Directory

Utility scripts for CardFlux development, testing, and pipeline management.

## Directory Structure

```
scripts/
├── identification/    # Card identification scripts
├── pipeline/          # Data pipeline management
├── testing/           # Test scripts
├── dev/              # Development utilities
└── make/             # Build and deployment scripts
```

## Quick Reference

### Identification
- `identification/identify_card.py` - Identify cards from images (200ms)

### Pipeline Management
- `pipeline/build_reprint_map.py` - Build reprint detection map
- `pipeline/rebuild_onepiece_pipeline.sh` - Rebuild full One Piece pipeline

### Testing
- `testing/test_sealed_filter.ts` - Test sealed product filtering (16 tests)
- `testing/test_identification.py` - Test card identification accuracy

## Usage Examples

### Identify a Card
```bash
python scripts/identification/identify_card.py data/images/one-piece/288230.jpg
```

### Rebuild Pipeline
```bash
bash scripts/pipeline/rebuild_onepiece_pipeline.sh
```

### Test Filtering
```bash
pnpm tsx scripts/testing/test_sealed_filter.ts
```

## See Also

- [Testing Guide](../docs/guides/TESTING_GUIDE.md)
- [Local Development Guide](../docs/guides/LOCAL_DEVELOPMENT.md)
