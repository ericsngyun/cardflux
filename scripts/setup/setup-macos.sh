#!/bin/bash
# CardFlux Desktop Setup Script for macOS
# Automates setup of CardFlux desktop scanner on macOS (Intel and Apple Silicon)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Flags
SKIP_PYTHON=false
SKIP_NODE=false
SKIP_DATA=false
USE_GPU=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-node)
            SKIP_NODE=true
            shift
            ;;
        --skip-data)
            SKIP_DATA=true
            shift
            ;;
        --gpu)
            USE_GPU=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-python] [--skip-node] [--skip-data] [--gpu]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}CardFlux Desktop Setup (macOS)${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# Detect Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${YELLOW}[i] Detected Apple Silicon (M1/M2/M3)${NC}"
    IS_APPLE_SILICON=true
else
    echo -e "${GRAY}[i] Detected Intel Mac${NC}"
    IS_APPLE_SILICON=false
fi
echo ""

# 1. Check/Install Homebrew
echo -e "${GREEN}[0/5] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}  [!] Homebrew not found. Installing...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon
    if [[ "$IS_APPLE_SILICON" == true ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    echo -e "${GRAY}  [OK] Homebrew installed${NC}"
else
    echo -e "${GRAY}  [OK] Homebrew already installed${NC}"
fi
echo ""

# 2. Check/Install Node.js and pnpm
if [[ "$SKIP_NODE" != true ]]; then
    echo -e "${GREEN}[1/5] Checking Node.js and pnpm...${NC}"

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GRAY}  [OK] Node.js $NODE_VERSION${NC}"
    else
        echo -e "${YELLOW}  [!] Node.js not found. Installing via Homebrew...${NC}"
        brew install node@20
        echo -e "${GRAY}  [OK] Node.js installed${NC}"
    fi

    if command -v pnpm &> /dev/null; then
        PNPM_VERSION=$(pnpm --version)
        echo -e "${GRAY}  [OK] pnpm $PNPM_VERSION${NC}"
    else
        echo -e "${YELLOW}  [!] pnpm not found. Installing via npm...${NC}"
        npm install -g pnpm
        echo -e "${GRAY}  [OK] pnpm installed${NC}"
    fi
    echo ""
fi

# 3. Check/Install Python
if [[ "$SKIP_PYTHON" != true ]]; then
    echo -e "${GREEN}[2/5] Checking Python...${NC}"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GRAY}  [OK] $PYTHON_VERSION${NC}"

        # Check Python version
        PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo $PYTHON_VER | cut -d. -f1)
        MINOR=$(echo $PYTHON_VER | cut -d. -f2)

        if [[ "$MAJOR" -lt 3 ]] || [[ "$MAJOR" -eq 3 && "$MINOR" -lt 10 ]]; then
            echo -e "${RED}  [!] Python 3.10+ required, but found Python $PYTHON_VER${NC}"
            echo -e "${YELLOW}  Installing Python 3.11 via Homebrew...${NC}"
            brew install python@3.11
            echo -e "${GRAY}  [OK] Python 3.11 installed${NC}"
        fi
    else
        echo -e "${YELLOW}  [!] Python not found. Installing Python 3.11 via Homebrew...${NC}"
        brew install python@3.11
        echo -e "${GRAY}  [OK] Python 3.11 installed${NC}"
    fi
    echo ""
fi

# 4. Install Node.js dependencies
echo -e "${GREEN}[3/5] Installing Node.js dependencies...${NC}"
if pnpm install; then
    echo -e "${GRAY}  [OK] Node.js dependencies installed${NC}"
else
    echo -e "${RED}  [!] Failed to install Node.js dependencies${NC}"
    exit 1
fi
echo ""

# 5. Install Python dependencies
echo -e "${GREEN}[4/5] Installing Python dependencies...${NC}"

# Use python3 explicitly on macOS
PYTHON_CMD=python3

if [[ "$IS_APPLE_SILICON" == true ]]; then
    echo -e "${YELLOW}  [i] Configuring for Apple Silicon...${NC}"

    # For Apple Silicon, PyTorch with MPS support
    if [[ "$USE_GPU" == true ]]; then
        echo -e "${YELLOW}  [i] Installing PyTorch with MPS (Metal) support...${NC}"
        $PYTHON_CMD -m pip install torch torchvision
    else
        $PYTHON_CMD -m pip install torch torchvision
    fi

    # Install other dependencies
    $PYTHON_CMD -m pip install -r requirements.txt --no-deps
    echo -e "${GRAY}  [OK] Python dependencies installed (Apple Silicon optimized)${NC}"

elif [[ "$USE_GPU" == true ]]; then
    echo -e "${YELLOW}  [i] Installing with CUDA support...${NC}"
    $PYTHON_CMD -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    $PYTHON_CMD -m pip install faiss-gpu
    $PYTHON_CMD -m pip install -r requirements.txt --no-deps
    echo -e "${GRAY}  [OK] Python dependencies installed (GPU)${NC}"
else
    $PYTHON_CMD -m pip install -r requirements.txt
    echo -e "${GRAY}  [OK] Python dependencies installed${NC}"
fi
echo ""

# 6. Check/Download data and artifacts
if [[ "$SKIP_DATA" != true ]]; then
    echo -e "${GREEN}[5/5] Checking data and artifacts...${NC}"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DATA_PATH="$SCRIPT_DIR/../../data/curated/one-piece.jsonl"
    INDEX_PATH="$SCRIPT_DIR/../../artifacts/faiss/one-piece-dinov2/index.faiss"

    if [[ -f "$DATA_PATH" ]]; then
        echo -e "${GRAY}  [OK] Data found: $DATA_PATH${NC}"
    else
        echo -e "${YELLOW}  [!] Data not found. You need to either:${NC}"
        echo -e "${YELLOW}      1. Download pre-built artifacts (recommended)${NC}"
        echo -e "${YELLOW}      2. Run the data pipeline manually${NC}"
        echo ""
        echo -e "${YELLOW}  To download artifacts (if available):${NC}"
        echo -e "${YELLOW}    pnpm update:sync${NC}"
        echo ""
        echo -e "${YELLOW}  To build pipeline from scratch:${NC}"
        echo -e "${YELLOW}    See docs/guides/LOCAL_DEVELOPMENT.md${NC}"
    fi

    if [[ -f "$INDEX_PATH" ]]; then
        echo -e "${GRAY}  [OK] FAISS index found: $INDEX_PATH${NC}"
    else
        echo -e "${YELLOW}  [!] FAISS index not found${NC}"
    fi
    echo ""
fi

# Success message
echo -e "${CYAN}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${CYAN}================================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${NC}  1. If data/artifacts are missing, download or build them:${NC}"
echo -e "${GRAY}     pnpm update:sync${NC}"
echo ""
echo -e "${NC}  2. Build and run the desktop app:${NC}"
echo -e "${GRAY}     cd apps/desktop${NC}"
echo -e "${GRAY}     pnpm build:dev${NC}"
echo -e "${GRAY}     pnpm start${NC}"
echo ""
echo -e "${CYAN}For detailed documentation, see:${NC}"
echo -e "${NC}  - README.md - Overview and quick start${NC}"
echo -e "${NC}  - docs/guides/LOCAL_DEVELOPMENT.md - Development guide${NC}"
echo -e "${NC}  - apps/desktop/README.md - Desktop app specifics${NC}"
echo ""

if [[ "$IS_APPLE_SILICON" == true ]]; then
    echo -e "${YELLOW}Note: PyTorch will use Metal Performance Shaders (MPS) for GPU acceleration.${NC}"
    echo ""
fi
