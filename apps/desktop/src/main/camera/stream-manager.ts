import * as cv from 'opencv4nodejs';
import { EventEmitter } from 'events';

export interface StreamManagerConfig {
  cameraId: number;
  fps: number;
  width?: number;
  height?: number;
  bufferSize?: number;
}

export interface Frame {
  mat: cv.Mat;
  timestamp: number;
  frameNumber: number;
}

/**
 * Manages video stream capture and frame buffering
 * Provides a consistent frame rate and handles camera lifecycle
 */
export class StreamManager extends EventEmitter {
  private capture: cv.VideoCapture | null = null;
  private config: Required<StreamManagerConfig>;
  private running = false;
  private frameNumber = 0;
  private frameBuffer: Frame[] = [];
  private intervalId: NodeJS.Timeout | null = null;

  constructor(config: StreamManagerConfig) {
    super();
    this.config = {
      width: 1280,
      height: 720,
      bufferSize: 3,
      ...config,
    };
  }

  /**
   * Initialize the camera capture
   */
  async initialize(): Promise<void> {
    try {
      // Open camera
      this.capture = new cv.VideoCapture(this.config.cameraId);

      // Set camera properties
      if (this.config.width && this.config.height) {
        this.capture.set(cv.CAP_PROP_FRAME_WIDTH, this.config.width);
        this.capture.set(cv.CAP_PROP_FRAME_HEIGHT, this.config.height);
      }

      // Set FPS if possible
      this.capture.set(cv.CAP_PROP_FPS, this.config.fps);

      // Verify camera is opened
      if (!this.capture.isOpened()) {
        throw new Error(`Failed to open camera ${this.config.cameraId}`);
      }

      console.log('Camera initialized successfully');
      this.emit('initialized');
    } catch (error) {
      console.error('Failed to initialize camera:', error);
      throw error;
    }
  }

  /**
   * Start capturing frames
   */
  start(): void {
    if (this.running) {
      console.warn('Stream manager already running');
      return;
    }

    if (!this.capture) {
      throw new Error('Camera not initialized. Call initialize() first.');
    }

    this.running = true;
    const frameInterval = 1000 / this.config.fps;

    this.intervalId = setInterval(() => {
      this.captureFrame();
    }, frameInterval);

    this.emit('started');
    console.log(`Stream started at ${this.config.fps} FPS`);
  }

  /**
   * Stop capturing frames
   */
  stop(): void {
    if (!this.running) {
      return;
    }

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.running = false;
    this.frameBuffer = [];
    this.emit('stopped');
    console.log('Stream stopped');
  }

  /**
   * Capture a single frame
   */
  private captureFrame(): void {
    if (!this.capture || !this.running) {
      return;
    }

    try {
      const mat = this.capture.read();

      if (mat.empty) {
        console.warn('Empty frame captured');
        return;
      }

      const frame: Frame = {
        mat,
        timestamp: Date.now(),
        frameNumber: this.frameNumber++,
      };

      // Add to buffer
      this.frameBuffer.push(frame);

      // Keep buffer size limited
      if (this.frameBuffer.length > this.config.bufferSize) {
        const old = this.frameBuffer.shift();
        // Release old frame memory
        old?.mat.release();
      }

      // Emit frame event
      this.emit('frame', frame);
    } catch (error) {
      console.error('Error capturing frame:', error);
      this.emit('error', error);
    }
  }

  /**
   * Get the latest frame from buffer
   */
  getLatestFrame(): Frame | null {
    return this.frameBuffer[this.frameBuffer.length - 1] || null;
  }

  /**
   * Get all frames in buffer
   */
  getFrameBuffer(): Frame[] {
    return [...this.frameBuffer];
  }

  /**
   * Check if stream is running
   */
  isRunning(): boolean {
    return this.running;
  }

  /**
   * Get camera properties
   */
  getCameraInfo(): {
    width: number;
    height: number;
    fps: number;
  } {
    if (!this.capture) {
      throw new Error('Camera not initialized');
    }

    return {
      width: this.capture.get(cv.CAP_PROP_FRAME_WIDTH),
      height: this.capture.get(cv.CAP_PROP_FRAME_HEIGHT),
      fps: this.capture.get(cv.CAP_PROP_FPS),
    };
  }

  /**
   * Release resources
   */
  async dispose(): Promise<void> {
    this.stop();

    // Release all frames in buffer
    for (const frame of this.frameBuffer) {
      frame.mat.release();
    }
    this.frameBuffer = [];

    if (this.capture) {
      this.capture.release();
      this.capture = null;
    }

    console.log('Stream manager disposed');
  }
}
