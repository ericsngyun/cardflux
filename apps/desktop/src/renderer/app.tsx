import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { CameraView } from './components/CameraView';
import { CardStack, CardStackItem } from './components/CardStack';
import { SettingsPanel, IdentificationSettings } from './components/SettingsPanel';
import { ErrorBoundary } from './components/ErrorBoundary';
import { createModuleLogger } from './utils/logger';
import { APP_CONSTANTS } from './constants';
import './styles.css';

const logger = createModuleLogger('App');

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
  multiFrameEnabled: false,    // Off by default (can enable in settings)
  multiFrameCount: 3,           // 3 frames when enabled
  acceptLowConfidence: false,   // OFF by default (only accept HIGH+MODERATE)
  autoAddModerate: true,        // ON by default (auto-add MODERATE)
};

// Use constants for storage keys
const SETTINGS_STORAGE_KEY = APP_CONSTANTS.SETTINGS_STORAGE_KEY;
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

  // Use ref to track if we've shown the "System initialized" notification
  const hasShownReadyNotification = useRef(false);
  const [scanStats, setScanStats] = useState({
    totalScans: 0,
    highConfidence: 0,
    moderateConfidence: 0,
    lowConfidence: 0,
    sessionStart: Date.now(),
  });
  const [capturedFrames, setCapturedFrames] = useState<string[]>([]);  // For multi-frame fusion
  const [pendingReview, setPendingReview] = useState<{
    card: any;
    confidence: string;
    timestamp: number;
  } | null>(null);  // For manual review of MODERATE/LOW confidence
  const [settings, setSettings] = useState<IdentificationSettings>(() => {
    // Load settings from localStorage (or file fallback)
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
      }
    } catch (error) {
      logger.warn('Failed to load settings from localStorage, will try file fallback', error);
      // Note: File loading happens asynchronously in useEffect below
    }
    return DEFAULT_SETTINGS;
  });

  // Helper functions (defined early to avoid "used before declaration" errors)
  const showNotification = useCallback((
    type: 'success' | 'error' | 'warning',
    message: string
  ) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), APP_CONSTANTS.NOTIFICATION_DURATION_MS);
  }, []);

  const playSuccessSound = useCallback(() => {
    // Optional: Play a success sound
    // const audio = new Audio('/assets/success.mp3');
    // audio.play().catch(() => {});
  }, []);

  // HIGH SEVERITY FIX: Persist settings with fallback when localStorage fails
  useEffect(() => {
    const saveSettings = async () => {
      try {
        // Try localStorage first
        localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
        logger.debug('Settings saved to localStorage', { settings });
      } catch (error) {
        logger.warn('localStorage failed, using file fallback', error);

        // Fallback: Save to file via IPC
        try {
          const result = await window.settings.saveToFile(settings);
          if (result.success) {
            showNotification('warning', 'Settings saved to file (localStorage unavailable)');
          } else {
            logger.error('File fallback failed', undefined, { error: result.error });
            showNotification('error', 'Failed to save settings! Please check disk space.');
          }
        } catch (fileError) {
          logger.error('Failed to save settings to file', fileError);
          showNotification('error', 'Failed to save settings! Please check disk space.');
        }
      }
    };

    saveSettings();
  }, [settings, showNotification]);

  // Load settings from file on startup if localStorage empty
  useEffect(() => {
    const loadSettingsFromFile = async () => {
      try {
        const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
        if (!stored) {
          // localStorage empty, try loading from file
          const result = await window.settings.loadFromFile();
          if (result.success && result.settings) {
            setSettings({ ...DEFAULT_SETTINGS, ...result.settings });
            logger.info('Settings loaded from file fallback', { settings: result.settings });
          }
        }
      } catch (error) {
        logger.warn('Could not load settings from file fallback', error);
      }
    };

    loadSettingsFromFile();
  }, []); // Run once on mount

  // Poll Python service status until ready (no re-initialization)
  useEffect(() => {
    let startupPollInterval: NodeJS.Timeout | null = null;
    let healthCheckInterval: NodeJS.Timeout | null = null;
    let attempts = 0;
    const maxStartupAttempts = 30;

    const startupPoll = async () => {
      // Initial check
      const initialStatus = await checkSystemStatus();

      // If already ready on first check, skip to health check mode
      if (initialStatus?.ready) {
        logger.info('Service already ready - starting health check mode');
        healthCheckInterval = setInterval(checkSystemStatus, 30000);
        return;
      }

      // Otherwise, poll aggressively every 1 second during startup
      startupPollInterval = setInterval(async () => {
        attempts++;
        const status = await checkSystemStatus();

        // Once ready, stop startup polling and switch to health check mode
        if (status?.ready) {
          logger.info('Service became ready - switching to health check mode (30s intervals)');
          if (startupPollInterval) {
            clearInterval(startupPollInterval);
            startupPollInterval = null;
          }
          // Switch to occasional health check (every 30 seconds)
          healthCheckInterval = setInterval(checkSystemStatus, 30000);
          return;
        }

        // Give up after 30 seconds if not ready
        if (attempts >= maxStartupAttempts && !status?.ready) {
          if (startupPollInterval) {
            clearInterval(startupPollInterval);
            startupPollInterval = null;
          }
          setInitError('Python service failed to start within 30 seconds');
        }
      }, 1000);
    };

    startupPoll();

    return () => {
      if (startupPollInterval) clearInterval(startupPollInterval);
      if (healthCheckInterval) clearInterval(healthCheckInterval);
    };
  }, []);

  const checkSystemStatus = async () => {
    try {
      // Don't call initialize - main process already did it
      // Just check if it's ready yet
      const status = await window.identifier.getStatus();

      // Only show notification ONCE when system first becomes ready
      const isNowReady = status.initialized && status.ready;

      setSystemStatus((prev) => ({ ...prev, identifier: status }));

      if (isNowReady && !hasShownReadyNotification.current) {
        // First time becoming ready - show notification once
        logger.info('System ready - showing notification');
        hasShownReadyNotification.current = true;
        showNotification('success', 'System initialized - Ready to scan!');
      }

      return status;
    } catch (error: any) {
      logger.error('Status check error', error);
      // Don't set init error yet - Python might still be starting
      if (systemStatus.identifier.ready) {
        // Only show error if we were ready before
        setInitError(error.message || 'Failed to connect to identification service');
      }
      return null;
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
        logger.info('Multi-frame identification', { frameCount: newFrames.length });
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
            logger.debug('Multi-frame fusion stats', multiFrame);
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
              imageUrl: card.imageUrl,  // FIX: Add image URL for card thumbnail display
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

          logger.info('Multi-frame complete', { card: card.name, confidence });
        } catch (error: any) {
          logger.error('Multi-frame identification error', error);
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
        logger.debug('Identifying card', { imagePath });

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

        // Confidence threshold logic based on settings
        const shouldAutoAdd =
          confidence === 'HIGH' ||
          (confidence === 'MODERATE' && settings.autoAddModerate);

        const shouldReview =
          (confidence === 'MODERATE' && !settings.autoAddModerate) ||
          (confidence === 'LOW' && settings.acceptLowConfidence);

        if (shouldAutoAdd) {
          // AUTO-ADD: HIGH or MODERATE (if autoAddModerate enabled)
          // Check for duplicates in configured window
          const now = Date.now();
          const recentDuplicate = cards.find(
            (c) => c.productId === card.productId && now - c.timestamp < APP_CONSTANTS.DUPLICATE_DETECTION_WINDOW_MS
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
            imageUrl: card.imageUrl,  // Add image URL for thumbnail
          };

          setCards((prev) => [stackItem, ...prev]);

          const confidenceEmoji = confidence === 'HIGH' ? '✓' : '~';
          showNotification(
            confidence === 'HIGH' ? 'success' : 'warning',
            `${confidenceEmoji} ${card.name} - $${price.toFixed(2)} (${confidence})`
          );

          playSuccessSound();
        } else if (shouldReview) {
          // MANUAL REVIEW: Show confirmation dialog
          setPendingReview({
            card: { ...card, price },
            confidence,
            timestamp: Date.now(),
          });

          showNotification(
            'warning',
            `${confidence} confidence: "${card.name}" - Please review and confirm`
          );
        } else {
          // REJECTED: Low confidence not accepted
          showNotification(
            'error',
            `${confidence} confidence: Found "${card.name}" but not confident. ${
              confidence === 'LOW'
                ? 'Enable "Accept LOW confidence" in Settings to review these cards.'
                : 'Enable "Auto-add MODERATE" in Settings for faster scanning.'
            }`
          );
        }

        logger.info('Identification complete', { card: card.name, confidence });
      } catch (error: any) {
        logger.error('Identification error', error);

        // HIGH SEVERITY FIX: Check if error is rate limit and provide user feedback
        const errorMsg = error.message || error.toString();
        if (errorMsg.includes('rate limit') || errorMsg.includes('Too many')) {
          showNotification('warning', '⏱ Please wait a moment before scanning again');
        } else if (errorMsg.includes('Service not initialized')) {
          showNotification('error', 'System still initializing. Please wait...');
        } else {
          showNotification('error', `Identification failed: ${errorMsg}`);
        }

        setScanStats((prev) => ({ ...prev, totalScans: prev.totalScans + 1, lowConfidence: prev.lowConfidence + 1 }));
      } finally {
        setIsIdentifying(false);
      }
    },
    [isIdentifying, settings, cards, capturedFrames, showNotification, playSuccessSound]
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
  }, [cards, showNotification]);

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
  }, [cards, showNotification]);

  const handleRemoveCard = useCallback((id: string) => {
    setCards((prev) => prev.filter((card) => card.id !== id));
    showNotification('success', 'Card removed');
  }, [showNotification]);

  const handleAcceptReview = useCallback(() => {
    if (!pendingReview) return;

    const { card, confidence } = pendingReview;

    const stackItem: CardStackItem = {
      id: `${card.productId}-${Date.now()}`,
      name: card.name,
      number: card.number,
      rarity: card.rarity,
      set: card.set,
      price: card.price,
      confidence: confidence,
      timestamp: Date.now(),
      productId: card.productId,
      imageUrl: card.imageUrl,  // Stock TCGPlayer image for thumbnail
    };

    setCards((prev) => [stackItem, ...prev]);
    setPendingReview(null);

    showNotification('success', `✓ Added: ${card.name} - $${card.price.toFixed(2)} (${confidence})`);
    playSuccessSound();
  }, [pendingReview, showNotification, playSuccessSound]);

  const handleRejectReview = useCallback(() => {
    if (!pendingReview) return;

    setPendingReview(null);
    showNotification('warning', 'Card rejected - scan again with better positioning');
  }, [pendingReview, showNotification]);

  // Keyboard shortcuts for review modal (Enter=Accept, Esc=Reject)
  useEffect(() => {
    if (!pendingReview) return;

    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleAcceptReview();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleRejectReview();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [pendingReview, handleAcceptReview, handleRejectReview]);

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
  }, [isSyncing, settings.tcgGame, showNotification]);

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

  // ⚠️ IMPORTANT: All hooks must be called BEFORE any conditional returns (Rules of Hooks)
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

  const isSystemReady = systemStatus.identifier.ready;

  // Conditional rendering AFTER all hooks
  // Show loading screen while Python service is initializing
  if (!systemStatus.identifier.ready && !initError) {
    return (
      <div className="app-container loading-state">
        <div className="loading-panel">
          <div className="loading-spinner-large"></div>
          <h1>Initializing CardFlux</h1>
          <p className="loading-message">Loading AI models and card database...</p>
          <div className="loading-steps">
            <div className={`loading-step ${systemStatus.identifier.initialized ? 'complete' : 'active'}`}>
              <span className="step-icon">{systemStatus.identifier.initialized ? '✓' : '⏳'}</span>
              <span>Starting Python service</span>
            </div>
            <div className={`loading-step ${systemStatus.identifier.ready ? 'complete' : systemStatus.identifier.initialized ? 'active' : ''}`}>
              <span className="step-icon">{systemStatus.identifier.ready ? '✓' : systemStatus.identifier.initialized ? '⏳' : '○'}</span>
              <span>Loading DINOv2 vision model</span>
            </div>
            <div className={`loading-step ${systemStatus.identifier.ready ? 'complete' : ''}`}>
              <span className="step-icon">{systemStatus.identifier.ready ? '✓' : '○'}</span>
              <span>Loading card index (5,390 cards)</span>
            </div>
          </div>
          <p className="loading-hint">This takes 3-5 seconds on first startup</p>
        </div>
      </div>
    );
  }

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
          <button className="btn btn-primary" onClick={checkSystemStatus}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Top Bar */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">
            <span className="app-icon">♠</span>
            CardFlux
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
              <svg className="sync-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M13.6533 2.34667C12.1064 0.79991 10.0494 0 8.00003 0C5.95066 0 3.89366 0.79991 2.34667 2.34667C0.79991 3.89343 0 5.95066 0 8C0 10.0494 0.79991 12.1064 2.34667 13.6533C3.89366 15.2001 5.95066 16 8.00003 16C10.0494 16 12.1064 15.2001 13.6533 13.6533C15.2001 12.1064 16 10.0494 16 8C16 5.95066 15.2001 3.89343 13.6533 2.34667ZM11.4133 3.58667L13.0667 5.24L9.33337 8.97333L5.6 5.24L7.25333 3.58667L8.66667 5V2.66667H10V5L11.4133 3.58667Z" fill="currentColor" opacity="0.7"/>
              </svg>
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
                'Sync Now'
              )}
            </button>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowSettings(true)}
            aria-label="Open settings"
          >
            Settings
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
              {notification.type === 'success' && (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM8 15L3 10L4.41 8.59L8 12.17L15.59 4.58L17 6L8 15Z" fill="currentColor"/>
                </svg>
              )}
              {notification.type === 'error' && (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM11 15H9V13H11V15ZM11 11H9V5H11V11Z" fill="currentColor"/>
                </svg>
              )}
              {notification.type === 'warning' && (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM11 15H9V13H11V15ZM11 11H9V5H11V11Z" fill="currentColor"/>
                </svg>
              )}
            </span>
            <span className="notification-message">{notification.message}</span>
          </div>
          <button
            className="notification-close"
            onClick={() => setNotification(null)}
            aria-label="Close notification"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12.6 3.4L8 8L3.4 3.4L2 4.8L6.6 9.4L2 14L3.4 15.4L8 10.8L12.6 15.4L14 14L9.4 9.4L14 4.8L12.6 3.4Z" fill="currentColor"/>
            </svg>
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

      {/* Review Modal for MODERATE/LOW confidence */}
      {pendingReview && (
        <div className="review-modal-overlay" onClick={handleRejectReview} role="presentation">
          <div
            className="review-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-title"
            aria-describedby="review-description"
          >
            <div className="review-header">
              <h2 id="review-title">🔍 Manual Review Required</h2>
              <span className={`confidence-badge confidence-${pendingReview.confidence.toLowerCase()}`}>
                {pendingReview.confidence}
              </span>
            </div>

            <div className="review-content">
              <div className="review-card-info">
                <h3>{pendingReview.card.name}</h3>
                <div className="review-details">
                  <span><strong>Number:</strong> {pendingReview.card.number}</span>
                  <span><strong>Set:</strong> {pendingReview.card.set}</span>
                  <span><strong>Rarity:</strong> {pendingReview.card.rarity}</span>
                  <span><strong>Price:</strong> ${pendingReview.card.price.toFixed(2)}</span>
                </div>
              </div>

              <div className="review-message" id="review-description">
                <p>
                  {pendingReview.confidence === 'LOW'
                    ? '⚠️ This identification has LOW confidence. Please verify the card matches before adding.'
                    : '~ This identification has MODERATE confidence. Please verify before adding.'}
                </p>
                <p className="review-hint">
                  <kbd>Enter</kbd> to accept • <kbd>Esc</kbd> to reject
                </p>
              </div>
            </div>

            <div className="review-actions">
              <button
                className="btn btn-reject"
                onClick={handleRejectReview}
                aria-label="Reject and rescan card"
              >
                ✕ Reject & Rescan
              </button>
              <button
                className="btn btn-accept"
                onClick={handleAcceptReview}
                aria-label="Accept and add card to stack"
                autoFocus
              >
                ✓ Accept & Add
              </button>
            </div>
          </div>
        </div>
      )}

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
    console.log('[App] Rendering app with ErrorBoundary...');
    root.render(
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    );
    console.log('[App] App rendered successfully');
  } catch (error) {
    console.error('[App] Error mounting React app:', error);
    // Show fallback error UI if React fails to mount
    container.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #0a0a0a; color: #e0e0e0; font-family: sans-serif; text-align: center; padding: 20px;">
        <div>
          <h1 style="color: #f44336; font-size: 32px;">⚠️ Fatal Error</h1>
          <p style="font-size: 18px; margin: 20px 0;">CardFlux failed to start</p>
          <p style="font-size: 14px; color: #999;">${error instanceof Error ? error.message : String(error)}</p>
          <button onclick="window.location.reload()" style="margin-top: 20px; padding: 12px 24px; background: #4CAF50; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer;">
            Reload Application
          </button>
        </div>
      </div>
    `;
  }
} else {
  console.error('[App] Root container not found!');
}

export default App;
