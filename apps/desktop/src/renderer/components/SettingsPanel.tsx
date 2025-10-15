import React from 'react';

export interface IdentificationSettings {
  tcgGame: string;
  useOCR: boolean;
  useFoilDetection: boolean;
  topK: number;
  useGeometric: boolean;
}

interface SettingsPanelProps {
  settings: IdentificationSettings;
  onSettingsChange: (settings: IdentificationSettings) => void;
  onClose: () => void;
}

const TCG_GAMES = [
  { value: 'one-piece', label: 'One Piece TCG' },
  { value: 'pokemon', label: 'Pokémon TCG' },
  { value: 'magic', label: 'Magic: The Gathering' },
  { value: 'yugioh', label: 'Yu-Gi-Oh!' },
  { value: 'digimon', label: 'Digimon Card Game' },
  { value: 'lorcana', label: 'Disney Lorcana' },
];

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
              onChange={(e) => handleChange('tcgGame', e.target.value)}
            >
              {TCG_GAMES.map((game) => (
                <option key={game.value} value={game.value}>
                  {game.label}
                </option>
              ))}
            </select>
            <p className="setting-description">
              Select the card game you're scanning for better accuracy
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
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={onClose}>
            Save Settings
          </button>
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
