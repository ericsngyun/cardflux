import { app, BrowserWindow, ipcMain, systemPreferences } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { setupIpcHandlers } from './ipc/handlers';
import { PythonIdentificationBridge } from './identifier/python-bridge';
import { logger } from './core/logger';
import { ResourceManager } from './core/resource-manager';
import { DataManager } from './core/data-manager';
import { createRateLimitMiddleware } from './core/rate-limiter';

let mainWindow: BrowserWindow | null = null;
let identificationService: PythonIdentificationBridge | null = null;
let resourceManager: ResourceManager | null = null;
let dataManager: DataManager | null = null;

// CRITICAL FIX: Add initialization lock to prevent race conditions
let isInitializing = false;

// HIGH SEVERITY FIX: Track active identification request for cancellation
let activeIdentificationAbortController: AbortController | null = null;

// HIGH SEVERITY FIX: Rate limiting to prevent DoS attacks via IPC spam
// Identification: Max 10 requests per 10 seconds (600ms avg per request)
const identifyRateLimiter = createRateLimitMiddleware({
  maxRequests: 10,
  windowMs: 10000,
  message: 'Too many identification requests. Please wait a moment.',
});

// Detection: Max 30 requests per 10 seconds (~333ms interval, we poll at 500ms)
const detectRateLimiter = createRateLimitMiddleware({
  maxRequests: 30,
  windowMs: 10000,
  message: 'Detection rate limit exceeded.',
});

// Camera capture: Max 20 captures per 10 seconds (user can spam SPACE key)
const captureRateLimiter = createRateLimitMiddleware({
  maxRequests: 20,
  windowMs: 10000,
  message: 'Too many capture requests. Please wait a moment.',
});

// Data sync: Max 1 request per 60 seconds (expensive operation)
const syncRateLimiter = createRateLimitMiddleware({
  maxRequests: 1,
  windowMs: 60000,
  message: 'Data sync already in progress. Please wait before syncing again.',
});

/**
 * Request camera permissions on macOS
 */
async function requestCameraPermission(): Promise<boolean> {
  if (process.platform === 'darwin') {
    try {
      const status = await systemPreferences.getMediaAccessStatus('camera');

      if (status === 'not-determined') {
        const granted = await systemPreferences.askForMediaAccess('camera');
        return granted;
      }

      return status === 'granted';
    } catch (error) {
      console.error('Error requesting camera permission:', error);
      return false;
    }
  }

  // Windows and Linux don't require explicit permission requests
  return true;
}

/**
 * Create the main application window
 */
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, '../preload/preload.js'),
      sandbox: false,
      // Disable background throttling for consistent performance
      backgroundThrottling: false,
    },
    title: 'CardFlux - Real-time Card Scanner',
    // Ensure smooth rendering
    backgroundColor: '#0a0a0a',
  });

  // Load the app from built files
  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // Open dev tools in development
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Performance optimizations - enable hardware acceleration
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('disable-gpu-vsync'); // Remove vsync for instant rendering
app.commandLine.appendSwitch('disable-frame-rate-limit'); // No FPS throttling

// App lifecycle events
app.whenReady().then(async () => {
  logger.info('App', 'Application starting', {
    version: app.getVersion(),
    isPackaged: app.isPackaged,
    platform: process.platform,
  });

  try {
    // Initialize resource manager
    logger.info('App', 'Initializing ResourceManager');
    resourceManager = ResourceManager.getInstance();
    await resourceManager.initialize();

    // Check if Python is available
    const pythonAvailable = await resourceManager.checkPythonAvailable();
    if (!pythonAvailable) {
      logger.error('App', 'Python runtime not available', undefined);
      // TODO: Show error dialog to user
      app.quit();
      return;
    }

    // Initialize data manager
    logger.info('App', 'Initializing DataManager');
    dataManager = DataManager.getInstance();
    await dataManager.initialize();

    // Check if game data is installed (for default game: one-piece)
    const gameInstalled = dataManager.isGameInstalled('one-piece');
    if (!gameInstalled) {
      logger.warn('App', 'Game data not installed, will need to download');
      // TODO: Show first-run wizard
    }

    // Request camera permissions (but don't quit if denied - let user see error in UI)
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) {
      logger.warn('App', 'Camera permission denied - app will show error UI');
      // Don't quit - let the app show camera error in UI
    }

    // Initialize Python identification service ONCE at startup
    logger.info('App', 'Initializing Python identification service');
    try {
      identificationService = new PythonIdentificationBridge();
      await identificationService.start('one-piece');
      logger.info('App', 'Python identification service ready');
    } catch (error) {
      logger.error('App', 'Failed to initialize identification service', error as Error);
      // Continue anyway - we'll show error in UI
    }

    createWindow();
    setupIpcHandlers(ipcMain);

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });

    logger.info('App', 'Application ready');
  } catch (error) {
    logger.error('App', 'Failed to initialize application', error as Error);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', async () => {
  logger.info('App', 'Application quitting, cleaning up resources');

  if (identificationService) {
    await identificationService.stop();
    identificationService = null;
  }

  // Close logger to flush logs
  await logger.close();
});

// Handle identification service
ipcMain.handle('identifier:initialize', async (_event, game: string = 'one-piece') => {
  try {
    // Service is already initialized at startup - just return status
    if (identificationService && identificationService.isInitialized()) {
      return { success: true, game };
    }

    // CRITICAL FIX: Prevent concurrent initialization attempts
    if (isInitializing) {
      return { success: false, error: 'Initialization already in progress' };
    }

    // If not initialized, try to initialize now
    if (!identificationService) {
      isInitializing = true;
      try {
        identificationService = new PythonIdentificationBridge();
        await identificationService.start(game);
        return { success: true, game };
      } finally {
        isInitializing = false;
      }
    }
    return { success: true, game };
  } catch (error: any) {
    console.error('Failed to initialize identification service:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('identifier:identify', identifyRateLimiter.wrap('identifier:identify', async (_event, imagePath: string, options: any = {}) => {
  try {
    if (!identificationService || !identificationService.isInitialized()) {
      return { success: false, error: 'Service not initialized' };
    }

    // HIGH SEVERITY FIX: Cancel previous identification if still running
    if (activeIdentificationAbortController) {
      logger.info('Main', 'Cancelling previous identification request');
      activeIdentificationAbortController.abort();
      activeIdentificationAbortController = null;
    }

    // Create new abort controller for this request
    activeIdentificationAbortController = new AbortController();
    const currentController = activeIdentificationAbortController;

    try {
      // Note: Python service doesn't support AbortSignal yet, but we can at least
      // detect when request is superseded and avoid returning stale results
      const result = await identificationService.identifyCard(imagePath, options);

      // Check if this request was cancelled while waiting
      if (currentController.signal.aborted) {
        logger.info('Main', 'Identification completed but was cancelled - discarding result');
        return { success: false, error: 'Request was cancelled' };
      }

      return { success: true, result };
    } finally {
      // Clear controller if it's still the active one
      if (activeIdentificationAbortController === currentController) {
        activeIdentificationAbortController = null;
      }
    }
  } catch (error: any) {
    console.error('Identification failed:', error);
    return { success: false, error: error.message };
  }
}));

ipcMain.handle('identifier:identify-multi-frame', async (_event, imagePaths: string[], options: any = {}) => {
  try {
    if (!identificationService || !identificationService.isInitialized()) {
      return { success: false, error: 'Service not initialized' };
    }

    // HIGH SEVERITY FIX: Validate input to prevent crashes and path traversal
    if (!Array.isArray(imagePaths)) {
      throw new Error('imagePaths must be an array');
    }

    if (imagePaths.length === 0) {
      throw new Error('imagePaths cannot be empty');
    }

    if (imagePaths.length > 10) {
      throw new Error('Maximum 10 frames allowed for multi-frame identification');
    }

    // Validate each path for security
    const tempDir = path.join(app.getPath('temp'), 'cardflux');
    for (const imagePath of imagePaths) {
      // Must be a string
      if (typeof imagePath !== 'string') {
        throw new Error('All paths must be strings');
      }

      // Must be absolute
      if (!path.isAbsolute(imagePath)) {
        throw new Error(`Paths must be absolute: ${imagePath}`);
      }

      // Normalize and check for path traversal
      const normalizedPath = path.normalize(imagePath);
      const normalizedTemp = path.normalize(tempDir);

      // Must be within tempDir (prevent path traversal)
      if (!normalizedPath.startsWith(normalizedTemp)) {
        throw new Error(`Path outside allowed directory: ${imagePath}`);
      }

      // Must exist
      if (!fs.existsSync(normalizedPath)) {
        throw new Error(`File not found: ${imagePath}`);
      }

      // Verify it's a file, not directory
      const stats = fs.statSync(normalizedPath);
      if (!stats.isFile()) {
        throw new Error(`Path is not a file: ${imagePath}`);
      }

      // Check file size (prevent DoS via huge files)
      const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB per frame
      if (stats.size > MAX_FILE_SIZE) {
        throw new Error(`File too large: ${imagePath} (${stats.size} bytes > ${MAX_FILE_SIZE} bytes)`);
      }
    }

    const result = await identificationService.identifyCardMultiFrame(imagePaths, options);
    return { success: true, result };
  } catch (error: any) {
    logger.error('Main', 'Multi-frame identification error', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('identifier:detect-card', detectRateLimiter.wrap('identifier:detect-card', async (_event, imageData: string) => {
  try {
    if (!identificationService || !identificationService.isInitialized()) {
      return { success: false, error: 'Service not initialized' };
    }

    const result = await identificationService.detectCard(imageData);
    return { success: true, result };
  } catch (error: any) {
    console.error('Card detection failed:', error);
    return { success: false, error: error.message };
  }
}));

ipcMain.handle('identifier:status', async () => {
  if (!identificationService) {
    return { initialized: false, ready: false, running: false };
  }

  try {
    const status = await identificationService.getStatus();
    return {
      ...status,
      running: identificationService.isRunning(),
    };
  } catch (error) {
    return { initialized: false, ready: false, running: false };
  }
});

ipcMain.handle('identifier:stop', async () => {
  if (identificationService) {
    await identificationService.stop();
    identificationService = null;
  }
  return { success: true };
});

// Handle camera capture for identification
ipcMain.handle('camera:capture', captureRateLimiter.wrap('camera:capture', async (_event, imageData: string) => {
  try {
    // HIGH SEVERITY FIX: Validate input to prevent memory exhaustion attacks
    if (!imageData || typeof imageData !== 'string') {
      throw new Error('Invalid image data: must be a non-empty string');
    }

    // Check data URI prefix
    if (!imageData.startsWith('data:image/')) {
      throw new Error('Invalid image data: must be a data URI with image/* MIME type');
    }

    // Extract base64 portion
    const base64Data = imageData.replace(/^data:image\/\w+;base64,/, '');

    // Validate base64 size (10MB limit = 13.3MB base64)
    const MAX_BASE64_SIZE = 14 * 1024 * 1024; // ~10MB actual image data
    if (base64Data.length > MAX_BASE64_SIZE) {
      throw new Error(`Image too large: ${(base64Data.length / 1024 / 1024).toFixed(1)}MB (max 10MB)`);
    }

    // Validate base64 format
    if (!/^[A-Za-z0-9+/=]+$/.test(base64Data)) {
      throw new Error('Invalid base64 encoding');
    }

    // Use temp directory
    const tempDir = path.join(app.getPath('temp'), 'cardflux');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const outputPath = path.join(tempDir, `capture-${Date.now()}.jpg`);

    // Convert base64 to buffer and save
    const buffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(outputPath, buffer);

    console.log('[Camera] Image saved:', outputPath);
    return { success: true, imagePath: outputPath };
  } catch (error: any) {
    console.error('Camera capture failed:', error);
    return { success: false, error: error.message };
  }
}));

// Handle data sync
// Handle renderer logging (centralized logging)
ipcMain.handle('logger:log', async (_event, level: string, module: string, message: string, data?: any) => {
  // Forward renderer logs to main logger with [Renderer] prefix
  const logModule = `Renderer:${module}`;

  switch (level) {
    case 'debug':
      logger.debug(logModule, message, data);
      break;
    case 'info':
      logger.info(logModule, message, data);
      break;
    case 'warn':
      logger.warn(logModule, message, data);
      break;
    case 'error':
      logger.error(logModule, message, data instanceof Error ? data : undefined, typeof data === 'object' ? data : undefined);
      break;
    default:
      logger.info(logModule, message, data);
  }
});

// Handle settings file persistence (fallback when localStorage fails)
ipcMain.handle('settings:save-to-file', async (_event, settings: any) => {
  try {
    const settingsPath = path.join(app.getPath('userData'), 'settings.json');
    await fs.promises.writeFile(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
    logger.info('Settings', 'Settings saved to file', { path: settingsPath });
    return { success: true };
  } catch (error: any) {
    logger.error('Settings', 'Failed to save settings to file', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('settings:load-from-file', async () => {
  try {
    const settingsPath = path.join(app.getPath('userData'), 'settings.json');

    if (!fs.existsSync(settingsPath)) {
      return { success: false, error: 'Settings file not found' };
    }

    const data = await fs.promises.readFile(settingsPath, 'utf-8');
    const settings = JSON.parse(data);
    logger.info('Settings', 'Settings loaded from file', { path: settingsPath });
    return { success: true, settings };
  } catch (error: any) {
    logger.error('Settings', 'Failed to load settings from file', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('sync:data', syncRateLimiter.wrap('sync:data', async (_event, game: string) => {
  try {
    // CRITICAL FIX: Whitelist allowed game values to prevent command injection
    const ALLOWED_GAMES = ['one-piece', 'pokemon', 'magic', 'yugioh'];
    if (!ALLOWED_GAMES.includes(game)) {
      throw new Error(`Invalid game: ${game}. Allowed games: ${ALLOWED_GAMES.join(', ')}`);
    }

    console.log('[Sync] Starting data sync for:', game);

    const { spawn } = require('child_process');
    const rootDir = path.join(__dirname, '../../../..');

    // Run TCGPlayer scraper for the specified game
    const scraperPath = path.join(rootDir, 'services/ingest/bin/tcgplayer-scraper-onepiece.ts');

    console.log('[Sync] Root dir:', rootDir);
    console.log('[Sync] Scraper path:', scraperPath);
    console.log('[Sync] Working directory:', process.cwd());

    // Verify scraper file exists
    if (!fs.existsSync(scraperPath)) {
      throw new Error(`Scraper script not found: ${scraperPath}`);
    }

    return new Promise((resolve, reject) => {
      // CRITICAL FIX: Use argument array instead of shell=true to prevent injection
      // Pass pnpm and tsx as separate arguments
      const scraper = spawn('pnpm', ['tsx', scraperPath], {
        cwd: rootDir,
        stdio: 'pipe',
        shell: false, // SECURE: No shell interpretation
        env: {
          ...process.env,
          FORCE_COLOR: '0', // Disable colors in output for easier parsing
        },
      });

      let output = '';
      let errorOutput = '';

      scraper.stdout?.on('data', (data: Buffer) => {
        const text = data.toString();
        output += text;
        console.log('[Scraper]', text.trim());
      });

      scraper.stderr?.on('data', (data: Buffer) => {
        const text = data.toString();
        errorOutput += text;
        console.error('[Scraper Error]', text.trim());
      });

      scraper.on('close', (code: number) => {
        if (code === 0) {
          console.log('[Sync] Sync completed successfully');

          // Parse output to get stats
          // Look for patterns like "Scraped 4813 cards" or "Updated 4813 cards"
          const scrapedMatch = output.match(/(?:scraped|updated|processed)\s+(\d+)\s+cards?/i);
          const newMatch = output.match(/(\d+)\s+new\s+cards?/i);

          const cardCount = scrapedMatch ? parseInt(scrapedMatch[1]) : 0;

          resolve({
            success: true,
            updatedCards: cardCount,
            newCards: newMatch ? parseInt(newMatch[1]) : 0,
          });
        } else {
          console.error('[Sync] Scraper failed with code:', code);
          console.error('[Sync] Error output:', errorOutput);
          reject(new Error(`Scraper exited with code ${code}. Check console for details.`));
        }
      });

      scraper.on('error', (error: Error) => {
        console.error('[Sync] Spawn error:', error);
        reject(error);
      });

      // Timeout after 5 minutes
      const timeout = setTimeout(() => {
        console.warn('[Sync] Timeout reached, killing scraper');
        scraper.kill();
        reject(new Error('Sync timeout - operation took longer than 5 minutes'));
      }, 5 * 60 * 1000);

      // Clear timeout when process closes
      scraper.on('close', () => clearTimeout(timeout));
    });
  } catch (error: any) {
    console.error('[Sync] Sync failed:', error);
    return { success: false, error: error.message };
  }
}));
