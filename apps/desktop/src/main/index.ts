import { app, BrowserWindow, ipcMain, systemPreferences } from 'electron';
import * as path from 'path';
import { setupIpcHandlers } from './ipc/handlers';
import { RealtimeScanner } from './scanner/realtime-scanner';

let mainWindow: BrowserWindow | null = null;
let scanner: RealtimeScanner | null = null;

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
    },
    title: 'CardFlux - Real-time Card Scanner',
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (scanner) {
      scanner.stop();
      scanner = null;
    }
  });
}

/**
 * Initialize the realtime scanner
 */
async function initializeScanner(): Promise<void> {
  if (!mainWindow) {
    console.error('Cannot initialize scanner: main window not available');
    return;
  }

  try {
    scanner = new RealtimeScanner({
      cameraId: 0, // Default camera
      fps: 30,
      detectionThreshold: 0.7,
      verificationThreshold: 0.8,
    });

    // Forward detection results to renderer
    scanner.on('detection', (result) => {
      mainWindow?.webContents.send('scanner:detection', result);
    });

    scanner.on('error', (error) => {
      console.error('Scanner error:', error);
      mainWindow?.webContents.send('scanner:error', error.message);
    });

    await scanner.initialize();
    console.log('Scanner initialized successfully');
  } catch (error) {
    console.error('Failed to initialize scanner:', error);
    throw error;
  }
}

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

  // Initialize scanner after window is ready
  mainWindow?.webContents.once('did-finish-load', async () => {
    try {
      await initializeScanner();
    } catch (error) {
      console.error('Scanner initialization failed:', error);
    }
  });

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

app.on('will-quit', () => {
  if (scanner) {
    scanner.stop();
    scanner = null;
  }
});

// Handle scanner control from IPC
ipcMain.handle('scanner:start', async () => {
  if (!scanner) {
    await initializeScanner();
  }
  await scanner?.start();
  return { success: true };
});

ipcMain.handle('scanner:stop', async () => {
  await scanner?.stop();
  return { success: true };
});

ipcMain.handle('scanner:status', () => {
  return {
    running: scanner?.isRunning() ?? false,
    initialized: scanner !== null,
  };
});
