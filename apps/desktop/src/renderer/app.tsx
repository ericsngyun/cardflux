import React, { useEffect, useState, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { ScannerView } from './components/ScannerView';
import { DetectionOverlay } from './components/DetectionOverlay';
import './styles.css';

interface DetectionResult {
  card: {
    boundingBox: { x: number; y: number; width: number; height: number };
    confidence: number;
  };
  timestamp: number;
  verified: boolean;
}

const App: React.FC = () => {
  const [isScanning, setIsScanning] = useState(false);
  const [detection, setDetection] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scannerStatus, setScannerStatus] = useState({ running: false, initialized: false });

  useEffect(() => {
    // Setup detection listener
    const cleanupDetection = window.scanner.onDetection((result: DetectionResult | null) => {
      setDetection(result);
    });

    // Setup error listener
    const cleanupError = window.scanner.onError((err: string) => {
      setError(err);
      console.error('Scanner error:', err);
    });

    // Get initial status
    window.scanner.getStatus().then(setScannerStatus);

    // Cleanup on unmount
    return () => {
      cleanupDetection();
      cleanupError();
    };
  }, []);

  const handleStartScanning = useCallback(async () => {
    try {
      setError(null);
      const result = await window.scanner.start();
      if (result.success) {
        setIsScanning(true);
        const status = await window.scanner.getStatus();
        setScannerStatus(status);
      }
    } catch (err) {
      setError(String(err));
      console.error('Failed to start scanner:', err);
    }
  }, []);

  const handleStopScanning = useCallback(async () => {
    try {
      const result = await window.scanner.stop();
      if (result.success) {
        setIsScanning(false);
        setDetection(null);
        const status = await window.scanner.getStatus();
        setScannerStatus(status);
      }
    } catch (err) {
      setError(String(err));
      console.error('Failed to stop scanner:', err);
    }
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>CardFlux Scanner</h1>
        <div className="status-indicator">
          <span className={`status-dot ${scannerStatus.running ? 'active' : ''}`}></span>
          <span>{scannerStatus.running ? 'Scanning' : 'Idle'}</span>
        </div>
      </header>

      <main className="app-main">
        <ScannerView
          isScanning={isScanning}
          onStart={handleStartScanning}
          onStop={handleStopScanning}
        />

        {detection && (
          <DetectionOverlay
            detection={detection}
            isVerified={detection.verified}
          />
        )}

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Position a trading card in front of the camera</p>
        {detection && (
          <div className="detection-info">
            <span>Confidence: {(detection.card.confidence * 100).toFixed(1)}%</span>
            {detection.verified && <span className="verified-badge">✓ Verified</span>}
          </div>
        )}
      </footer>
    </div>
  );
};

// Mount the React app
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<App />);
}
