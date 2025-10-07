# CardFlux Documentation

Complete documentation for the CardFlux trading card identification system.

## 📚 Documentation Index

### Getting Started
- **[Main README](../README.md)** - Project overview and quick start
- **[Local Development Guide](guides/LOCAL_DEVELOPMENT.md)** - Development setup and workflow
- **[Testing Guide](guides/TESTING_GUIDE.md)** - Running tests and validation

### User Guides
- **[One Piece Identification Guide](guides/TEST_ONEPIECE_IDENTIFICATION.md)** - Testing the identification system
- All guides located in [`guides/`](guides/)

### Architecture & Technical Docs
- **[Architecture Overview](architecture/ARCHITECTURE.md)** - System design and components
- **[Sealed Product Filtering](architecture/SEALED_PRODUCT_FILTERING.md)** - How we filter booster boxes, etc.
- All architecture docs in [`architecture/`](architecture/)

### Project Status
- **[Final Status](status/FINAL_STATUS.md)** - Current project state and metrics
- **[Progress Summary](status/PROGRESS_SUMMARY.md)** - Development progress report
- **[Identification Test Results](status/IDENTIFICATION_TEST_RESULTS.md)** - Accuracy and performance metrics
- All status reports in [`status/`](status/)

### Historical
- **[Archive](archive/)** - Older documentation and migration guides

## 🎯 Quick Links by Task

### I want to...

**Set up the project**
→ [Local Development Guide](guides/LOCAL_DEVELOPMENT.md)

**Test card identification**
→ [One Piece Identification Guide](guides/TEST_ONEPIECE_IDENTIFICATION.md)

**Understand the architecture**
→ [Architecture Overview](architecture/ARCHITECTURE.md)

**See current status**
→ [Final Status](status/FINAL_STATUS.md)

**Run tests**
→ [Testing Guide](guides/TESTING_GUIDE.md)

**Add a new TCG game**
→ [Architecture Overview](architecture/ARCHITECTURE.md) (see "Extending to Other Games" section)

## 📊 Key Metrics (One Piece TCG)

- **Cards Indexed**: 5,186 (324 sealed products filtered)
- **Identification Speed**: 200ms per card
- **Accuracy**: 100% on exact matches, 92-99% on variants
- **Reprint Detection**: 1,014 cards with multiple versions

## 🏗️ Project Structure

```
cardflux/
├── apps/desktop/          # Electron desktop app
├── packages/              # Shared packages
│   ├── config/           # Configuration
│   ├── database/         # SQLite layer
│   └── shared/           # Utilities
├── services/              # Data pipeline services
│   ├── embedder/         # CLIP embeddings
│   ├── indexer/          # FAISS indexing
│   └── ingest/           # Data scraping
├── scripts/               # Utility scripts
├── docs/                  # This directory
├── data/                  # Card data and images
└── artifacts/             # ML artifacts (indexes, embeddings)
```

## 🔄 Data Pipeline Flow

```
1. Scraper → 2. Images → 3. Embeddings → 4. Index → 5. Reprints → 6. Identify
   (5,186)     (5,053)      (5,053)        (FAISS)    (1,014)      (200ms)
```

## 🛠️ Technology Stack

- **Backend**: Node.js, TypeScript, Python
- **ML**: CLIP (OpenAI), FAISS (Facebook AI), PyTorch
- **Desktop**: Electron, React, Tailwind CSS
- **Database**: SQLite

## 📝 Contributing

When updating documentation:

1. **Guides** → `docs/guides/` - User-facing tutorials and howtos
2. **Architecture** → `docs/architecture/` - Technical design docs
3. **Status** → `docs/status/` - Project status and metrics
4. **Archive** → `docs/archive/` - Historical/deprecated docs

## 🆘 Need Help?

- Check the [Testing Guide](guides/TESTING_GUIDE.md) for common issues
- See [Local Development Guide](guides/LOCAL_DEVELOPMENT.md) for setup problems
- Review [Architecture docs](architecture/) for technical questions

---

**Last Updated**: 2025-10-07
**Status**: Production-ready for One Piece TCG
