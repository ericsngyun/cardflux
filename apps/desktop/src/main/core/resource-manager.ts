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

    // Project root - safely navigate from app path
    // In development, app.getAppPath() can return either:
    //   Case 1: C:\Users\...\cardflux\apps\desktop\dist\main (when run from built files)
    //   Case 2: C:\Users\...\cardflux\apps\desktop (when run directly with electron .)
    const appPath = app.getAppPath();

    logger.debug('ResourceManager', 'Resolving paths from app path', { appPath });

    // Determine project root based on appPath structure
    let projectRoot: string;

    // Check if we're in dist/main (Case 1) or apps/desktop (Case 2)
    if (appPath.includes(path.join('apps', 'desktop', 'dist'))) {
      // Case 1: In dist/main, go up 4 levels
      projectRoot = path.resolve(appPath, '..', '..', '..', '..');
    } else if (appPath.endsWith(path.join('apps', 'desktop'))) {
      // Case 2: In apps/desktop, go up 2 levels
      projectRoot = path.resolve(appPath, '..', '..');
    } else {
      // Fallback: Try to find 'cardflux' in the path
      const pathParts = appPath.split(path.sep);
      const cardfluxIndex = pathParts.findIndex(part => part.toLowerCase() === 'cardflux');
      if (cardfluxIndex === -1) {
        throw new Error(
          `Cannot determine project root: appPath does not contain 'cardflux': ${appPath}`
        );
      }
      projectRoot = pathParts.slice(0, cardfluxIndex + 1).join(path.sep);
    }

    // SECURITY: Validate the resolved path is what we expect
    // 1. Path must be absolute
    if (!path.isAbsolute(projectRoot)) {
      throw new Error(`Invalid project root (not absolute): ${projectRoot}`);
    }

    // 2. Path must contain 'cardflux' (project name)
    const normalizedRoot = projectRoot.toLowerCase().replace(/\\/g, '/');
    if (!normalizedRoot.includes('cardflux')) {
      throw new Error(
        `Invalid project root (does not contain 'cardflux'): ${projectRoot}`
      );
    }

    // 3. HIGH SEVERITY FIX: Prevent path traversal using path.relative()
    // Check that appPath doesn't escape projectRoot by using '..'
    const normalizedProjectRoot = path.normalize(projectRoot);
    const normalizedAppPath = path.normalize(appPath);

    // Get relative path from project root to app path
    const relativePath = path.relative(normalizedProjectRoot, normalizedAppPath);

    // If relative path starts with '..', appPath is outside projectRoot
    if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
      throw new Error(
        `Path traversal detected: appPath=${appPath} escapes projectRoot=${projectRoot} (relative: ${relativePath})`
      );
    }

    // Build child paths using safe path.join (no '..' allowed in components)
    const scriptsPath = path.join(projectRoot, 'scripts', 'identification');
    const dataPath = path.join(projectRoot, 'data');

    // Validate scripts path exists and is within project root
    const normalizedScriptsPath = path.normalize(scriptsPath).toLowerCase();
    const normalizedProjectRootLower = normalizedProjectRoot.toLowerCase();
    if (!normalizedScriptsPath.startsWith(normalizedProjectRootLower)) {
      throw new Error(
        `Path traversal detected in scripts: ${scriptsPath} (normalized: ${normalizedScriptsPath}) does not start with project root: ${normalizedProjectRootLower}`
      );
    }

    logger.info('ResourceManager', 'Development paths resolved', {
      appPath,
      projectRoot,
      scriptsPath,
      dataPath,
    });

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
        logger.debug('ResourceManager', `Verified: ${description}`, { path: filepath });
      } catch (error) {
        const errorMsg = `${description} not found: ${filepath}`;
        errors.push(errorMsg);
        logger.error('ResourceManager', `Missing: ${description}`, error as Error, {
          path: filepath,
          error: (error as NodeJS.ErrnoException).code,
        });
      }
    };

    // In production, verify bundled Python exists
    if (this.isPackaged) {
      await checkExists(paths.pythonExecutable, 'Python executable');
      await checkExists(paths.pythonHome, 'Python home directory');
      await checkExists(paths.sitePackages, 'Site packages directory');
      await checkExists(paths.scripts, 'Python scripts directory');
    } else {
      // In development, only verify scripts exist
      await checkExists(paths.scripts, 'Scripts directory');
    }

    // Verify identification_service.py exists
    const servicePath = this.getServiceScriptPath();
    await checkExists(servicePath, 'Identification service script');

    if (errors.length > 0) {
      const error = new Error(
        `Resource verification failed (${errors.length} ${errors.length === 1 ? 'error' : 'errors'}):\n${errors.join('\n')}`
      );
      logger.error('ResourceManager', 'Path verification failed', error, {
        errorCount: errors.length,
        errors,
        isPackaged: this.isPackaged,
      });
      throw error;
    }

    logger.info('ResourceManager', 'All resource paths verified successfully', {
      pythonExecutable: paths.pythonExecutable,
      scripts: paths.scripts,
      dataDir: paths.dataDir,
    });
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
      // app.getAppPath() can be either:
      //   Case 1: .../apps/desktop/dist/main → go up 2 to apps/desktop
      //   Case 2: .../apps/desktop → already there
      const appPath = app.getAppPath();

      let desktopRoot: string;
      if (appPath.includes(path.join('apps', 'desktop', 'dist'))) {
        // Case 1: In dist/main, go up 2 levels to apps/desktop
        desktopRoot = path.resolve(appPath, '..', '..');
      } else if (appPath.endsWith(path.join('apps', 'desktop'))) {
        // Case 2: Already in apps/desktop
        desktopRoot = appPath;
      } else {
        // Fallback: Find 'desktop' after 'apps' in path
        const pathParts = appPath.split(path.sep);
        const appsIndex = pathParts.findIndex(part => part.toLowerCase() === 'apps');
        if (appsIndex !== -1 && appsIndex + 1 < pathParts.length) {
          desktopRoot = pathParts.slice(0, appsIndex + 2).join(path.sep);
        } else {
          throw new Error(`Cannot determine desktop root from appPath: ${appPath}`);
        }
      }

      const servicePath = path.join(desktopRoot, 'src', 'python', 'identification_service.py');

      // SECURITY: Validate path is within expected bounds
      const normalizedServicePath = path.normalize(servicePath).toLowerCase();
      if (!normalizedServicePath.includes('cardflux') || !normalizedServicePath.includes('identification_service.py')) {
        throw new Error(`Invalid service script path: ${servicePath}`);
      }

      logger.debug('ResourceManager', 'Service script path resolved', {
        appPath,
        desktopRoot,
        servicePath,
      });

      return servicePath;
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
        timeout: 5000, // 5 second timeout for version check
      });

      let output = '';
      let resolved = false;

      const cleanup = (result: boolean) => {
        if (resolved) return;
        resolved = true;

        // Kill process if still running
        if (proc && !proc.killed) {
          proc.kill('SIGTERM');
        }

        resolve(result);
      };

      // Timeout handler
      const timeoutId = setTimeout(() => {
        logger.error('ResourceManager', 'Python version check timed out after 5s');
        cleanup(false);
      }, 5000);

      proc.stdout?.on('data', (data: Buffer) => {
        output += data.toString();
      });

      proc.stderr?.on('data', (data: Buffer) => {
        output += data.toString();
      });

      proc.on('close', (code: number) => {
        clearTimeout(timeoutId);

        if (code === 0) {
          logger.info('ResourceManager', 'Python version check passed', {
            version: output.trim(),
          });
          cleanup(true);
        } else {
          logger.error('ResourceManager', 'Python version check failed', undefined, {
            code,
            output: output.trim(),
          });
          cleanup(false);
        }
      });

      proc.on('error', (error: Error) => {
        clearTimeout(timeoutId);
        logger.error('ResourceManager', 'Failed to spawn Python', error);
        cleanup(false);
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
