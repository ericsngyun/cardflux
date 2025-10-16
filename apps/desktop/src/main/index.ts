import { app, BrowserWindow, ipcMain, systemPreferences } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { setupIpcHandlers } from './ipc/handlers';
import { PythonIdentificationBridge } from './identifier/python-bridge';

let mainWindow: BrowserWindow | null = null;
let identificationService: PythonIdentificationBridge | null = null;

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
  // Request camera permissions
  const hasPermission = await requestCameraPermission();

  if (!hasPermission) {
    console.error('Camera permission denied');
    app.quit();
    return;
  }

  createWindow();
  setupIpcHandlers(ipcMain);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', async () => {
  if (identificationService) {
    await identificationService.stop();
    identificationService = null;
  }
});

// Handle identification service
ipcMain.handle('identifier:initialize', async (_event, game: string = 'one-piece') => {
  try {
    if (!identificationService) {
      identificationService = new PythonIdentificationBridge();
      await identificationService.start(game);
    }
    return { success: true, game };
  } catch (error: any) {
    console.error('Failed to initialize identification service:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('identifier:identify', async (_event, imagePath: string, options: any = {}) => {
  try {
    if (!identificationService || !identificationService.isInitialized()) {
      // Auto-initialize if not ready
      identificationService = new PythonIdentificationBridge();
      await identificationService.start(options.game || 'one-piece');
    }

    const result = await identificationService.identifyCard(imagePath, options);
    return { success: true, result };
  } catch (error: any) {
    console.error('Identification failed:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('identifier:detect-card', async (_event, imageData: string) => {
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
});

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
ipcMain.handle('camera:capture', async (_event, imageData: string) => {
  try {
    // Use temp directory
    const tempDir = path.join(app.getPath('temp'), 'cardflux');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const outputPath = path.join(tempDir, `capture-${Date.now()}.jpg`);

    // Convert base64 to buffer and save
    const base64Data = imageData.replace(/^data:image\/\w+;base64,/, '');
    const buffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(outputPath, buffer);

    console.log('[Camera] Image saved:', outputPath);
    return { success: true, imagePath: outputPath };
  } catch (error: any) {
    console.error('Camera capture failed:', error);
    return { success: false, error: error.message };
  }
});

// Handle data sync
ipcMain.handle('sync:data', async (_event, game: string) => {
  try {
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
      // Use shell to properly resolve pnpm in PATH
      // On Windows, this uses cmd.exe which has access to PATH
      const command = process.platform === 'win32'
        ? `pnpm tsx "${scraperPath}"`
        : `pnpm tsx ${scraperPath}`;

      console.log('[Sync] Running command:', command);

      const scraper = spawn(command, [], {
        cwd: rootDir,
        stdio: 'pipe',
        shell: true, // Use shell to resolve pnpm in PATH
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
});
