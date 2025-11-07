import React, { useRef, useEffect, useState } from 'react';
import { createModuleLogger } from '../utils/logger';
import {
  CAMERA_CONSTANTS,
  POLL_INTERVALS,
} from '../constants';

const logger = createModuleLogger('CameraView');

interface CameraViewProps {
  onCapture: (imagePath: string) => void;
  isIdentifying: boolean;
}

interface CardDetectionResult {
  status: string;
  confidence: number;
  qualityScore: number;
  warnings: string[];
  isReady: boolean;
  bbox: [number, number, number, number] | null;
}

interface SmoothedBBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export const CameraView: React.FC<CameraViewProps> = React.memo(({ onCapture, isIdentifying }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectionResult, setDetectionResult] = useState<CardDetectionResult | null>(null);
  const detectionIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const detectionInProgressRef = useRef<boolean>(false);  // Prevent concurrent detections

  // CRITICAL FIX: Reuse detection canvas to prevent memory leak
  const detectionCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Smoothing and stabilization
  const smoothedBBoxRef = useRef<SmoothedBBox | null>(null);
  const statusHistoryRef = useRef<string[]>([]);
  const stableStatusRef = useRef<string>('no_card');
  const readyTimerRef = useRef<number>(0);
  const animationFrameRef = useRef<number | null>(null);

  // Auto-capture settings (disabled by default - manual scan recommended)
  const [autoCapture, setAutoCapture] = useState(false);
  const [autoCapturCountdown, setAutoCapturCountdown] = useState<number | null>(null);
  const autoCapturTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Camera tips visibility
  const [showCameraTips, setShowCameraTips] = useState(true);

  useEffect(() => {
    startCamera();

    return () => {
      stopCamera();

      // CRITICAL FIX: Cleanup detection canvas on unmount
      if (detectionCanvasRef.current) {
        const ctx = detectionCanvasRef.current.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, detectionCanvasRef.current.width, detectionCanvasRef.current.height);
        }
        detectionCanvasRef.current = null;
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      // Request highest quality camera for accurate card identification
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1920, min: 1280 },
          height: { ideal: 1080, min: 720 },
          facingMode: 'environment',
          frameRate: { ideal: 30, min: 15 },
          aspectRatio: { ideal: 16/9 },
          // Advanced focus settings for card scanning
          focusMode: 'continuous',
          focusDistance: { ideal: 0.3 }, // 30cm - ideal for card scanning
          exposureMode: 'continuous',
          whiteBalanceMode: 'continuous',
        } as MediaTrackConstraints,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;

        // Try to apply advanced focus settings after stream is active
        try {
          const videoTrack = stream.getVideoTracks()[0];
          const capabilities = videoTrack.getCapabilities() as any; // Extended capabilities not in TS types

          // Log available capabilities for debugging
          logger.debug('Camera capabilities available', {
            focusMode: capabilities.focusMode,
            focusDistance: capabilities.focusDistance,
            zoom: capabilities.zoom,
          });

          // Apply best available focus settings
          const constraints: any = {};

          if (capabilities.focusMode?.includes('continuous')) {
            constraints.focusMode = 'continuous';
          } else if (capabilities.focusMode?.includes('single-shot')) {
            constraints.focusMode = 'single-shot';
          }

          // Set focus distance for close-up card scanning (20-40cm range)
          if (capabilities.focusDistance) {
            constraints.focusDistance = 0.3; // 30cm
          }

          // Apply zoom if available (helps with focus on some webcams)
          if (capabilities.zoom && capabilities.zoom.min !== undefined && capabilities.zoom.max !== undefined) {
            // Slight zoom (1.2x) can help force focus on closer objects
            constraints.zoom = Math.min(1.2, capabilities.zoom.max);
          }

          if (Object.keys(constraints).length > 0) {
            await videoTrack.applyConstraints({ advanced: [constraints] });
            logger.info('Applied advanced focus constraints', { constraints });
          }
        } catch (constraintError) {
          logger.warn('Could not apply advanced constraints', constraintError);
          // Continue anyway - basic stream is still usable
        }

        setIsCameraActive(true);
        setError(null);
      }
    } catch (err: any) {
      logger.error('Failed to access camera', err);
      setError('Failed to access camera. Please check permissions.');
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    // HIGH SEVERITY FIX: Add error handling to prevent resource leak
    try {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        // Check if tracks are still active before stopping
        stream.getTracks().forEach((track) => {
          if (track.readyState !== 'ended') {
            track.stop();
          }
        });
        videoRef.current.srcObject = null;
      }
    } catch (error) {
      logger.error('Error stopping video tracks', error);
    } finally {
      // Always mark camera as inactive, even if track.stop() fails
      setIsCameraActive(false);
    }

    // Stop detection interval
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
      detectionIntervalRef.current = null;
    }

    // Stop animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Clear auto-capture timer
    if (autoCapturTimerRef.current) {
      clearTimeout(autoCapturTimerRef.current);
      autoCapturTimerRef.current = null;
    }
  };

  /**
   * Smooth bounding box using exponential moving average
   * Reduces jitter and flickering
   */
  const smoothBBox = (newBBox: [number, number, number, number]): SmoothedBBox => {
    const [x, y, w, h] = newBBox;
    const alpha = CAMERA_CONSTANTS.BBOX_SMOOTHING_ALPHA; // Smoothing factor (lower = smoother, higher = more responsive)

    if (!smoothedBBoxRef.current) {
      smoothedBBoxRef.current = { x, y, w, h };
      return smoothedBBoxRef.current;
    }

    // Exponential moving average
    smoothedBBoxRef.current = {
      x: smoothedBBoxRef.current.x * (1 - alpha) + x * alpha,
      y: smoothedBBoxRef.current.y * (1 - alpha) + y * alpha,
      w: smoothedBBoxRef.current.w * (1 - alpha) + w * alpha,
      h: smoothedBBoxRef.current.h * (1 - alpha) + h * alpha,
    };

    return smoothedBBoxRef.current;
  };

  /**
   * Debounce status changes - require N consecutive same statuses
   * Prevents flickering between states
   */
  const debounceStatus = (status: string): string => {
    const REQUIRED_CONSECUTIVE = CAMERA_CONSTANTS.STATUS_DEBOUNCE_COUNT; // Must see same status 3 times
    const MAX_HISTORY = CAMERA_CONSTANTS.STATUS_HISTORY_MAX;

    // Add to history
    statusHistoryRef.current.push(status);
    if (statusHistoryRef.current.length > MAX_HISTORY) {
      statusHistoryRef.current.shift();
    }

    // Check if last N statuses are the same
    const recentStatuses = statusHistoryRef.current.slice(-REQUIRED_CONSECUTIVE);
    if (recentStatuses.length === REQUIRED_CONSECUTIVE &&
        recentStatuses.every(s => s === status)) {
      // All recent statuses match - update stable status
      stableStatusRef.current = status;
    }

    return stableStatusRef.current;
  };

  const detectCardInFrame = async () => {
    // Skip if already detecting (prevent request pileup)
    if (!videoRef.current || !canvasRef.current || isIdentifying || detectionInProgressRef.current) {
      return;
    }

    const video = videoRef.current;

    // CRITICAL: Check if video has loaded frames before attempting detection
    // readyState >= 2 means HAVE_CURRENT_DATA (frame is available)
    // videoWidth/videoHeight > 0 means dimensions are known
    if (video.readyState < 2 || video.videoWidth === 0 || video.videoHeight === 0) {
      logger.debug('Video not ready for detection', {
        readyState: video.readyState,
        width: video.videoWidth,
        height: video.videoHeight,
      });
      return;
    }

    detectionInProgressRef.current = true;

    const canvas = canvasRef.current;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current frame
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) {
      detectionInProgressRef.current = false;
      return;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // CRITICAL FIX: Reuse detection canvas instead of creating new one
    // Creates new canvas every 500ms = ~6.5GB memory leak after 1 hour
    if (!detectionCanvasRef.current) {
      detectionCanvasRef.current = document.createElement('canvas');
    }
    const detectionCanvas = detectionCanvasRef.current;

    // Convert to base64 with lower resolution for detection (reduce IPC overhead)
    // Downsample to 640x360 for detection (4x smaller than full HD)
    const targetWidth = CAMERA_CONSTANTS.DETECTION_WIDTH;
    const targetHeight = Math.round((canvas.height / canvas.width) * targetWidth);

    // Canvas automatically clears when resized
    detectionCanvas.width = targetWidth;
    detectionCanvas.height = targetHeight;

    const detectionCtx = detectionCanvas.getContext('2d', { alpha: false });
    if (detectionCtx) {
      detectionCtx.imageSmoothingEnabled = true;
      detectionCtx.imageSmoothingQuality = 'medium';
      detectionCtx.drawImage(canvas, 0, 0, targetWidth, targetHeight);
    }

    // Convert to base64 (low quality for detection, faster transmission)
    const imageData = detectionCanvas.toDataURL('image/jpeg', CAMERA_CONSTANTS.DETECTION_JPEG_QUALITY);

    try {
      // Call detection API
      const result = await window.identifier.detectCard(imageData);

      if (result.success && result.result) {
        const rawResult = result.result;

        // Apply status debouncing to prevent flickering
        const stableStatus = debounceStatus(rawResult.status);

        // Create stabilized result
        const stabilizedResult = {
          ...rawResult,
          status: stableStatus,
          // Smooth bbox if present
          bbox: rawResult.bbox ? smoothBBox(rawResult.bbox) : null,
        };

        setDetectionResult(stabilizedResult as CardDetectionResult);

        // Handle auto-capture logic
        handleAutoCapture(stabilizedResult.status, stabilizedResult.isReady);

        // Request animation frame for smooth overlay drawing
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }

        animationFrameRef.current = requestAnimationFrame(() => {
          drawDetectionOverlay(stabilizedResult as CardDetectionResult);
        });
      }
    } catch (error) {
      logger.error('Detection error', error);
    } finally {
      // Always clear the in-progress flag
      detectionInProgressRef.current = false;
    }
  };

  /**
   * Handle auto-capture logic when card is ready
   */
  const handleAutoCapture = (status: string, isReady: boolean) => {
    if (!autoCapture || isIdentifying) {
      // Reset countdown if auto-capture disabled or already identifying
      setAutoCapturCountdown(null);
      if (autoCapturTimerRef.current) {
        clearTimeout(autoCapturTimerRef.current);
        autoCapturTimerRef.current = null;
      }
      readyTimerRef.current = 0;
      return;
    }

    if (status === 'card_ready' && isReady) {
      // Card is ready - start/continue countdown
      if (readyTimerRef.current === 0) {
        // Just became ready - start countdown
        readyTimerRef.current = Date.now();
        startAutoCapturCountdown();
      }
      // If countdown already started, let it continue
    } else {
      // Card not ready anymore - PROPERLY reset all timers
      if (autoCapturTimerRef.current) {
        clearTimeout(autoCapturTimerRef.current);
        autoCapturTimerRef.current = null;
      }
      setAutoCapturCountdown(null);
      readyTimerRef.current = 0;
    }
  };

  /**
   * Start auto-capture countdown timer
   */
  const startAutoCapturCountdown = () => {
    const READY_DURATION = 2000; // 2 seconds
    const UPDATE_INTERVAL = 100; // Update countdown every 100ms

    const updateCountdown = () => {
      if (!autoCapture || isIdentifying) {
        setAutoCapturCountdown(null);
        return;
      }

      const elapsed = Date.now() - readyTimerRef.current;
      const remaining = Math.max(0, READY_DURATION - elapsed);

      if (remaining > 0) {
        // Update countdown display
        setAutoCapturCountdown(Math.ceil(remaining / 1000));

        // Schedule next update
        autoCapturTimerRef.current = setTimeout(updateCountdown, UPDATE_INTERVAL) as any;
      } else {
        // Countdown complete - trigger capture
        setAutoCapturCountdown(null);
        handleCapture();
      }
    };

    updateCountdown();
  };

  const drawDetectionOverlay = (result: CardDetectionResult) => {
    if (!overlayCanvasRef.current || !videoRef.current) return;

    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match video display
    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;

    // Clear previous overlay with slight fade for smoother transitions
    ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bounding box if card detected (using smoothed bbox)
    if (result.bbox && smoothedBBoxRef.current) {
      const { x, y, w, h } = smoothedBBoxRef.current;

      // Scale bbox to display size
      const scaleX = canvas.width / video.videoWidth;
      const scaleY = canvas.height / video.videoHeight;

      const displayX = x * scaleX;
      const displayY = y * scaleY;
      const displayW = w * scaleX;
      const displayH = h * scaleY;

      // Choose color based on status
      let color = '#4CAF50'; // Green for ready
      if (result.status === 'card_too_far' || result.status === 'card_too_close') {
        color = '#FFC107'; // Yellow for position issues
      } else if (result.status === 'too_blurry' || result.status === 'glare_detected' || result.status === 'poor_lighting') {
        color = '#F44336'; // Red for quality issues
      }

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(displayX, displayY, displayW, displayH);

      // Draw corner markers
      const cornerSize = 20;
      ctx.lineWidth = 4;

      // Top-left
      ctx.beginPath();
      ctx.moveTo(displayX, displayY + cornerSize);
      ctx.lineTo(displayX, displayY);
      ctx.lineTo(displayX + cornerSize, displayY);
      ctx.stroke();

      // Top-right
      ctx.beginPath();
      ctx.moveTo(displayX + displayW - cornerSize, displayY);
      ctx.lineTo(displayX + displayW, displayY);
      ctx.lineTo(displayX + displayW, displayY + cornerSize);
      ctx.stroke();

      // Bottom-left
      ctx.beginPath();
      ctx.moveTo(displayX, displayY + displayH - cornerSize);
      ctx.lineTo(displayX, displayY + displayH);
      ctx.lineTo(displayX + cornerSize, displayY + displayH);
      ctx.stroke();

      // Bottom-right
      ctx.beginPath();
      ctx.moveTo(displayX + displayW - cornerSize, displayY + displayH);
      ctx.lineTo(displayX + displayW, displayY + displayH);
      ctx.lineTo(displayX + displayW, displayY + displayH - cornerSize);
      ctx.stroke();
    }
  };

  // CRITICAL FIX: Start/stop live detection when camera state changes
  // Wait for video to be ready before starting interval to prevent wasted IPC calls
  useEffect(() => {
    // Clear any existing interval first
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
      detectionIntervalRef.current = null;
    }

    // If not active or identifying, stop and reset
    if (!isCameraActive || isIdentifying) {
      // Reset smoothing state when not detecting
      smoothedBBoxRef.current = null;
      statusHistoryRef.current = [];
      stableStatusRef.current = 'no_card';
      setAutoCapturCountdown(null);
      detectionInProgressRef.current = false;
      return;
    }

    // Camera is active and not identifying - wait for video to be ready
    const video = videoRef.current;
    if (!video) return;

    /**
     * Wait for video to have loaded frames before starting detection
     * Prevents ~20 wasted IPC calls during Python service initialization
     */
    const waitForVideoReady = () => {
      // Check if video has loaded metadata and has valid dimensions
      // readyState >= 2 = HAVE_CURRENT_DATA (at least one frame available)
      if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
        // Video is ready - start detection interval
        logger.info('Video ready, starting detection', {
          readyState: video.readyState,
          width: video.videoWidth,
          height: video.videoHeight,
        });

        detectionIntervalRef.current = setInterval(() => {
          detectCardInFrame();
        }, POLL_INTERVALS.ACTIVE);
      } else {
        // Video not ready yet - check again soon
        logger.debug('Waiting for video ready', {
          readyState: video.readyState,
          width: video.videoWidth,
          height: video.videoHeight,
        });

        setTimeout(waitForVideoReady, POLL_INTERVALS.VIDEO_READY_CHECK);
      }
    };

    // Start the ready check
    waitForVideoReady();

    // Cleanup on unmount or state change
    return () => {
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
    };
  }, [isCameraActive, isIdentifying]);

  /**
   * Downscale canvas to optimal resolution and encode to JPEG
   *
   * PERFORMANCE OPTIMIZATION:
   * - Camera captures are often 1920x1080 (2.07 MP)
   * - Test images are ~600x600 (0.36 MP) or 1280x720 (0.92 MP)
   * - Bilateral filter time scales with pixel count (5.75x slower for 1080p)
   * - Downscaling to max 1280px reduces preprocessing by 50-70%
   * - No accuracy loss - DINOv2 resizes to 224x224 anyway
   *
   * @param sourceCanvas - Canvas with captured image
   * @returns base64 JPEG data URL
   */
  const downscaleAndEncode = (sourceCanvas: HTMLCanvasElement): string => {
    const MAX_DIMENSION = CAMERA_CONSTANTS.CAPTURE_MAX_DIMENSION || 1280;
    const JPEG_QUALITY = CAMERA_CONSTANTS.CAPTURE_JPEG_QUALITY;

    // Check if downscaling needed
    const needsDownscale = sourceCanvas.width > MAX_DIMENSION || sourceCanvas.height > MAX_DIMENSION;

    if (!needsDownscale) {
      // Already optimal size - encode directly
      return sourceCanvas.toDataURL('image/jpeg', JPEG_QUALITY);
    }

    // Calculate scale to fit within MAX_DIMENSION
    const scale = Math.min(
      MAX_DIMENSION / sourceCanvas.width,
      MAX_DIMENSION / sourceCanvas.height
    );

    const targetWidth = Math.round(sourceCanvas.width * scale);
    const targetHeight = Math.round(sourceCanvas.height * scale);

    // Create temporary canvas for downscaling
    const downscaleCanvas = document.createElement('canvas');
    downscaleCanvas.width = targetWidth;
    downscaleCanvas.height = targetHeight;

    const ctx = downscaleCanvas.getContext('2d', { alpha: false });
    if (!ctx) {
      // Fallback to original if context creation fails
      logger.warn('Failed to create downscale context, using original size');
      return sourceCanvas.toDataURL('image/jpeg', JPEG_QUALITY);
    }

    // High-quality downscaling
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(sourceCanvas, 0, 0, targetWidth, targetHeight);

    logger.debug('Downscaled capture', {
      original: `${sourceCanvas.width}x${sourceCanvas.height}`,
      downscaled: `${targetWidth}x${targetHeight}`,
      scale: scale.toFixed(2),
    });

    return downscaleCanvas.toDataURL('image/jpeg', JPEG_QUALITY);
  };

  const handleCapture = async () => {
    if (!videoRef.current || !canvasRef.current || isIdentifying) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Check if we have a detected card bbox
    const hasBBox = detectionResult?.bbox && smoothedBBoxRef.current;

    if (hasBBox && smoothedBBoxRef.current) {
      // Crop to detected card boundary
      const { x, y, w, h } = smoothedBBoxRef.current;

      // Add padding around detected card for safety
      const padding = CAMERA_CONSTANTS.BBOX_PADDING;
      const paddedX = Math.max(0, x - w * padding);
      const paddedY = Math.max(0, y - h * padding);
      const paddedW = Math.min(video.videoWidth - paddedX, w * (1 + 2 * padding));
      const paddedH = Math.min(video.videoHeight - paddedY, h * (1 + 2 * padding));

      // Set canvas to cropped size
      canvas.width = paddedW;
      canvas.height = paddedH;

      const ctx = canvas.getContext('2d', {
        alpha: false,
        desynchronized: false,
        willReadFrequently: false,
      });

      if (ctx) {
        // Use high-quality image smoothing
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // Draw only the cropped region
        ctx.drawImage(
          video,
          paddedX, paddedY, paddedW, paddedH,  // Source rectangle (from video)
          0, 0, paddedW, paddedH                // Destination rectangle (to canvas)
        );

        // PERFORMANCE FIX: Downscale to optimal resolution before saving
        // Match test image resolution (~600-1280px) for consistent performance
        // Reduces preprocessing time by 50-70% without quality loss
        const imageData = downscaleAndEncode(canvas);

        // Send to main process to save
        const captureResult = await window.camera.capture(imageData);

        if (captureResult.success && captureResult.imagePath) {
          onCapture(captureResult.imagePath);
        } else {
          logger.error('Capture failed', undefined, { error: captureResult.error });
        }
      }
    } else {
      // No bbox detected - capture full frame (fallback)
      // Python service will crop it server-side
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext('2d', {
        alpha: false,
        desynchronized: false,
        willReadFrequently: false,
      });

      if (ctx) {
        // Use high-quality image smoothing
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // Draw the full frame
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // PERFORMANCE FIX: Downscale to optimal resolution before saving
        const imageData = downscaleAndEncode(canvas);

        // Send to main process to save
        const captureResult = await window.camera.capture(imageData);

        if (captureResult.success && captureResult.imagePath) {
          onCapture(captureResult.imagePath);
        } else {
          logger.error('Capture failed', undefined, { error: captureResult.error });
        }
      }
    }
  };

  // Handle spacebar capture
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !isIdentifying && isCameraActive) {
        e.preventDefault();
        handleCapture();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isIdentifying, isCameraActive]);

  const getDetectionHint = () => {
    if (!detectionResult) {
      return <div className="camera-hint">Position card in frame - Press SPACE to capture</div>;
    }

    const { status, isReady, warnings, confidence, qualityScore } = detectionResult;

    let hintText = '';
    let hintClass = 'camera-hint';

    switch (status) {
      case 'no_card':
        hintText = 'Position card in frame';
        break;
      case 'card_detected':
        hintText = 'Card detected - Adjusting position...';
        hintClass = 'camera-hint hint-warning';
        break;
      case 'card_too_far':
        hintText = 'Move closer to the camera';
        hintClass = 'camera-hint hint-warning';
        break;
      case 'card_too_close':
        hintText = 'Move card away from camera';
        hintClass = 'camera-hint hint-warning';
        break;
      case 'card_angled':
        hintText = 'Hold card flat and parallel to camera';
        hintClass = 'camera-hint hint-warning';
        break;
      case 'card_ready':
        if (autoCapture && autoCapturCountdown !== null) {
          hintText = `✓ Auto-capturing in ${autoCapturCountdown}...`;
          hintClass = 'camera-hint hint-success hint-countdown';
        } else if (autoCapture) {
          hintText = '✓ Card ready - Hold steady...';
          hintClass = 'camera-hint hint-success';
        } else {
          hintText = '✓ Card ready - Press SPACE to capture';
          hintClass = 'camera-hint hint-success';
        }
        break;
      case 'poor_lighting':
        hintText = 'Improve lighting conditions';
        hintClass = 'camera-hint hint-error';
        break;
      case 'too_blurry':
        hintText = 'Hold steady - Image is blurry (Try 20-40cm from camera)';
        hintClass = 'camera-hint hint-error';
        break;
      case 'glare_detected':
        hintText = 'Reduce glare on card surface';
        hintClass = 'camera-hint hint-error';
        break;
      default:
        hintText = 'Position card in frame';
    }

    return (
      <div className={hintClass}>
        <div>{hintText}</div>
        {warnings.length > 0 && (
          <div className="detection-warnings">
            {warnings.map((warning, idx) => (
              <div key={idx} className="warning-text">⚠ {warning}</div>
            ))}
          </div>
        )}
        {isReady && (
          <div className="detection-metrics">
            Confidence: {(confidence * 100).toFixed(0)}% | Quality: {(qualityScore * 100).toFixed(0)}%
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="camera-view">
      <div className="camera-container">
        {error ? (
          <div className="camera-error">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button className="btn btn-primary" onClick={startCamera}>
              Retry
            </button>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="camera-video"
            />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <canvas
              ref={overlayCanvasRef}
              className="detection-overlay"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            />

            {isCameraActive && (
              <div className="camera-overlay">
                {!detectionResult?.bbox && (
                  <div className="guide-frame">
                    <div className="corner corner-tl" />
                    <div className="corner corner-tr" />
                    <div className="corner corner-bl" />
                    <div className="corner corner-br" />
                    <div className="guide-hint">Place card anywhere in frame</div>
                  </div>
                )}
                {getDetectionHint()}
              </div>
            )}

            {isIdentifying && (
              <div className="identifying-overlay">
                <div className="spinner" />
                <p>Identifying card...</p>
              </div>
            )}
          </>
        )}
      </div>

      <div className="camera-controls">
        <div className="control-row">
          <button
            className="btn btn-primary btn-lg btn-capture"
            onClick={handleCapture}
            disabled={!isCameraActive || isIdentifying}
          >
            {isIdentifying ? (
              <>
                <span className="spinner-sm" />
                Identifying...
              </>
            ) : (
              <>
                📸 Capture Card
                <span className="keyboard-hint">SPACE</span>
              </>
            )}
          </button>

          <label className="auto-capture-toggle">
            <input
              type="checkbox"
              checked={autoCapture}
              onChange={(e) => setAutoCapture(e.target.checked)}
              disabled={isIdentifying}
            />
            <span className="toggle-label">
              Auto-capture {autoCapture ? '(2s)' : '(manual)'}
            </span>
          </label>
        </div>
      </div>

      {/* Camera Tips Banner */}
      {showCameraTips && isCameraActive && (
        <div className="camera-tips-banner">
          <div className="tips-header">
            <span className="tips-icon">💡</span>
            <strong>Camera Focus Tips</strong>
            <button
              className="tips-close"
              onClick={() => setShowCameraTips(false)}
              aria-label="Close tips"
            >
              ×
            </button>
          </div>
          <ul className="tips-list">
            <li><strong>Distance:</strong> Hold card 20-40cm (8-16 inches) from camera</li>
            <li><strong>Lighting:</strong> Use bright, even lighting (avoid glare and shadows)</li>
            <li><strong>Stability:</strong> Keep camera and card steady for best focus</li>
            <li><strong>Position:</strong> Hold card flat and parallel to camera lens</li>
            <li><strong>If blurry:</strong> Try moving card slowly in/out until sharp, then hold still</li>
          </ul>
        </div>
      )}
    </div>
  );
});
