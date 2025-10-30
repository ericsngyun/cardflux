import React, { useRef, useEffect, useState } from 'react';

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

  // Smoothing and stabilization
  const smoothedBBoxRef = useRef<SmoothedBBox | null>(null);
  const statusHistoryRef = useRef<string[]>([]);
  const stableStatusRef = useRef<string>('no_card');
  const readyTimerRef = useRef<number>(0);
  const animationFrameRef = useRef<number | null>(null);

  // Auto-capture settings
  const [autoCapture, setAutoCapture] = useState(true);
  const [autoCapturCountdown, setAutoCapturCountdown] = useState<number | null>(null);
  const autoCapturTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Camera tips visibility
  const [showCameraTips, setShowCameraTips] = useState(true);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
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
          console.log('[Camera] Capabilities:', {
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
            console.log('[Camera] Applied advanced focus constraints:', constraints);
          }
        } catch (constraintError) {
          console.warn('[Camera] Could not apply advanced constraints:', constraintError);
          // Continue anyway - basic stream is still usable
        }

        setIsCameraActive(true);
        setError(null);
      }
    } catch (err: any) {
      console.error('Camera error:', err);
      setError('Failed to access camera. Please check permissions.');
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
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
    const alpha = 0.3; // Smoothing factor (lower = smoother, higher = more responsive)

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
    const REQUIRED_CONSECUTIVE = 3; // Must see same status 3 times
    const MAX_HISTORY = 5;

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

    detectionInProgressRef.current = true;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current frame
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64 with lower resolution for detection (reduce IPC overhead)
    // Downsample to 640x360 for detection (4x smaller than full HD)
    const detectionCanvas = document.createElement('canvas');
    const targetWidth = 640;
    const targetHeight = Math.round((canvas.height / canvas.width) * targetWidth);
    detectionCanvas.width = targetWidth;
    detectionCanvas.height = targetHeight;

    const detectionCtx = detectionCanvas.getContext('2d', { alpha: false });
    if (detectionCtx) {
      detectionCtx.imageSmoothingEnabled = true;
      detectionCtx.imageSmoothingQuality = 'medium';
      detectionCtx.drawImage(canvas, 0, 0, targetWidth, targetHeight);
    }

    // Convert to base64 (low quality for detection, faster transmission)
    const imageData = detectionCanvas.toDataURL('image/jpeg', 0.5);

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
      console.error('Detection error:', error);
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

  // Start/stop live detection when camera state changes
  useEffect(() => {
    if (isCameraActive && !isIdentifying) {
      // Start detection interval (every 500ms for better performance)
      // Reduced frequency to minimize IPC overhead and CPU usage
      // 500ms is still responsive enough for user feedback
      detectionIntervalRef.current = setInterval(() => {
        detectCardInFrame();
      }, 500);
    } else {
      // Stop detection interval
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }

      // Reset smoothing state when not detecting
      smoothedBBoxRef.current = null;
      statusHistoryRef.current = [];
      stableStatusRef.current = 'no_card';
      setAutoCapturCountdown(null);
      detectionInProgressRef.current = false;
    }

    return () => {
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
    };
  }, [isCameraActive, isIdentifying]);

  const handleCapture = async () => {
    if (!videoRef.current || !canvasRef.current || isIdentifying) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Set canvas size to match video (capture at full resolution)
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw video frame to canvas with high-quality rendering
    const ctx = canvas.getContext('2d', {
      alpha: false,
      desynchronized: false,
      willReadFrequently: false,
    });

    if (ctx) {
      // Use high-quality image smoothing
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      // Draw the frame
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert to JPEG with high quality (98% for card details)
      // JPEG chosen over PNG for faster transmission (card photos compress well)
      const imageData = canvas.toDataURL('image/jpeg', 0.98);

      // Send to main process to save
      const captureResult = await window.camera.capture(imageData);

      if (captureResult.success && captureResult.imagePath) {
        onCapture(captureResult.imagePath);
      } else {
        console.error('Capture failed:', captureResult.error);
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
