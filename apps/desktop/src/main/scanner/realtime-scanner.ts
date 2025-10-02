import { EventEmitter } from 'events';
import { StreamManager } from '../camera/stream-manager';
import { CardDetector, DetectedCard } from '../detector/card-detector';
import * as cv from 'opencv4nodejs';

export interface RealtimeScannerConfig {
  cameraId: number;
  fps: number;
  detectionThreshold: number;
  verificationThreshold: number;
  stabilityFrames?: number;
}

export interface DetectionResult {
  card: DetectedCard;
  timestamp: number;
  verified: boolean;
}

/**
 * Coordinates camera streaming and card detection for realtime scanning
 * Implements stability checking to avoid false positives
 */
export class RealtimeScanner extends EventEmitter {
  private streamManager: StreamManager;
  private cardDetector: CardDetector;
  private config: Required<RealtimeScannerConfig>;
  private running = false;
  private lastDetections: DetectedCard[] = [];
  private stableDetectionCount = 0;

  constructor(config: RealtimeScannerConfig) {
    super();

    this.config = {
      stabilityFrames: 5,
      ...config,
    };

    this.streamManager = new StreamManager({
      cameraId: config.cameraId,
      fps: config.fps,
      width: 1280,
      height: 720,
      bufferSize: 3,
    });

    this.cardDetector = new CardDetector({
      minArea: 10000,
      maxArea: 500000,
      aspectRatioMin: 0.6,
      aspectRatioMax: 0.8,
      warpedWidth: 250,
      warpedHeight: 350,
    });

    this.setupStreamHandlers();
  }

  /**
   * Setup event handlers for stream manager
   */
  private setupStreamHandlers(): void {
    this.streamManager.on('frame', (frame) => {
      this.processFrame(frame.mat);
    });

    this.streamManager.on('error', (error) => {
      this.emit('error', error);
    });

    this.streamManager.on('initialized', () => {
      this.emit('initialized');
    });

    this.streamManager.on('started', () => {
      this.emit('started');
    });

    this.streamManager.on('stopped', () => {
      this.emit('stopped');
    });
  }

  /**
   * Initialize the scanner (camera and detector)
   */
  async initialize(): Promise<void> {
    try {
      await this.streamManager.initialize();
      console.log('RealtimeScanner initialized successfully');
    } catch (error) {
      console.error('Failed to initialize RealtimeScanner:', error);
      throw error;
    }
  }

  /**
   * Start the realtime scanning process
   */
  async start(): Promise<void> {
    if (this.running) {
      console.warn('RealtimeScanner already running');
      return;
    }

    this.running = true;
    this.streamManager.start();
    console.log('RealtimeScanner started');
  }

  /**
   * Stop the realtime scanning process
   */
  async stop(): Promise<void> {
    if (!this.running) {
      return;
    }

    this.running = false;
    this.streamManager.stop();
    this.lastDetections = [];
    this.stableDetectionCount = 0;
    console.log('RealtimeScanner stopped');
  }

  /**
   * Process a single frame for card detection
   */
  private processFrame(frame: cv.Mat): void {
    if (!this.running) {
      return;
    }

    try {
      // Detect cards in the frame
      const detections = this.cardDetector.detect(frame);

      // Filter by confidence threshold
      const highConfidenceDetections = detections.filter(
        (d) => d.confidence >= this.config.detectionThreshold
      );

      if (highConfidenceDetections.length === 0) {
        // No detections, reset stability counter
        this.stableDetectionCount = 0;
        this.lastDetections = [];
        this.emit('detection', null);

        // Release warped images from all detections to prevent memory leak
        for (const detection of detections) {
          if (detection.warpedImage) {
            detection.warpedImage.release();
          }
        }

        return;
      }

      // Get the best detection (highest confidence)
      const bestDetection = highConfidenceDetections[0];

      // Check if detection is stable (similar to previous frames)
      const isStable = this.isDetectionStable(bestDetection);

      if (isStable) {
        this.stableDetectionCount++;
      } else {
        this.stableDetectionCount = 1;
        this.lastDetections = [bestDetection];
      }

      // Clone the warped image before emitting (original will be released)
      // This prevents memory leak when frame is released by StreamManager
      const warpedClone = bestDetection.warpedImage.clone();

      // Emit detection result with cloned image
      const result: DetectionResult = {
        card: {
          ...bestDetection,
          warpedImage: warpedClone,
        },
        timestamp: Date.now(),
        verified: this.stableDetectionCount >= this.config.stabilityFrames,
      };

      this.emit('detection', result);

      // If detection is verified (stable), emit verified event
      if (result.verified && bestDetection.confidence >= this.config.verificationThreshold) {
        this.emit('verified', result);
        console.log(`Card verified with confidence: ${bestDetection.confidence.toFixed(2)}`);
      }

      // Release all warped images from detections (we've cloned the one we need)
      for (const detection of detections) {
        if (detection.warpedImage) {
          detection.warpedImage.release();
        }
      }

    } catch (error) {
      console.error('Error processing frame:', error);
      this.emit('error', error);
    }
  }

  /**
   * Check if current detection is stable compared to previous detections
   */
  private isDetectionStable(current: DetectedCard): boolean {
    if (this.lastDetections.length === 0) {
      this.lastDetections.push(current);
      return false;
    }

    const last = this.lastDetections[this.lastDetections.length - 1];

    // Compare bounding boxes
    const boxSimilarity = this.calculateBoxSimilarity(
      current.boundingBox,
      last.boundingBox
    );

    // Consider stable if position is similar (>90% overlap)
    const isStable = boxSimilarity > 0.9;

    if (isStable) {
      // Keep only recent detections
      if (this.lastDetections.length >= this.config.stabilityFrames) {
        this.lastDetections.shift();
      }
      this.lastDetections.push(current);
    }

    return isStable;
  }

  /**
   * Calculate similarity between two bounding boxes using IoU (Intersection over Union)
   */
  private calculateBoxSimilarity(box1: cv.Rect, box2: cv.Rect): number {
    // Calculate intersection
    const x1 = Math.max(box1.x, box2.x);
    const y1 = Math.max(box1.y, box2.y);
    const x2 = Math.min(box1.x + box1.width, box2.x + box2.width);
    const y2 = Math.min(box1.y + box1.height, box2.y + box2.height);

    const intersectionWidth = Math.max(0, x2 - x1);
    const intersectionHeight = Math.max(0, y2 - y1);
    const intersectionArea = intersectionWidth * intersectionHeight;

    // Calculate union
    const box1Area = box1.width * box1.height;
    const box2Area = box2.width * box2.height;
    const unionArea = box1Area + box2Area - intersectionArea;

    // Return IoU
    return unionArea > 0 ? intersectionArea / unionArea : 0;
  }

  /**
   * Check if scanner is running
   */
  isRunning(): boolean {
    return this.running;
  }

  /**
   * Get detector warmup status
   */
  isReady(): boolean {
    return this.cardDetector.isReady();
  }

  /**
   * Get warmup progress
   */
  getWarmupProgress(): number {
    return this.cardDetector.getWarmupProgress();
  }

  /**
   * Get camera info
   */
  getCameraInfo() {
    return this.streamManager.getCameraInfo();
  }

  /**
   * Clean up resources and release memory
   */
  async dispose(): Promise<void> {
    await this.stop();

    // Release any stored detection images
    for (const detection of this.lastDetections) {
      if (detection.warpedImage) {
        detection.warpedImage.release();
      }
    }
    this.lastDetections = [];

    await this.streamManager.dispose();
    console.log('RealtimeScanner disposed');
  }
}
