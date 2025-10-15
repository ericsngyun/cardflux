#!/bin/bash
# CardFlux Setup Verification Script
# Checks if all components are correctly installed and configured

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}CardFlux Setup Verification${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Function to check command
check_command() {
    local cmd=$1
    local name=$2
    local expected=$3

    if command -v $cmd &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -1)
        echo -e "${GREEN}✓${NC} $name: $version"

        if [[ ! -z "$expected" ]]; then
            # Extract version number
            local ver=$(echo $version | grep -oP '\d+\.\d+' | head -1)
            if [[ "$ver" < "$expected" ]]; then
                echo -e "${YELLOW}  ⚠ Warning: Version $expected+ recommended${NC}"
                ((WARNINGS++))
            fi
        fi
    else
        echo -e "${RED}✗${NC} $name: Not found"
        ((ERRORS++))
    fi
}

# Check Node.js
echo -e "${CYAN}Checking runtime dependencies...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | grep -oP '\d+')
    if [ "$NODE_VERSION" -ge 20 ]; then
        echo -e "${GREEN}✓${NC} Node.js: $(node --version)"
    else
        echo -e "${RED}✗${NC} Node.js: $(node --version) (20.0.0+ required)"
        ((ERRORS++))
    fi
else
    echo -e "${RED}✗${NC} Node.js: Not found"
    ((ERRORS++))
fi

check_command "pnpm" "pnpm" "9.0"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}✗${NC} Python: Not found"
    ((ERRORS++))
    PYTHON_CMD=""
fi

if [[ ! -z "$PYTHON_CMD" ]]; then
    PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    MAJOR=$(echo $PY_VER | cut -d. -f1)
    MINOR=$(echo $PY_VER | cut -d. -f2)

    if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 10 ]]; then
        echo -e "${GREEN}✓${NC} Python: $($PYTHON_CMD --version)"
    else
        echo -e "${RED}✗${NC} Python: $($PYTHON_CMD --version) (3.10+ required)"
        ((ERRORS++))
    fi
fi

echo ""

# Check Python packages
echo -e "${CYAN}Checking Python packages...${NC}"
if [[ ! -z "$PYTHON_CMD" ]]; then
    PACKAGES=("torch" "transformers" "faiss" "cv2" "PIL" "numpy" "tqdm")

    for pkg in "${PACKAGES[@]}"; do
        if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
            # Get version if available
            VERSION=$($PYTHON_CMD -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>/dev/null)
            echo -e "${GREEN}✓${NC} $pkg: $VERSION"
        else
            echo -e "${RED}✗${NC} $pkg: Not installed"
            ((ERRORS++))
        fi
    done

    # Check EasyOCR
    if $PYTHON_CMD -c "import easyocr" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} easyocr: installed"
    else
        echo -e "${YELLOW}⚠${NC} easyocr: Not installed (optional, for card number extraction)"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC} Cannot check Python packages (Python not found)"
    ((ERRORS++))
fi

echo ""

# Check project structure
echo -e "${CYAN}Checking project structure...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# Check node_modules
if [[ -d "$PROJECT_ROOT/node_modules" ]]; then
    echo -e "${GREEN}✓${NC} node_modules: present"
else
    echo -e "${RED}✗${NC} node_modules: missing (run 'pnpm install')"
    ((ERRORS++))
fi

# Check data
if [[ -f "$PROJECT_ROOT/data/curated/one-piece.jsonl" ]]; then
    CARD_COUNT=$(wc -l < "$PROJECT_ROOT/data/curated/one-piece.jsonl")
    echo -e "${GREEN}✓${NC} Card data: $CARD_COUNT cards"
else
    echo -e "${YELLOW}⚠${NC} Card data: missing (run 'pnpm update:sync' or build pipeline)"
    ((WARNINGS++))
fi

# Check FAISS index
if [[ -f "$PROJECT_ROOT/artifacts/faiss/one-piece-dinov2/index.faiss" ]]; then
    INDEX_SIZE=$(du -h "$PROJECT_ROOT/artifacts/faiss/one-piece-dinov2/index.faiss" | cut -f1)
    echo -e "${GREEN}✓${NC} FAISS index: $INDEX_SIZE"
else
    echo -e "${YELLOW}⚠${NC} FAISS index: missing (run 'pnpm update:sync' or build pipeline)"
    ((WARNINGS++))
fi

# Check embeddings
if [[ -f "$PROJECT_ROOT/artifacts/metadata/embeddings/one-piece-dinov2/embeddings.npy" ]]; then
    EMBED_SIZE=$(du -h "$PROJECT_ROOT/artifacts/metadata/embeddings/one-piece-dinov2/embeddings.npy" | cut -f1)
    echo -e "${GREEN}✓${NC} Embeddings: $EMBED_SIZE"
else
    echo -e "${YELLOW}⚠${NC} Embeddings: missing (run 'pnpm update:sync' or build pipeline)"
    ((WARNINGS++))
fi

# Check images
if [[ -d "$PROJECT_ROOT/data/images/one-piece" ]]; then
    IMAGE_COUNT=$(find "$PROJECT_ROOT/data/images/one-piece" -name "*.jpg" | wc -l)
    if [[ $IMAGE_COUNT -gt 0 ]]; then
        echo -e "${GREEN}✓${NC} Card images: $IMAGE_COUNT images"
    else
        echo -e "${YELLOW}⚠${NC} Card images: directory exists but empty"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Card images: missing (run 'pnpm update:sync' or fetch images)"
    ((WARNINGS++))
fi

echo ""

# Summary
echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}Verification Summary${NC}"
echo -e "${CYAN}================================${NC}"

if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo -e "Next steps:"
    echo -e "  cd apps/desktop"
    echo -e "  pnpm build:dev"
    echo -e "  pnpm start"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
    echo ""
    echo -e "System is functional but some optional features may not work."
    echo -e "Review warnings above for details."
    exit 0
else
    echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found${NC}"
    echo ""
    echo -e "Please fix the errors before running the desktop app."
    echo -e "See ${CYAN}DEPLOYMENT_GUIDE.md${NC} for detailed setup instructions."
    exit 1
fi
