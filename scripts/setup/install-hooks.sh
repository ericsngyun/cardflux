#!/bin/bash
# Install Git hooks for CardFlux development
# Run this script after cloning the repository to set up pre-commit hooks

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
HOOK_SOURCE="$REPO_ROOT/scripts/hooks"

echo "🔧 Installing Git hooks..."
echo ""

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Install pre-commit hook
if [ -f "$HOOK_SOURCE/pre-commit" ]; then
  cp "$HOOK_SOURCE/pre-commit" "$HOOK_DIR/pre-commit"
  chmod +x "$HOOK_DIR/pre-commit"
  echo "✅ Installed pre-commit hook"
else
  echo "❌ Error: pre-commit hook source not found at $HOOK_SOURCE/pre-commit"
  exit 1
fi

echo ""
echo "🎉 Git hooks installed successfully!"
echo ""
echo "The following checks will run before each commit:"
echo "  - 🎨 Prettier code formatting"
echo "  - 🔧 ESLint linting"
echo "  - 📘 TypeScript type checking"
echo ""
echo "To skip hooks for a commit (not recommended):"
echo "  git commit --no-verify"
echo ""
