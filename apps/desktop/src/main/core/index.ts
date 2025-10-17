/**
 * Core module exports
 *
 * Provides centralized access to core application managers and utilities
 */

export { logger, LogLevel } from './logger';
export { ResourceManager, type ResourcePaths } from './resource-manager';
export { DataManager, type GameDatabase, type DownloadProgress } from './data-manager';
