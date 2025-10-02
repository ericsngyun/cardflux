# CardFlux Desktop - Real-time Card Scanner

## Prerequisites

### Required for OpenCV support:
- **CMake** (v3.1 or higher)
- **Python** (v2.7 or v3.x)
- C++ compiler (MSVC on Windows, GCC/Clang on Linux/Mac)

### Windows Setup:
```bash
# Install CMake via Chocolatey
choco install cmake

# Or download from: https://cmake.org/download/
```

### macOS Setup:
```bash
brew install cmake
```

### Linux Setup:
```bash
sudo apt-get install cmake
```

## Installation

```bash
# From monorepo root
pnpm install

# Or from apps/desktop
cd apps/desktop
pnpm install
```

## Development

```bash
# Type checking
pnpm typecheck

# Build
pnpm build:webpack

# Run development build
pnpm dev
```

## Architecture

### Main Process (`src/main/`)
- **index.ts**: Electron main process entry point
- **scanner/realtime-scanner.ts**: Coordinates camera and detection
- **camera/stream-manager.ts**: Video capture and frame buffering
- **detector/card-detector.ts**: Card detection using computer vision
- **detector/background-model.ts**: Background subtraction
- **ipc/handlers.ts**: IPC communication handlers

### Preload (`src/preload/`)
- **preload.ts**: Context bridge for secure IPC

### Renderer (`src/renderer/`)
- **app.tsx**: React application entry point
- **components/**: UI components

## Notes

- OpenCV is marked as optional dependency
- If CMake is not installed, the app will build without computer vision features
- TODO file tracks realtime scanning implementation progress
