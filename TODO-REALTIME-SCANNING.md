# Realtime Scanning Implementation TODO

## Context
Implementing realtime card scanning capabilities for the CardFlux application.

## Completed Tasks
- [x] Research existing codebase structure
- [x] Identify camera/scanning components
- [x] Create RealtimeScanner orchestration class
- [x] Implement StreamManager for camera access
- [x] Implement CardDetector with background subtraction
- [x] Create IPC handlers for main-renderer communication
- [x] Implement secure preload script with contextBridge
- [x] Build React-based renderer UI
- [x] Add TypeScript strict type checking
- [x] Configure Webpack build system

## Remaining Tasks

### 1. Core Scanning Infrastructure
- [x] Set up camera access and permissions handling (macOS in index.ts:12-31)
- [x] Implement video stream processing (StreamManager in camera/stream-manager.ts)
- [x] Create frame capture mechanism for card detection (StreamManager frame events)

### 2. Card Detection Logic
- [x] Integrate or implement card detection algorithm (CardDetector using MOG2 background subtraction)
- [x] Add edge detection for card boundaries (Contour detection in card-detector.ts:51-56)
- [x] Implement perspective correction for skewed cards (warpPerspective in card-detector.ts:153-171)
- [x] Add card orientation detection (Corner ordering in card-detector.ts:117-148)

### 3. OCR/Recognition Integration
- [ ] Choose and integrate OCR library (Tesseract, cloud API, or custom)
- [ ] Implement card text extraction
- [ ] Add card number validation
- [ ] Implement card type detection (credit, debit, ID, etc.)

### 4. Real-time Processing
- [x] Optimize frame processing rate (Configurable FPS in StreamManager)
- [x] Add confidence thresholds for detection (detectionThreshold & verificationThreshold in RealtimeScanner)
- [x] Implement feedback UI (highlighting detected card) (DetectionOverlay component)
- [x] Add auto-capture when card is stable and detected (Stability checking with IoU in realtime-scanner.ts:161-210)

### 5. UI/UX Components
- [x] Create scanning view component (ScannerView.tsx)
- [x] Add camera preview overlay (Camera preview in ScannerView)
- [x] Implement guide frame for card placement (Guide frame with corners in styles.css)
- [x] Add feedback indicators (success, error, processing) (Status indicators, error banner)
- [ ] Create manual capture fallback

### 6. Data Flow
- [ ] Connect scanned data to form fields
- [ ] Implement data validation
- [ ] Add error handling for scan failures
- [ ] Create retry mechanisms

### 7. Testing & Optimization
- [ ] Test with various card types
- [ ] Test in different lighting conditions
- [ ] Optimize performance on target devices
- [ ] Add unit tests for detection logic
- [ ] Add integration tests for scanning flow

### 8. Platform-Specific Considerations
- [x] Handle macOS camera permissions (systemPreferences API in index.ts:12-31)
- [ ] Handle Windows camera permissions (Currently returns true, needs implementation)
- [ ] Handle Linux camera permissions (Currently returns true, needs implementation)
- [ ] Test on different device sizes/cameras
- [ ] Ensure accessibility compliance

## Technical Decisions Needed
- [ ] Choose OCR solution (client-side vs cloud)
- [ ] Decide on ML model if using custom detection
- [ ] Determine minimum supported device specs
- [ ] Define privacy/security requirements for card data

## Implementation Notes

### Architecture Decisions Made:
- **Camera Access**: Using Electron's systemPreferences for macOS, opencv4nodejs VideoCapture for video streaming
- **Computer Vision**: opencv4nodejs with MOG2 background subtraction for card detection
- **Security**: Implemented Electron security best practices (contextIsolation, preload scripts, no nodeIntegration)
- **State Management**: Event-driven architecture with EventEmitter for scanner components
- **Build System**: Webpack for bundling, TypeScript with strict mode

### Current Limitations:
- **OpenCV Dependency**: Requires CMake installation - marked as optional dependency
- **Platform Support**: macOS permissions implemented, Windows/Linux need testing
- **OCR Integration**: tesseract.js available but not yet integrated
- **Live Camera Preview**: Currently placeholder - needs video stream rendering

### Next Steps for Production:
1. Integrate actual camera preview in renderer (canvas or video element)
2. Implement OCR for card text recognition
3. Connect to card database/search functionality
4. Add comprehensive error handling and user feedback
5. Performance testing and optimization
6. Cross-platform testing (Windows/Linux/macOS)
7. Implement manual capture fallback
8. Add unit and integration tests
9. Consider PCI compliance if handling payment cards
