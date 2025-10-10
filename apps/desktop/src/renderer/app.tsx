import React, { useEffect, useState, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { CameraView } from './components/CameraView';
import { CardStack, CardStackItem } from './components/CardStack';
import { SettingsPanel, IdentificationSettings } from './components/SettingsPanel';
import './styles.css';

interface SystemStatus {
  identifier: { initialized: boolean; ready: boolean; running: boolean };
}

// Default settings
const DEFAULT_SETTINGS: IdentificationSettings = {
  tcgGame: 'one-piece',
  useOCR: false,
  useFoilDetection: false,
  topK: 20,
  useGeometric: true,
};

// LocalStorage key
const SETTINGS_STORAGE_KEY = 'cardflux-settings';

const App: React.FC = () => {
  const [cards, setCards] = useState<CardStackItem[]>([]);
  const [isIdentifying, setIsIdentifying] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    identifier: { initialized: false, ready: false, running: false },
  });
  const [initError, setInitError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'warning';
    message: string;
  } | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<IdentificationSettings>(() => {
    // Load settings from localStorage
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.error('[App] Failed to load settings from localStorage:', error);
    }
    return DEFAULT_SETTINGS;
  });

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
      console.log('[App] Settings saved:', settings);
    } catch (error) {
      console.error('[App] Failed to save settings to localStorage:', error);
    }
  }, [settings]);

  // Initialize identification service on mount
  useEffect(() => {
    initializeSystem();
  }, []);

  const initializeSystem = async () => {
    try {
      console.log('[App] Initializing identification service...');
      const result = await window.identifier.initialize(settings.tcgGame);

      if (!result.success) {
        throw new Error(result.error || 'Failed to initialize');
      }

      // Get status
      const status = await window.identifier.getStatus();
      setSystemStatus((prev) => ({ ...prev, identifier: status }));

      console.log('[App] System ready');
      showNotification('success', 'System initialized - Ready to scan!');
    } catch (error: any) {
      console.error('[App] Initialization error:', error);
      setInitError(error.message || 'Failed to initialize system');
      showNotification('error', `Initialization failed: ${error.message}`);
    }
  };

  const handleCapture = useCallback(
    async (imagePath: string) => {
      if (isIdentifying) return;

      // Optimistic UI update - immediate feedback
      setIsIdentifying(true);

      try {
        console.log('[App] Identifying card:', imagePath);

        const result = await window.identifier.identify(imagePath, {
          topK: settings.topK,
          useGeometric: settings.useGeometric,
          skipOCR: !settings.useOCR,
          skipFoil: !settings.useFoilDetection,
          tcgHint: settings.tcgGame,
        });

        if (!result.success) {
          throw new Error(result.error || 'Identification failed');
        }

        const { card, confidence } = result.result;

        // Only add HIGH confidence cards to stack
        if (confidence === 'HIGH') {
          // Get price
          const price = card.prices?.normal?.market || card.prices?.foil?.market || 0;

          const stackItem: CardStackItem = {
            id: `${card.productId}-${Date.now()}`,
            name: card.name,
            number: card.number,
            rarity: card.rarity,
            set: card.set,
            price: price,
            confidence: confidence,
            timestamp: Date.now(),
            productId: card.productId,
          };

          setCards((prev) => [stackItem, ...prev]);
          showNotification('success', `Added: ${card.name} ($${price.toFixed(2)})`);

          // Visual feedback
          playSuccessSound();
        } else {
          // Low confidence warning
          showNotification(
            'warning',
            `Low confidence (${confidence}) - Not added to stack. Try again with better positioning.`
          );
        }

        console.log('[App] Identification complete:', card.name, confidence);
      } catch (error: any) {
        console.error('[App] Identification error:', error);
        showNotification('error', `Identification failed: ${error.message}`);
      } finally {
        setIsIdentifying(false);
      }
    },
    [isIdentifying, settings]
  );

  const handleClearStack = useCallback(() => {
    if (cards.length === 0) return;

    const totalValue = cards.reduce((sum, card) => sum + card.price, 0);

    if (
      window.confirm(
        `Clear ${cards.length} cards totaling $${totalValue.toFixed(2)}?\n\nThis cannot be undone.`
      )
    ) {
      setCards([]);
      showNotification('success', 'Stack cleared');
    }
  }, [cards]);

  const handleExportStack = useCallback(() => {
    if (cards.length === 0) {
      showNotification('warning', 'Nothing to export');
      return;
    }

    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const filename = `cardflux-scan-${timestamp}.csv`;

      const totalValue = cards.reduce((sum, card) => sum + card.price, 0);

      let csv = 'Card Name,Number,Rarity,Set,Price,Confidence,Timestamp\n';

      cards.forEach((card) => {
        const time = new Date(card.timestamp).toLocaleString();
        csv += `"${card.name}","${card.number}","${card.rarity}","${card.set}","$${card.price.toFixed(
          2
        )}","${card.confidence}","${time}"\n`;
      });

      csv += `\nTOTAL,,,,"$${totalValue.toFixed(2)}",\n`;
      csv += `\nCard Count: ${cards.length}\n`;
      csv += `Export Date: ${new Date().toLocaleString()}\n`;

      // Create download
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      showNotification('success', `Exported ${cards.length} cards to ${filename}`);
    } catch (error: any) {
      console.error('[App] Export error:', error);
      showNotification('error', `Export failed: ${error.message}`);
    }
  }, [cards]);

  const handleRemoveCard = useCallback((id: string) => {
    setCards((prev) => prev.filter((card) => card.id !== id));
    showNotification('success', 'Card removed');
  }, []);

  const showNotification = (
    type: 'success' | 'error' | 'warning',
    message: string
  ) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const playSuccessSound = () => {
    // Optional: Play a success sound
    // const audio = new Audio('/assets/success.mp3');
    // audio.play().catch(() => {});
  };

  if (initError) {
    return (
      <div className="app-container error-state">
        <div className="error-panel">
          <div className="error-icon">⚠️</div>
          <h1>System Error</h1>
          <p>{initError}</p>
          <div className="error-help">
            <h3>Troubleshooting:</h3>
            <ul>
              <li>Ensure Python 3.10+ is installed</li>
              <li>Check that all Python dependencies are installed</li>
              <li>Verify FAISS index files exist in artifacts/faiss/</li>
              <li>Check the console for detailed error messages</li>
            </ul>
          </div>
          <button className="btn btn-primary" onClick={initializeSystem}>
            Retry Initialization
          </button>
        </div>
      </div>
    );
  }

  const isSystemReady = systemStatus.identifier.ready;

  return (
    <div className="app-container">
      {/* Top Bar */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">
            <span className="app-icon">🎴</span>
            CardFlux Scanner
          </h1>
          <div className="game-badge">
            {settings.tcgGame === 'one-piece' && 'One Piece TCG'}
            {settings.tcgGame === 'pokemon' && 'Pokémon TCG'}
            {settings.tcgGame === 'magic' && 'Magic: The Gathering'}
            {settings.tcgGame === 'yugioh' && 'Yu-Gi-Oh!'}
            {settings.tcgGame === 'digimon' && 'Digimon Card Game'}
            {settings.tcgGame === 'lorcana' && 'Disney Lorcana'}
          </div>
        </div>

        <div className="header-right">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowSettings(true)}
            aria-label="Open settings"
          >
            ⚙️ Settings
          </button>
          <div className="system-status">
            <div className={`status-indicator ${isSystemReady ? 'ready' : 'loading'}`}>
              <span className="status-dot" />
              <span className="status-text">
                {isSystemReady ? 'Ready' : 'Initializing...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* Left Panel - Camera */}
        <div className="main-left">
          <CameraView onCapture={handleCapture} isIdentifying={isIdentifying} />
        </div>

        {/* Right Panel - Card Stack */}
        <div className="main-right">
          <CardStack
            cards={cards}
            onClear={handleClearStack}
            onExport={handleExportStack}
            onRemoveCard={handleRemoveCard}
          />
        </div>
      </main>

      {/* Notifications */}
      {notification && (
        <div className={`notification notification-${notification.type}`}>
          <div className="notification-content">
            <span className="notification-icon">
              {notification.type === 'success' && '✓'}
              {notification.type === 'error' && '✕'}
              {notification.type === 'warning' && '⚠'}
            </span>
            <span className="notification-message">{notification.message}</span>
          </div>
          <button
            className="notification-close"
            onClick={() => setNotification(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <SettingsPanel
          settings={settings}
          onSettingsChange={(newSettings) => {
            setSettings(newSettings);
            showNotification('success', 'Settings saved');
          }}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-help">
          <span className="help-item">
            <kbd>SPACE</kbd> Capture Card
          </span>
          <span className="help-item">
            <kbd>ESC</kbd> Clear notification
          </span>
        </div>
        <div className="footer-stats">
          <span>Cards Scanned: {cards.length}</span>
          <span className="separator">•</span>
          <span>
            Total Value: ${cards.reduce((sum, card) => sum + card.price, 0).toFixed(2)}
          </span>
        </div>
      </footer>
    </div>
  );
};

// Mount the React app
console.log('[App] Starting React mount...');
const container = document.getElementById('root');
console.log('[App] Container found:', container);

if (container) {
  try {
    console.log('[App] Creating React root...');
    const root = createRoot(container);
    console.log('[App] Rendering app...');
    root.render(<App />);
    console.log('[App] App rendered successfully');
  } catch (error) {
    console.error('[App] Error mounting React app:', error);
  }
} else {
  console.error('[App] Root container not found!');
}

export default App;
