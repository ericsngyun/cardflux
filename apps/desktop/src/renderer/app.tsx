import React, { useEffect, useState, useCallback, useMemo } from 'react';
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
  multiFrameEnabled: false,  // Off by default (can enable in settings)
  multiFrameCount: 3,         // 3 frames when enabled
};

// LocalStorage keys
const SETTINGS_STORAGE_KEY = 'cardflux-settings';
const SYNC_STATUS_STORAGE_KEY = 'cardflux-sync-status';

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
  const [showCaptureFlash, setShowCaptureFlash] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<number | null>(() => {
    try {
      const stored = localStorage.getItem(SYNC_STATUS_STORAGE_KEY);
      return stored ? JSON.parse(stored).timestamp : null;
    } catch {
      return null;
    }
  });
  const [scanStats, setScanStats] = useState({
    totalScans: 0,
    highConfidence: 0,
    moderateConfidence: 0,
    lowConfidence: 0,
    sessionStart: Date.now(),
  });
  const [capturedFrames, setCapturedFrames] = useState<string[]>([]);  // For multi-frame fusion
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

      // Capture flash animation - instant professional feedback
      setShowCaptureFlash(true);
      setTimeout(() => setShowCaptureFlash(false), 150);

      // Multi-frame fusion logic
      if (settings.multiFrameEnabled) {
        const newFrames = [...capturedFrames, imagePath];
        setCapturedFrames(newFrames);

        // Show progress notification
        const remaining = settings.multiFrameCount - newFrames.length;
        if (remaining > 0) {
          showNotification('warning', `Frame ${newFrames.length}/${settings.multiFrameCount} captured - ${remaining} more...`);
          return; // Wait for more frames
        }

        // All frames captured - run multi-frame identification
        console.log('[App] Multi-frame identification:', newFrames.length, 'frames');
        setIsIdentifying(true);
        setCapturedFrames([]); // Reset for next card

        try {
          const result = await window.identifier.identifyMultiFrame(newFrames, {
            topK: settings.topK,
            useGeometric: settings.useGeometric,
            tcgHint: settings.tcgGame,
          });

          if (!result.success) {
            throw new Error(result.error || 'Multi-frame identification failed');
          }

          const { card, confidence, multiFrame } = result.result;
          
          // Show fusion info
          if (multiFrame) {
            console.log('[App] Multi-frame fusion:', multiFrame);
          }

          const price = card.prices?.normal?.market || card.prices?.foil?.market || 0;

          // Update scan statistics
          setScanStats((prev) => ({
            ...prev,
            totalScans: prev.totalScans + 1,
            highConfidence: prev.highConfidence + (confidence === 'HIGH' ? 1 : 0),
            moderateConfidence: prev.moderateConfidence + (confidence === 'MODERATE' ? 1 : 0),
            lowConfidence: prev.lowConfidence + (confidence === 'LOW' ? 1 : 0),
          }));

          // Accept HIGH and MODERATE confidence
          if (confidence === 'HIGH' || confidence === 'MODERATE') {
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

            const emoji = multiFrame?.confidenceBoost ? '⚡' : confidence === 'HIGH' ? '✓' : '~';
            const suffix = multiFrame ? ` (${multiFrame.fusionVotes.toFixed(1)} votes)` : '';
            showNotification(
              confidence === 'HIGH' ? 'success' : 'warning',
              `${emoji} ${card.name} - $${price.toFixed(2)} (${confidence})${suffix}`
            );

            playSuccessSound();
          } else {
            showNotification(
              'error',
              `Low confidence: Found "${card.name}" but not confident. Try: better lighting, center card, reduce glare.`
            );
          }

          console.log('[App] Multi-frame complete:', card.name, confidence);
        } catch (error: any) {
          console.error('[App] Multi-frame identification error:', error);
          showNotification('error', `Multi-frame identification failed: ${error.message}`);
          setCapturedFrames([]); // Reset on error
        } finally {
          setIsIdentifying(false);
        }

        return; // Exit after multi-frame processing
      }

      // Single-frame identification (original logic)
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
        const price = card.prices?.normal?.market || card.prices?.foil?.market || 0;

        // Update scan statistics
        setScanStats((prev) => ({
          ...prev,
          totalScans: prev.totalScans + 1,
          highConfidence: prev.highConfidence + (confidence === 'HIGH' ? 1 : 0),
          moderateConfidence: prev.moderateConfidence + (confidence === 'MODERATE' ? 1 : 0),
          lowConfidence: prev.lowConfidence + (confidence === 'LOW' ? 1 : 0),
        }));

        // Accept HIGH and MODERATE confidence (60%+ threshold)
        if (confidence === 'HIGH' || confidence === 'MODERATE') {
          // Check for duplicates in last 30 seconds
          const now = Date.now();
          const recentDuplicate = cards.find(
            (c) => c.productId === card.productId && now - c.timestamp < 30000
          );

          if (recentDuplicate) {
            const secondsAgo = Math.floor((now - recentDuplicate.timestamp) / 1000);
            showNotification(
              'warning',
              `Duplicate: ${card.name} was scanned ${secondsAgo}s ago. Added anyway.`
            );
          }

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

          const confidenceEmoji = confidence === 'HIGH' ? '✓' : '~';
          showNotification(
            confidence === 'HIGH' ? 'success' : 'warning',
            `${confidenceEmoji} ${card.name} - $${price.toFixed(2)} (${confidence})`
          );

          playSuccessSound();
        } else {
          // Low confidence - show what was identified with helpful tips
          showNotification(
            'error',
            `Low confidence: Found "${card.name}" but not confident. Try: better lighting, center card, reduce glare.`
          );
        }

        console.log('[App] Identification complete:', card.name, confidence);
      } catch (error: any) {
        console.error('[App] Identification error:', error);
        showNotification('error', `Identification failed: ${error.message}`);
        setScanStats((prev) => ({ ...prev, totalScans: prev.totalScans + 1, lowConfidence: prev.lowConfidence + 1 }));
      } finally {
        setIsIdentifying(false);
      }
    },
    [isIdentifying, settings, cards]
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

  const handleSync = useCallback(async () => {
    if (isSyncing) return;

    setIsSyncing(true);
    showNotification('warning', 'Syncing card data and prices...');

    try {
      console.log('[App] Starting data sync...');

      // Call sync IPC handler
      const result = await window.sync.syncData(settings.tcgGame);

      if (!result.success) {
        throw new Error(result.error || 'Sync failed');
      }

      // Update last sync time
      const now = Date.now();
      setLastSyncTime(now);
      localStorage.setItem(
        SYNC_STATUS_STORAGE_KEY,
        JSON.stringify({ timestamp: now, game: settings.tcgGame })
      );

      showNotification(
        'success',
        `Sync complete! Updated ${result.updatedCards || 0} cards, ${result.newCards || 0} new cards.`
      );

      console.log('[App] Sync complete:', result);
    } catch (error: any) {
      console.error('[App] Sync error:', error);
      showNotification('error', `Sync failed: ${error.message}`);
    } finally {
      setIsSyncing(false);
    }
  }, [isSyncing, settings.tcgGame]);

  // Calculate sync status
  const getSyncStatus = useMemo(() => {
    if (!lastSyncTime) {
      return { text: 'Never synced', status: 'warning', needsSync: true };
    }

    const now = Date.now();
    const diffMs = now - lastSyncTime;
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffHours / 24;

    if (diffDays >= 3) {
      return {
        text: `${Math.floor(diffDays)} days ago`,
        status: 'error',
        needsSync: true,
      };
    } else if (diffDays >= 1) {
      return {
        text: `${Math.floor(diffDays)} day${Math.floor(diffDays) > 1 ? 's' : ''} ago`,
        status: 'warning',
        needsSync: true,
      };
    } else if (diffHours >= 1) {
      return {
        text: `${Math.floor(diffHours)} hour${Math.floor(diffHours) > 1 ? 's' : ''} ago`,
        status: 'success',
        needsSync: false,
      };
    } else {
      return {
        text: 'Just now',
        status: 'success',
        needsSync: false,
      };
    }
  }, [lastSyncTime]);

  // Global keyboard shortcuts - defined after all handlers
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Don't trigger if user is in settings or typing
      if (showSettings) return;

      switch (e.key.toLowerCase()) {
        case 'c':
          if (cards.length > 0) handleClearStack();
          break;
        case 'e':
          if (cards.length > 0) handleExportStack();
          break;
        case 's':
          setShowSettings(true);
          break;
        case 'escape':
          setNotification(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [showSettings, cards, handleClearStack, handleExportStack]);

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

  // Memoize total value calculation for performance
  const totalValue = useMemo(() => {
    return cards.reduce((sum, card) => sum + card.price, 0);
  }, [cards]);

  // Calculate scan statistics
  const sessionDuration = Math.floor((Date.now() - scanStats.sessionStart) / 60000); // minutes
  const scansPerMinute = sessionDuration > 0 ? (scanStats.totalScans / sessionDuration).toFixed(1) : '0.0';
  const successRate = scanStats.totalScans > 0
    ? (((scanStats.highConfidence + scanStats.moderateConfidence) / scanStats.totalScans) * 100).toFixed(0)
    : '0';

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
          {/* Sync Status & Button */}
          <div className="sync-container">
            <div className={`sync-status sync-status-${getSyncStatus.status}`}>
              <span className="sync-icon">🔄</span>
              <div className="sync-info">
                <span className="sync-label">Last Sync</span>
                <span className="sync-time">{getSyncStatus.text}</span>
              </div>
            </div>
            <button
              className={`btn btn-sync btn-sm ${isSyncing ? 'btn-syncing' : ''} ${
                getSyncStatus.needsSync ? 'btn-sync-needed' : ''
              }`}
              onClick={handleSync}
              disabled={isSyncing}
              aria-label="Sync data"
              title={getSyncStatus.needsSync ? 'Sync recommended - data may be outdated' : 'Sync card data and prices'}
            >
              {isSyncing ? (
                <>
                  <span className="spinner-sm" />
                  Syncing...
                </>
              ) : (
                <>
                  🔄 Sync
                </>
              )}
            </button>
          </div>

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

      {/* Capture Flash */}
      {showCaptureFlash && <div className="capture-flash" />}

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-help">
          <span className="help-item">
            <kbd>SPACE</kbd> Capture
          </span>
          <span className="help-item">
            <kbd>C</kbd> Clear
          </span>
          <span className="help-item">
            <kbd>E</kbd> Export
          </span>
          <span className="help-item">
            <kbd>S</kbd> Settings
          </span>
        </div>
        <div className="footer-stats">
          <span>Cards: {cards.length}</span>
          <span className="separator">•</span>
          <span>Value: ${totalValue.toFixed(2)}</span>
          {scanStats.totalScans > 0 && (
            <>
              <span className="separator">•</span>
              <span>Success: {successRate}%</span>
              <span className="separator">•</span>
              <span>{scansPerMinute} scans/min</span>
            </>
          )}
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
