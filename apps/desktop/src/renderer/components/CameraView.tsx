import React, { useRef, useEffect, useState } from 'react';

interface CameraViewProps {
  onCapture: (imagePath: string) => void;
  isIdentifying: boolean;
}

export const CameraView: React.FC<CameraViewProps> = React.memo(({ onCapture, isIdentifying }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  };

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

            {isCameraActive && (
              <div className="camera-overlay">
                <div className="guide-frame">
                  <div className="corner corner-tl" />
                  <div className="corner corner-tr" />
                  <div className="corner corner-bl" />
                  <div className="corner corner-br" />
                </div>
                <div className="camera-hint">Position card in frame - Press SPACE to capture</div>
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
