#!/usr/bin/env pwsh
# CardFlux Desktop Setup Script for Windows
# Automates setup of CardFlux desktop scanner on Windows 10/11

param(
    [switch]$SkipPython,
    [switch]$SkipNode,
    [switch]$SkipData,
    [switch]$GPU
)

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "CardFlux Desktop Setup (Windows)" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin (recommended but not required)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "[!] Not running as Administrator. Some operations may fail." -ForegroundColor Yellow
    Write-Host ""
}

# Function to check command existence
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# 1. Check/Install Node.js and pnpm
if (-not $SkipNode) {
    Write-Host "[1/5] Checking Node.js and pnpm..." -ForegroundColor Green

    if (Test-Command node) {
        $nodeVersion = node --version
        Write-Host "  [OK] Node.js $nodeVersion" -ForegroundColor Gray
    } else {
        Write-Host "  [!] Node.js not found!" -ForegroundColor Red
        Write-Host "  Please install Node.js 20+ from: https://nodejs.org/" -ForegroundColor Yellow
        Write-Host "  After installation, restart this script." -ForegroundColor Yellow
        exit 1
    }

    if (Test-Command pnpm) {
        $pnpmVersion = pnpm --version
        Write-Host "  [OK] pnpm $pnpmVersion" -ForegroundColor Gray
    } else {
        Write-Host "  [!] pnpm not found. Installing via npm..." -ForegroundColor Yellow
        npm install -g pnpm
        Write-Host "  [OK] pnpm installed" -ForegroundColor Gray
    }
    Write-Host ""
}

# 2. Check/Install Python
if (-not $SkipPython) {
    Write-Host "[2/5] Checking Python..." -ForegroundColor Green

    if (Test-Command python) {
        $pythonVersion = python --version
        Write-Host "  [OK] $pythonVersion" -ForegroundColor Gray

        # Check Python version
        $versionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $major, $minor = $versionOutput -split '\.'
        if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
            Write-Host "  [!] Python 3.10+ required, but found Python $versionOutput" -ForegroundColor Red
            Write-Host "  Please install Python 3.10+ from: https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "  [!] Python not found!" -ForegroundColor Red
        Write-Host "  Please install Python 3.10+ from: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
        exit 1
    }
    Write-Host ""
}

# 3. Install Node.js dependencies
Write-Host "[3/5] Installing Node.js dependencies..." -ForegroundColor Green
try {
    pnpm install
    Write-Host "  [OK] Node.js dependencies installed" -ForegroundColor Gray
} catch {
    Write-Host "  [!] Failed to install Node.js dependencies" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. Install Python dependencies
Write-Host "[4/5] Installing Python dependencies..." -ForegroundColor Green
try {
    if ($GPU) {
        Write-Host "  Installing with GPU support (CUDA)..." -ForegroundColor Yellow
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
        pip install faiss-gpu
        pip install -r requirements.txt --no-deps
    } else {
        pip install -r requirements.txt
    }
    Write-Host "  [OK] Python dependencies installed" -ForegroundColor Gray
} catch {
    Write-Host "  [!] Failed to install Python dependencies" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "  Try installing manually:" -ForegroundColor Yellow
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 5. Check/Download data and artifacts
if (-not $SkipData) {
    Write-Host "[5/5] Checking data and artifacts..." -ForegroundColor Green

    $dataPath = Join-Path $PSScriptRoot "..\..\data\curated\one-piece.jsonl"
    $indexPath = Join-Path $PSScriptRoot "..\..\artifacts\faiss\one-piece-dinov2\index.faiss"

    if (Test-Path $dataPath) {
        Write-Host "  [OK] Data found: $dataPath" -ForegroundColor Gray
    } else {
        Write-Host "  [!] Data not found. You need to either:" -ForegroundColor Yellow
        Write-Host "      1. Download pre-built artifacts (recommended)" -ForegroundColor Yellow
        Write-Host "      2. Run the data pipeline manually" -ForegroundColor Yellow
        Write-Host "" -ForegroundColor Yellow
        Write-Host "  To download artifacts (if available):" -ForegroundColor Yellow
        Write-Host "    pnpm update:sync" -ForegroundColor Yellow
        Write-Host "" -ForegroundColor Yellow
        Write-Host "  To build pipeline from scratch:" -ForegroundColor Yellow
        Write-Host "    See docs/guides/LOCAL_DEVELOPMENT.md" -ForegroundColor Yellow
    }

    if (Test-Path $indexPath) {
        Write-Host "  [OK] FAISS index found: $indexPath" -ForegroundColor Gray
    } else {
        Write-Host "  [!] FAISS index not found" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Success message
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. If data/artifacts are missing, download or build them:" -ForegroundColor White
Write-Host "     pnpm update:sync" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "  2. Build and run the desktop app:" -ForegroundColor White
Write-Host "     cd apps/desktop" -ForegroundColor Gray
Write-Host "     pnpm build:dev" -ForegroundColor Gray
Write-Host "     pnpm start" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "For detailed documentation, see:" -ForegroundColor Cyan
Write-Host "  - README.md - Overview and quick start" -ForegroundColor White
Write-Host "  - docs/guides/LOCAL_DEVELOPMENT.md - Development guide" -ForegroundColor White
Write-Host "  - apps/desktop/README.md - Desktop app specifics" -ForegroundColor White
Write-Host ""
