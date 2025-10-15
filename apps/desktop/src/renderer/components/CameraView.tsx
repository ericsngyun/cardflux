import React, { useRef, useEffect, useState, useMemo } from 'react';
import { detectCard, DetectedCard } from '../utils/cardDetection';

interface CameraViewProps {
  onCapture: (imagePath: string) => void;
  isIdentifying: boolean;
}

export const CameraView: React.FC<CameraViewProps> = React.memo(({ onCapture, isIdentifying }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const detectionCanvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectedCard, setDetectedCard] = useState<DetectedCard | null>(null);
  const animationFrameRef = useRef<number>();

  // Memoize canvas dimensions for performance
  const canvasDimensions = useMemo(() => ({
    width: detectionCanvasRef.current?.width || 1,
    height: detectionCanvasRef.current?.height || 1,
  }), [detectionCanvasRef.current?.width, detectionCanvasRef.current?.height]);

  // Memoize detected card box style for performance
  const detectedCardStyle = useMemo(() => {
    if (!detectedCard) return null;

    return {
      position: 'absolute' as const,
      left: `${(detectedCard.x / canvasDimensions.width) * 100}%`,
      top: `${(detectedCard.y / canvasDimensions.height) * 100}%`,
      width: `${(detectedCard.width / canvasDimensions.width) * 100}%`,
      height: `${(detectedCard.height / canvasDimensions.height) * 100}%`,
      border: '2px solid rgba(255, 255, 255, 0.8)',
      borderRadius: '4px',
      pointerEvents: 'none' as const,
    };
  }, [detectedCard, canvasDimensions]);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment',
        },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
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
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  };

  // Continuous card detection (throttled for performance)
  useEffect(() => {
    if (!isCameraActive || !videoRef.current || !detectionCanvasRef.current) {
      return;
    }

    const video = videoRef.current;
    const detectionCanvas = detectionCanvasRef.current;
    const detectionCtx = detectionCanvas.getContext('2d')!;

    // Throttle detection to ~5 FPS (200ms) instead of 60 FPS for better performance
    const DETECTION_INTERVAL = 200; // ms
    let lastDetectionTime = 0;

    const detectCardInFrame = (timestamp: number) => {
      // Throttle detection
      if (timestamp - lastDetectionTime < DETECTION_INTERVAL) {
        animationFrameRef.current = requestAnimationFrame(detectCardInFrame);
        return;
      }

      lastDetectionTime = timestamp;

      if (!video.videoWidth || !video.videoHeight) {
        animationFrameRef.current = requestAnimationFrame(detectCardInFrame);
        return;
      }

      // Set canvas size once (not on every frame)
      if (detectionCanvas.width !== video.videoWidth) {
        detectionCanvas.width = video.videoWidth;
        detectionCanvas.height = video.videoHeight;
      }

      // Draw current frame
      detectionCtx.drawImage(video, 0, 0);

      // Get image data
      const imageData = detectionCtx.getImageData(0, 0, detectionCanvas.width, detectionCanvas.height);

      // Detect card
      const result = detectCard(imageData, {
        minArea: 30000,
        maxArea: 600000,
        aspectRatio: { min: 0.60, max: 0.75 },
      });

      setDetectedCard(result.card);

      // Continue loop
      animationFrameRef.current = requestAnimationFrame(detectCardInFrame);
    };

    // Start detection loop
    animationFrameRef.current = requestAnimationFrame(detectCardInFrame);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isCameraActive]);

  const handleCapture = async () => {
    if (!videoRef.current || !canvasRef.current || isIdentifying) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw video frame to canvas
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert canvas to base64 data URL
      const imageData = canvas.toDataURL('image/jpeg', 0.95);

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
            <canvas ref={detectionCanvasRef} style={{ display: 'none' }} />

            {isCameraActive && (
              <div className="camera-overlay">
                {detectedCard && detectedCardStyle ? (
                  <>
                    <div className="detected-card-box" style={detectedCardStyle}>
                      <div className="detection-corners">
                        <div className="corner corner-tl" />
                        <div className="corner corner-tr" />
                        <div className="corner corner-bl" />
                        <div className="corner corner-br" />
                      </div>
                      <div className="detection-label">
                        Card Detected ({(detectedCard.confidence * 100).toFixed(0)}%)
                      </div>
                    </div>
                    <div className="camera-hint camera-hint-ready">Card detected - Press SPACE to capture</div>
                  </>
                ) : (
                  <>
                    <div className="guide-frame">
                      <div className="corner corner-tl" />
                      <div className="corner corner-tr" />
                      <div className="corner corner-bl" />
                      <div className="corner corner-br" />
                    </div>
                    <div className="camera-hint">Position card on playmat</div>
                  </>
                )}
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
      </div>
    </div>
  );
});
