import React from 'react';

export interface IdentificationSettings {
  tcgGame: string;
  useOCR: boolean;
  useFoilDetection: boolean;
  topK: number;
  useGeometric: boolean;
  multiFrameEnabled: boolean;  // New: Enable multi-frame fusion
  multiFrameCount: number;     // New: Number of frames to capture (default: 3)
  acceptLowConfidence: boolean; // New: Accept LOW confidence cards (with review)
  autoAddModerate: boolean;     // New: Auto-add MODERATE or require review
}

interface SettingsPanelProps {
  settings: IdentificationSettings;
  onSettingsChange: (settings: IdentificationSettings) => void;
  onClose: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = React.memo(({
  settings,
  onSettingsChange,
  onClose,
}) => {
  const handleChange = (key: keyof IdentificationSettings, value: any) => {
    onSettingsChange({
      ...settings,
      [key]: value,
    });
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Identification Settings</h2>
          <button className="btn-icon" onClick={onClose} aria-label="Close settings">
            ✕
          </button>
        </div>

        <div className="settings-content">
          {/* TCG Game Selector */}
          <div className="setting-group">
            <label htmlFor="tcg-game" className="setting-label">
              Trading Card Game
            </label>
            <select
              id="tcg-game"
              className="setting-select"
              value={settings.tcgGame}
              disabled
              style={{ opacity: 0.7, cursor: 'not-allowed' }}
            >
              <option value="one-piece">One Piece TCG</option>
            </select>
            <p className="setting-description">
              Currently supporting One Piece TCG (5,390 cards). Additional games coming soon.
            </p>
          </div>

          {/* OCR Toggle */}
          <div className="setting-group">
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.useOCR}
                onChange={(e) => handleChange('useOCR', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Card Number Extraction (OCR)</span>
            </label>
            <p className="setting-description">
              Extract card numbers from images. Slower but more accurate for variants.
              {settings.useOCR && (
                <span className="setting-warning"> (~170ms slower per scan</span>
              )}
            </p>
          </div>

          {/* Foil Detection Toggle */}
          <div className="setting-group">
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.useFoilDetection}
                onChange={(e) => handleChange('useFoilDetection', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Foil Detection</span>
            </label>
            <p className="setting-description">
              Detect foil/holographic cards for variant matching
            </p>
          </div>

          {/* Geometric Verification Toggle */}
          <div className="setting-group">
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.useGeometric}
                onChange={(e) => handleChange('useGeometric', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Geometric Verification (ORB)</span>
            </label>
            <p className="setting-description">
              Use feature matching for more accurate identification. Recommended for optimal results.
            </p>
          </div>

          {/* Multi-Frame Fusion */}
          <div className="setting-group">
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.multiFrameEnabled}
                onChange={(e) => handleChange('multiFrameEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Multi-Frame Fusion ⚡</span>
            </label>
            <p className="setting-description">
              Capture and fuse multiple frames for +15-20% accuracy. Adds ~300ms per card.
            </p>
            
            {settings.multiFrameEnabled && (
              <div className="sub-setting">
                <label htmlFor="frame-count" className="setting-label">
                  Frame Count: {settings.multiFrameCount}
                </label>
                <div className="setting-slider-container">
                  <input
                    id="frame-count"
                    type="range"
                    min="2"
                    max="5"
                    step="1"
                    value={settings.multiFrameCount}
                    onChange={(e) => handleChange('multiFrameCount', parseInt(e.target.value, 10))}
                    className="setting-slider"
                  />
                  <span className="setting-value">{settings.multiFrameCount} frames</span>
                </div>
                <p className="setting-hint">
                  More frames = higher accuracy but slower (3 recommended for shops)
                </p>
              </div>
            )}
          </div>

          {/* Confidence Threshold Settings */}
          <div className="setting-group">
            <h3 className="setting-section-title">🎯 Confidence Thresholds</h3>

            {/* Auto-add MODERATE */}
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.autoAddModerate}
                onChange={(e) => handleChange('autoAddModerate', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Auto-add MODERATE confidence</span>
            </label>
            <p className="setting-description">
              When ON: AUTO-add MODERATE + HIGH (recommended for fast scanning)<br/>
              When OFF: Only AUTO-add HIGH, MODERATE requires manual review
            </p>
          </div>

          <div className="setting-group">
            {/* Accept LOW confidence */}
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={settings.acceptLowConfidence}
                onChange={(e) => handleChange('acceptLowConfidence', e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Accept LOW confidence with review</span>
            </label>
            <p className="setting-description">
              Show LOW confidence cards for manual review instead of rejecting.<br/>
              {settings.acceptLowConfidence && (
                <span className="setting-warning">⚠️ Requires manual confirmation for each LOW card</span>
              )}
            </p>
          </div>

          {/* Advanced: Top-K */}
          <div className="setting-group">
            <label htmlFor="top-k" className="setting-label">
              Candidate Count (Top-K)
            </label>
            <div className="setting-slider-container">
              <input
                id="top-k"
                type="range"
                min="10"
                max="50"
                step="5"
                value={settings.topK}
                onChange={(e) => handleChange('topK', parseInt(e.target.value, 10))}
                className="setting-slider"
              />
              <span className="setting-value">{settings.topK}</span>
            </div>
            <p className="setting-description">
              Number of candidates to evaluate. Higher = more accurate but slower.
            </p>
          </div>

          {/* Performance Estimate */}
          <div className="setting-group setting-info">
            <h3>Estimated Performance</h3>
            <div className="performance-estimate">
              <div className="perf-item">
                <span className="perf-label">Initialization:</span>
                <span className="perf-value">~3-5 seconds</span>
              </div>
              <div className="perf-item">
                <span className="perf-label">Per-card scan:</span>
                <span className="perf-value">
                  ~{estimateSpeed(settings)}ms
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button className="btn btn-primary" onClick={onClose}>
            Close
          </button>
          <p style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
            Settings are automatically saved
          </p>
        </div>
      </div>
    </div>
  );
});

/**
 * Estimate identification speed based on settings
 */
function estimateSpeed(settings: IdentificationSettings): number {
  let baseSpeed = 100; // Base DINOv2 + FAISS

  if (settings.useOCR) baseSpeed += 170;
  if (settings.useFoilDetection) baseSpeed += 30;
  if (settings.useGeometric) baseSpeed += 150;

  // Top-K impact (linear approximation)
  baseSpeed += settings.topK * 2;

  return Math.round(baseSpeed);
}
