#!/usr/bin/env pwsh
# Package all gitignored data files for distribution
# Creates a .zip file that can be shared via GitHub Releases or cloud storage

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "CardFlux Data Packaging Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Get version from package.json or use timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd"
$version = "v1.0.0-$timestamp"
$outputFile = "cardflux-data-$version.zip"

Write-Host "[1/4] Checking required files..." -ForegroundColor Yellow

$requiredPaths = @(
    "data/curated/one-piece.jsonl",
    "data/images/one-piece",
    "artifacts/faiss/one-piece-dinov2/index.faiss",
    "artifacts/faiss/one-piece-dinov2/ids.json",
    "artifacts/faiss/one-piece-dinov2/index_config.json",
    "artifacts/metadata/embeddings/one-piece-dinov2/embeddings.npy",
    "artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl",
    "artifacts/metadata/embeddings/one-piece-dinov2/reprints.json"
)

$allExist = $true
foreach ($path in $requiredPaths) {
    if (-not (Test-Path $path)) {
        Write-Host "  [MISSING] $path" -ForegroundColor Red
        $allExist = $false
    } else {
        Write-Host "  [OK] $path" -ForegroundColor Green
    }
}

if (-not $allExist) {
    Write-Host ""
    Write-Host "ERROR: Some required files are missing." -ForegroundColor Red
    Write-Host "Run the full pipeline first to generate all data." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/4] Creating temporary staging directory..." -ForegroundColor Yellow

$tempDir = "temp-package"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host ""
Write-Host "[3/4] Copying files to staging..." -ForegroundColor Yellow

# Copy data files
Write-Host "  Copying data/curated/..." -ForegroundColor Gray
New-Item -ItemType Directory -Path "$tempDir/data/curated" -Force | Out-Null
Copy-Item "data/curated/one-piece.jsonl" "$tempDir/data/curated/"

Write-Host "  Copying data/images/one-piece/ (5,113 images, this will take a moment)..." -ForegroundColor Gray
New-Item -ItemType Directory -Path "$tempDir/data/images/one-piece" -Force | Out-Null
Copy-Item "data/images/one-piece/*" "$tempDir/data/images/one-piece/" -Recurse

# Copy FAISS index
Write-Host "  Copying artifacts/faiss/..." -ForegroundColor Gray
New-Item -ItemType Directory -Path "$tempDir/artifacts/faiss/one-piece-dinov2" -Force | Out-Null
Copy-Item "artifacts/faiss/one-piece-dinov2/*" "$tempDir/artifacts/faiss/one-piece-dinov2/"

# Copy metadata
Write-Host "  Copying artifacts/metadata/..." -ForegroundColor Gray
New-Item -ItemType Directory -Path "$tempDir/artifacts/metadata/embeddings/one-piece-dinov2" -Force | Out-Null
Copy-Item "artifacts/metadata/embeddings/one-piece-dinov2/*" "$tempDir/artifacts/metadata/embeddings/one-piece-dinov2/"

# Create README for the package
Write-Host "  Creating README..." -ForegroundColor Gray
$readmeContent = @"
# CardFlux Data Package

**Version**: $version
**Generated**: $timestamp
**Total Size**: ~324 MB

## Contents

This package contains all the required data files for running CardFlux desktop app:

``````
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
            ├── embeddings.npy   (DINOv2 embeddings, ~7 MB)
            ├── metadata.jsonl   (Card metadata, 2.7 MB)
            └── reprints.json    (Reprint mapping, 4.0 MB)
``````

## Installation

1. **Clone the CardFlux repository:**
   ``````bash
   git clone https://github.com/yourusername/cardflux.git
   cd cardflux
   ``````

2. **Extract this package to the repository root:**
   ``````bash
   # Windows
   Expand-Archive cardflux-data-$version.zip -DestinationPath .

   # macOS/Linux
   unzip cardflux-data-$version.zip
   ``````

3. **Verify files exist:**
   ``````bash
   ls data/curated/one-piece.jsonl
   ls artifacts/faiss/one-piece-dinov2/index.faiss
   ``````

4. **Install dependencies and run:**
   ``````bash
   # Install Node.js dependencies
   pnpm install

   # Install Python dependencies
   pip install -r requirements.txt

   # Build and run desktop app
   cd apps/desktop
   NODE_ENV=production pnpm run build:webpack
   pnpm start
   ``````

## Coverage

- **Total cards in database**: 5,195 One Piece TCG
- **Cards with images**: 5,113 (98.4%)
- **Cards indexed**: 4,815 (92.7%)
- **Reprint groups**: 1,011 unique card names

## Notes

- This package was built from the production pipeline on $timestamp
- All images are 600x600 JPG format
- FAISS index uses exact search (IndexFlatIP) for highest accuracy
- DINOv2 embeddings are 384-dimensional

For more information, see the main repository README.
"@

Set-Content -Path "$tempDir/README.txt" -Value $readmeContent

Write-Host ""
Write-Host "[4/4] Creating ZIP archive..." -ForegroundColor Yellow
Write-Host "  Output: $outputFile" -ForegroundColor Gray

if (Test-Path $outputFile) {
    Remove-Item $outputFile
}

# Compress (this will take a few minutes due to image files)
Compress-Archive -Path "$tempDir/*" -DestinationPath $outputFile -CompressionLevel Optimal

# Cleanup
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Package created: $outputFile" -ForegroundColor Cyan

# Get file size
$size = (Get-Item $outputFile).Length / 1MB
Write-Host "Size: $([math]::Round($size, 1)) MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Upload to GitHub Release" -ForegroundColor Gray
Write-Host "  2. Or upload to cloud storage (Google Drive, Dropbox, S3)" -ForegroundColor Gray
Write-Host "  3. Share the download link in DATA_REQUIREMENTS.md" -ForegroundColor Gray
Write-Host ""
