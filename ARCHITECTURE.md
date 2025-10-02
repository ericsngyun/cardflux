# CardFlux Architecture

## Project Structure

```
cardflux/
├── apps/
│   └── desktop/              # Electron desktop application
│       ├── src/
│       │   ├── main/        # Electron main process
│       │   ├── preload/     # Preload scripts (security bridge)
│       │   └── renderer/    # React UI
│       └── package.json
├── packages/
│   ├── shared/              # Shared types and utilities
│   ├── config/              # Game-specific configurations
│   └── ...
├── services/
│   ├── ingest/              # Data ingestion and normalization
│   ├── embedder/            # Card image embeddings (Python)
│   ├── indexer/             # FAISS index building (Python)
│   ├── publisher/           # Manifest generation
│   └── pricefeed/           # Price data integration
└── infra/                   # AWS CDK infrastructure
```

## Desktop Application Architecture

### Security Model
The desktop app follows Electron security best practices:

1. **Context Isolation**: Enabled - renderer cannot access Node.js APIs directly
2. **Node Integration**: Disabled in renderer
3. **Sandbox**: Disabled for main process (required for native modules)
4. **Preload Scripts**: Use `contextBridge` to expose safe IPC APIs

### Process Communication

```
┌─────────────────┐         ┌──────────────┐         ┌──────────────┐
│  Renderer       │  IPC    │   Preload    │  IPC    │     Main     │
│  (React UI)     │◄───────►│  (Bridge)    │◄───────►│  (Node.js)   │
└─────────────────┘         └──────────────┘         └──────────────┘
      │                                                      │
      │ window.scanner.start()                             │
      │────────────────────────────────────────────────────►│
      │                                                      │
      │◄─────────────────────────── scanner:detection ──────│
```

### Core Components

#### Main Process (`apps/desktop/src/main/`)

**index.ts**
- Application lifecycle management
- Window creation
- Camera permissions handling
- Scanner initialization

**scanner/realtime-scanner.ts**
- Orchestrates camera and card detection
- Implements stability checking (IoU-based)
- Event-driven result publishing
- Configurable thresholds

**camera/stream-manager.ts**
- Video capture from camera
- Frame buffering
- FPS control
- Memory management

**detector/card-detector.ts**
- Background subtraction (MOG2)
- Contour detection
- Perspective transformation
- Confidence scoring

**detector/background-model.ts**
- Gaussian Mixture Model background subtraction
- Noise reduction (morphological operations)
- Adaptive learning rate

**ipc/handlers.ts**
- IPC handler registration
- Camera device enumeration

#### Preload (`apps/desktop/src/preload/`)

**preload.ts**
- Exposes `window.scanner` API
- Exposes `window.camera` API
- Type-safe IPC communication

#### Renderer (`apps/desktop/src/renderer/`)

**app.tsx**
- Main React application
- Scanner state management
- Detection event handling

**components/ScannerView.tsx**
- Camera preview
- Guide frame
- Scanner controls

**components/DetectionOverlay.tsx**
- Bounding box visualization
- Confidence display
- Verification status

## Data Pipeline Architecture

### Offline Processing Pipeline

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  Raw Data  │───►│ Normalize  │───►│  Embed     │───►│   Index    │
│  (JSON)    │    │  (Node.js) │    │  (Python)  │    │  (FAISS)   │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
                         │                                    │
                         ▼                                    ▼
                  ┌────────────┐                      ┌────────────┐
                  │  Metadata  │                      │ Manifests  │
                  │  (SQLite)  │                      │   (JSON)   │
                  └────────────┘                      └────────────┘
```

### Real-time Scanning Pipeline

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│   Camera   │───►│  Detect    │───►│  Verify    │───►│   Match    │
│  (OpenCV)  │    │   Card     │    │  Stability │    │  Database  │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
      30 FPS          Computer         5 frames          Embedding
                      Vision           threshold          Search
```

## Technology Stack

### Desktop App
- **Electron**: Cross-platform desktop framework
- **React**: UI framework
- **TypeScript**: Type safety
- **opencv4nodejs**: Computer vision
- **tesseract.js**: OCR (optional)
- **Webpack**: Module bundling

### Backend Services
- **Node.js**: Data processing (TypeScript)
- **Python**: ML embeddings and indexing
- **SQLite**: Metadata storage
- **FAISS**: Vector similarity search

### Infrastructure
- **AWS CDK**: Infrastructure as code
- **S3**: Data storage
- **CloudFront**: CDN distribution

## Design Patterns

### Event-Driven Architecture
- Components communicate via EventEmitter
- Loose coupling between scanner components
- Easy to extend with new features

### Separation of Concerns
- Camera management separate from detection
- Detection separate from UI
- Clear boundaries between processes

### Resource Management
- Explicit memory cleanup (cv.Mat.release())
- Frame buffer size limits
- Proper cleanup on component disposal

## Best Practices Applied

1. **Security**
   - Context isolation enabled
   - No direct Node.js access from renderer
   - Safe IPC API surface via preload

2. **Type Safety**
   - Strict TypeScript configuration
   - No implicit any
   - Proper interface definitions

3. **Performance**
   - Frame buffer management
   - Efficient background subtraction
   - Stability checking to reduce false positives

4. **Error Handling**
   - Try-catch blocks in async operations
   - Error event emission
   - User-friendly error display

5. **Code Organization**
   - Modular component structure
   - Clear file naming conventions
   - Separation of concerns

## Future Enhancements

1. **OCR Integration**: Extract card text for enhanced matching
2. **ML-based Detection**: Deep learning for better card detection
3. **Cloud Sync**: Sync collection across devices
4. **Price Tracking**: Real-time price updates
5. **Collection Management**: Inventory and wishlist features
6. **Batch Scanning**: Scan multiple cards in sequence
7. **Export/Import**: Share collections
8. **Analytics**: Collection statistics and trends
