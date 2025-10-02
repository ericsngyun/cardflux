import { IpcMain } from 'electron';

/**
 * Setup all IPC handlers for communication between main and renderer processes
 * Following Electron security best practices with contextIsolation enabled
 */
export function setupIpcHandlers(ipcMain: IpcMain): void {
  // Camera permissions check
  ipcMain.handle('camera:check-permission', async () => {
    try {
      // This will be handled by the platform-specific permission system
      return { granted: true };
    } catch (error) {
      console.error('Error checking camera permission:', error);
      return { granted: false, error: String(error) };
    }
  });

  // Get available cameras
  ipcMain.handle('camera:get-devices', async () => {
    try {
      // Note: opencv4nodejs will handle device enumeration
      // For now, return default camera
      return {
        devices: [
          { id: 0, label: 'Default Camera' },
        ],
      };
    } catch (error) {
      console.error('Error getting camera devices:', error);
      return { devices: [], error: String(error) };
    }
  });

  // Scanner IPC handlers are registered in main/index.ts
  // This allows access to the scanner instance

  console.log('IPC handlers registered successfully');
}
