#!/usr/bin/env pwsh
# CardFlux Setup Verification Script (Windows)
# Checks if all components are correctly installed and configured

$ErrorActionPreference = "Continue"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "CardFlux Setup Verification" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$Errors = 0
$Warnings = 0

# Function to check command
function Test-CommandVersion {
    param(
        [string]$Command,
        [string]$Name,
        [string]$MinVersion
    )

    try {
        $version = & $Command --version 2>&1 | Select-Object -First 1
        Write-Host "[OK] $Name`: $version" -ForegroundColor Green

        if ($MinVersion) {
            # Extract version number
            if ($version -match '(\d+\.\d+)') {
                $actualVersion = [version]$Matches[1]
                $requiredVersion = [version]$MinVersion

                if ($actualVersion -lt $requiredVersion) {
                    Write-Host "  [!] Warning: Version $MinVersion+ recommended" -ForegroundColor Yellow
                    $script:Warnings++
                }
            }
        }
    } catch {
        Write-Host "[X] $Name`: Not found" -ForegroundColor Red
        $script:Errors++
    }
}

# Check Node.js
Write-Host "Checking runtime dependencies..." -ForegroundColor Cyan

if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    $nodeVersionNumber = [int]($nodeVersion -replace 'v(\d+).*', '$1')

    if ($nodeVersionNumber -ge 20) {
        Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
    } else {
        Write-Host "[X] Node.js: $nodeVersion (20.0.0+ required)" -ForegroundColor Red
        $Errors++
    }
} else {
    Write-Host "[X] Node.js: Not found" -ForegroundColor Red
    $Errors++
}

# Check pnpm
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    $pnpmVersion = pnpm --version
    Write-Host "[OK] pnpm: $pnpmVersion" -ForegroundColor Green
} else {
    Write-Host "[X] pnpm: Not found" -ForegroundColor Red
    $Errors++
}

# Check Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "[X] Python: Not found" -ForegroundColor Red
    $Errors++
}

if ($pythonCmd) {
    $pythonVersion = & $pythonCmd --version 2>&1
    $pyVer = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $major, $minor = $pyVer -split '\.'

    if ([int]$major -ge 3 -and [int]$minor -ge 10) {
        Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "[X] Python: $pythonVersion (3.10+ required)" -ForegroundColor Red
        $Errors++
    }
}

Write-Host ""

# Check Python packages
Write-Host "Checking Python packages..." -ForegroundColor Cyan

if ($pythonCmd) {
    $packages = @("torch", "transformers", "faiss", "cv2", "PIL", "numpy", "tqdm")

    foreach ($pkg in $packages) {
        try {
            $version = & $pythonCmd -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>$null
            Write-Host "[OK] $pkg`: $version" -ForegroundColor Green
        } catch {
            Write-Host "[X] $pkg`: Not installed" -ForegroundColor Red
            $Errors++
        }
    }

    # Check EasyOCR (optional)
    try {
        & $pythonCmd -c "import easyocr" 2>$null | Out-Null
        Write-Host "[OK] easyocr: installed" -ForegroundColor Green
    } catch {
        Write-Host "[!] easyocr: Not installed (optional, for card number extraction)" -ForegroundColor Yellow
        $Warnings++
    }
} else {
    Write-Host "[X] Cannot check Python packages (Python not found)" -ForegroundColor Red
    $Errors++
}

Write-Host ""

# Check project structure
Write-Host "Checking project structure..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# Check node_modules
if (Test-Path "$ProjectRoot\node_modules") {
    Write-Host "[OK] node_modules: present" -ForegroundColor Green
} else {
    Write-Host "[X] node_modules: missing (run 'pnpm install')" -ForegroundColor Red
    $Errors++
}

# Check data
$dataPath = "$ProjectRoot\data\curated\one-piece.jsonl"
if (Test-Path $dataPath) {
    $cardCount = (Get-Content $dataPath | Measure-Object -Line).Lines
    Write-Host "[OK] Card data: $cardCount cards" -ForegroundColor Green
} else {
    Write-Host "[!] Card data: missing (run 'pnpm update:sync' or build pipeline)" -ForegroundColor Yellow
    $Warnings++
}

# Check FAISS index
$indexPath = "$ProjectRoot\artifacts\faiss\one-piece-dinov2\index.faiss"
if (Test-Path $indexPath) {
    $indexSize = [math]::Round((Get-Item $indexPath).Length / 1MB, 1)
    Write-Host "[OK] FAISS index: $indexSize MB" -ForegroundColor Green
} else {
    Write-Host "[!] FAISS index: missing (run 'pnpm update:sync' or build pipeline)" -ForegroundColor Yellow
    $Warnings++
}

# Check embeddings
$embedPath = "$ProjectRoot\artifacts\metadata\embeddings\one-piece-dinov2\embeddings.npy"
if (Test-Path $embedPath) {
    $embedSize = [math]::Round((Get-Item $embedPath).Length / 1MB, 1)
    Write-Host "[OK] Embeddings: $embedSize MB" -ForegroundColor Green
} else {
    Write-Host "[!] Embeddings: missing (run 'pnpm update:sync' or build pipeline)" -ForegroundColor Yellow
    $Warnings++
}

# Check images
$imagesPath = "$ProjectRoot\data\images\one-piece"
if (Test-Path $imagesPath) {
    $imageCount = (Get-ChildItem $imagesPath -Filter *.jpg -Recurse).Count
    if ($imageCount -gt 0) {
        Write-Host "[OK] Card images: $imageCount images" -ForegroundColor Green
    } else {
        Write-Host "[!] Card images: directory exists but empty" -ForegroundColor Yellow
        $Warnings++
    }
} else {
    Write-Host "[!] Card images: missing (run 'pnpm update:sync' or fetch images)" -ForegroundColor Yellow
    $Warnings++
}

Write-Host ""

# Summary
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Verification Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if ($Errors -eq 0 -and $Warnings -eq 0) {
    Write-Host "[OK] All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  cd apps/desktop"
    Write-Host "  pnpm build:dev"
    Write-Host "  pnpm start"
    exit 0
} elseif ($Errors -eq 0) {
    Write-Host "[!] $Warnings warning(s) found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "System is functional but some optional features may not work."
    Write-Host "Review warnings above for details."
    exit 0
} else {
    Write-Host "[X] $Errors error(s) and $Warnings warning(s) found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the errors before running the desktop app."
    Write-Host "See DEPLOYMENT_GUIDE.md for detailed setup instructions." -ForegroundColor Cyan
    exit 1
}
