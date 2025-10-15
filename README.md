# CardFlux

> AI-powered trading card identification system for card shops and collectors

CardFlux uses computer vision and machine learning to identify trading cards in real-time, with support for multiple TCG games and automatic variant/reprint detection.

## Features

- **Fast Card Identification**: Sub-200ms identification using CLIP embeddings and FAISS similarity search
- **Multi-Game Support**: One Piece, Magic: The Gathering, Pokémon, Yu-Gi-Oh!, and more
- **Reprint Detection**: Automatically shows all variants and reprints for accurate pricing
- **Sealed Product Filtering**: Excludes booster boxes, starter decks, and sealed products
- **High Accuracy**: 100% on exact matches, 92-99% on variants
- **Desktop App**: Electron-based GUI for shops

## Quick Start

### For Desktop App Users

**New to CardFlux? Start here:**

👉 **[Complete Deployment Guide](DEPLOYMENT_GUIDE.md)** - Step-by-step setup for Windows, macOS, and Linux

**Quick automated setup:**

```bash
# Windows
git clone https://github.com/yourusername/cardflux.git
cd cardflux
pwsh scripts/setup/setup-windows.ps1

# macOS/Linux
git clone https://github.com/yourusername/cardflux.git
cd cardflux
chmod +x scripts/setup/setup-macos.sh  # or setup-linux.sh
./scripts/setup/setup-macos.sh
```

### For Developers

#### Prerequisites

- Node.js 20+ and pnpm
- Python 3.10+
- Git

#### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/cardflux.git
cd cardflux

# Install Node dependencies
pnpm install

# Install Python dependencies
pip install -r requirements.txt
```

### Build One Piece TCG Index

```bash
# 1. Scrape card data
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# 2. Download card images
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts

# 3. Generate embeddings
python services/embedder/bin/embed_onepiece.py

# 4. Build FAISS index
python services/indexer/bin/build_faiss_onepiece.py

# 5. Build reprint map
python scripts/pipeline/build_reprint_map.py
```

### Test Identification

```bash
python scripts/identification/identify_card.py data/images/one-piece/288230.jpg
```

## Project Structure

```
cardflux/
├── apps/
│   └── desktop/          # Electron desktop application
├── packages/
│   ├── config/           # Shared configuration (TCGPlayer, filtering)
│   ├── database/         # SQLite database layer
│   └── shared/           # Shared utilities
├── services/
│   ├── embedder/         # CLIP embedding generation
│   ├── indexer/          # FAISS index building
│   └── ingest/           # Data scraping and image fetching
├── scripts/
│   ├── identification/   # Card identification scripts
│   ├── pipeline/         # Pipeline management scripts
│   └── testing/          # Test scripts
├── docs/
│   ├── guides/           # User guides and tutorials
│   ├── architecture/     # Technical architecture docs
│   ├── status/           # Project status reports
│   └── archive/          # Historical documentation
├── data/
│   ├── raw/              # Raw scraped data
│   ├── curated/          # Processed JSONL data
│   └── images/           # Downloaded card images
└── artifacts/
    ├── faiss/            # FAISS indexes
    ├── metadata/         # Embeddings and metadata
    └── models/           # ML model info
```

## Documentation

### Getting Started
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - ⭐ Complete setup guide for Windows, macOS, and Linux
- **[Local Development Guide](docs/guides/LOCAL_DEVELOPMENT.md)** - Development workflow and testing
- **[Testing Guide](docs/guides/TESTING_GUIDE.md)** - Running tests and validating changes
- **[One Piece Identification Guide](docs/guides/TEST_ONEPIECE_IDENTIFICATION.md)** - Test identification system

### Architecture
- **[Architecture Overview](docs/architecture/ARCHITECTURE.md)** - System design and components
- **[Sealed Product Filtering](docs/architecture/SEALED_PRODUCT_FILTERING.md)** - How filtering works

### Status Reports
- **[Final Status](docs/status/FINAL_STATUS.md)** - Current project status
- **[Progress Summary](docs/status/PROGRESS_SUMMARY.md)** - Development progress
- **[Identification Test Results](docs/status/IDENTIFICATION_TEST_RESULTS.md)** - Accuracy metrics

## Performance

- **Identification Speed**: 200ms per card (CPU)
- **Accuracy**: 100% on exact matches, 92-99% on variants
- **Database**: 5,186 One Piece cards (324 sealed products filtered)
- **Reprint Detection**: 1,014 unique cards with multiple versions

## Technology Stack

### Backend
- **Node.js/TypeScript**: Data pipeline and desktop app
- **Python**: ML inference and embedding generation
- **SQLite**: Local card database

### Machine Learning
- **CLIP**: Vision transformer for image embeddings (OpenAI)
- **FAISS**: Fast similarity search (Facebook AI)
- **PyTorch**: ML framework

### Desktop App
- **Electron**: Cross-platform desktop framework
- **React**: UI framework
- **Tailwind CSS**: Styling

## Commands

### Development
```bash
# Build all packages
pnpm build

# Run desktop app
pnpm dev

# Type check
pnpm typecheck

# Lint
pnpm lint
```

### Data Pipeline
```bash
# Scrape all enabled TCG games
pnpm tcgplayer:scrape

# Scrape One Piece only
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts

# Fetch images
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts
```

### Testing
```bash
# Test sealed product filtering
pnpm tsx scripts/testing/test_sealed_filter.ts

# Test identification
python scripts/identification/identify_card.py <image_path>
```

## Supported TCG Games

| Game | Status | Cards | Sealed Filtering |
|------|--------|-------|-----------------|
| One Piece | ✅ Complete | 5,186 | ✅ |
| Magic: The Gathering | 🔜 Planned | - | - |
| Pokémon | 🔜 Planned | - | - |
| Yu-Gi-Oh! | 🔜 Planned | - | - |
| Digimon | 🔜 Planned | - | - |

## License

MIT

## Contributing

Contributions are welcome! Please read our contributing guidelines first.

## Support

For issues and questions:
- **GitHub Issues**: [github.com/yourusername/cardflux/issues](https://github.com/yourusername/cardflux/issues)
- **Documentation**: See `/docs` directory

---

**Status**: Production-ready for One Piece TCG • Next: Camera integration and additional game support
