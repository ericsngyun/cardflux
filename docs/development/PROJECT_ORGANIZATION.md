# CardFlux Project Organization

> **Last Updated**: 2025-10-07
> **Status**: Organized and production-ready

This document outlines the complete organization of the CardFlux project, including file structure, documentation, and naming conventions.

## 📁 Directory Structure

### Root Level

```
cardflux/
├── README.md                    # Main project overview and quick start
├── CONTRIBUTING.md              # Contributing guidelines
├── PROJECT_ORGANIZATION.md      # This file
├── package.json                 # Monorepo configuration
├── pnpm-workspace.yaml          # Workspace configuration
├── tsconfig.json                # TypeScript base config
├── .gitignore                   # Git ignore rules
│
├── apps/                        # Applications
│   └── desktop/                 # Electron desktop app
│
├── packages/                    # Shared packages
│   ├── config/                  # Configuration (TCGPlayer, filtering)
│   ├── database/                # SQLite database layer
│   └── shared/                  # Shared utilities
│
├── services/                    # Data pipeline services
│   ├── embedder/                # CLIP embedding generation
│   ├── indexer/                 # FAISS index building
│   └── ingest/                  # Data scraping and image fetching
│
├── scripts/                     # Utility scripts
│   ├── identification/          # Card identification
│   ├── pipeline/                # Pipeline management
│   ├── testing/                 # Test scripts
│   ├── dev/                     # Development utilities
│   └── make/                    # Build scripts
│
├── docs/                        # Documentation
│   ├── README.md                # Documentation index
│   ├── guides/                  # User guides
│   ├── architecture/            # Technical docs
│   ├── status/                  # Status reports
│   └── archive/                 # Historical docs
│
├── data/                        # Card data (gitignored)
│   ├── raw/                     # Raw scraped data
│   ├── curated/                 # Processed JSONL
│   ├── images/                  # Card images
│   └── state/                   # Pipeline state
│
└── artifacts/                   # ML artifacts (gitignored)
    ├── faiss/                   # FAISS indexes
    ├── metadata/                # Embeddings and metadata
    └── models/                  # Model information
```

## 📚 Documentation Organization

### Main Documentation (`/`)
- `README.md` - Project overview, quick start, and commands
- `CONTRIBUTING.md` - How to contribute to the project
- `PROJECT_ORGANIZATION.md` - This file

### Docs Directory (`/docs`)

#### Index
- `docs/README.md` - Complete documentation index with quick links

#### Guides (`docs/guides/`)
User-facing tutorials and how-to guides:
- `LOCAL_DEVELOPMENT.md` - Development setup and workflow
- `TESTING_GUIDE.md` - Running tests and validation
- `TEST_ONEPIECE_IDENTIFICATION.md` - Testing the identification system

#### Architecture (`docs/architecture/`)
Technical design and implementation docs:
- `ARCHITECTURE.md` - System design and components
- `SEALED_PRODUCT_FILTERING.md` - Sealed product filtering implementation

#### Status (`docs/status/`)
Current project status and metrics:
- `FINAL_STATUS.md` - Current project state and achievements
- `PROGRESS_SUMMARY.md` - Development progress report
- `IDENTIFICATION_TEST_RESULTS.md` - Accuracy and performance metrics

#### Archive (`docs/archive/`)
Historical and deprecated documentation:
- Old guides and migration docs
- Superseded by current documentation

## 🛠️ Scripts Organization

### Identification (`scripts/identification/`)
- `identify_card.py` - Main identification script (200ms, with reprints)

### Pipeline (`scripts/pipeline/`)
- `build_reprint_map.py` - Build reprint detection mapping
- `rebuild_onepiece_pipeline.sh` - Rebuild full One Piece pipeline

### Testing (`scripts/testing/`)
- `test_sealed_filter.ts` - Test sealed product filtering (16 tests)
- `test_identification.py` - Test identification accuracy

### Development (`scripts/dev/`)
- Development utilities and helpers

### Make (`scripts/make/`)
- Build and deployment scripts

## 📦 Package Structure

### Config Package (`packages/config/`)
```
config/
├── src/
│   ├── tcgplayer-config.ts    # TCGPlayer API config and filtering
│   └── index.ts               # Package exports
├── package.json
└── tsconfig.json
```

**Key Exports**:
- `TCGCSV_CONFIG` - API configuration
- `isSealedProduct()` - Sealed product filtering
- `getEnabledCategories()` - Active TCG games
- Type interfaces for TCGPlayer data

### Database Package (`packages/database/`)
```
database/
├── src/
│   ├── client.ts              # SQLite client
│   ├── schema.ts              # Database schema
│   └── index.ts               # Package exports
├── package.json
└── tsconfig.json
```

### Shared Package (`packages/shared/`)
```
shared/
├── src/
│   ├── logger.ts              # Logging utilities
│   ├── retry.ts               # Retry logic
│   ├── sleep.ts               # Delay utilities
│   └── index.ts               # Package exports
├── package.json
└── tsconfig.json
```

## 🔄 Data Pipeline Services

### Ingest Service (`services/ingest/`)
```
ingest/
├── bin/
│   ├── tcgplayer-scraper.ts            # All-games scraper
│   ├── tcgplayer-scraper-onepiece.ts   # One Piece only
│   ├── fetch_images.ts                 # All-games image fetcher
│   └── fetch_images_onepiece.ts        # One Piece only
├── src/
│   └── [shared scraping logic]
├── package.json
└── tsconfig.json
```

### Embedder Service (`services/embedder/`)
```
embedder/
├── bin/
│   ├── embed.py                        # All-games embedder
│   └── embed_onepiece.py               # One Piece only
└── requirements.txt
```

### Indexer Service (`services/indexer/`)
```
indexer/
├── bin/
│   ├── build_faiss.py                  # All-games indexer
│   └── build_faiss_onepiece.py         # One Piece only
└── requirements.txt
```

## 🎯 Naming Conventions

### Files
- **TypeScript**: `kebab-case.ts` (e.g., `tcgplayer-config.ts`)
- **Python**: `snake_case.py` (e.g., `build_reprint_map.py`)
- **Documentation**: `UPPERCASE.md` for root, `Title Case.md` for nested
- **Tests**: `*.test.ts` or `test_*.py`

### Directories
- **Apps/Services**: `lowercase` (e.g., `desktop`, `embedder`)
- **Docs sections**: `lowercase` (e.g., `guides`, `architecture`)
- **Data/Artifacts**: `lowercase` (e.g., `faiss`, `metadata`)

### Functions
- **TypeScript**: `camelCase` (e.g., `fetchGroups()`, `isSealedProduct()`)
- **Python**: `snake_case` (e.g., `identify_card()`, `build_reprint_map()`)

### Variables
- **TypeScript**: `camelCase` for locals, `UPPER_CASE` for constants
- **Python**: `snake_case` for locals, `UPPER_CASE` for constants

### Types/Interfaces
- **TypeScript**: `PascalCase` (e.g., `TCGCategory`, `TCGProduct`)
- **Python**: `PascalCase` for classes (e.g., `FastCardIdentifier`)

## 📊 Data Organization

### Raw Data (`data/raw/`)
```
raw/
└── tcgplayer/
    ├── one-piece/              # Raw One Piece data
    │   ├── {groupId}_{name}.json
    │   └── ...
    ├── magic/                  # Raw Magic data
    └── ...
```

### Curated Data (`data/curated/`)
```
curated/
├── one-piece.jsonl             # One card per line
├── magic.jsonl
├── pokemon.jsonl
└── ...
```

### Images (`data/images/`)
```
images/
├── one-piece/
│   ├── {productId}.jpg
│   └── ...
├── magic/
└── ...
```

### Artifacts (`artifacts/`)
```
artifacts/
├── faiss/
│   ├── one-piece/
│   │   ├── index.faiss         # FAISS index
│   │   └── ids.json            # ID mapping
│   └── ...
├── metadata/
│   └── embeddings/
│       ├── one-piece/
│       │   ├── embeddings.npy  # Numpy embeddings
│       │   ├── metadata.jsonl  # Card metadata
│       │   └── reprints.json   # Reprint mapping
│       └── ...
└── models/
    └── model_info.json         # ML model information
```

## 🔍 Finding Things

### "Where do I find..."

**Configuration for TCGPlayer API?**
→ `packages/config/src/tcgplayer-config.ts`

**Sealed product filtering logic?**
→ `packages/config/src/tcgplayer-config.ts` (`isSealedProduct()`)

**Data scraping?**
→ `services/ingest/bin/tcgplayer-scraper*.ts`

**Image downloading?**
→ `services/ingest/bin/fetch_images*.ts`

**Embedding generation?**
→ `services/embedder/bin/embed*.py`

**FAISS index building?**
→ `services/indexer/bin/build_faiss*.py`

**Card identification?**
→ `scripts/identification/identify_card.py`

**Reprint detection?**
→ `scripts/pipeline/build_reprint_map.py`

**Tests?**
→ `scripts/testing/`

**Documentation?**
→ `docs/` (see `docs/README.md` for index)

## 🔐 Git Ignore

Large or generated files are git-ignored:

- `node_modules/` - Node dependencies
- `dist/` - Build output
- `data/` - Card data and images (too large)
- `artifacts/` - ML artifacts (regeneratable)
- `.env` - Environment variables
- `*.log` - Log files

## 📝 Documentation Standards

### When to Create Docs

- **User-facing feature**: Add to `docs/guides/`
- **Technical design**: Add to `docs/architecture/`
- **Project milestone**: Add to `docs/status/`
- **Deprecated info**: Move to `docs/archive/`

### Documentation Format

- Use Markdown (`.md`)
- Include table of contents for long docs
- Use code blocks with language tags
- Add "Last Updated" date for status docs
- Link between related docs

## 🚀 Quick Reference

### Start Here
1. Read [README.md](README.md)
2. Follow [LOCAL_DEVELOPMENT.md](docs/guides/LOCAL_DEVELOPMENT.md)
3. Review [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

### Common Tasks
- **Add new game**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Run tests**: See [TESTING_GUIDE.md](docs/guides/TESTING_GUIDE.md)
- **Check status**: See [FINAL_STATUS.md](docs/status/FINAL_STATUS.md)

---

**Organization completed**: 2025-10-07
**Maintained by**: Project team
**Questions**: See [CONTRIBUTING.md](CONTRIBUTING.md)
