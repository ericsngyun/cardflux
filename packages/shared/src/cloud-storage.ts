/**
 * Cloud-agnostic storage abstraction
 * Supports AWS S3, Google Cloud Storage, Azure Blob Storage, and local filesystem
 */

import * as fs from 'fs';
import * as path from 'path';
import { logger } from './logger';

export interface StorageConfig {
  provider: 'local' | 's3' | 'gcs' | 'azure';
  bucket?: string;
  region?: string;
  credentials?: {
    accessKeyId?: string;
    secretAccessKey?: string;
    projectId?: string;
    clientEmail?: string;
    privateKey?: string;
  };
  localPath?: string;
}

export interface StorageFile {
  path: string;
  size: number;
  lastModified: Date;
  etag?: string;
}

/**
 * Abstract storage interface
 */
export interface CloudStorage {
  /**
   * Upload a file
   */
  upload(data: Buffer | string, remotePath: string, contentType?: string): Promise<void>;

  /**
   * Download a file
   */
  download(remotePath: string): Promise<Buffer>;

  /**
   * Check if file exists
   */
  exists(remotePath: string): Promise<boolean>;

  /**
   * List files with optional prefix
   */
  list(prefix?: string): Promise<StorageFile[]>;

  /**
   * Delete a file
   */
  delete(remotePath: string): Promise<void>;

  /**
   * Get file metadata
   */
  getMetadata(remotePath: string): Promise<StorageFile | null>;

  /**
   * Copy file within storage
   */
  copy(sourcePath: string, destPath: string): Promise<void>;
}

/**
 * Local filesystem storage (for development/testing)
 */
export class LocalStorage implements CloudStorage {
  private basePath: string;

  constructor(config: StorageConfig) {
    this.basePath = config.localPath || path.join(process.cwd(), 'storage');
    fs.mkdirSync(this.basePath, { recursive: true });
  }

  private getFullPath(remotePath: string): string {
    return path.join(this.basePath, remotePath);
  }

  async upload(data: Buffer | string, remotePath: string): Promise<void> {
    const fullPath = this.getFullPath(remotePath);
    const dir = path.dirname(fullPath);

    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(fullPath, data);

    logger.debug('Uploaded to local storage', { path: remotePath });
  }

  async download(remotePath: string): Promise<Buffer> {
    const fullPath = this.getFullPath(remotePath);

    if (!fs.existsSync(fullPath)) {
      throw new Error(`File not found: ${remotePath}`);
    }

    return fs.readFileSync(fullPath);
  }

  async exists(remotePath: string): Promise<boolean> {
    const fullPath = this.getFullPath(remotePath);
    return fs.existsSync(fullPath);
  }

  async list(prefix: string = ''): Promise<StorageFile[]> {
    const fullPath = this.getFullPath(prefix);
    const files: StorageFile[] = [];

    const walk = (dir: string, baseDir: string = '') => {
      if (!fs.existsSync(dir)) return;

      const entries = fs.readdirSync(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullEntryPath = path.join(dir, entry.name);
        const relativePath = path.join(baseDir, entry.name);

        if (entry.isDirectory()) {
          walk(fullEntryPath, relativePath);
        } else {
          const stats = fs.statSync(fullEntryPath);
          files.push({
            path: relativePath,
            size: stats.size,
            lastModified: stats.mtime,
          });
        }
      }
    };

    walk(fullPath);
    return files;
  }

  async delete(remotePath: string): Promise<void> {
    const fullPath = this.getFullPath(remotePath);

    if (fs.existsSync(fullPath)) {
      fs.unlinkSync(fullPath);
      logger.debug('Deleted from local storage', { path: remotePath });
    }
  }

  async getMetadata(remotePath: string): Promise<StorageFile | null> {
    const fullPath = this.getFullPath(remotePath);

    if (!fs.existsSync(fullPath)) {
      return null;
    }

    const stats = fs.statSync(fullPath);
    return {
      path: remotePath,
      size: stats.size,
      lastModified: stats.mtime,
    };
  }

  async copy(sourcePath: string, destPath: string): Promise<void> {
    const srcFull = this.getFullPath(sourcePath);
    const destFull = this.getFullPath(destPath);
    const destDir = path.dirname(destFull);

    fs.mkdirSync(destDir, { recursive: true });
    fs.copyFileSync(srcFull, destFull);

    logger.debug('Copied in local storage', { from: sourcePath, to: destPath });
  }
}

/**
 * AWS S3 Storage (placeholder - implement when needed)
 */
export class S3Storage implements CloudStorage {
  constructor(config: StorageConfig) {
    // TODO: Initialize AWS SDK
    throw new Error('S3Storage not yet implemented. Use LocalStorage for now.');
  }

  async upload(data: Buffer | string, remotePath: string, contentType?: string): Promise<void> {
    // TODO: Implement S3 upload
    throw new Error('Not implemented');
  }

  async download(remotePath: string): Promise<Buffer> {
    // TODO: Implement S3 download
    throw new Error('Not implemented');
  }

  async exists(remotePath: string): Promise<boolean> {
    // TODO: Implement S3 exists check
    throw new Error('Not implemented');
  }

  async list(prefix?: string): Promise<StorageFile[]> {
    // TODO: Implement S3 list
    throw new Error('Not implemented');
  }

  async delete(remotePath: string): Promise<void> {
    // TODO: Implement S3 delete
    throw new Error('Not implemented');
  }

  async getMetadata(remotePath: string): Promise<StorageFile | null> {
    // TODO: Implement S3 metadata
    throw new Error('Not implemented');
  }

  async copy(sourcePath: string, destPath: string): Promise<void> {
    // TODO: Implement S3 copy
    throw new Error('Not implemented');
  }
}

/**
 * Factory function to create storage instance
 */
export function createStorage(config: StorageConfig): CloudStorage {
  switch (config.provider) {
    case 'local':
      return new LocalStorage(config);
    case 's3':
      return new S3Storage(config);
    case 'gcs':
      throw new Error('GCS storage not yet implemented');
    case 'azure':
      throw new Error('Azure storage not yet implemented');
    default:
      throw new Error(`Unknown storage provider: ${config.provider}`);
  }
}
