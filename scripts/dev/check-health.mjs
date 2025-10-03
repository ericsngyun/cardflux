#!/usr/bin/env node
/**
 * Health check script for local development
 * Verifies all components are working
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');

const checks = [];

// Check 1: Node.js version
function checkNodeVersion() {
  const version = process.version;
  const major = parseInt(version.slice(1).split('.')[0]);

  if (major >= 20) {
    return { passed: true, message: `Node.js ${version} ✓` };
  } else {
    return { passed: false, message: `Node.js ${version} (requires >=20.0.0)` };
  }
}

// Check 2: Python availability
async function checkPython() {
  return new Promise(async (resolve) => {
    const { spawn } = await import('child_process');
    const proc = spawn('python', ['--version'], { shell: true });

    let output = '';
    proc.stdout.on('data', (data) => (output += data));
    proc.stderr.on('data', (data) => (output += data));

    proc.on('close', (code) => {
      if (code === 0) {
        resolve({ passed: true, message: `Python ${output.trim()} ✓` });
      } else {
        resolve({ passed: false, message: 'Python not found' });
      }
    });
  });
}

// Check 3: Required directories
function checkDirectories() {
  const dirs = [
    'data/raw/tcgplayer',
    'data/curated',
    'data/images',
    'data/state',
    'artifacts/metadata',
    'artifacts/faiss',
    'artifacts/manifests',
  ];

  const missing = dirs.filter((dir) => !fs.existsSync(path.join(ROOT, dir)));

  if (missing.length === 0) {
    return { passed: true, message: `All directories exist ✓` };
  } else {
    // Create missing directories
    for (const dir of missing) {
      fs.mkdirSync(path.join(ROOT, dir), { recursive: true });
    }
    return { passed: true, message: `Created ${missing.length} missing directories ✓` };
  }
}

// Check 4: Scraped data
function checkScrapedData() {
  const curatedDir = path.join(ROOT, 'data/curated');

  if (!fs.existsSync(curatedDir)) {
    return { passed: false, message: 'No curated data found (run scraper first)' };
  }

  const files = fs.readdirSync(curatedDir).filter((f) => f.endsWith('.jsonl'));

  if (files.length === 0) {
    return { passed: false, message: 'No curated JSONL files (run scraper first)' };
  }

  return { passed: true, message: `${files.length} categories scraped ✓` };
}

// Check 5: Database
function checkDatabase() {
  const dbPath = path.join(ROOT, 'artifacts/metadata/cards.db');

  if (!fs.existsSync(dbPath)) {
    return { passed: false, message: 'Database not built (run: pnpm tcgplayer:db)' };
  }

  const stats = fs.statSync(dbPath);
  const sizeMB = (stats.size / 1024 / 1024).toFixed(2);

  return { passed: true, message: `Database exists (${sizeMB} MB) ✓` };
}

// Check 6: FAISS indices
function checkFaissIndices() {
  const faissDir = path.join(ROOT, 'artifacts/faiss');

  if (!fs.existsSync(faissDir)) {
    return { passed: false, message: 'No FAISS indices (run: pnpm pipeline:index)' };
  }

  const games = fs.readdirSync(faissDir).filter((f) => {
    const indexPath = path.join(faissDir, f, 'index.faiss');
    return fs.existsSync(indexPath);
  });

  if (games.length === 0) {
    return { passed: false, message: 'No FAISS indices built' };
  }

  return { passed: true, message: `${games.length} FAISS indices built ✓` };
}

// Check 7: Disk space
function checkDiskSpace() {
  const dataDir = path.join(ROOT, 'data');
  const artifactsDir = path.join(ROOT, 'artifacts');

  function getDirSize(dir) {
    if (!fs.existsSync(dir)) return 0;

    let size = 0;
    const files = fs.readdirSync(dir, { withFileTypes: true });

    for (const file of files) {
      const filePath = path.join(dir, file.name);
      if (file.isDirectory()) {
        size += getDirSize(filePath);
      } else {
        size += fs.statSync(filePath).size;
      }
    }

    return size;
  }

  const dataSize = getDirSize(dataDir);
  const artifactsSize = getDirSize(artifactsDir);
  const totalSize = dataSize + artifactsSize;

  const totalGB = (totalSize / 1024 / 1024 / 1024).toFixed(2);

  if (totalGB > 50) {
    return { passed: false, message: `Using ${totalGB} GB (consider cleanup)` };
  }

  return { passed: true, message: `Using ${totalGB} GB ✓` };
}

// Check 8: API connectivity
async function checkApiConnectivity() {
  return new Promise(async (resolve) => {
    const https = await import('https');

    https.default
      .get('https://tcgcsv.com/tcgplayer/categories', (res) => {
        if (res.statusCode === 200) {
          resolve({ passed: true, message: 'tcgcsv.com API reachable ✓' });
        } else {
          resolve({ passed: false, message: `API returned ${res.statusCode}` });
        }
      })
      .on('error', () => {
        resolve({ passed: false, message: 'Cannot reach tcgcsv.com API' });
      });
  });
}

// Run all checks
async function runHealthCheck() {
  console.log('\n' + '='.repeat(60));
  console.log('CARDFLUX LOCAL DEVELOPMENT HEALTH CHECK');
  console.log('='.repeat(60) + '\n');

  const results = [
    { name: 'Node.js Version', result: checkNodeVersion() },
    { name: 'Python Installation', result: await checkPython() },
    { name: 'Directory Structure', result: checkDirectories() },
    { name: 'Scraped Data', result: checkScrapedData() },
    { name: 'Database', result: checkDatabase() },
    { name: 'FAISS Indices', result: checkFaissIndices() },
    { name: 'Disk Usage', result: checkDiskSpace() },
    { name: 'API Connectivity', result: await checkApiConnectivity() },
  ];

  let allPassed = true;

  for (const { name, result } of results) {
    const icon = result.passed ? '✅' : '❌';
    console.log(`${icon} ${name}: ${result.message}`);
    if (!result.passed) allPassed = false;
  }

  console.log('\n' + '='.repeat(60));

  if (allPassed) {
    console.log('✅ All checks passed! System ready for development.\n');
    console.log('🚀 Next steps:');
    console.log('  - Test scraper: node scripts/dev/test-scraper.mjs');
    console.log('  - Run pipeline: node scripts/dev/local-pipeline.mjs');
    console.log('  - Start desktop app: cd apps/desktop && pnpm dev\n');
  } else {
    console.log('⚠️  Some checks failed. See errors above.\n');
    console.log('🔧 Quick fixes:');
    console.log('  - Install Python: https://www.python.org/downloads/');
    console.log('  - Run scraper: pnpm dev:test-scrape');
    console.log('  - Build database: pnpm tcgplayer:db');
    console.log('  - Build indices: pnpm pipeline:index\n');
    process.exit(1);
  }
}

runHealthCheck().catch((error) => {
  console.error('Health check error:', error);
  process.exit(1);
});
