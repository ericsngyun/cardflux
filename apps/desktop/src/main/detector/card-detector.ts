import * as cv from 'opencv4nodejs';
import { BackgroundModel } from './background-model';

export interface DetectedCard {
  boundingBox: cv.Rect;
  contour: cv.Contour;
  corners: cv.Point2[];
  confidence: number;
  warpedImage: cv.Mat;
}

export interface CardDetectorConfig {
  minArea: number;
  maxArea: number;
  aspectRatioMin: number;
  aspectRatioMax: number;
  warpedWidth: number;
  warpedHeight: number;
}

/**
 * Detects trading cards in video frames using background subtraction,
 * contour finding, and perspective transformation
 */
export class CardDetector {
  private backgroundModel: BackgroundModel;
  private config: CardDetectorConfig;

  constructor(config: Partial<CardDetectorConfig> = {}) {
    this.config = {
      minArea: 10000, // Minimum contour area (pixels)
      maxArea: 500000, // Maximum contour area (pixels)
      aspectRatioMin: 0.6, // Trading cards are roughly 2.5:3.5 = 0.71
      aspectRatioMax: 0.8,
      warpedWidth: 250, // Standard warped card size
      warpedHeight: 350,
      ...config,
    };

    this.backgroundModel = new BackgroundModel();
  }

  /**
   * Detect cards in a frame
   */
  detect(frame: cv.Mat): DetectedCard[] {
    // Apply background subtraction
    const fgMask = this.backgroundModel.apply(frame);

    // Find contours in the foreground mask
    const contours = fgMask.findContours(
      cv.RETR_EXTERNAL,
      cv.CHAIN_APPROX_SIMPLE
    );

    const detectedCards: DetectedCard[] = [];

    for (const contour of contours) {
      const area = contour.area;

      // Filter by area
      if (area < this.config.minArea || area > this.config.maxArea) {
        continue;
      }

      // Get bounding rectangle
      const boundingBox = contour.boundingRect();
      const aspectRatio = boundingBox.width / boundingBox.height;

      // Filter by aspect ratio (trading cards are portrait orientation)
      if (
        aspectRatio < this.config.aspectRatioMin ||
        aspectRatio > this.config.aspectRatioMax
      ) {
        continue;
      }

      // Approximate contour to polygon
      const peri = contour.arcLength(true);
      const approx = contour.approxPolyDP(0.02 * peri, true);

      // Check if we have a quadrilateral (4 corners)
      if (approx.length !== 4) {
        continue;
      }

      // Extract corner points
      const corners = approx.map((pt: cv.Point2) => new cv.Point2(pt.x, pt.y));

      // Order corners (top-left, top-right, bottom-right, bottom-left)
      const orderedCorners = this.orderCorners(corners);

      // Perform perspective transform to get warped card image
      const warpedImage = this.warpPerspective(frame, orderedCorners);

      // Calculate confidence based on contour regularity
      const confidence = this.calculateConfidence(contour, approx);

      detectedCards.push({
        boundingBox,
        contour,
        corners: orderedCorners,
        confidence,
        warpedImage,
      });
    }

    // Sort by confidence (highest first)
    detectedCards.sort((a, b) => b.confidence - a.confidence);

    return detectedCards;
  }

  /**
   * Order corners in clockwise order starting from top-left
   */
  private orderCorners(corners: cv.Point2[]): cv.Point2[] {
    // Calculate centroid
    const cx = corners.reduce((sum, p) => sum + p.x, 0) / corners.length;
    const cy = corners.reduce((sum, p) => sum + p.y, 0) / corners.length;

    // Sort by angle from centroid
    const sorted = corners.sort((a, b) => {
      const angleA = Math.atan2(a.y - cy, a.x - cx);
      const angleB = Math.atan2(b.y - cy, b.x - cx);
      return angleA - angleB;
    });

    // Find top-left corner (smallest x + y)
    let minIdx = 0;
    let minSum = sorted[0].x + sorted[0].y;

    for (let i = 1; i < sorted.length; i++) {
      const sum = sorted[i].x + sorted[i].y;
      if (sum < minSum) {
        minSum = sum;
        minIdx = i;
      }
    }

    // Reorder starting from top-left
    const ordered = [
      ...sorted.slice(minIdx),
      ...sorted.slice(0, minIdx),
    ];

    return ordered;
  }

  /**
   * Warp perspective to get frontal view of card
   */
  private warpPerspective(frame: cv.Mat, corners: cv.Point2[]): cv.Mat {
    const { warpedWidth, warpedHeight } = this.config;

    // Destination points for warped image
    const dstPoints = [
      new cv.Point2(0, 0),
      new cv.Point2(warpedWidth - 1, 0),
      new cv.Point2(warpedWidth - 1, warpedHeight - 1),
      new cv.Point2(0, warpedHeight - 1),
    ];

    // Get perspective transform matrix
    const M = cv.getPerspectiveTransform(corners, dstPoints);

    // Apply transform
    const warped = frame.warpPerspective(M, new cv.Size(warpedWidth, warpedHeight));

    return warped;
  }

  /**
   * Calculate detection confidence based on contour properties
   */
  private calculateConfidence(contour: cv.Contour, approx: cv.Point2[]): number {
    // Factors that contribute to confidence:
    // 1. How close the contour is to a rectangle (convexity)
    const hull = contour.convexHull();
    const hullArea = cv.contourArea(hull);
    const contourArea = contour.area;
    const convexityScore = contourArea / hullArea;

    // 2. How square the corners are (should be close to 90 degrees)
    const angleScore = this.calculateAngleScore(approx);

    // 3. How smooth/stable the contour is
    const smoothnessScore = this.calculateSmoothnessScore(contour);

    // Weighted average
    const confidence =
      0.4 * convexityScore +
      0.4 * angleScore +
      0.2 * smoothnessScore;

    return Math.min(Math.max(confidence, 0), 1);
  }

  /**
   * Calculate score based on corner angles (should be close to 90 degrees)
   */
  private calculateAngleScore(corners: cv.Point2[]): number {
    if (corners.length !== 4) return 0;

    let totalDiff = 0;

    for (let i = 0; i < 4; i++) {
      const p1 = corners[i];
      const p2 = corners[(i + 1) % 4];
      const p3 = corners[(i + 2) % 4];

      const angle = this.calculateAngle(p1, p2, p3);
      const diff = Math.abs(angle - 90);
      totalDiff += diff;
    }

    // Lower diff is better, normalize to 0-1
    const avgDiff = totalDiff / 4;
    return Math.max(0, 1 - avgDiff / 45); // Perfect at 0 diff, 0 at 45 degrees off
  }

  /**
   * Calculate angle between three points (in degrees)
   */
  private calculateAngle(p1: cv.Point2, p2: cv.Point2, p3: cv.Point2): number {
    const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
    const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };

    const dot = v1.x * v2.x + v1.y * v2.y;
    const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
    const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y);

    const cos = dot / (mag1 * mag2);
    const angle = Math.acos(Math.max(-1, Math.min(1, cos)));

    return (angle * 180) / Math.PI;
  }

  /**
   * Calculate smoothness score based on contour perimeter vs area
   */
  private calculateSmoothnessScore(contour: cv.Contour): number {
    const area = contour.area;
    const perimeter = contour.arcLength(true);

    // For a rectangle: perimeter^2 / area should be close to 16
    const ratio = (perimeter * perimeter) / area;
    const idealRatio = 16;

    const diff = Math.abs(ratio - idealRatio);
    return Math.max(0, 1 - diff / idealRatio);
  }

  /**
   * Check if background model is ready
   */
  isReady(): boolean {
    return this.backgroundModel.isWarmedUp();
  }

  /**
   * Get warmup progress
   */
  getWarmupProgress(): number {
    return this.backgroundModel.getWarmupProgress();
  }

  /**
   * Reset detector
   */
  reset(): void {
    this.backgroundModel.reset();
  }
}
