/**
 * Card Detection Utilities
 * Detects trading cards in camera feed for overhead setup
 */

export interface DetectedCard {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  corners: { x: number; y: number }[];
}

export interface DetectionResult {
  card: DetectedCard | null;
  debugCanvas?: HTMLCanvasElement;
}

/**
 * Detect a trading card in an image using edge detection and contour analysis
 * Optimized for overhead camera setup with card lying flat on surface
 */
export function detectCard(
  imageData: ImageData,
  options: {
    minArea?: number;
    maxArea?: number;
    aspectRatio?: { min: number; max: number };
    debug?: boolean;
  } = {}
): DetectionResult {
  const {
    minArea = 50000, // Min pixels (approx 224x224)
    maxArea = 500000, // Max pixels (approx 707x707)
    aspectRatio = { min: 0.6, max: 0.75 }, // Trading card aspect ratio (2.5:3.5)
    debug = false,
  } = options;

  const { width, height, data } = imageData;

  // Convert to grayscale
  const gray = new Uint8ClampedArray(width * height);
  for (let i = 0; i < data.length; i += 4) {
    const avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
    gray[i / 4] = avg;
  }

  // Apply Gaussian blur to reduce noise
  const blurred = gaussianBlur(gray, width, height, 5);

  // Edge detection using Sobel operator
  const edges = sobelEdgeDetection(blurred, width, height);

  // Apply adaptive threshold
  const binary = adaptiveThreshold(edges, width, height, 15, 10);

  // Find contours
  const contours = findContours(binary, width, height);

  // Filter contours by area and aspect ratio
  let bestCard: DetectedCard | null = null;
  let bestScore = 0;

  for (const contour of contours) {
    const rect = getBoundingRect(contour);
    const area = rect.width * rect.height;

    if (area < minArea || area > maxArea) continue;

    const ratio = Math.min(rect.width, rect.height) / Math.max(rect.width, rect.height);

    if (ratio < aspectRatio.min || ratio > aspectRatio.max) continue;

    // Score based on area, aspect ratio, and position
    const areaScore = Math.min(area / maxArea, 1);
    const ratioScore = 1 - Math.abs(ratio - 0.67); // Ideal trading card ratio
    const centerScore = calculateCenterScore(rect, width, height);

    const score = areaScore * 0.4 + ratioScore * 0.4 + centerScore * 0.2;

    if (score > bestScore) {
      bestScore = score;
      bestCard = {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
        confidence: score,
        corners: contour.slice(0, 4), // Top 4 corner points
      };
    }
  }

  let debugCanvas: HTMLCanvasElement | undefined;

  if (debug && bestCard) {
    debugCanvas = createDebugVisualization(imageData, bestCard, edges);
  }

  return {
    card: bestCard,
    debugCanvas,
  };
}

/**
 * Gaussian blur filter
 */
function gaussianBlur(
  data: Uint8ClampedArray,
  width: number,
  height: number,
  kernelSize: number
): Uint8ClampedArray {
  const result = new Uint8ClampedArray(data.length);
  const kernel = createGaussianKernel(kernelSize);
  const half = Math.floor(kernelSize / 2);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sum = 0;
      let weightSum = 0;

      for (let ky = -half; ky <= half; ky++) {
        for (let kx = -half; kx <= half; kx++) {
          const py = y + ky;
          const px = x + kx;

          if (px >= 0 && px < width && py >= 0 && py < height) {
            const idx = py * width + px;
            const weight = kernel[ky + half][kx + half];
            sum += data[idx] * weight;
            weightSum += weight;
          }
        }
      }

      result[y * width + x] = sum / weightSum;
    }
  }

  return result;
}

/**
 * Create Gaussian kernel
 */
function createGaussianKernel(size: number): number[][] {
  const kernel: number[][] = [];
  const sigma = size / 6;
  const half = Math.floor(size / 2);

  for (let y = -half; y <= half; y++) {
    kernel[y + half] = [];
    for (let x = -half; x <= half; x++) {
      const value = Math.exp(-(x * x + y * y) / (2 * sigma * sigma));
      kernel[y + half][x + half] = value;
    }
  }

  return kernel;
}

/**
 * Sobel edge detection
 */
function sobelEdgeDetection(
  data: Uint8ClampedArray,
  width: number,
  height: number
): Uint8ClampedArray {
  const result = new Uint8ClampedArray(data.length);

  const sobelX = [
    [-1, 0, 1],
    [-2, 0, 2],
    [-1, 0, 1],
  ];

  const sobelY = [
    [-1, -2, -1],
    [0, 0, 0],
    [1, 2, 1],
  ];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      let gx = 0;
      let gy = 0;

      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          const idx = (y + ky) * width + (x + kx);
          gx += data[idx] * sobelX[ky + 1][kx + 1];
          gy += data[idx] * sobelY[ky + 1][kx + 1];
        }
      }

      const magnitude = Math.sqrt(gx * gx + gy * gy);
      result[y * width + x] = Math.min(255, magnitude);
    }
  }

  return result;
}

/**
 * Adaptive threshold
 */
function adaptiveThreshold(
  data: Uint8ClampedArray,
  width: number,
  height: number,
  blockSize: number,
  C: number
): Uint8ClampedArray {
  const result = new Uint8ClampedArray(data.length);
  const half = Math.floor(blockSize / 2);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sum = 0;
      let count = 0;

      for (let ky = -half; ky <= half; ky++) {
        for (let kx = -half; kx <= half; kx++) {
          const py = y + ky;
          const px = x + kx;

          if (px >= 0 && px < width && py >= 0 && py < height) {
            sum += data[py * width + px];
            count++;
          }
        }
      }

      const threshold = sum / count - C;
      const idx = y * width + x;
      result[idx] = data[idx] > threshold ? 255 : 0;
    }
  }

  return result;
}

/**
 * Simple contour finding (flood fill based)
 */
function findContours(
  binary: Uint8ClampedArray,
  width: number,
  height: number
): { x: number; y: number }[][] {
  const visited = new Uint8ClampedArray(binary.length);
  const contours: { x: number; y: number }[][] = [];

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = y * width + x;

      if (binary[idx] === 255 && !visited[idx]) {
        const contour = traceContour(binary, visited, width, height, x, y);
        if (contour.length > 100) {
          // Minimum contour size
          contours.push(contour);
        }
      }
    }
  }

  return contours;
}

/**
 * Trace a single contour using flood fill
 */
function traceContour(
  binary: Uint8ClampedArray,
  visited: Uint8ClampedArray,
  width: number,
  height: number,
  startX: number,
  startY: number
): { x: number; y: number }[] {
  const contour: { x: number; y: number }[] = [];
  const stack: { x: number; y: number }[] = [{ x: startX, y: startY }];

  while (stack.length > 0) {
    const { x, y } = stack.pop()!;
    const idx = y * width + x;

    if (x < 0 || x >= width || y < 0 || y >= height) continue;
    if (visited[idx] || binary[idx] !== 255) continue;

    visited[idx] = 1;
    contour.push({ x, y });

    // 8-connectivity
    stack.push({ x: x + 1, y });
    stack.push({ x: x - 1, y });
    stack.push({ x, y: y + 1 });
    stack.push({ x, y: y - 1 });
    stack.push({ x: x + 1, y: y + 1 });
    stack.push({ x: x - 1, y: y - 1 });
    stack.push({ x: x + 1, y: y - 1 });
    stack.push({ x: x - 1, y: y + 1 });
  }

  return contour;
}

/**
 * Get bounding rectangle from contour
 */
function getBoundingRect(contour: { x: number; y: number }[]): {
  x: number;
  y: number;
  width: number;
  height: number;
} {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const point of contour) {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  }

  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

/**
 * Calculate score based on how centered the card is
 */
function calculateCenterScore(
  rect: { x: number; y: number; width: number; height: number },
  imageWidth: number,
  imageHeight: number
): number {
  const centerX = rect.x + rect.width / 2;
  const centerY = rect.y + rect.height / 2;

  const imageCenterX = imageWidth / 2;
  const imageCenterY = imageHeight / 2;

  const distX = Math.abs(centerX - imageCenterX) / (imageWidth / 2);
  const distY = Math.abs(centerY - imageCenterY) / (imageHeight / 2);

  return 1 - (distX + distY) / 2;
}

/**
 * Create debug visualization
 */
function createDebugVisualization(
  imageData: ImageData,
  card: DetectedCard,
  edges: Uint8ClampedArray
): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = imageData.width;
  canvas.height = imageData.height;

  const ctx = canvas.getContext('2d')!;

  // Draw original image
  ctx.putImageData(imageData, 0, 0);

  // Draw edges overlay
  ctx.globalAlpha = 0.3;
  const edgeImageData = new ImageData(imageData.width, imageData.height);
  for (let i = 0; i < edges.length; i++) {
    edgeImageData.data[i * 4] = edges[i];
    edgeImageData.data[i * 4 + 1] = edges[i];
    edgeImageData.data[i * 4 + 2] = edges[i];
    edgeImageData.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(edgeImageData, 0, 0);

  ctx.globalAlpha = 1;

  // Draw detected card rectangle
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 3;
  ctx.strokeRect(card.x, card.y, card.width, card.height);

  // Draw confidence
  ctx.fillStyle = '#00ff00';
  ctx.font = '16px monospace';
  ctx.fillText(`${(card.confidence * 100).toFixed(0)}%`, card.x, card.y - 10);

  return canvas;
}
