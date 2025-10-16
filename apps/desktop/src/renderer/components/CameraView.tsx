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

export const CameraView: React.FC<CameraViewProps> = React.memo(({ onCapture, isIdentifying }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectionResult, setDetectionResult] = useState<CardDetectionResult | null>(null);
  const detectionIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, []);

  const startCamera = async () => {
    try {
      // Request highest quality camera for accurate card identification
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1920, min: 1280 },  // Increased from 1280
          height: { ideal: 1080, min: 720 },   // Increased from 720
          facingMode: 'environment',
          // Advanced constraints for better quality
          frameRate: { ideal: 30, min: 15 },
          aspectRatio: { ideal: 16/9 },
          // Request auto-focus and exposure for card details
          focusMode: 'continuous',
          exposureMode: 'continuous',
          whiteBalanceMode: 'continuous',
        } as MediaTrackConstraints,
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
  };

  const detectCardInFrame = async () => {
    if (!videoRef.current || !canvasRef.current || isIdentifying) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current frame
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64 (lower quality for detection, faster transmission)
    const imageData = canvas.toDataURL('image/jpeg', 0.7);

    try {
      // Call detection API
      const result = await window.identifier.detectCard(imageData);

      if (result.success && result.result) {
        setDetectionResult(result.result);
        drawDetectionOverlay(result.result);
      }
    } catch (error) {
      console.error('Detection error:', error);
    }
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

    // Clear previous overlay
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw bounding box if card detected
    if (result.bbox) {
      const [x, y, w, h] = result.bbox;

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
      // Start detection interval (every 200ms for smooth feedback)
      detectionIntervalRef.current = setInterval(() => {
        detectCardInFrame();
      }, 200);
    } else {
      // Stop detection interval
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
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
        hintText = '✓ Card ready - Press SPACE to capture';
        hintClass = 'camera-hint hint-success';
        break;
      case 'poor_lighting':
        hintText = 'Improve lighting conditions';
        hintClass = 'camera-hint hint-error';
        break;
      case 'too_blurry':
        hintText = 'Hold steady - Image is blurry';
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
