/**
 * Cloud-agnostic storage abstraction
 * Supports AWS S3, Google Cloud Storage, Azure Blob Storage, and local filesystem
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
  DeleteObjectCommand,
  ListObjectsV2Command,
  CopyObjectCommand
} from '@aws-sdk/client-s3';
import { logger } from './logger.js';

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
 * AWS S3 Storage
 */
export class S3Storage implements CloudStorage {
  private client: S3Client;
  private bucket: string;

  constructor(config: StorageConfig) {
    if (!config.bucket) {
      throw new Error('S3 bucket name is required');
    }

    this.bucket = config.bucket;

    // Initialize S3 client with credentials
    const clientConfig: any = {
      region: config.region || 'us-east-1',
    };

    if (config.credentials?.accessKeyId && config.credentials?.secretAccessKey) {
      clientConfig.credentials = {
        accessKeyId: config.credentials.accessKeyId,
        secretAccessKey: config.credentials.secretAccessKey,
      };
    }
    // If no credentials provided, SDK will use default credential chain
    // (environment variables, IAM roles, etc.)

    this.client = new S3Client(clientConfig);
    logger.info('S3Storage initialized', { bucket: this.bucket, region: clientConfig.region });
  }

  async upload(data: Buffer | string, remotePath: string, contentType?: string): Promise<void> {
    try {
      const body = typeof data === 'string' ? Buffer.from(data) : data;

      const command = new PutObjectCommand({
        Bucket: this.bucket,
        Key: remotePath,
        Body: body,
        ContentType: contentType,
      });

      await this.client.send(command);
      logger.debug('Uploaded to S3', { bucket: this.bucket, path: remotePath, size: body.length });
    } catch (error: any) {
      logger.error('S3 upload failed', { path: remotePath }, error);
      throw new Error(`S3 upload failed: ${error.message}`);
    }
  }

  async download(remotePath: string): Promise<Buffer> {
    try {
      const command = new GetObjectCommand({
        Bucket: this.bucket,
        Key: remotePath,
      });

      const response = await this.client.send(command);

      if (!response.Body) {
        throw new Error('No data received from S3');
      }

      // Convert ReadableStream to Buffer
      const chunks: Uint8Array[] = [];
      const stream = response.Body as any;

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      const buffer = Buffer.concat(chunks);
      logger.debug('Downloaded from S3', { bucket: this.bucket, path: remotePath, size: buffer.length });
      return buffer;
    } catch (error: any) {
      logger.error('S3 download failed', { path: remotePath }, error);
      throw new Error(`S3 download failed: ${error.message}`);
    }
  }

  async exists(remotePath: string): Promise<boolean> {
    try {
      const command = new HeadObjectCommand({
        Bucket: this.bucket,
        Key: remotePath,
      });

      await this.client.send(command);
      return true;
    } catch (error: any) {
      if (error.name === 'NotFound' || error.$metadata?.httpStatusCode === 404) {
        return false;
      }
      logger.error('S3 exists check failed', { path: remotePath }, error);
      throw new Error(`S3 exists check failed: ${error.message}`);
    }
  }

  async list(prefix: string = ''): Promise<StorageFile[]> {
    try {
      const files: StorageFile[] = [];
      let continuationToken: string | undefined;

      do {
        const command = new ListObjectsV2Command({
          Bucket: this.bucket,
          Prefix: prefix,
          ContinuationToken: continuationToken,
        });

        const response = await this.client.send(command);

        if (response.Contents) {
          for (const item of response.Contents) {
            if (item.Key) {
              files.push({
                path: item.Key,
                size: item.Size || 0,
                lastModified: item.LastModified || new Date(),
                etag: item.ETag,
              });
            }
          }
        }

        continuationToken = response.NextContinuationToken;
      } while (continuationToken);

      logger.debug('Listed S3 files', { bucket: this.bucket, prefix, count: files.length });
      return files;
    } catch (error: any) {
      logger.error('S3 list failed', { prefix }, error);
      throw new Error(`S3 list failed: ${error.message}`);
    }
  }

  async delete(remotePath: string): Promise<void> {
    try {
      const command = new DeleteObjectCommand({
        Bucket: this.bucket,
        Key: remotePath,
      });

      await this.client.send(command);
      logger.debug('Deleted from S3', { bucket: this.bucket, path: remotePath });
    } catch (error: any) {
      logger.error('S3 delete failed', { path: remotePath }, error);
      throw new Error(`S3 delete failed: ${error.message}`);
    }
  }

  async getMetadata(remotePath: string): Promise<StorageFile | null> {
    try {
      const command = new HeadObjectCommand({
        Bucket: this.bucket,
        Key: remotePath,
      });

      const response = await this.client.send(command);

      return {
        path: remotePath,
        size: response.ContentLength || 0,
        lastModified: response.LastModified || new Date(),
        etag: response.ETag,
      };
    } catch (error: any) {
      if (error.name === 'NotFound' || error.$metadata?.httpStatusCode === 404) {
        return null;
      }
      logger.error('S3 getMetadata failed', { path: remotePath }, error);
      throw new Error(`S3 getMetadata failed: ${error.message}`);
    }
  }

  async copy(sourcePath: string, destPath: string): Promise<void> {
    try {
      const command = new CopyObjectCommand({
        Bucket: this.bucket,
        CopySource: `${this.bucket}/${sourcePath}`,
        Key: destPath,
      });

      await this.client.send(command);
      logger.debug('Copied in S3', { bucket: this.bucket, from: sourcePath, to: destPath });
    } catch (error: any) {
      logger.error('S3 copy failed', { from: sourcePath, to: destPath }, error);
      throw new Error(`S3 copy failed: ${error.message}`);
    }
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
