#!/bin/bash
# CardFlux Desktop Setup Script for Linux
# Automates setup of CardFlux desktop scanner on Ubuntu/Debian and Fedora/RHEL

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
echo -e "${CYAN}CardFlux Desktop Setup (Linux)${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    echo -e "${GRAY}[i] Detected: $PRETTY_NAME${NC}"
else
    echo -e "${RED}[!] Cannot detect Linux distribution${NC}"
    exit 1
fi
echo ""

# Set package manager commands
case $OS in
    ubuntu|debian|pop|linuxmint)
        PKG_MANAGER="apt-get"
        PKG_INSTALL="sudo apt-get install -y"
        PKG_UPDATE="sudo apt-get update"
        ;;
    fedora|rhel|centos|rocky|almalinux)
        PKG_MANAGER="dnf"
        PKG_INSTALL="sudo dnf install -y"
        PKG_UPDATE="sudo dnf check-update || true"
        ;;
    arch|manjaro)
        PKG_MANAGER="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
        ;;
    *)
        echo -e "${YELLOW}[!] Unsupported distribution: $OS${NC}"
        echo -e "${YELLOW}    Please install dependencies manually.${NC}"
        PKG_MANAGER="unknown"
        ;;
esac

# 1. Update package lists
if [[ "$PKG_MANAGER" != "unknown" ]]; then
    echo -e "${GREEN}[0/6] Updating package lists...${NC}"
    $PKG_UPDATE
    echo -e "${GRAY}  [OK] Package lists updated${NC}"
    echo ""
fi

# 2. Install system dependencies
echo -e "${GREEN}[1/6] Installing system dependencies...${NC}"

case $OS in
    ubuntu|debian|pop|linuxmint)
        $PKG_INSTALL build-essential curl git cmake
        $PKG_INSTALL libsm6 libxext6 libxrender-dev libgomp1  # OpenCV deps
        $PKG_INSTALL libglib2.0-0 libgl1-mesa-glx  # Additional deps
        ;;
    fedora|rhel|centos|rocky|almalinux)
        $PKG_INSTALL gcc gcc-c++ make curl git cmake
        $PKG_INSTALL libSM libXext libXrender gomp  # OpenCV deps
        ;;
    arch|manjaro)
        $PKG_INSTALL base-devel curl git cmake
        $PKG_INSTALL libsm libxext libxrender  # OpenCV deps
        ;;
esac

echo -e "${GRAY}  [OK] System dependencies installed${NC}"
echo ""

# 3. Check/Install Node.js and pnpm
if [[ "$SKIP_NODE" != true ]]; then
    echo -e "${GREEN}[2/6] Checking Node.js and pnpm...${NC}"

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GRAY}  [OK] Node.js $NODE_VERSION${NC}"
    else
        echo -e "${YELLOW}  [!] Node.js not found. Installing via NodeSource...${NC}"

        case $OS in
            ubuntu|debian|pop|linuxmint)
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                $PKG_INSTALL nodejs
                ;;
            fedora|rhel|centos|rocky|almalinux)
                curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                $PKG_INSTALL nodejs
                ;;
            arch|manjaro)
                $PKG_INSTALL nodejs npm
                ;;
        esac

        echo -e "${GRAY}  [OK] Node.js installed${NC}"
    fi

    if command -v pnpm &> /dev/null; then
        PNPM_VERSION=$(pnpm --version)
        echo -e "${GRAY}  [OK] pnpm $PNPM_VERSION${NC}"
    else
        echo -e "${YELLOW}  [!] pnpm not found. Installing via npm...${NC}"
        sudo npm install -g pnpm
        echo -e "${GRAY}  [OK] pnpm installed${NC}"
    fi
    echo ""
fi

# 4. Check/Install Python
if [[ "$SKIP_PYTHON" != true ]]; then
    echo -e "${GREEN}[3/6] Checking Python...${NC}"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GRAY}  [OK] $PYTHON_VERSION${NC}"

        # Check Python version
        PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo $PYTHON_VER | cut -d. -f1)
        MINOR=$(echo $PYTHON_VER | cut -d. -f2)

        if [[ "$MAJOR" -lt 3 ]] || [[ "$MAJOR" -eq 3 && "$MINOR" -lt 10 ]]; then
            echo -e "${RED}  [!] Python 3.10+ required, but found Python $PYTHON_VER${NC}"
            echo -e "${YELLOW}  Installing Python 3.11...${NC}"

            case $OS in
                ubuntu|debian|pop|linuxmint)
                    $PKG_INSTALL python3.11 python3.11-venv python3.11-dev python3-pip
                    ;;
                fedora|rhel|centos|rocky|almalinux)
                    $PKG_INSTALL python3.11 python3.11-devel python3-pip
                    ;;
                arch|manjaro)
                    $PKG_INSTALL python python-pip
                    ;;
            esac

            echo -e "${GRAY}  [OK] Python 3.11 installed${NC}"
        fi
    else
        echo -e "${YELLOW}  [!] Python not found. Installing Python 3.11...${NC}"

        case $OS in
            ubuntu|debian|pop|linuxmint)
                $PKG_INSTALL python3.11 python3.11-venv python3.11-dev python3-pip
                ;;
            fedora|rhel|centos|rocky|almalinux)
                $PKG_INSTALL python3.11 python3.11-devel python3-pip
                ;;
            arch|manjaro)
                $PKG_INSTALL python python-pip
                ;;
        esac

        echo -e "${GRAY}  [OK] Python 3.11 installed${NC}"
    fi
    echo ""
fi

# 5. Install Node.js dependencies
echo -e "${GREEN}[4/6] Installing Node.js dependencies...${NC}"
if pnpm install; then
    echo -e "${GRAY}  [OK] Node.js dependencies installed${NC}"
else
    echo -e "${RED}  [!] Failed to install Node.js dependencies${NC}"
    exit 1
fi
echo ""

# 6. Install Python dependencies
echo -e "${GREEN}[5/6] Installing Python dependencies...${NC}"

# Use python3 explicitly on Linux
PYTHON_CMD=python3

if [[ "$USE_GPU" == true ]]; then
    echo -e "${YELLOW}  [i] Installing with CUDA support...${NC}"
    echo -e "${YELLOW}  [!] Make sure CUDA 12.1+ is installed on your system${NC}"

    $PYTHON_CMD -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    $PYTHON_CMD -m pip install faiss-gpu
    $PYTHON_CMD -m pip install -r requirements.txt --no-deps
    echo -e "${GRAY}  [OK] Python dependencies installed (GPU)${NC}"
else
    $PYTHON_CMD -m pip install -r requirements.txt
    echo -e "${GRAY}  [OK] Python dependencies installed${NC}"
fi
echo ""

# 7. Check/Download data and artifacts
if [[ "$SKIP_DATA" != true ]]; then
    echo -e "${GREEN}[6/6] Checking data and artifacts...${NC}"

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

if [[ "$USE_GPU" == true ]]; then
    echo -e "${YELLOW}Note: GPU support requires NVIDIA CUDA 12.1+ to be installed.${NC}"
    echo -e "${YELLOW}      Verify installation: nvidia-smi${NC}"
    echo ""
fi
