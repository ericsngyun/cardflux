#!/usr/bin/env pwsh
# CardFlux Complete Setup Verification Script
# Comprehensive check of all components for Windows deployment

$ErrorActionPreference = "Continue"  # Don't stop on first error

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CardFlux Complete Setup Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$global:passCount = 0
$global:failCount = 0
$global:warnCount = 0

function Test-Check {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [bool]$Required = $true
    )

    Write-Host -NoNewline "Checking $Name... " -ForegroundColor Gray

    try {
        $result = & $Test
        if ($result) {
            Write-Host "✓ PASS" -ForegroundColor Green
            $global:passCount++
            return $true
        } else {
            if ($Required) {
                Write-Host "✗ FAIL" -ForegroundColor Red
                $global:failCount++
            } else {
                Write-Host "⚠ WARN (optional)" -ForegroundColor Yellow
                $global:warnCount++
            }
            return $false
        }
    } catch {
        if ($Required) {
            Write-Host "✗ FAIL ($($_.Exception.Message))" -ForegroundColor Red
            $global:failCount++
        } else {
            Write-Host "⚠ WARN (optional)" -ForegroundColor Yellow
            $global:warnCount++
        }
        return $false
    }
}

# ============================================
# SECTION 1: Runtime Dependencies
# ============================================
Write-Host "`n[1/6] Runtime Dependencies" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

Test-Check "Node.js installed" {
    try {
        $version = node --version 2>$null
        if ($version -match "v(\d+)\.") {
            $major = [int]$Matches[1]
            if ($major -ge 20) {
                Write-Host -NoNewline "  (Node.js $version) " -ForegroundColor Gray
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

Test-Check "pnpm installed" {
    try {
        $version = pnpm --version 2>$null
        if ($version) {
            Write-Host -NoNewline "  (pnpm $version) " -ForegroundColor Gray
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

Test-Check "Python installed" {
    try {
        $version = python --version 2>$null
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 10) {
                Write-Host -NoNewline "  ($version) " -ForegroundColor Gray
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

# ============================================
# SECTION 2: Python Packages
# ============================================
Write-Host "`n[2/6] Python Packages" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

Test-Check "PyTorch installed" {
    $output = python -c "import torch; print(torch.__version__)" 2>$null
    if ($output) {
        Write-Host -NoNewline "  (torch $output) " -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-Check "Transformers installed" {
    $output = python -c "import transformers; print(transformers.__version__)" 2>$null
    if ($output) {
        Write-Host -NoNewline "  (transformers $output) " -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-Check "FAISS installed" {
    $output = python -c "import faiss; print('OK')" 2>$null
    if ($output -eq "OK") {
        Write-Host -NoNewline "  (faiss OK) " -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-Check "OpenCV installed" {
    $output = python -c "import cv2; print(cv2.__version__)" 2>$null
    if ($output) {
        Write-Host -NoNewline "  (opencv $output) " -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-Check "PIL/Pillow installed" {
    $output = python -c "import PIL; print(PIL.__version__)" 2>$null
    if ($output) {
        Write-Host -NoNewline "  (Pillow $output) " -ForegroundColor Gray
        return $true
    }
    return $false
}

Test-Check "NumPy installed" {
    $output = python -c "import numpy; print(numpy.__version__)" 2>$null
    if ($output) {
        Write-Host -NoNewline "  (numpy $output) " -ForegroundColor Gray
        return $true
    }
    return $false
}

# Optional packages
Test-Check "EasyOCR installed" {
    $output = python -c "import easyocr; print('OK')" 2>$null
    return ($output -eq "OK")
} -Required $false

Test-Check "PaddleOCR installed" {
    $output = python -c "import paddleocr; print('OK')" 2>$null
    return ($output -eq "OK")
} -Required $false

# ============================================
# SECTION 3: Project Structure
# ============================================
Write-Host "`n[3/6] Project Structure" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

Test-Check "node_modules exists" {
    return (Test-Path "node_modules")
}

Test-Check "scripts/identification exists" {
    return (Test-Path "scripts/identification/core")
}

Test-Check "Python __init__.py files" {
    return (Test-Path "scripts/identification/__init__.py") -and
           (Test-Path "scripts/identification/core/__init__.py") -and
           (Test-Path "scripts/identification/tools/__init__.py")
}

Test-Check "Desktop app source exists" {
    return (Test-Path "apps/desktop/src/main/index.ts") -and
           (Test-Path "apps/desktop/src/python/identification_service.py")
}

# ============================================
# SECTION 4: Data and Artifacts
# ============================================
Write-Host "`n[4/6] Data and Artifacts" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

$dataPath = "data/curated/one-piece.jsonl"
Test-Check "Card data (one-piece.jsonl)" {
    if (Test-Path $dataPath) {
        $size = (Get-Item $dataPath).Length
        $cards = (Get-Content $dataPath | Measure-Object -Line).Lines
        Write-Host -NoNewline "  ($cards cards, $([math]::Round($size/1MB, 1)) MB) " -ForegroundColor Gray
        return $true
    }
    return $false
}

$indexPath = "artifacts/faiss/one-piece-dinov2/index.faiss"
Test-Check "FAISS index" {
    if (Test-Path $indexPath) {
        $size = (Get-Item $indexPath).Length
        Write-Host -NoNewline "  ($([math]::Round($size/1MB, 1)) MB) " -ForegroundColor Gray
        return $true
    }
    return $false
}

$embeddingPath = "artifacts/metadata/embeddings/one-piece-dinov2/embeddings.npy"
Test-Check "Embeddings file" {
    if (Test-Path $embeddingPath) {
        $size = (Get-Item $embeddingPath).Length
        Write-Host -NoNewline "  ($([math]::Round($size/1MB, 1)) MB) " -ForegroundColor Gray
        return $true
    }
    return $false
}

$imagesPath = "data/images/one-piece"
Test-Check "Card images directory" {
    if (Test-Path $imagesPath) {
        $count = (Get-ChildItem $imagesPath -Filter "*.jpg" | Measure-Object).Count
        Write-Host -NoNewline "  ($count images) " -ForegroundColor Gray
        return $true
    }
    return $false
}

# ============================================
# SECTION 5: Desktop App Build
# ============================================
Write-Host "`n[5/6] Desktop App Build" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

Test-Check "Desktop app built" {
    return (Test-Path "apps/desktop/dist/index.js") -and
           (Test-Path "apps/desktop/dist/python/identification_service.py")
}

Test-Check "Desktop package.json" {
    return (Test-Path "apps/desktop/package.json")
}

# ============================================
# SECTION 6: Python Service Imports
# ============================================
Write-Host "`n[6/6] Python Service Imports" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray

Test-Check "Production identifier import" {
    $output = python -c @"
import sys
from pathlib import Path
scripts_dir = Path('./scripts/identification')
sys.path.insert(0, str(scripts_dir))
from core.production_card_identifier import ProductionCardIdentifier
print('OK')
"@ 2>$null
    return ($output -eq "OK")
}

Test-Check "Card detector import" {
    $output = python -c @"
import sys
from pathlib import Path
scripts_dir = Path('./scripts/identification')
sys.path.insert(0, str(scripts_dir))
from core.polished_card_detector import PolishedCardDetector, CardDetectionStatus
print('OK')
"@ 2>$null
    return ($output -eq "OK")
}

Test-Check "Version manager import" {
    $output = python -c @"
import sys
from pathlib import Path
scripts_dir = Path('./scripts/identification')
sys.path.insert(0, str(scripts_dir))
from tools.identifier_version_manager import IdentifierVersionManager
print('OK')
"@ 2>$null
    return ($output -eq "OK")
}

# ============================================
# SUMMARY
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Verification Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$total = $global:passCount + $global:failCount + $global:warnCount
Write-Host "Total checks: $total" -ForegroundColor White
Write-Host "  ✓ Passed:  $global:passCount" -ForegroundColor Green
Write-Host "  ✗ Failed:  $global:failCount" -ForegroundColor $(if ($global:failCount -gt 0) { "Red" } else { "Gray" })
Write-Host "  ⚠ Warnings: $global:warnCount" -ForegroundColor $(if ($global:warnCount -gt 0) { "Yellow" } else { "Gray" })
Write-Host ""

if ($global:failCount -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your CardFlux setup is complete and ready to use!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Build the desktop app:" -ForegroundColor White
    Write-Host "     cd apps/desktop" -ForegroundColor Gray
    Write-Host "     pnpm build:dev" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Start the app:" -ForegroundColor White
    Write-Host "     pnpm start" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "⚠ SETUP INCOMPLETE" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the failed checks above before running the app." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Cyan
    Write-Host "  - Missing Python packages: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  - Missing data/artifacts: pnpm update:sync" -ForegroundColor White
    Write-Host "  - Missing node_modules: pnpm install" -ForegroundColor White
    Write-Host ""
    Write-Host "For detailed setup instructions, see:" -ForegroundColor Cyan
    Write-Host "  docs/guides/WINDOWS_SETUP_GUIDE.md" -ForegroundColor White
    Write-Host ""
    exit 1
}
