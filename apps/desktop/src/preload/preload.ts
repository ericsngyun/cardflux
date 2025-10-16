import { contextBridge, ipcRenderer } from 'electron';

/**
 * Preload script to expose safe IPC APIs to the renderer process
 * Following Electron security best practices with contextBridge
 */

export interface ScannerAPI {
  start: () => Promise<{ success: boolean }>;
  stop: () => Promise<{ success: boolean }>;
  getStatus: () => Promise<{ running: boolean; initialized: boolean }>;
  onDetection: (callback: (result: any) => void) => () => void;
  onError: (callback: (error: string) => void) => () => void;
}

export interface CameraAPI {
  checkPermission: () => Promise<{ granted: boolean; error?: string }>;
  getDevices: () => Promise<{ devices: Array<{ id: number; label: string }>; error?: string }>;
  capture: (imageData: string) => Promise<{ success: boolean; imagePath?: string; error?: string }>;
}

export interface IdentifierAPI {
  initialize: (game?: string) => Promise<{ success: boolean; game?: string; error?: string }>;
  identify: (imagePath: string, options?: any) => Promise<{ success: boolean; result?: any; error?: string }>;
  detectCard: (imageData: string) => Promise<{ success: boolean; result?: any; error?: string }>;
  getStatus: () => Promise<{ initialized: boolean; ready: boolean; running: boolean }>;
  stop: () => Promise<{ success: boolean }>;
}

export interface SyncAPI {
  syncData: (game: string) => Promise<{ success: boolean; updatedCards?: number; newCards?: number; error?: string }>;
}

// Expose protected APIs to renderer
contextBridge.exposeInMainWorld('scanner', {
  start: () => ipcRenderer.invoke('scanner:start'),
  stop: () => ipcRenderer.invoke('scanner:stop'),
  getStatus: () => ipcRenderer.invoke('scanner:status'),

  onDetection: (callback: (result: any) => void) => {
    const listener = (_event: any, result: any) => callback(result);
    ipcRenderer.on('scanner:detection', listener);

    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('scanner:detection', listener);
    };
  },

  onError: (callback: (error: string) => void) => {
    const listener = (_event: any, error: string) => callback(error);
    ipcRenderer.on('scanner:error', listener);

    // Return cleanup function
    return () => {
      ipcRenderer.removeListener('scanner:error', listener);
    };
  },
} as ScannerAPI);

contextBridge.exposeInMainWorld('camera', {
  checkPermission: () => ipcRenderer.invoke('camera:check-permission'),
  getDevices: () => ipcRenderer.invoke('camera:get-devices'),
  capture: (imageData: string) => ipcRenderer.invoke('camera:capture', imageData),
} as CameraAPI);

contextBridge.exposeInMainWorld('identifier', {
  initialize: (game?: string) => ipcRenderer.invoke('identifier:initialize', game),
  identify: (imagePath: string, options?: any) => ipcRenderer.invoke('identifier:identify', imagePath, options),
  detectCard: (imageData: string) => ipcRenderer.invoke('identifier:detect-card', imageData),
  getStatus: () => ipcRenderer.invoke('identifier:status'),
  stop: () => ipcRenderer.invoke('identifier:stop'),
} as IdentifierAPI);

contextBridge.exposeInMainWorld('sync', {
  syncData: (game: string) => ipcRenderer.invoke('sync:data', game),
} as SyncAPI);

// Expose type declarations for TypeScript support in renderer
declare global {
  interface Window {
    scanner: ScannerAPI;
    camera: CameraAPI;
    identifier: IdentifierAPI;
    sync: SyncAPI;
  }
}
