import React from 'react';

interface DetectionResult {
  card: {
    boundingBox: { x: number; y: number; width: number; height: number };
    confidence: number;
  };
  timestamp: number;
  verified: boolean;
}

interface DetectionOverlayProps {
  detection: DetectionResult;
  isVerified: boolean;
}

export const DetectionOverlay: React.FC<DetectionOverlayProps> = ({ detection, isVerified }) => {
  const { boundingBox, confidence } = detection.card;

  return (
    <div className="detection-overlay">
      <div
        className={`detection-box ${isVerified ? 'verified' : 'detecting'}`}
        style={{
          left: `${boundingBox.x}px`,
          top: `${boundingBox.y}px`,
          width: `${boundingBox.width}px`,
          height: `${boundingBox.height}px`,
        }}
      >
        <div className="detection-label">
          {isVerified ? '✓ Card Detected' : 'Detecting...'}
          <span className="confidence">{(confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};
