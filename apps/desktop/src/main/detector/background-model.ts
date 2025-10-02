import * as cv from 'opencv4nodejs';

export interface BackgroundModelConfig {
  learningRate: number;
  history: number;
  varThreshold: number;
  detectShadows: boolean;
}

/**
 * Background subtraction model for detecting moving objects (cards)
 * Uses MOG2 (Mixture of Gaussians) background subtraction
 */
export class BackgroundModel {
  private model: cv.BackgroundSubtractorMOG2;
  private config: BackgroundModelConfig;
  private frameCount = 0;
  private readonly WARMUP_FRAMES = 30; // Number of frames to learn background

  constructor(config: Partial<BackgroundModelConfig> = {}) {
    this.config = {
      learningRate: 0.001,
      history: 500,
      varThreshold: 16,
      detectShadows: true,
      ...config,
    };

    this.model = new cv.BackgroundSubtractorMOG2(
      this.config.history,
      this.config.varThreshold,
      this.config.detectShadows
    );
  }

  /**
   * Apply background subtraction to a frame
   * Returns a binary mask of foreground objects
   */
  apply(frame: cv.Mat): cv.Mat {
    this.frameCount++;

    // Use higher learning rate during warmup to quickly learn background
    const learningRate =
      this.frameCount < this.WARMUP_FRAMES ? 0.1 : this.config.learningRate;

    const fgMask = this.model.apply(frame, learningRate);

    // Post-process mask to reduce noise
    return this.postProcessMask(fgMask);
  }

  /**
   * Post-process foreground mask to reduce noise
   */
  private postProcessMask(mask: cv.Mat): cv.Mat {
    // Morphological operations to clean up mask
    const kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, new cv.Size(5, 5));

    // Remove small noise with opening
    let processed = mask.morphologyEx(cv.MORPH_OPEN, kernel);

    // Close small holes with closing
    processed = processed.morphologyEx(cv.MORPH_CLOSE, kernel);

    // Dilate slightly to ensure card edges are detected
    processed = processed.dilate(kernel, new cv.Point2(-1, -1), 1);

    return processed;
  }

  /**
   * Check if background model is warmed up
   */
  isWarmedUp(): boolean {
    return this.frameCount >= this.WARMUP_FRAMES;
  }

  /**
   * Get current frame count
   */
  getFrameCount(): number {
    return this.frameCount;
  }

  /**
   * Reset the background model
   */
  reset(): void {
    this.frameCount = 0;
    this.model = new cv.BackgroundSubtractorMOG2(
      this.config.history,
      this.config.varThreshold,
      this.config.detectShadows
    );
  }

  /**
   * Get warmup progress (0-1)
   */
  getWarmupProgress(): number {
    return Math.min(this.frameCount / this.WARMUP_FRAMES, 1.0);
  }
}
