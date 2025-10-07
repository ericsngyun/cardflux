# CardFlux Onboarding Guide
## Welcome, Junior Engineer! 👋

Hi! I'm your senior engineer on the CardFlux project. This guide will walk you through everything you need to know about our codebase, from the big picture down to implementation details. Think of this as your technical mentor in document form.

---

## Table of Contents
1. [What is CardFlux?](#what-is-cardflux)
2. [The Big Picture: How Everything Fits Together](#the-big-picture)
3. [Your Development Environment Setup](#development-environment-setup)
4. [Understanding the Data Pipeline](#understanding-the-data-pipeline)
5. [The Desktop Application Deep Dive](#desktop-application-deep-dive)
6. [Common Tasks & Workflows](#common-tasks--workflows)
7. [Debugging Tips & Tricks](#debugging-tips--tricks)
8. [Best Practices We Follow](#best-practices)
9. [What to Do When You're Stuck](#when-youre-stuck)

---

## What is CardFlux?

CardFlux is an **offline-first trading card game (TCG) scanner** that uses computer vision and machine learning to identify trading cards in real-time. Think of it like Shazam, but for Magic: The Gathering, Pokémon, Yu-Gi-Oh!, and other card games.

### The Problem We're Solving
- Card collectors have thousands of cards and manually cataloging them is tedious
- Existing solutions require internet connectivity
- Price checking requires visiting multiple websites
- No unified solution across different card games

### Our Solution
1. **Offline scanning**: Point your camera at a card, we identify it instantly
2. **Pre-built database**: All card data and images downloaded once
3. **Fast search**: Using FAISS (Facebook AI Similarity Search) for millisecond lookups
4. **Cross-platform**: Desktop app built with Electron

---

## The Big Picture

Let me show you how everything connects. CardFlux has **two main parts**:

### Part 1: The Data Pipeline (Runs Once to Build Database)
```
Internet APIs → Download Data → Process Images → Create Search Index → Package for Distribution
```

### Part 2: The Desktop App (What Users Run)
```
Camera Feed → Detect Card → Match Against Index → Display Results
```

Here's a visual flow:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE (Offline)                       │
│                     Runs on our build servers                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. INGEST    │───►│ 2. EMBED     │───►│ 3. INDEX     │───►│ 4. PUBLISH   │
│              │    │              │    │              │    │              │
│ Download card│    │ Create ML    │    │ Build FAISS  │    │ Generate     │
│ data from    │    │ embeddings   │    │ search index │    │ manifests    │
│ Scryfall,    │    │ using CLIP   │    │              │    │              │
│ Pokémon API  │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                    │                    │
       │                   │                    │                    │
       ▼                   ▼                    ▼                    ▼
   Raw JSON         embeddings.npy        index.faiss          manifest.json
   images/              (512-D)          metadata.jsonl         checksums


┌─────────────────────────────────────────────────────────────────────┐
│                     DESKTOP APP (Online)                             │
│                     Runs on user's computer                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Camera      │───►│  Detector    │───►│  Matcher     │───►│   Display    │
│              │    │              │    │              │    │              │
│ Capture      │    │ Find card    │    │ Search FAISS │    │ Show card    │
│ video frames │    │ boundaries   │    │ index        │    │ name, price  │
│ (OpenCV)     │    │ (MOG2)       │    │              │    │ set, rarity  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

**Key Insight**: We separate "building the database" from "using the database". This lets the app work offline after initial download.

---

## Development Environment Setup

### Prerequisites
You'll need these tools installed:

#### Required for Basic Development
```bash
# Node.js (we use v20+)
node --version  # Should be >= 20.0.0

# pnpm (package manager - faster than npm)
pnpm --version  # Should be >= 9.0.0

# Python (for ML pipeline)
python --version  # Should be >= 3.8
```

#### Required for Desktop App (OpenCV)
```bash
# CMake (for building OpenCV)
cmake --version  # Should be >= 3.1

# Visual Studio Build Tools (Windows only)
# Download from: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"
```

#### Required for ML Pipeline
```bash
# Install Python dependencies
pip install torch transformers faiss-cpu pillow numpy tqdm
```

### Installation Steps

1. **Clone and Install**
```bash
git clone <your-repo-url> cardflux
cd cardflux
pnpm install  # Installs all workspace dependencies
```

2. **Project Structure** (What you just cloned)
```
cardflux/
├── apps/
│   └── desktop/           # Electron desktop app
│       ├── src/
│       │   ├── main/      # Node.js backend (camera, detection)
│       │   ├── preload/   # Security bridge
│       │   └── renderer/  # React UI
│       └── package.json
│
├── packages/
│   ├── shared/            # Types used everywhere
│   │   ├── types.ts       # Card, Game interfaces
│   │   └── schemas.ts     # Validation schemas
│   └── config/            # Game configurations
│       ├── mtg.json       # Magic: The Gathering config
│       ├── pokemon.json   # Pokémon config
│       └── ...
│
├── services/
│   ├── ingest/            # Download and normalize card data
│   │   └── bin/
│   │       ├── normalize.ts      # Convert API data to our format
│   │       ├── fetch_images.ts   # Download card images
│   │       └── build_sqlite.ts   # Create metadata database
│   │
│   ├── embedder/          # Create ML embeddings (Python)
│   │   └── bin/
│   │       └── embed_cards.py    # CLIP embeddings
│   │
│   ├── indexer/           # Build FAISS search index (Python)
│   │   └── bin/
│   │       └── build_faiss.py    # Vector index
│   │
│   ├── publisher/         # Generate manifests
│   │   └── bin/
│   │       └── generate_manifests.ts
│   │
│   └── pricefeed/         # Price data integration
│       └── bin/
│           └── build_price_patch.ts
│
├── infra/                 # AWS infrastructure (CDK)
│   ├── lib/
│   │   ├── storage-stack.ts      # S3 buckets
│   │   ├── cdn-stack.ts          # CloudFront CDN
│   │   └── pipeline-stack.ts     # CI/CD pipeline
│   └── bin/
│       └── pipeline.ts
│
├── scripts/
│   └── make/
│       └── run-pipeline.mjs      # Orchestrates entire pipeline
│
├── data/                  # Generated by pipeline
│   ├── raw/              # Original API responses
│   ├── curated/          # Normalized JSONL files
│   └── images/           # Downloaded card images
│
└── artifacts/            # Pipeline outputs
    ├── faiss/            # Search indexes
    ├── metadata/         # SQLite databases
    └── manifests/        # Version manifests
```

---

## Understanding the Data Pipeline

Let me walk you through what happens when we run the pipeline. This is the "offline" part that runs on our servers.

### Step 1: Data Ingestion (`services/ingest`)

**What happens**: We fetch card data from various APIs and standardize it.

**Code**: `services/ingest/bin/normalize.ts`

```typescript
// How it works:
1. Read game config (e.g., packages/config/mtg.json)
2. Fetch data from API (e.g., Scryfall for Magic cards)
3. Normalize to our schema:
   {
     id: "card-uuid",
     game: "mtg",
     name: "Lightning Bolt",
     set: "LEA",
     rarity: "common",
     imageUrl: "https://..."
   }
4. Save to data/curated/mtg.jsonl (JSONL = JSON Lines format)
```

**Why JSONL?** Each line is a separate JSON object. This is efficient for streaming processing - we can read one card at a time without loading the entire file into memory.

**Run it**:
```bash
pnpm pipeline:normalize
```

**What you'll see**:
```
Fetching data for Magic: The Gathering...
Saved raw data to data/raw/mtg.json
Saved 25,000 normalized cards to data/curated/mtg.jsonl
```

### Step 2: Image Fetching (`services/ingest`)

**What happens**: Download card images for visual matching.

**Code**: `services/ingest/bin/fetch_images.ts`

This script:
1. Reads `data/curated/mtg.jsonl`
2. Downloads each `imageUrl`
3. Saves to `data/images/mtg/{card-id}.jpg`

**Important**: Images are large! ~25K cards × ~100KB = ~2.5GB per game

### Step 3: Embedding (`services/embedder`)

**What happens**: Convert images to 512-dimensional vectors using AI.

**Code**: `services/embedder/bin/embed_cards.py`

```python
# How CLIP works:
1. Load pretrained model (openai/clip-vit-base-patch32)
2. For each card image:
   - Read image
   - Pass through neural network
   - Get 512-number "embedding" (vector)
3. Save embeddings.npy (NumPy array format)
```

**Why embeddings?** Neural networks convert images to numbers. Similar-looking cards have similar numbers. This lets us do math to find matches!

**Example**:
```
Lightning Bolt image → [0.23, -0.45, 0.12, ..., 0.67]  (512 numbers)
                                    ↓
               Two similar cards have similar vectors:
                                    ↓
         distance(Lightning Bolt, Shock) = 0.15  (very similar)
         distance(Lightning Bolt, Forest) = 0.89  (very different)
```

**Run it**:
```bash
pnpm pipeline:embed
```

**Requirements**: This needs a GPU (CUDA) for speed, but works on CPU (slower).

### Step 4: Index Building (`services/indexer`)

**What happens**: Create a fast search index using FAISS.

**Code**: `services/indexer/bin/build_faiss.py`

```python
# FAISS (Facebook AI Similarity Search)
1. Load all embeddings (e.g., 25,000 cards × 512 dimensions)
2. Build an IndexFlatL2 (L2 = Euclidean distance)
3. Save index.faiss file
```

**Why FAISS?** It's incredibly fast. Searching 25,000 vectors takes ~1 millisecond!

**How it works internally**:
- Traditional search: Compare your query to ALL 25,000 cards sequentially
- FAISS: Uses clever algorithms (like kd-trees) to skip most comparisons
- Result: 1000× faster

**Run it**:
```bash
pnpm pipeline:index
```

### Step 5: Metadata Database (`services/ingest`)

**What happens**: Create SQLite database for card metadata.

**Code**: `services/ingest/bin/build_sqlite.ts`

```typescript
// Creates a SQLite database with:
CREATE TABLE cards (
  id TEXT PRIMARY KEY,
  game TEXT,
  name TEXT,
  set TEXT,
  rarity TEXT,
  type TEXT,
  image_path TEXT
);

CREATE INDEX idx_game ON cards(game);
CREATE INDEX idx_name ON cards(name);
```

**Why SQLite?** Fast, serverless, single-file database. Perfect for desktop apps.

### Step 6: Manifest Generation (`services/publisher`)

**What happens**: Create version manifests with checksums.

**Code**: `services/publisher/bin/generate_manifests.ts`

```typescript
// Generates manifest.json:
{
  "mtg": {
    "version": "0.1.0",
    "timestamp": "2025-01-15T10:30:00Z",
    "files": {
      "index": {
        "path": "faiss/mtg/index.faiss",
        "size": 51200000,
        "checksum": "sha256:abc123..."
      },
      "metadata": {...},
      "sqlite": {...}
    },
    "stats": {
      "totalCards": 25000,
      "dimension": 512
    }
  }
}
```

**Why manifests?** The app downloads this first to know:
1. What version of data is available
2. What files to download
3. If downloads succeeded (checksum verification)

### Running the Entire Pipeline

```bash
# One command to rule them all:
pnpm pipeline:all

# Or step by step:
pnpm pipeline:normalize      # Step 1: Download and normalize
pnpm pipeline:fetch-images   # Step 2: Download images
pnpm pipeline:metadata       # Step 3: Build SQLite
pnpm pipeline:embed          # Step 4: Create embeddings (Python)
pnpm pipeline:index          # Step 5: Build FAISS (Python)
pnpm pipeline:manifests      # Step 6: Generate manifests
pnpm pipeline:prices         # Step 7: Price data (optional)
```

**Time estimate**:
- Normalize: ~5 minutes
- Fetch images: ~2 hours (network dependent)
- Embed: ~30 minutes (GPU) or ~3 hours (CPU)
- Index: ~2 minutes
- Metadata: ~1 minute
- Manifests: ~10 seconds

**Total**: ~3-5 hours for full pipeline

---

## Desktop Application Deep Dive

Now let's talk about the app users actually run. This is the Electron desktop application.

### Electron Architecture Primer

Electron runs **three types of processes**:

```
┌─────────────────────────────────────────────────────────────┐
│                     Electron App                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐       ┌──────────────┐       ┌─────────┐ │
│  │ Main Process │◄─────►│   Preload    │◄─────►│Renderer │ │
│  │              │  IPC  │              │  IPC  │         │ │
│  │ Node.js      │       │  Bridge      │       │ Browser │ │
│  │ Full access  │       │  Security    │       │ No Node │ │
│  │              │       │              │       │         │ │
│  │ - Camera     │       │ contextBridge│       │ React   │ │
│  │ - File I/O   │       │ exposes safe │       │ UI      │ │
│  │ - OpenCV     │       │ APIs         │       │         │ │
│  └──────────────┘       └──────────────┘       └─────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Why three processes?**

1. **Main Process**: Can do dangerous things (file access, camera). Runs in Node.js.
2. **Renderer Process**: Displays UI. Runs in Chromium browser. **Cannot** access Node.js directly (security).
3. **Preload**: Acts as a secure bridge. Exposes only safe APIs to renderer.

**Security principle**: Never give the browser full Node.js access. A malicious script could read your files!

### Main Process (`apps/desktop/src/main/`)

This is the "backend" of our desktop app.

#### Entry Point: `index.ts`

```typescript
// apps/desktop/src/main/index.ts

// 1. Create window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,       // ❌ Browser can't use require()
      contextIsolation: true,        // ✅ Separate JS contexts
      preload: path.join(__dirname, '../preload/preload.js'),
    },
  });
}

// 2. Request camera permissions (macOS)
async function requestCameraPermission() {
  if (process.platform === 'darwin') {
    const status = await systemPreferences.getMediaAccessStatus('camera');
    if (status === 'not-determined') {
      return await systemPreferences.askForMediaAccess('camera');
    }
    return status === 'granted';
  }
  return true;  // Windows/Linux don't need explicit permission
}

// 3. Initialize scanner
async function initializeScanner() {
  scanner = new RealtimeScanner({
    cameraId: 0,              // Default camera
    fps: 30,                  // Process 30 frames/second
    detectionThreshold: 0.7,  // 70% confidence to show detection
    verificationThreshold: 0.8, // 80% confidence to verify
  });

  // Forward events to renderer
  scanner.on('detection', (result) => {
    mainWindow.webContents.send('scanner:detection', result);
  });
}
```

**Key concepts**:
- **IPC (Inter-Process Communication)**: How main and renderer talk
- **Event-driven**: Scanner emits events, main process forwards to renderer
- **Permissions**: macOS requires explicit camera permission

#### RealtimeScanner: `scanner/realtime-scanner.ts`

This orchestrates everything. Let me break it down:

```typescript
// apps/desktop/src/main/scanner/realtime-scanner.ts

export class RealtimeScanner extends EventEmitter {
  private streamManager: StreamManager;     // Camera
  private cardDetector: CardDetector;       // Computer vision
  private stableDetectionCount = 0;         // Stability counter

  async start() {
    this.running = true;
    this.streamManager.start();  // Start camera
  }

  private processFrame(frame: cv.Mat) {
    // 1. Detect cards in frame
    const detections = this.cardDetector.detect(frame);

    // 2. Filter by confidence
    const highConfidence = detections.filter(
      d => d.confidence >= this.config.detectionThreshold
    );

    if (highConfidence.length === 0) {
      this.emit('detection', null);  // No card found
      return;
    }

    // 3. Get best detection
    const best = highConfidence[0];

    // 4. Check stability (is detection consistent?)
    const isStable = this.isDetectionStable(best);

    // 5. Emit result
    this.emit('detection', {
      card: best,
      verified: this.stableDetectionCount >= 5
    });
  }

  // Stability checking using IoU (Intersection over Union)
  private isDetectionStable(current: DetectedCard): boolean {
    if (this.lastDetections.length === 0) {
      this.lastDetections.push(current);
      return false;
    }

    const last = this.lastDetections[this.lastDetections.length - 1];

    // Compare bounding boxes
    const similarity = this.calculateBoxSimilarity(
      current.boundingBox,
      last.boundingBox
    );

    return similarity > 0.9;  // >90% overlap = stable
  }
}
```

**Why stability checking?** Camera shake causes detections to jump around. We want 5 consecutive stable frames before verifying.

**IoU (Intersection over Union)**: Measures how much two bounding boxes overlap.

```
Box 1: ┌────────┐
       │        │
       │  ┌─────┼──┐  ← Box 2
       └──┼─────┘  │
          └────────┘

IoU = Area of overlap / Area of union
    = 0.5 (50% overlap)

If IoU > 0.9 → boxes are almost identical → stable!
```

#### StreamManager: `camera/stream-manager.ts`

Handles camera access and frame buffering.

```typescript
// apps/desktop/src/main/camera/stream-manager.ts

export class StreamManager extends EventEmitter {
  async initialize() {
    // Open camera using OpenCV
    this.capture = new cv.VideoCapture(this.config.cameraId);

    // Set resolution
    this.capture.set(cv.CAP_PROP_FRAME_WIDTH, 1280);
    this.capture.set(cv.CAP_PROP_FRAME_HEIGHT, 720);
    this.capture.set(cv.CAP_PROP_FPS, 30);
  }

  start() {
    // Capture frames at specified FPS
    const frameInterval = 1000 / this.config.fps;

    this.intervalId = setInterval(() => {
      this.captureFrame();
    }, frameInterval);
  }

  private captureFrame() {
    const mat = this.capture.read();  // Read frame from camera

    const frame = {
      mat,                            // OpenCV matrix (image data)
      timestamp: Date.now(),
      frameNumber: this.frameNumber++
    };

    // Add to buffer (keep last 3 frames)
    this.frameBuffer.push(frame);
    if (this.frameBuffer.length > 3) {
      const old = this.frameBuffer.shift();
      old.mat.release();  // ⚠️ IMPORTANT: Free memory!
    }

    // Emit for processing
    this.emit('frame', frame);
  }
}
```

**Memory management**: `cv.Mat` objects hold image data in C++ memory. We MUST call `.release()` or we'll leak memory!

#### CardDetector: `detector/card-detector.ts`

Computer vision to find cards in images.

```typescript
// apps/desktop/src/main/detector/card-detector.ts

export class CardDetector {
  private backgroundModel: BackgroundModel;  // MOG2 background subtraction

  detect(frame: cv.Mat): DetectedCard[] {
    // 1. Background subtraction
    const fgMask = this.backgroundModel.apply(frame);

    // fgMask is a binary image:
    // White pixels = foreground (card)
    // Black pixels = background (desk)

    // 2. Find contours (outlines)
    const contours = fgMask.findContours(
      cv.RETR_EXTERNAL,       // Only outer contours
      cv.CHAIN_APPROX_SIMPLE  // Compress contour points
    );

    // 3. Filter contours
    for (const contour of contours) {
      const area = contour.area;

      // Too small or too large?
      if (area < 10000 || area > 500000) continue;

      // Get bounding box
      const box = contour.boundingRect();
      const aspectRatio = box.width / box.height;

      // Trading cards are portrait (0.6-0.8 aspect ratio)
      if (aspectRatio < 0.6 || aspectRatio > 0.8) continue;

      // Approximate contour to polygon
      const approx = contour.approxPolyDP(0.02 * contour.arcLength(true), true);

      // Must be a quadrilateral (4 corners)
      if (approx.length !== 4) continue;

      // 4. Perspective transform
      const corners = this.orderCorners(approx);
      const warpedImage = this.warpPerspective(frame, corners);

      // 5. Calculate confidence
      const confidence = this.calculateConfidence(contour, approx);

      detectedCards.push({
        boundingBox: box,
        contour,
        corners,
        confidence,
        warpedImage  // Straightened card image
      });
    }

    return detectedCards.sort((a, b) => b.confidence - a.confidence);
  }
}
```

**Background subtraction**: Learns what the "background" looks like (your desk), then anything different must be "foreground" (the card).

**Perspective transform**: Takes a skewed card and straightens it:

```
Input (skewed):          Output (straight):
    ╱──────╲                 ┌──────┐
   ╱        ╲                │      │
  ╱   CARD   ╲     →→→       │ CARD │
 ╱            ╲              │      │
╱──────────────╲             └──────┘
```

This is crucial for matching - we need a canonical view of the card.

### Preload Script: `preload/preload.ts`

The security bridge.

```typescript
// apps/desktop/src/preload/preload.ts

import { contextBridge, ipcRenderer } from 'electron';

// Expose safe APIs to renderer
contextBridge.exposeInMainWorld('scanner', {
  // Start scanning
  start: () => ipcRenderer.invoke('scanner:start'),

  // Stop scanning
  stop: () => ipcRenderer.invoke('scanner:stop'),

  // Listen for detections
  onDetection: (callback) => {
    const listener = (_event, result) => callback(result);
    ipcRenderer.on('scanner:detection', listener);

    // Return cleanup function
    return () => ipcRenderer.removeListener('scanner:detection', listener);
  }
});
```

**What this does**: Creates `window.scanner` in the renderer. The renderer can call `window.scanner.start()` safely.

**Why safe?** We only expose specific functions, not all of Node.js.

### Renderer Process: `renderer/`

The React UI.

```typescript
// apps/desktop/src/renderer/app.tsx

const App = () => {
  const [detection, setDetection] = useState(null);

  useEffect(() => {
    // Listen for detections
    const cleanup = window.scanner.onDetection((result) => {
      setDetection(result);
    });

    return cleanup;  // Cleanup on unmount
  }, []);

  const handleStart = async () => {
    await window.scanner.start();
  };

  return (
    <div>
      <button onClick={handleStart}>Start Scanning</button>

      {detection && (
        <div>
          <p>Confidence: {detection.card.confidence * 100}%</p>
          {detection.verified && <p>✓ Verified!</p>}
        </div>
      )}
    </div>
  );
};
```

**React hooks**:
- `useState`: Store detection results
- `useEffect`: Setup event listeners (cleanup on unmount!)

---

## Common Tasks & Workflows

### Task 1: Adding Support for a New Card Game

Let's say you want to add support for "Flesh and Blood" TCG.

**Step 1**: Create game config

```typescript
// packages/config/src/flesh-and-blood.json
{
  "slug": "fab",
  "name": "Flesh and Blood",
  "source": {
    "type": "api",
    "url": "https://api.flesh-and-blood.com/v1/cards"
  },
  "schema": {
    "id": "unique_id",
    "name": "name",
    "set": "edition",
    "rarity": "rarity",
    "type": "type",
    "image": "images.normal"
  }
}
```

**Step 2**: Add to config index

```typescript
// packages/config/src/index.ts
import fabConfig from './flesh-and-blood.json';

export function getAllGames(): GameConfig[] {
  return [
    // ... existing games
    fabConfig as GameConfig,
  ];
}
```

**Step 3**: Run pipeline

```bash
pnpm pipeline:all
```

That's it! The pipeline will:
1. Download FAB card data
2. Fetch images
3. Create embeddings
4. Build search index
5. Generate manifest

### Task 2: Debugging Detection Issues

**Problem**: App detects cards but confidence is low.

**Solution**: Tune detection thresholds

```typescript
// apps/desktop/src/main/detector/card-detector.ts

// Try adjusting these:
this.config = {
  minArea: 8000,        // Lower = detect smaller cards
  maxArea: 600000,      // Higher = detect larger cards
  aspectRatioMin: 0.55, // Wider range
  aspectRatioMax: 0.85,
};
```

**Problem**: Too many false positives (detecting non-cards).

**Solution**: Increase confidence threshold

```typescript
// apps/desktop/src/main/index.ts
scanner = new RealtimeScanner({
  detectionThreshold: 0.8,  // Raise from 0.7 to 0.8
  verificationThreshold: 0.9,
});
```

**Problem**: Detection is jumpy/unstable.

**Solution**: Increase stability frames

```typescript
// apps/desktop/src/main/scanner/realtime-scanner.ts
this.config = {
  stabilityFrames: 10,  // Increase from 5 to 10
};
```

### Task 3: Adding a New Feature to the UI

Let's add a "capture history" feature.

**Step 1**: Add state

```typescript
// apps/desktop/src/renderer/app.tsx
const [history, setHistory] = useState([]);

useEffect(() => {
  const cleanup = window.scanner.onDetection((result) => {
    if (result?.verified) {
      setHistory(prev => [result, ...prev].slice(0, 10));  // Keep last 10
    }
  });
  return cleanup;
}, []);
```

**Step 2**: Add UI

```typescript
<div className="history">
  <h3>Recent Scans</h3>
  {history.map((item, i) => (
    <div key={i}>
      {item.card.name} - {item.timestamp}
    </div>
  ))}
</div>
```

**Step 3**: Style it

```css
/* apps/desktop/src/renderer/styles.css */
.history {
  position: fixed;
  right: 20px;
  top: 100px;
  background: rgba(0,0,0,0.8);
  padding: 1rem;
  border-radius: 8px;
}
```

---

## Debugging Tips & Tricks

### Main Process Debugging

```bash
# Add debugging to index.ts
console.log('Scanner initialized:', scanner);

# Run with DevTools
pnpm dev  # Opens Electron DevTools automatically
```

**View logs**: Check the terminal, not browser DevTools (main process runs in Node.js).

### Renderer Process Debugging

**In browser DevTools**:
```javascript
// Console tab
window.scanner  // Should show exposed API

// Test scanner manually
await window.scanner.start()
```

**React DevTools**: Install extension for Electron:
```bash
npm install -g electron-devtools-installer
```

### Python Debugging

```bash
# Add debug prints
print(f"Processing {len(embeddings)} embeddings")

# Run directly (skip pnpm)
cd services/embedder
python bin/embed_cards.py
```

### Common Errors

**Error**: `'cmake' is not recognized`

**Fix**: Install CMake:
```bash
# Windows
choco install cmake

# macOS
brew install cmake
```

**Error**: `Camera permission denied`

**Fix** (macOS):
1. System Preferences → Security & Privacy → Camera
2. Check the box next to your app

**Error**: `Module not found: opencv4nodejs`

**Fix**:
```bash
cd apps/desktop
pnpm install opencv4nodejs
```

---

## Best Practices

### 1. Memory Management

```typescript
// ❌ BAD: Memory leak
const frame = this.capture.read();
// ... use frame ...
// Forgot to release!

// ✅ GOOD: Always release
const frame = this.capture.read();
try {
  // ... use frame ...
} finally {
  frame.release();  // Always cleanup
}
```

### 2. Error Handling

```typescript
// ❌ BAD: Silent failures
async function fetchData() {
  const result = await api.get('/cards');
  return result.data;
}

// ✅ GOOD: Explicit error handling
async function fetchData() {
  try {
    const result = await api.get('/cards');
    return result.data;
  } catch (error) {
    console.error('Failed to fetch cards:', error);
    // Emit error event
    this.emit('error', error);
    throw error;  // Re-throw for caller
  }
}
```

### 3. Type Safety

```typescript
// ❌ BAD: Using any
function processCard(card: any) {
  return card.name.toUpperCase();  // Could crash if name is undefined
}

// ✅ GOOD: Proper types
interface Card {
  id: string;
  name: string;
  set?: string;  // Optional
}

function processCard(card: Card): string {
  return card.name.toUpperCase();  // TypeScript guarantees name exists
}
```

### 4. Event Cleanup

```typescript
// ❌ BAD: Memory leak (event listener never removed)
useEffect(() => {
  window.scanner.onDetection((result) => {
    setDetection(result);
  });
}, []);

// ✅ GOOD: Cleanup
useEffect(() => {
  const cleanup = window.scanner.onDetection((result) => {
    setDetection(result);
  });
  return cleanup;  // React calls this on unmount
}, []);
```

### 5. Async/Await

```typescript
// ❌ BAD: Nested promises (callback hell)
function runPipeline() {
  normalize().then(() => {
    fetchImages().then(() => {
      embed().then(() => {
        buildIndex();
      });
    });
  });
}

// ✅ GOOD: Clean async/await
async function runPipeline() {
  await normalize();
  await fetchImages();
  await embed();
  await buildIndex();
}
```

---

## When You're Stuck

### 1. Read the Error Message (Seriously!)

Error messages tell you:
- **What** went wrong
- **Where** it happened (file:line)
- **Why** it happened (sometimes)

```
Error: Camera not initialized. Call initialize() first.
    at StreamManager.start (stream-manager.ts:74)
```

This tells you:
- **What**: Camera not initialized
- **Where**: `stream-manager.ts`, line 74
- **Why**: You need to call `initialize()` first

### 2. Use the Debugger

**VS Code**:
1. Set breakpoint (click left of line number)
2. Press F5 (Run → Start Debugging)
3. Code pauses at breakpoint
4. Inspect variables, step through code

### 3. Console.log is Your Friend

```typescript
console.log('Detection:', detection);
console.log('Confidence:', detection?.confidence);
console.log('Type:', typeof detection);
```

### 4. Check the Docs

- **Electron**: https://www.electronjs.org/docs
- **OpenCV**: https://docs.opencv.org/
- **React**: https://react.dev/
- **FAISS**: https://github.com/facebookresearch/faiss/wiki

### 5. Ask for Help

When asking questions, include:
1. What you're trying to do
2. What you expected to happen
3. What actually happened (error message)
4. Code snippet (minimal example)
5. What you've tried

**Good question**:
> I'm trying to start the scanner but getting "Camera not initialized" error. I'm calling `scanner.start()` in `index.ts:115`. I tried adding `await scanner.initialize()` before it but still getting the error. Here's my code: ...

**Bad question**:
> Scanner doesn't work, help!

### 6. Rubber Duck Debugging

Explain your code to a rubber duck (or colleague, or yourself). Often, explaining forces you to understand the problem, and you solve it yourself!

---

## Next Steps

You're ready to start coding! Here's what I recommend:

### Week 1: Get Familiar
- [ ] Set up development environment
- [ ] Run the pipeline end-to-end
- [ ] Build and run the desktop app
- [ ] Make a small UI change (change a color, add a button)

### Week 2: Make a Contribution
- [ ] Fix a bug from the issue tracker
- [ ] Add a new feature (start small!)
- [ ] Write tests for your code
- [ ] Submit a pull request

### Week 3: Dive Deeper
- [ ] Read the OpenCV documentation
- [ ] Understand the FAISS indexing in detail
- [ ] Optimize performance (profile, find bottlenecks)
- [ ] Add telemetry/analytics

### Resources
- **ARCHITECTURE.md**: System design overview
- **TODO-REALTIME-SCANNING.md**: Feature implementation checklist
- **apps/desktop/README.md**: Desktop app setup
- **Code comments**: I've added detailed comments throughout

---

## Final Words

Welcome to the team! 🎉

Building CardFlux is a challenging but rewarding project. You'll learn:
- **Computer vision**: Object detection, image processing
- **Machine learning**: Neural networks, embeddings, similarity search
- **Desktop development**: Electron, multi-process architecture
- **Full-stack skills**: TypeScript, Python, React, AWS

Don't be afraid to:
- Ask questions (there are no stupid questions!)
- Make mistakes (that's how we learn)
- Experiment (we have version control!)
- Suggest improvements (fresh eyes spot things we miss)

Remember: **Every expert was once a beginner.** The fact that you're reading this guide shows you're on the right path.

Happy coding! 🚀

---

*Questions? Reach out to your senior engineer or team lead.*
*Found an error in this guide? Submit a PR to fix it!*
