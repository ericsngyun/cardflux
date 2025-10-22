# Contributing to CardFlux

Thank you for your interest in contributing to CardFlux! This document provides guidelines and standards for contributing to the project.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/cardflux.git`
3. Install dependencies: `pnpm install && pip install -r requirements.txt`
4. Create a branch: `git checkout -b feature/your-feature-name`

## Development Workflow

### TypeScript/Node.js

```bash
# Build all packages
pnpm build

# Run type checking
pnpm typecheck

# Run linting
pnpm lint

# Run desktop app in development
pnpm dev
```

### Python

```bash
# Run type checking
mypy services/embedder/ services/indexer/

# Run tests
pytest
```

## Project Structure

### Adding a New TCG Game

1. **Update Config** (`packages/config/src/tcgplayer-config.ts`)
   - Add category to `enabledCategories`
   - Update `isSealedProduct()` if game has unique sealed product patterns

2. **Create Scraper** (`services/ingest/bin/`)
   - Follow pattern from `tcgplayer-scraper-onepiece.ts`
   - Use sealed product filtering
   - Save to `data/curated/{game}.jsonl`

3. **Create Image Fetcher** (`services/ingest/bin/`)
   - Follow pattern from `fetch_images_onepiece.ts`
   - Download to `data/images/{game}/`

4. **Create Embedder** (`services/embedder/bin/`)
   - Follow pattern from `embed_onepiece.py`
   - Save to `artifacts/metadata/embeddings/{game}/`

5. **Create Indexer** (`services/indexer/bin/`)
   - Follow pattern from `build_faiss_onepiece.py`
   - Save to `artifacts/faiss/{game}/`

### Code Style

#### TypeScript
- Use TypeScript strict mode
- Prefer interfaces over types for objects
- Use async/await over promises
- Document exported functions with JSDoc

```typescript
/**
 * Fetch groups for a TCG category
 * @param categoryId - TCGPlayer category ID
 * @returns Array of groups
 */
export async function fetchGroups(categoryId: number): Promise<TCGGroup[]> {
  // implementation
}
```

#### Python
- Follow PEP 8
- Use type hints
- Document functions with docstrings

```python
def identify_card(image_path: str, top_k: int = 5) -> List[Match]:
    """
    Identify a card from an image.

    Args:
        image_path: Path to card image
        top_k: Number of matches to return

    Returns:
        List of top matches with similarity scores
    """
    # implementation
```

## Testing

### Required Tests

- **Sealed Product Filtering**: Must pass all 16 tests
  ```bash
  pnpm tsx scripts/testing/test_sealed_filter.ts
  ```

- **Identification Accuracy**: Test on sample images
  ```bash
  python scripts/testing/test_identification.py
  ```

### Adding New Tests

- Unit tests → `{package}/__tests__/`
- Integration tests → `scripts/testing/`
- E2E tests → `apps/desktop/test/`

## Documentation

### Required Documentation

When adding a feature:

1. **Code Comments**: Document complex logic
2. **JSDoc/Docstrings**: All exported functions
3. **README**: Update relevant README files
4. **Guides**: Add to `docs/guides/` if user-facing

### Documentation Structure

```
docs/
├── guides/           # User-facing tutorials
├── architecture/     # Technical design docs
├── status/          # Project status reports
└── archive/         # Historical docs
```

## Commit Messages

Use conventional commits:

```
feat: Add Pokemon TCG support
fix: Correct sealed product filtering for Magic
docs: Update identification guide
test: Add tests for reprint detection
refactor: Simplify FAISS index building
```

## Pull Request Process

1. **Create PR** against `main` branch
2. **Title**: Clear description of changes
3. **Description**:
   - What changed and why
   - Link to related issues
   - Testing performed
4. **Checks**: All CI checks must pass
5. **Review**: Address review comments
6. **Merge**: Squash and merge when approved

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Sealed product filtering tests pass
- [ ] Identification tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Performance Standards

### Identification Speed
- Target: <2000ms per card
- Current: ~200ms
- Maintain or improve performance

### Accuracy
- Exact matches: ≥99%
- Variants: ≥90%
- Clear separation: Different cards <85%

### Database Quality
- Sealed products filtered: Yes
- Duplicate detection: Required
- Data validation: All fields present

## Adding Sealed Product Patterns

When adding new sealed product patterns to `isSealedProduct()`:

1. Add pattern to regex array with comment
2. Add test case to `scripts/testing/test_sealed_filter.ts`
3. Verify existing cards still filter correctly
4. Document in `docs/architecture/SEALED_PRODUCT_FILTERING.md`

## Questions?

- **Technical**: See [Architecture docs](docs/architecture/)
- **Setup**: See [Local Development Guide](docs/guides/LOCAL_DEVELOPMENT.md)
- **Testing**: See [Testing Guide](docs/guides/TESTING_GUIDE.md)
- **Issues**: Open a GitHub issue

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
