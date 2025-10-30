#!/usr/bin/env node
/**
 * Windows Python Bundler
 *
 * Downloads and bundles Python 3.13 embedded package for Windows
 * Installs all required pip packages
 * Copies Python scripts
 *
 * This runs ONLY when building for production, not during development
 *
 * Usage: node scripts/build/bundle-python-windows.js
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');
const { createWriteStream, createReadStream } = require('fs');
const { pipeline } = require('stream/promises');
const AdmZip = require('adm-zip');

// Configuration
const PYTHON_VERSION = '3.13.1';
const PYTHON_DOWNLOAD_URL = `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip`;

// SHA256 checksum from https://www.python.org/downloads/release/python-3131/
// Updated 2025-10-30 - Windows embeddable package (64-bit)
// NOTE: Update this when Python version changes
const PYTHON_SHA256 = '7b7923ff0183a8b8fca90f6047184b419b108cb437f75fc1c002f9d2f8bcec16';

// get-pip.py SHA256 from https://bootstrap.pypa.io/get-pip.py
// Downloaded and verified on 2025-10-20
// NOTE: Update this when get-pip.py version changes
const GET_PIP_SHA256 = 'b4c0f2a23c8c26893d5b9bdcd3ef8e6d3915d90f84acccafa3e7829bd0bf4414';

const ROOT_DIR = path.join(__dirname, '../../../..');
const DESKTOP_DIR = path.join(ROOT_DIR, 'apps', 'desktop');
const RESOURCES_DIR = path.join(DESKTOP_DIR, 'resources');
const PYTHON_RUNTIME_DIR = path.join(RESOURCES_DIR, 'python-runtime', 'win32');
const SITE_PACKAGES_DIR = path.join(RESOURCES_DIR, 'python-site-packages');
const SCRIPTS_DIR = path.join(RESOURCES_DIR, 'python-scripts');
const TEMP_DIR = path.join(DESKTOP_DIR, '.bundle-temp');

// Color console output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function logStep(step, message) {
  log(`[${step}] ${message}`, colors.cyan);
}

function logSuccess(message) {
  log(`✓ ${message}`, colors.green);
}

function logError(message) {
  log(`✗ ${message}`, colors.red);
}

function logWarning(message) {
  log(`⚠ ${message}`, colors.yellow);
}

/**
 * Verify SHA256 checksum of a file
 */
async function verifyChecksum(filePath, expectedSha256) {
  return new Promise((resolve, reject) => {
    logStep('VERIFY', `Verifying checksum: ${path.basename(filePath)}`);

    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);

    stream.on('data', (data) => hash.update(data));
    stream.on('end', () => {
      const actualSha256 = hash.digest('hex');
      if (actualSha256 === expectedSha256) {
        logSuccess(`Checksum verified: ${actualSha256.substring(0, 16)}...`);
        resolve();
      } else {
        reject(new Error(
          `Checksum mismatch!\n` +
          `  Expected: ${expectedSha256}\n` +
          `  Got:      ${actualSha256}\n` +
          `  This could indicate a corrupted download or MITM attack.`
        ));
      }
    });
    stream.on('error', reject);
  });
}

/**
 * Download file with progress and validation
 */
async function downloadFile(url, destPath, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) {
      reject(new Error('Too many redirects'));
      return;
    }

    logStep('DOWNLOAD', `Downloading from ${url}`);

    // Ensure HTTPS
    if (!url.startsWith('https://')) {
      reject(new Error('Only HTTPS downloads are allowed for security'));
      return;
    }

    const file = createWriteStream(destPath);
    let downloadedBytes = 0;
    let fileOpened = true;

    const request = https.get(url, { timeout: 30000 }, (response) => {
      // Handle redirects
      if (response.statusCode === 302 || response.statusCode === 301) {
        fileOpened = false;
        file.close();

        // Wait for file to close before unlinking
        file.on('close', () => {
          if (fs.existsSync(destPath)) {
            fs.unlinkSync(destPath);
          }

          const redirectUrl = response.headers.location;
          // Ensure redirect is also HTTPS
          if (!redirectUrl.startsWith('https://')) {
            reject(new Error(`Insecure redirect to: ${redirectUrl}`));
            return;
          }

          downloadFile(redirectUrl, destPath, maxRedirects - 1).then(resolve).catch(reject);
        });
        return;
      }

      if (response.statusCode !== 200) {
        fileOpened = false;
        file.close();
        reject(new Error(`Download failed: HTTP ${response.statusCode}`));
        return;
      }

      const totalBytes = parseInt(response.headers['content-length'], 10);

      response.on('data', (chunk) => {
        downloadedBytes += chunk.length;
        if (totalBytes > 0) {
          const progress = ((downloadedBytes / totalBytes) * 100).toFixed(1);
          process.stdout.write(`\r  Progress: ${progress}% (${(downloadedBytes / 1024 / 1024).toFixed(1)} MB / ${(totalBytes / 1024 / 1024).toFixed(1)} MB)`);
        }
      });

      response.pipe(file);

      file.on('finish', () => {
        fileOpened = false;
        file.close();
        console.log(''); // New line after progress
        logSuccess(`Downloaded to ${destPath}`);
        resolve();
      });
    });

    request.on('timeout', () => {
      request.destroy();
      if (fileOpened) {
        fileOpened = false;
        file.close();
        file.on('close', () => {
          if (fs.existsSync(destPath)) {
            fs.unlinkSync(destPath);
          }
        });
      }
      reject(new Error('Download timeout after 30 seconds'));
    });

    request.on('error', (error) => {
      if (fileOpened) {
        fileOpened = false;
        file.close();
        file.on('close', () => {
          if (fs.existsSync(destPath)) {
            fs.unlinkSync(destPath);
          }
        });
      }
      reject(error);
    });

    file.on('error', (error) => {
      if (fileOpened) {
        fileOpened = false;
        file.close();
      }
      request.destroy();
      reject(error);
    });
  });
}

/**
 * Extract ZIP file
 */
function extractZip(zipPath, destPath) {
  logStep('EXTRACT', `Extracting ${zipPath}`);

  try {
    const zip = new AdmZip(zipPath);
    zip.extractAllTo(destPath, true);
    logSuccess(`Extracted to ${destPath}`);
  } catch (error) {
    throw new Error(`Failed to extract ZIP: ${error.message}`);
  }
}

/**
 * Install pip packages
 */
async function installPipPackages() {
  logStep('PIP', 'Installing pip packages');

  try {
    // Path to bundled Python executable
    const pythonExe = path.join(PYTHON_RUNTIME_DIR, 'python.exe');

    if (!fs.existsSync(pythonExe)) {
      throw new Error(`Python executable not found: ${pythonExe}`);
    }

    // First, we need to install pip in the embedded Python
    logStep('PIP', 'Installing pip in embedded Python');

    // Check for bundled get-pip.py first (secure option)
    const bundledGetPipPath = path.join(RESOURCES_DIR, 'get-pip.py');
    const getPipPath = path.join(TEMP_DIR, 'get-pip.py');

    if (fs.existsSync(bundledGetPipPath)) {
      // Use bundled version (secure, no network needed)
      logSuccess('Using bundled get-pip.py');
      fs.copyFileSync(bundledGetPipPath, getPipPath);

      // Verify bundled checksum
      await verifyChecksum(getPipPath, GET_PIP_SHA256);
    } else {
      // Download from official source as fallback
      logWarning('Bundled get-pip.py not found, downloading from bootstrap.pypa.io');
      await downloadFile('https://bootstrap.pypa.io/get-pip.py', getPipPath);

      // Verify downloaded checksum
      await verifyChecksum(getPipPath, GET_PIP_SHA256);
    }

    // Install pip
    execSync(`"${pythonExe}" "${getPipPath}" --no-warn-script-location`, {
      stdio: 'inherit',
      cwd: PYTHON_RUNTIME_DIR,
      timeout: 120000, // 2 minute timeout
    });

    logSuccess('Pip installed');

    // Install packages from requirements.txt
    const requirementsPath = path.join(RESOURCES_DIR, 'python-requirements.txt');

    if (!fs.existsSync(requirementsPath)) {
      throw new Error(`Requirements file not found: ${requirementsPath}`);
    }

    logStep('PIP', `Installing packages from ${requirementsPath}`);

    // Install to site-packages directory with timeout
    // Note: This can take 5-10 minutes for large packages like torch
    execSync(
      `"${pythonExe}" -m pip install --target "${SITE_PACKAGES_DIR}" -r "${requirementsPath}" --no-warn-script-location`,
      {
        stdio: 'inherit',
        cwd: PYTHON_RUNTIME_DIR,
        timeout: 600000, // 10 minute timeout for large packages
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer for pip output
      }
    );

    logSuccess('All packages installed');

    // Clean up unnecessary files to reduce size
    logStep('CLEANUP', 'Removing unnecessary files');
    await cleanupSitePackages();
    logSuccess('Cleanup complete');
  } catch (error) {
    throw new Error(`Failed to install pip packages: ${error.message}`);
  }
}

/**
 * Clean up site-packages to reduce size
 * Removes unnecessary files like tests, caches, and dist-info
 */
async function cleanupSitePackages() {
  const patternsToRemove = [
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyo',
    '**/tests',
    '**/test',
    '**/*.dist-info',
    '**/*.egg-info',
  ];

  const { glob } = require('glob');
  let removedCount = 0;
  let savedBytes = 0;

  for (const pattern of patternsToRemove) {
    try {
      const files = await glob(pattern, {
        cwd: SITE_PACKAGES_DIR,
        absolute: true,
        dot: true,
        nodir: false,
      });

      for (const file of files) {
        try {
          if (fs.existsSync(file)) {
            const stats = fs.statSync(file);
            savedBytes += stats.size;

            if (stats.isDirectory()) {
              fs.rmSync(file, { recursive: true, force: true });
            } else {
              fs.unlinkSync(file);
            }
            removedCount++;
          }
        } catch (error) {
          // Log but continue on individual file errors
          logWarning(`Failed to remove ${file}: ${error.message}`);
        }
      }
    } catch (error) {
      // Log but continue if pattern fails
      logWarning(`Pattern ${pattern} failed: ${error.message}`);
    }
  }

  if (removedCount > 0) {
    logSuccess(`Removed ${removedCount} files/folders (saved ${(savedBytes / 1024 / 1024).toFixed(1)} MB)`);
  }
}

/**
 * Copy Python scripts
 */
function copyPythonScripts() {
  logStep('SCRIPTS', 'Copying Python scripts');

  // Ensure scripts directory exists
  if (!fs.existsSync(SCRIPTS_DIR)) {
    fs.mkdirSync(SCRIPTS_DIR, { recursive: true });
  }

  // Copy scripts from project root
  const scriptsSource = path.join(ROOT_DIR, 'scripts', 'identification');

  if (!fs.existsSync(scriptsSource)) {
    throw new Error(`Scripts source directory not found: ${scriptsSource}`);
  }

  // Copy all Python files
  const files = fs.readdirSync(scriptsSource);
  files.forEach((file) => {
    if (file.endsWith('.py')) {
      const src = path.join(scriptsSource, file);
      const dest = path.join(SCRIPTS_DIR, file);
      fs.copyFileSync(src, dest);
      logSuccess(`Copied ${file}`);
    }
  });

  // Also copy the desktop app Python files
  const desktopPythonSource = path.join(DESKTOP_DIR, 'src', 'python');
  const desktopPythonFiles = fs.readdirSync(desktopPythonSource);
  desktopPythonFiles.forEach((file) => {
    if (file.endsWith('.py')) {
      const src = path.join(desktopPythonSource, file);
      const dest = path.join(SCRIPTS_DIR, file);
      fs.copyFileSync(src, dest);
      logSuccess(`Copied ${file} (desktop)`);
    }
  });
}

/**
 * Main bundler function
 */
async function bundle() {
  console.log('\n========================================');
  console.log('  CardFlux Python Bundler (Windows)');
  console.log('========================================\n');

  const startTime = Date.now();

  try {
    // 1. Create directories
    logStep('SETUP', 'Creating directories');
    [RESOURCES_DIR, PYTHON_RUNTIME_DIR, SITE_PACKAGES_DIR, SCRIPTS_DIR, TEMP_DIR].forEach((dir) => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
    logSuccess('Directories created');

    // 2. Download Python
    const pythonZipPath = path.join(TEMP_DIR, `python-${PYTHON_VERSION}-embed-amd64.zip`);
    const pythonExePath = path.join(PYTHON_RUNTIME_DIR, 'python.exe');

    if (!fs.existsSync(pythonZipPath)) {
      await downloadFile(PYTHON_DOWNLOAD_URL, pythonZipPath);

      // Verify checksum immediately after download
      await verifyChecksum(pythonZipPath, PYTHON_SHA256);
    } else {
      logWarning('Python ZIP already exists, verifying checksum');
      // Always verify checksum even if file exists (could be corrupted)
      try {
        await verifyChecksum(pythonZipPath, PYTHON_SHA256);
      } catch (error) {
        logError('Checksum verification failed, re-downloading');
        fs.unlinkSync(pythonZipPath);
        await downloadFile(PYTHON_DOWNLOAD_URL, pythonZipPath);
        await verifyChecksum(pythonZipPath, PYTHON_SHA256);
      }
    }

    // 3. Extract Python
    if (!fs.existsSync(pythonExePath)) {
      extractZip(pythonZipPath, PYTHON_RUNTIME_DIR);

      // Verify extraction succeeded
      if (!fs.existsSync(pythonExePath)) {
        throw new Error('Python extraction failed - python.exe not found after extraction');
      }
    } else {
      logWarning('Python already extracted, skipping');
    }

    // 4. Install pip packages
    const sitePackagesContents = fs.existsSync(SITE_PACKAGES_DIR)
      ? fs.readdirSync(SITE_PACKAGES_DIR)
      : [];

    if (sitePackagesContents.length === 0) {
      await installPipPackages();
    } else {
      logWarning(`Site packages already exist (${sitePackagesContents.length} items), skipping installation`);
    }

    // 5. Copy Python scripts
    copyPythonScripts();

    // 6. Cleanup temp files
    logStep('CLEANUP', 'Removing temporary files');
    fs.rmSync(TEMP_DIR, { recursive: true, force: true });
    logSuccess('Temporary files removed');

    // Success summary
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log('\n========================================');
    logSuccess(`✓ Bundle complete in ${duration}s`);
    console.log('========================================\n');

    // Show bundle size
    const { execSync } = require('child_process');
    try {
      const size = execSync(`powershell "(Get-ChildItem -Path '${RESOURCES_DIR}' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"`)
        .toString()
        .trim();
      log(`Bundle size: ${parseFloat(size).toFixed(1)} MB`, colors.cyan);
    } catch (error) {
      // Silently fail if we can't get size
    }

    process.exit(0);
  } catch (error) {
    console.error('\n========================================');
    logError(`✗ Bundle failed: ${error.message}`);
    console.error('========================================\n');
    console.error(error.stack);
    process.exit(1);
  }
}

// Run bundler
bundle();
