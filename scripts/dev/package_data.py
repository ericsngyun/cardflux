#!/usr/bin/env python3
"""
Package all gitignored data files for distribution.
Creates a .zip file that can be shared via GitHub Releases or cloud storage.
"""
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def package_data():
    print("=" * 60)
    print("CardFlux Data Packaging Script")
    print("=" * 60)
    print()

    # Get version
    timestamp = datetime.now().strftime("%Y-%m-%d")
    version = f"v1.0.0-{timestamp}"
    output_file = f"cardflux-data-{version}.zip"

    print("[1/4] Checking required files...")

    required_paths = [
        "data/curated/one-piece.jsonl",
        "data/images/one-piece",
        "artifacts/faiss/one-piece-dinov2/index.faiss",
        "artifacts/faiss/one-piece-dinov2/ids.json",
        "artifacts/faiss/one-piece-dinov2/index_config.json",
        "artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl",
        "artifacts/metadata/embeddings/one-piece-dinov2/reprints.json",
    ]

    all_exist = True
    for path_str in required_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"  [MISSING] {path}")
            all_exist = False
        else:
            print(f"  [OK] {path}")

    if not all_exist:
        print()
        print("ERROR: Some required files are missing.")
        print("Run the full pipeline first to generate all data.")
        return

    print()
    print("[2/4] Creating ZIP archive (this will take a few minutes)...")
    print(f"  Output: {output_file}")

    # Create zip file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add data/curated
        print("  Adding data/curated/one-piece.jsonl...")
        zipf.write("data/curated/one-piece.jsonl")

        # Add data/images (5,113 files)
        print("  Adding data/images/one-piece/ (5,113 images, this will take a moment)...")
        image_dir = Path("data/images/one-piece")
        for i, img_file in enumerate(image_dir.glob("*.jpg"), 1):
            zipf.write(str(img_file))
            if i % 1000 == 0:
                print(f"    {i} images added...")

        # Add FAISS index
        print("  Adding artifacts/faiss/...")
        for file in Path("artifacts/faiss/one-piece-dinov2").glob("*"):
            if file.is_file():
                zipf.write(str(file))

        # Add metadata
        print("  Adding artifacts/metadata/...")
        metadata_dir = Path("artifacts/metadata/embeddings/one-piece-dinov2")
        for file in metadata_dir.glob("*"):
            if file.is_file():
                zipf.write(str(file))

        # Add README
        print("  Adding README.txt...")
        readme_content = f"""# CardFlux Data Package

**Version**: {version}
**Generated**: {timestamp}
**Total Size**: ~324 MB

## Contents

This package contains all the required data files for running CardFlux desktop app:

```
data/
├── curated/
│   └── one-piece.jsonl          (5,195 cards metadata, 2.7 MB)
└── images/
    └── one-piece/               (5,113 card images, 307.4 MB)

artifacts/
├── faiss/
│   └── one-piece-dinov2/
│       ├── index.faiss          (FAISS vector index, 7.1 MB)
│       ├── ids.json             (Card ID mapping)
│       └── index_config.json    (Index configuration)
└── metadata/
    └── embeddings/
        └── one-piece-dinov2/
            ├── metadata.jsonl   (Card metadata, 2.7 MB)
            └── reprints.json    (Reprint mapping, 4.0 MB)
```

## Installation

1. **Clone the CardFlux repository:**
   ```bash
   git clone https://github.com/yourusername/cardflux.git
   cd cardflux
   ```

2. **Extract this package to the repository root:**
   ```bash
   # Windows
   Expand-Archive cardflux-data-{version}.zip -DestinationPath .

   # macOS/Linux
   unzip cardflux-data-{version}.zip
   ```

3. **Verify files exist:**
   ```bash
   ls data/curated/one-piece.jsonl
   ls artifacts/faiss/one-piece-dinov2/index.faiss
   ```

4. **Install dependencies and run:**
   ```bash
   # Install Node.js dependencies
   pnpm install

   # Install Python dependencies
   pip install -r requirements.txt

   # Build and run desktop app
   cd apps/desktop
   NODE_ENV=production pnpm run build:webpack
   pnpm start
   ```

## Coverage

- **Total cards in database**: 5,195 One Piece TCG
- **Cards with images**: 5,113 (98.4%)
- **Cards indexed**: 4,815 (92.7%)
- **Reprint groups**: 1,011 unique card names

## Notes

- This package was built from the production pipeline on {timestamp}
- All images are 600x600 JPG format
- FAISS index uses exact search (IndexFlatIP) for highest accuracy
- DINOv2 embeddings are 384-dimensional

For more information, see the main repository README.
"""
        zipf.writestr("README.txt", readme_content)

    print()
    print("[3/4] Verifying archive...")

    # Get file size
    size_mb = Path(output_file).stat().st_size / 1024 / 1024

    with zipfile.ZipFile(output_file, 'r') as zipf:
        file_count = len(zipf.namelist())
        print(f"  Files in archive: {file_count}")
        print(f"  Archive size: {size_mb:.1f} MB")

    print()
    print("=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print()
    print(f"Package created: {output_file}")
    print(f"Size: {size_mb:.1f} MB")
    print()
    print("Next steps:")
    print("  1. Upload to GitHub Release")
    print("  2. Or upload to cloud storage (Google Drive, Dropbox, S3)")
    print("  3. Update DATA_REQUIREMENTS.md with download link")
    print()

if __name__ == "__main__":
    package_data()
