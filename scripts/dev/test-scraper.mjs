#!/usr/bin/env node
/**
 * Test scraper with limited data for development
 * Fetches only a subset of data to test quickly
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONFIG_PATH = path.resolve(__dirname, '../../packages/config/src/tcgplayer-config.ts');

// Backup original config
const originalConfig = fs.readFileSync(CONFIG_PATH, 'utf-8');

// Create test config (only 1 category, limit to specific groups)
const testConfig = originalConfig.replace(
  /enabledCategories: \[[\s\S]*?\]/,
  `enabledCategories: [
    { categoryId: 1, name: 'Magic', enabled: true },  // Only Magic for testing
    { categoryId: 2, name: 'YuGiOh', enabled: false },
    { categoryId: 3, name: 'Pokemon', enabled: false },
    { categoryId: 24, name: 'One Piece', enabled: false },
    { categoryId: 26, name: 'Digimon', enabled: false },
  ]`
);

console.log('🧪 TEST MODE: Limited scraping for development');
console.log('📝 Categories: Magic only');
console.log('⏱️  This will be much faster than full scrape\n');

// Write test config
fs.writeFileSync(CONFIG_PATH, testConfig);

// Run scraper
const proc = spawn('pnpm', ['tcgplayer:scrape'], {
  stdio: 'inherit',
  shell: true,
});

proc.on('close', (code) => {
  // Restore original config
  fs.writeFileSync(CONFIG_PATH, originalConfig);

  if (code === 0) {
    console.log('\n✅ Test scrape completed successfully');
    console.log('📊 Run validation: pnpm dev:validate');
    console.log('🔨 Build database: pnpm tcgplayer:db');
  } else {
    console.log(`\n❌ Test scrape failed with code ${code}`);
    process.exit(1);
  }
});

// Handle Ctrl+C
process.on('SIGINT', () => {
  fs.writeFileSync(CONFIG_PATH, originalConfig);
  console.log('\n⚠️  Test scrape interrupted, config restored');
  process.exit(130);
});
