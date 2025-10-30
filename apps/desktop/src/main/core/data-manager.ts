/**
 * Data Manager
 *
 * Manages card database downloads from CDN
 * Handles:
 * - Version checking
 * - Download with progress tracking
 * - Retry logic with exponential backoff
 * - Checksum verification
 * - Extraction
 * - Update notifications
 */

import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import { createHash } from 'crypto';
import { EventEmitter } from 'events';
import { app } from 'electron';
import { logger } from './logger';
import { ResourceManager } from './resource-manager';

const CDN_BASE_URL = 'https://cdn.cardflux.com'; // TODO: Update with actual CDN
const FALLBACK_CDN_URL = 'https://github.com/yourusername/cardflux-data/releases/latest/download';

export interface GameDatabase {
  game: string;
  version: string;
  cardCount: number;
  size: number;
  files: {
    images: DatabaseFile;
    index: DatabaseFile;
    metadata: DatabaseFile;
  };
}

export interface DatabaseFile {
  url: string;
  size: number;
  checksum: string;
  path: string;
}

export interface DownloadProgress {
  game: string;
  file: string;
  bytesDownloaded: number;
  totalBytes: number;
  percentage: number;
  speed: number; // bytes per second
}

export class DataManager extends EventEmitter {
  private static instance: DataManager | null = null;
  private resourceManager: ResourceManager;
  private manifest: Record<string, GameDatabase> | null = null;
  private downloadAbortControllers: Map<string, AbortController> = new Map();

  private constructor() {
    super();
    this.resourceManager = ResourceManager.getInstance();
    logger.info('DataManager', 'Initialized');
  }

  /**
   * Get singleton instance
   */
  static getInstance(): DataManager {
    if (!DataManager.instance) {
      DataManager.instance = new DataManager();
    }
    return DataManager.instance;
  }

  /**
   * Initialize data manager
   */
  async initialize(): Promise<void> {
    logger.info('DataManager', 'Initializing');

    try {
      // Ensure data directory exists
      await this.resourceManager.ensureDataDir();

      // Load manifest from CDN
      await this.loadManifest();

      logger.info('DataManager', 'Initialized successfully');
    } catch (error) {
      logger.error('DataManager', 'Initialization failed', error as Error);
      throw error;
    }
  }

  /**
   * Load database manifest from CDN
   */
  private async loadManifest(): Promise<void> {
    logger.info('DataManager', 'Loading database manifest');

    try {
      const manifestUrl = `${CDN_BASE_URL}/databases/manifest.json`;
      this.manifest = await this.fetchJSON<Record<string, GameDatabase>>(manifestUrl);

      logger.info('DataManager', 'Manifest loaded', {
        games: Object.keys(this.manifest),
      });
    } catch (error) {
      logger.warn('DataManager', 'Failed to load manifest from primary CDN', error);

      // Try fallback
      try {
        const fallbackUrl = `${FALLBACK_CDN_URL}/manifest.json`;
        this.manifest = await this.fetchJSON<Record<string, GameDatabase>>(fallbackUrl);
        logger.info('DataManager', 'Manifest loaded from fallback CDN');
      } catch (fallbackError) {
        logger.error('DataManager', 'Failed to load manifest from fallback', fallbackError as Error);

        // Use embedded manifest as last resort
        this.manifest = this.getEmbeddedManifest();
        logger.warn('DataManager', 'Using embedded manifest');
      }
    }
  }

  /**
   * Get embedded manifest (bundled with app)
   */
  private getEmbeddedManifest(): Record<string, GameDatabase> {
    // TODO: Bundle manifest.json in resources/
    // For now, return default for One Piece
    return {
      'one-piece': {
        game: 'one-piece',
        version: '2025.01.17',
        cardCount: 4813,
        size: 414000000,
        files: {
          images: {
            url: `${CDN_BASE_URL}/databases/one-piece/v2025.01.17/images.tar.gz`,
            size: 400000000,
            checksum: 'sha256:placeholder',
            path: 'data/images/one-piece',
          },
          index: {
            url: `${CDN_BASE_URL}/databases/one-piece/v2025.01.17/index.tar.gz`,
            size: 7000000,
            checksum: 'sha256:placeholder',
            path: 'artifacts/faiss/one-piece-dinov2',
          },
          metadata: {
            url: `${CDN_BASE_URL}/databases/one-piece/v2025.01.17/metadata.tar.gz`,
            size: 7000000,
            checksum: 'sha256:placeholder',
            path: 'artifacts/metadata/embeddings/one-piece-dinov2',
          },
        },
      },
    };
  }

  /**
   * Check if game database is installed
   */
  isGameInstalled(game: string): boolean {
    const dataDir = this.resourceManager.getDataDir();
    // dataDir points to PROJECT_ROOT/data
    // artifacts are at PROJECT_ROOT/artifacts (sibling of data/)
    const projectRoot = path.dirname(dataDir);

    const gamePaths = [
      path.join(dataDir, 'images', game),
      path.join(projectRoot, 'artifacts', 'faiss', `${game}-dinov2`),
      path.join(projectRoot, 'artifacts', 'metadata', 'embeddings', `${game}-dinov2`),
    ];

    const installed = gamePaths.every(p => fs.existsSync(p));

    logger.debug('DataManager', `Game ${game} installed: ${installed}`, { gamePaths });
    return installed;
  }

  /**
   * Get installed game version
   */
  getInstalledVersion(game: string): string | null {
    const dataDir = this.resourceManager.getDataDir();
    const versionFile = path.join(dataDir, 'versions', `${game}.json`);

    if (!fs.existsSync(versionFile)) {
      return null;
    }

    try {
      const data = JSON.parse(fs.readFileSync(versionFile, 'utf-8'));
      return data.version;
    } catch (error) {
      logger.warn('DataManager', `Failed to read version file for ${game}`, error);
      return null;
    }
  }

  /**
   * Check if update is available for game
   */
  isUpdateAvailable(game: string): boolean {
    if (!this.manifest || !this.manifest[game]) {
      return false;
    }

    const installed = this.getInstalledVersion(game);
    const latest = this.manifest[game].version;

    return installed !== latest;
  }

  /**
   * Download and install game database
   */
  async installGame(game: string): Promise<void> {
    logger.info('DataManager', `Installing game: ${game}`);

    if (!this.manifest || !this.manifest[game]) {
      throw new Error(`Game not found in manifest: ${game}`);
    }

    const gameDb = this.manifest[game];
    const dataDir = this.resourceManager.getDataDir();
    // Manifest paths are relative to PROJECT_ROOT, not dataDir
    const projectRoot = path.dirname(dataDir);

    try {
      // Download all files
      for (const [fileType, fileInfo] of Object.entries(gameDb.files)) {
        logger.info('DataManager', `Downloading ${fileType}`, { game, fileInfo });

        const tempPath = path.join(app.getPath('temp'), 'cardflux', `${game}-${fileType}.tar.gz`);
        await this.downloadFileWithRetry(game, fileType, fileInfo.url, tempPath);

        // Verify checksum
        logger.info('DataManager', `Verifying ${fileType}`, { game });
        await this.verifyChecksum(tempPath, fileInfo.checksum);

        // Extract
        logger.info('DataManager', `Extracting ${fileType}`, { game });
        const destPath = path.join(projectRoot, fileInfo.path);
        await this.extractTarGz(tempPath, destPath);

        // Clean up temp file
        fs.unlinkSync(tempPath);

        logger.info('DataManager', `${fileType} installed successfully`, { game });
      }

      // Save version info
      await this.saveVersion(game, gameDb.version);

      logger.info('DataManager', `Game installed successfully: ${game}`);
      this.emit('install-complete', { game, version: gameDb.version });
    } catch (error) {
      logger.error('DataManager', `Failed to install game: ${game}`, error as Error);
      this.emit('install-error', { game, error });
      throw error;
    }
  }

  /**
   * Download file with retry logic
   */
  private async downloadFileWithRetry(
    game: string,
    fileType: string,
    url: string,
    destPath: string,
    maxRetries: number = 3
  ): Promise<void> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        logger.info('DataManager', `Download attempt ${attempt}/${maxRetries}`, {
          game,
          fileType,
          url,
        });

        await this.downloadFile(game, fileType, url, destPath);
        return; // Success
      } catch (error) {
        lastError = error as Error;
        logger.warn('DataManager', `Download attempt ${attempt} failed`, error);

        if (attempt < maxRetries) {
          // Exponential backoff: 2^attempt seconds
          const delay = Math.pow(2, attempt) * 1000;
          logger.info('DataManager', `Retrying in ${delay}ms`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw new Error(`Failed to download after ${maxRetries} attempts: ${lastError?.message}`);
  }

  /**
   * Download file with progress tracking and timeout
   */
  private async downloadFile(
    game: string,
    fileType: string,
    url: string,
    destPath: string
  ): Promise<void> {
    // SECURITY: Ensure HTTPS only
    if (!url.startsWith('https://')) {
      return Promise.reject(new Error('Only HTTPS URLs are allowed for security'));
    }

    return new Promise((resolve, reject) => {
      // Ensure destination directory exists (async mkdir)
      const destDir = path.dirname(destPath);
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }

      const file = fs.createWriteStream(destPath);
      let bytesDownloaded = 0;
      let totalBytes = 0;
      let startTime = Date.now();
      let downloadComplete = false;

      // Set timeout for download (30 minutes max)
      const DOWNLOAD_TIMEOUT = 30 * 60 * 1000;
      const timeout = setTimeout(() => {
        if (!downloadComplete) {
          file.close();
          if (fs.existsSync(destPath)) {
            fs.unlinkSync(destPath);
          }
          logger.error('DataManager', 'Download timeout', undefined, { game, fileType, url });
          reject(new Error(`Download timeout after ${DOWNLOAD_TIMEOUT / 1000}s`));
        }
      }, DOWNLOAD_TIMEOUT);

      const cleanup = () => {
        clearTimeout(timeout);
        this.downloadAbortControllers.delete(`${game}-${fileType}`);
      };

      const request = https.get(url, (response) => {
        if (response.statusCode !== 200) {
          cleanup();
          file.close();
          if (fs.existsSync(destPath)) {
            fs.unlinkSync(destPath);
          }
          reject(new Error(`Download failed: HTTP ${response.statusCode}`));
          return;
        }

        totalBytes = parseInt(response.headers['content-length'] || '0', 10);

        response.on('data', (chunk) => {
          bytesDownloaded += chunk.length;

          // Calculate speed
          const elapsed = (Date.now() - startTime) / 1000;
          const speed = bytesDownloaded / elapsed;

          // Emit progress
          const progress: DownloadProgress = {
            game,
            file: fileType,
            bytesDownloaded,
            totalBytes,
            percentage: totalBytes > 0 ? (bytesDownloaded / totalBytes) * 100 : 0,
            speed,
          };

          this.emit('download-progress', progress);
        });

        response.pipe(file);

        file.on('finish', () => {
          downloadComplete = true;
          cleanup();
          file.close();
          resolve();
        });
      });

      // Set request timeout (60 seconds for initial connection)
      request.setTimeout(60000, () => {
        cleanup();
        request.destroy();
        file.close();
        if (fs.existsSync(destPath)) {
          fs.unlinkSync(destPath);
        }
        reject(new Error('Request timeout: no response from server'));
      });

      request.on('error', (error) => {
        cleanup();
        file.close();
        if (fs.existsSync(destPath)) {
          fs.unlinkSync(destPath);
        }
        reject(error);
      });

      // Store abort controller for cancellation
      const abortController = new AbortController();
      this.downloadAbortControllers.set(`${game}-${fileType}`, abortController);

      file.on('close', () => {
        cleanup();
      });
    });
  }

  /**
   * Cancel download
   */
  cancelDownload(game: string, fileType: string): void {
    const key = `${game}-${fileType}`;
    const controller = this.downloadAbortControllers.get(key);

    if (controller) {
      controller.abort();
      logger.info('DataManager', 'Download cancelled', { game, fileType });
    }
  }

  /**
   * Verify file checksum
   */
  private async verifyChecksum(filePath: string, expectedChecksum: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const hash = createHash('sha256');
      const stream = fs.createReadStream(filePath);

      stream.on('data', (data) => {
        hash.update(data);
      });

      stream.on('end', () => {
        const actualChecksum = `sha256:${hash.digest('hex')}`;

        if (actualChecksum === expectedChecksum) {
          logger.debug('DataManager', 'Checksum verified', { filePath });
          resolve();
        } else {
          const error = new Error(
            `Checksum mismatch: expected ${expectedChecksum}, got ${actualChecksum}`
          );
          logger.error('DataManager', 'Checksum verification failed', error);
          reject(error);
        }
      });

      stream.on('error', reject);
    });
  }

  /**
   * Extract tar.gz file
   */
  private async extractTarGz(tarPath: string, destPath: string): Promise<void> {
    logger.info('DataManager', 'Extracting archive', { tarPath, destPath });

    try {
      // Ensure destination directory exists
      if (!fs.existsSync(destPath)) {
        fs.mkdirSync(destPath, { recursive: true });
      }

      // Extract using node-tar
      const tar = require('tar');
      await tar.x({
        file: tarPath,
        cwd: destPath,
        strict: true,
      });

      logger.info('DataManager', 'Extraction complete', { destPath });
    } catch (error) {
      logger.error('DataManager', 'Extraction failed', error as Error, { tarPath, destPath });
      throw error;
    }
  }

  /**
   * Save version info
   */
  private async saveVersion(game: string, version: string): Promise<void> {
    const dataDir = this.resourceManager.getDataDir();
    const versionDir = path.join(dataDir, 'versions');
    const versionFile = path.join(versionDir, `${game}.json`);

    if (!fs.existsSync(versionDir)) {
      fs.mkdirSync(versionDir, { recursive: true });
    }

    const data = {
      game,
      version,
      installedAt: new Date().toISOString(),
    };

    fs.writeFileSync(versionFile, JSON.stringify(data, null, 2), 'utf-8');
    logger.info('DataManager', 'Version info saved', data);
  }

  /**
   * Fetch JSON from URL with timeout
   */
  private async fetchJSON<T>(url: string): Promise<T> {
    return new Promise((resolve, reject) => {
      // SECURITY: Ensure HTTPS only
      if (!url.startsWith('https://')) {
        reject(new Error('Only HTTPS URLs are allowed for security'));
        return;
      }

      const request = https.get(url, (response) => {
        // Handle redirects
        if (response.statusCode === 301 || response.statusCode === 302) {
          const redirectUrl = response.headers.location;
          if (redirectUrl && redirectUrl.startsWith('https://')) {
            // Follow redirect (max 1 level to prevent loops)
            logger.debug('DataManager', 'Following redirect', { from: url, to: redirectUrl });
            this.fetchJSON<T>(redirectUrl).then(resolve).catch(reject);
          } else {
            reject(new Error(`Invalid redirect URL: ${redirectUrl}`));
          }
          return;
        }

        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode} fetching ${url}`));
          return;
        }

        let data = '';
        let receivedBytes = 0;
        const MAX_JSON_SIZE = 10 * 1024 * 1024; // 10 MB max for JSON

        response.on('data', (chunk) => {
          receivedBytes += chunk.length;

          // Prevent memory exhaustion from huge JSON files
          if (receivedBytes > MAX_JSON_SIZE) {
            request.destroy();
            reject(new Error(`JSON response too large (>10MB)`));
            return;
          }

          data += chunk;
        });

        response.on('end', () => {
          try {
            const parsed = JSON.parse(data);
            logger.debug('DataManager', 'JSON fetched successfully', {
              url,
              size: receivedBytes,
            });
            resolve(parsed);
          } catch (error) {
            logger.error('DataManager', 'JSON parse error', error as Error, { url });
            reject(new Error(`Invalid JSON from ${url}: ${(error as Error).message}`));
          }
        });
      });

      // Set timeout (10 seconds for manifest)
      request.setTimeout(10000, () => {
        request.destroy();
        logger.error('DataManager', 'Request timeout fetching JSON', undefined, { url });
        reject(new Error(`Request timeout fetching JSON from ${url} (10s)`));
      });

      request.on('error', (error) => {
        logger.error('DataManager', 'Request error fetching JSON', error, { url });
        reject(error);
      });
    });
  }
}
