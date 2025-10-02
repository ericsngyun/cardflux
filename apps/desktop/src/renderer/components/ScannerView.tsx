import React from 'react';

interface ScannerViewProps {
  isScanning: boolean;
  onStart: () => void;
  onStop: () => void;
}

export const ScannerView: React.FC<ScannerViewProps> = ({ isScanning, onStart, onStop }) => {
  return (
    <div className="scanner-view">
      <div className="camera-preview">
        {!isScanning ? (
          <div className="camera-placeholder">
            <div className="camera-icon">📷</div>
            <p>Camera preview will appear here</p>
          </div>
        ) : (
          <div className="camera-active">
            <div className="guide-frame">
              <div className="corner top-left"></div>
              <div className="corner top-right"></div>
              <div className="corner bottom-left"></div>
              <div className="corner bottom-right"></div>
            </div>
            <p className="instruction">Position card within the frame</p>
          </div>
        )}
      </div>

      <div className="scanner-controls">
        {!isScanning ? (
          <button className="btn btn-primary" onClick={onStart}>
            Start Scanning
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={onStop}>
            Stop Scanning
          </button>
        )}
      </div>
    </div>
  );
};
