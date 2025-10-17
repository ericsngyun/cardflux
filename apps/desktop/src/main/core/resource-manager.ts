/**
 * Resource Manager
 *
 * Manages paths to bundled resources (Python runtime, site-packages, scripts)
 * Handles differences between development and production environments
 *
 * In development:
 * - Uses system Python
 * - Scripts from project root
 *
 * In production:
 * - Uses bundled Python from resources/
 * - All dependencies bundled
 */

import * as path from 'path';
import * as fs from 'fs';
import { app } from 'electron';
import { logger } from './logger';

export interface ResourcePaths {
  pythonExecutable: string;
  pythonHome: string;
  sitePackages: string;
  scripts: string;
  dataDir: string;
}

export class ResourceManager {
  private static instance: ResourceManager | null = null;
  private paths: ResourcePaths | null = null;
  private isDevelopment: boolean;
  private isPackaged: boolean;

  private constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
    this.isPackaged = app.isPackaged;

    logger.info('ResourceManager', 'Initializing', {
      isDevelopment: this.isDevelopment,
      isPackaged: this.isPackaged,
      platform: process.platform,
    });
  }

  /**
   * Get singleton instance
   */
  static getInstance(): ResourceManager {
    if (!ResourceManager.instance) {
      ResourceManager.instance = new ResourceManager();
    }
    return ResourceManager.instance;
  }

  /**
   * Initialize and verify resource paths
   */
  async initialize(): Promise<ResourcePaths> {
    logger.info('ResourceManager', 'Resolving resource paths');

    try {
      if (this.isPackaged) {
        this.paths = await this.getProductionPaths();
      } else {
        this.paths = await this.getDevelopmentPaths();
      }

      // Verify paths exist
      await this.verifyPaths(this.paths);

      logger.info('ResourceManager', 'Resource paths resolved', this.paths);
      return this.paths;
    } catch (error) {
      logger.error('ResourceManager', 'Failed to resolve resource paths', error as Error);
      throw error;
    }
  }

  /**
   * Get resource paths (must call initialize() first)
   */
  getPaths(): ResourcePaths {
    if (!this.paths) {
      throw new Error('ResourceManager not initialized. Call initialize() first.');
    }
    return this.paths;
  }

  /**
   * Get paths for production (bundled)
   */
  private async getProductionPaths(): Promise<ResourcePaths> {
    const appPath = app.getAppPath();
    const resourcesPath = path.join(appPath, 'resources');

    // Platform-specific Python runtime paths
    let pythonExecutable: string;
    let pythonHome: string;

    if (process.platform === 'win32') {
      pythonHome = path.join(resourcesPath, 'python-runtime', 'win32');
      pythonExecutable = path.join(pythonHome, 'python.exe');
    } else if (process.platform === 'darwin') {
      pythonHome = path.join(resourcesPath, 'python-runtime', 'darwin');
      pythonExecutable = path.join(pythonHome, 'bin', 'python3');
    } else {
      // Linux
      pythonHome = path.join(resourcesPath, 'python-runtime', 'linux');
      pythonExecutable = path.join(pythonHome, 'bin', 'python3');
    }

    return {
      pythonExecutable,
      pythonHome,
      sitePackages: path.join(resourcesPath, 'python-site-packages'),
      scripts: path.join(resourcesPath, 'python-scripts'),
      dataDir: path.join(app.getPath('userData'), 'data'),
    };
  }

  /**
   * Get paths for development (use system Python)
   */
  private async getDevelopmentPaths(): Promise<ResourcePaths> {
    // Find Python executable on system
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

    // Project root - use path.resolve to prevent path traversal
    // In development, app.getAppPath() returns the dist/main directory
    const appPath = app.getAppPath();
    const projectRoot = path.resolve(appPath, '..', '..', '..', '..');

    // Validate that we're still within expected bounds
    if (!projectRoot.includes('cardflux')) {
      throw new Error(`Invalid project root path: ${projectRoot}`);
    }

    const scriptsPath = path.resolve(projectRoot, 'scripts', 'identification');
    const dataPath = path.resolve(projectRoot, 'data');

    return {
      pythonExecutable: pythonCmd, // Use system Python
      pythonHome: '', // Not needed for system Python
      sitePackages: '', // Not needed (use system site-packages)
      scripts: scriptsPath,
      dataDir: dataPath,
    };
  }

  /**
   * Verify that all required paths exist
   * Uses async fs.promises.access() instead of sync fs.existsSync()
   */
  private async verifyPaths(paths: ResourcePaths): Promise<void> {
    const errors: string[] = [];

    // Helper to check if path exists (async)
    const checkExists = async (filepath: string, description: string): Promise<void> => {
      try {
        await fs.promises.access(filepath, fs.constants.F_OK);
      } catch (error) {
        errors.push(`${description} not found: ${filepath}`);
      }
    };

    // In production, verify bundled Python exists
    if (this.isPackaged) {
      await checkExists(paths.pythonExecutable, 'Python executable');
      await checkExists(paths.pythonHome, 'Python home');
      await checkExists(paths.sitePackages, 'Site packages');
      await checkExists(paths.scripts, 'Python scripts');
    } else {
      // In development, only verify scripts exist
      await checkExists(paths.scripts, 'Scripts directory');
    }

    // Verify identification_service.py exists
    const servicePath = this.getServiceScriptPath();
    await checkExists(servicePath, 'Identification service script');

    if (errors.length > 0) {
      const error = new Error(`Resource verification failed:\n${errors.join('\n')}`);
      logger.error('ResourceManager', 'Path verification failed', error, { errors });
      throw error;
    }

    logger.info('ResourceManager', 'All resource paths verified successfully');
  }

  /**
   * Get path to identification service script
   */
  getServiceScriptPath(): string {
    const paths = this.getPaths();

    if (this.isPackaged) {
      return path.join(paths.scripts, 'identification_service.py');
    } else {
      // In development, use the actual source file
      return path.join(app.getAppPath(), '..', 'python', 'identification_service.py');
    }
  }

  /**
   * Get path to production card identifier script
   */
  getIdentifierScriptPath(): string {
    const paths = this.getPaths();
    return path.join(paths.scripts, 'production_card_identifier.py');
  }

  /**
   * Get environment variables for Python subprocess
   */
  getPythonEnvironment(): Record<string, string> {
    const paths = this.getPaths();
    const env: Record<string, string> = { ...process.env } as Record<string, string>;

    if (this.isPackaged) {
      // Set PYTHONHOME to bundled Python
      env.PYTHONHOME = paths.pythonHome;

      // Set PYTHONPATH to include bundled site-packages and scripts
      const pythonPath = [
        paths.sitePackages,
        paths.scripts,
      ].join(path.delimiter);

      env.PYTHONPATH = pythonPath;

      // Disable user site-packages (use only bundled packages)
      env.PYTHONNOUSERSITE = '1';

      // Ensure UTF-8 encoding
      env.PYTHONIOENCODING = 'utf-8';

      logger.debug('ResourceManager', 'Python environment configured', {
        PYTHONHOME: env.PYTHONHOME,
        PYTHONPATH: env.PYTHONPATH,
      });
    } else {
      // In development, just set PYTHONPATH to scripts
      env.PYTHONPATH = paths.scripts;
    }

    // Disable output buffering (always)
    env.PYTHONUNBUFFERED = '1';

    return env;
  }

  /**
   * Check if Python is available
   */
  async checkPythonAvailable(): Promise<boolean> {
    const { pythonExecutable } = this.getPaths();

    return new Promise((resolve) => {
      const { spawn } = require('child_process');

      const proc = spawn(pythonExecutable, ['--version'], {
        stdio: 'pipe',
        env: this.getPythonEnvironment(),
      });

      let output = '';

      proc.stdout?.on('data', (data: Buffer) => {
        output += data.toString();
      });

      proc.stderr?.on('data', (data: Buffer) => {
        output += data.toString();
      });

      proc.on('close', (code: number) => {
        if (code === 0) {
          logger.info('ResourceManager', 'Python version check passed', {
            version: output.trim(),
          });
          resolve(true);
        } else {
          logger.error('ResourceManager', 'Python version check failed', undefined, {
            code,
            output,
          });
          resolve(false);
        }
      });

      proc.on('error', (error: Error) => {
        logger.error('ResourceManager', 'Failed to spawn Python', error);
        resolve(false);
      });
    });
  }

  /**
   * Get data directory path
   */
  getDataDir(): string {
    return this.getPaths().dataDir;
  }

  /**
   * Ensure data directory exists (async)
   */
  async ensureDataDir(): Promise<void> {
    const dataDir = this.getDataDir();

    try {
      await fs.promises.access(dataDir, fs.constants.F_OK);
      // Directory exists
    } catch (error) {
      // Directory doesn't exist, create it
      logger.info('ResourceManager', 'Creating data directory', { dataDir });
      await fs.promises.mkdir(dataDir, { recursive: true });
    }
  }
}
