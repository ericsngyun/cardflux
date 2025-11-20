# Install Git hooks for CardFlux development
# Run this script after cloning the repository to set up pre-commit hooks

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$HookDir = Join-Path $RepoRoot ".git\hooks"
$HookSource = Join-Path $RepoRoot "scripts\hooks"

Write-Host "🔧 Installing Git hooks..." -ForegroundColor Cyan
Write-Host ""

# Create hooks directory if it doesn't exist
if (-not (Test-Path $HookDir)) {
    New-Item -ItemType Directory -Path $HookDir -Force | Out-Null
}

# Install pre-commit hook
$PreCommitSource = Join-Path $HookSource "pre-commit"
$PreCommitDest = Join-Path $HookDir "pre-commit"

if (Test-Path $PreCommitSource) {
    Copy-Item $PreCommitSource $PreCommitDest -Force
    Write-Host "✅ Installed pre-commit hook" -ForegroundColor Green
} else {
    Write-Host "❌ Error: pre-commit hook source not found at $PreCommitSource" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Git hooks installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The following checks will run before each commit:" -ForegroundColor Yellow
Write-Host "  - 🎨 Prettier code formatting"
Write-Host "  - 🔧 ESLint linting"
Write-Host "  - 📘 TypeScript type checking"
Write-Host ""
Write-Host "To skip hooks for a commit (not recommended):" -ForegroundColor Yellow
Write-Host "  git commit --no-verify"
Write-Host ""
