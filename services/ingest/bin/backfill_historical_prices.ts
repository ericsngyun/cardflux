#!/usr/bin/env node
/**
 * Historical Price Backfill from tcgcsv.com Archives
 *
 * Downloads and processes historical price data from tcgcsv.com archives
 * (available from Feb 8, 2024 onwards).
 *
 * Archive Structure:
 *   https://tcgcsv.com/archive/tcgplayer/prices-{YYYY-MM-DD}.ppmd.7z
 *   Extract to: {YYYY-MM-DD}/{categoryId}/{groupId}/prices
 *
 * For One Piece Card Game:
 *   - categoryId: 68
 *   - groupIds: extracted from our curated data
 *   - prices file contains JSON: { productId: { price data } }
 *
 * Strategy:
 * 1. Download daily archives (Feb 8, 2024 → yesterday)
 * 2. Extract category 68 (One Piece) data only
 * 3. Match productIds with our curated card database
 * 4. Store in unified price history database
 * 5. Clean up temp files
 *
 * Output: data/prices/historical/{game}.db (SQLite)
 */

import * as fs from 'fs';
import * as path from 'path';
import * as child_process from 'child_process';
import axios from 'axios';
import { getAllGames } from '@cardflux/config';
import { parseJsonLines, sleep } from '@cardflux/shared';
import { getCategoryByName } from '@cardflux/config';

const ARCHIVE_BASE_URL = 'https://tcgcsv.com/archive/tcgplayer';
const TEMP_DIR = path.resolve(__dirname, '../../../.temp/price-archives');
const PRICES_DIR = path.resolve(__dirname, '../../../data/prices/historical');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');

// Historical data starts Feb 8, 2024
const ARCHIVE_START_DATE = new Date('2024-02-08');

interface Card {
  id: string;
  game: string;
  name: string;
  productId: string | number;
  groupId: number;
  groupName?: string;
  set?: string;
  number?: string;
  rarity?: string;
}

interface ArchivePriceData {
  lowPrice: number | null;
  midPrice: number | null;
  highPrice: number | null;
  marketPrice: number | null;
  directLowPrice: number | null;
  subTypeName: string; // "Normal" or "Foil"
}

interface PriceSnapshot {
  productId: string;
  game: string;
  cardName: string;
  setName: string | null;
  number: string | null;
  date: string;

  marketPrice: number | null; // in cents
  lowPrice: number | null;
  midPrice: number | null;
  highPrice: number | null;
  directLowPrice: number | null;

  isFoil: boolean;
  source: string;
}

interface BackfillState {
  game: string;
  lastProcessedDate: string;
  totalDays: number;
  processedDays: number;
  failedDates: string[];
}

/**
 * Convert dollars to cents
 */
function dollarsToCents(dollars: number | null): number | null {
  if (dollars === null || dollars === undefined) return null;
  return Math.round(dollars * 100);
}

/**
 * Generate list of dates from start to end
 */
function generateDateRange(start: Date, end: Date): string[] {
  const dates: string[] = [];
  const current = new Date(start);

  while (current <= end) {
    dates.push(current.toISOString().split('T')[0]);
    current.setDate(current.getDate() + 1);
  }

  return dates;
}

/**
 * Download archive for a specific date
 */
async function downloadArchive(date: string): Promise<string | null> {
  const archiveUrl = `${ARCHIVE_BASE_URL}/prices-${date}.ppmd.7z`;
  const archivePath = path.join(TEMP_DIR, `prices-${date}.ppmd.7z`);

  // Skip if already downloaded
  if (fs.existsSync(archivePath)) {
    console.log(`  ✓ Archive already downloaded: ${date}`);
    return archivePath;
  }

  console.log(`  Downloading archive: ${date}...`);

  try {
    const response = await axios.get(archiveUrl, {
      responseType: 'arraybuffer',
      timeout: 120000, // 2 minutes
      maxContentLength: 50 * 1024 * 1024, // 50 MB max
    });

    fs.mkdirSync(TEMP_DIR, { recursive: true });
    fs.writeFileSync(archivePath, response.data);

    const sizeMB = (response.data.length / 1024 / 1024).toFixed(2);
    console.log(`  ✓ Downloaded ${sizeMB} MB`);

    return archivePath;

  } catch (error: any) {
    if (error.response?.status === 404) {
      console.log(`  ⚠️  Archive not available for ${date}`);
      return null;
    }

    console.error(`  ✗ Download failed for ${date}: ${error.message}`);
    return null;
  }
}

/**
 * Extract archive to temp directory
 */
function extractArchive(archivePath: string, date: string): string | null {
  const extractPath = path.join(TEMP_DIR, date);

  // Skip if already extracted
  if (fs.existsSync(extractPath)) {
    console.log(`  ✓ Archive already extracted: ${date}`);
    return extractPath;
  }

  console.log(`  Extracting archive: ${date}...`);

  try {
    // Use 7z command (must be installed)
    child_process.execSync(`7z x "${archivePath}" -o"${extractPath}" -y`, {
      stdio: 'pipe',
    });

    console.log(`  ✓ Extracted to ${extractPath}`);
    return extractPath;

  } catch (error: any) {
    console.error(`  ✗ Extraction failed for ${date}: ${error.message}`);
    console.error(`  Make sure 7-Zip is installed: https://www.7-zip.org/`);
    return null;
  }
}

/**
 * Load price data for a specific group from extracted archive
 */
function loadGroupPrices(
  extractedPath: string,
  categoryId: number,
  groupId: number
): Map<string, ArchivePriceData> | null {
  // Path: {date}/{categoryId}/{groupId}/prices
  const pricesPath = path.join(extractedPath, String(categoryId), String(groupId), 'prices');

  if (!fs.existsSync(pricesPath)) {
    return null;
  }

  try {
    const pricesJson = JSON.parse(fs.readFileSync(pricesPath, 'utf-8'));
    const pricesMap = new Map<string, ArchivePriceData>();

    // Convert object keys to map
    for (const [productId, priceData] of Object.entries(pricesJson)) {
      pricesMap.set(productId, priceData as ArchivePriceData);
    }

    return pricesMap;

  } catch (error) {
    console.warn(`    Failed to load prices for group ${groupId}: ${error}`);
    return null;
  }
}

/**
 * Process prices for one game for one date
 */
async function processPricesForDate(
  gameSlug: string,
  date: string,
  cards: Card[]
): Promise<PriceSnapshot[]> {
  console.log(`\nProcessing ${gameSlug} for ${date}...`);

  // Download archive
  const archivePath = await downloadArchive(date);
  if (!archivePath) {
    return [];
  }

  // Extract archive
  const extractedPath = extractArchive(archivePath, date);
  if (!extractedPath) {
    return [];
  }

  // Get unique group IDs from our cards
  const groupIds = Array.from(new Set(cards.map(c => c.groupId)));
  console.log(`  Processing ${groupIds.length} groups...`);

  const snapshots: PriceSnapshot[] = [];
  let matchedProducts = 0;

  // Get category ID for this game from TCGPlayer config
  const games = getAllGames();
  const gameConfig = games.find(g => g.slug === gameSlug);
  if (!gameConfig) {
    console.error(`  ✗ No game config found for ${gameSlug}`);
    return [];
  }

  // Map game name to TCGPlayer category
  const category = getCategoryByName(gameConfig.name);
  if (!category) {
    console.error(`  ✗ No TCGPlayer category found for ${gameConfig.name}`);
    return [];
  }

  const categoryId = category.categoryId;
  console.log(`  Using TCGPlayer category ${categoryId}: ${category.name}`);

  // Process each group
  for (const groupId of groupIds) {
    const groupPrices = loadGroupPrices(extractedPath, categoryId, groupId);

    if (!groupPrices) {
      continue;
    }

    // Match products from this group
    const groupCards = cards.filter(c => c.groupId === groupId);

    for (const card of groupCards) {
      const productId = String(card.productId);
      const priceData = groupPrices.get(productId);

      if (!priceData) {
        continue;
      }

      const snapshot: PriceSnapshot = {
        productId,
        game: gameSlug,
        cardName: card.name,
        setName: card.set || card.groupName || null,
        number: card.number || null,
        date,

        marketPrice: dollarsToCents(priceData.marketPrice),
        lowPrice: dollarsToCents(priceData.lowPrice),
        midPrice: dollarsToCents(priceData.midPrice),
        highPrice: dollarsToCents(priceData.highPrice),
        directLowPrice: dollarsToCents(priceData.directLowPrice),

        isFoil: priceData.subTypeName === 'Foil',
        source: 'tcgcsv-archive',
      };

      snapshots.push(snapshot);
      matchedProducts++;
    }
  }

  console.log(`  ✓ Matched ${matchedProducts} products with price data`);

  return snapshots;
}

/**
 * Save price snapshots to JSONL
 */
function savePriceSnapshots(gameSlug: string, date: string, snapshots: PriceSnapshot[]): void {
  if (snapshots.length === 0) return;

  const outputDir = path.join(PRICES_DIR, gameSlug);
  fs.mkdirSync(outputDir, { recursive: true });

  const outputPath = path.join(outputDir, `${date}.jsonl`);
  const lines = snapshots.map(s => JSON.stringify(s)).join('\n');

  fs.writeFileSync(outputPath, lines + '\n');
  console.log(`  ✓ Saved ${snapshots.length} snapshots to ${outputPath}`);
}

/**
 * Load backfill state
 */
function loadState(gameSlug: string): BackfillState | null {
  const statePath = path.join(STATE_DIR, `${gameSlug}.price-backfill.json`);

  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
  } catch (error) {
    console.warn(`Failed to load backfill state: ${error}`);
    return null;
  }
}

/**
 * Save backfill state
 */
function saveState(state: BackfillState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, `${state.game}.price-backfill.json`);
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Backfill historical prices for one game
 */
async function backfillGamePrices(gameSlug: string): Promise<void> {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`BACKFILLING HISTORICAL PRICES: ${gameSlug}`);
  console.log('='.repeat(80));

  // Load cards
  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);
  if (!fs.existsSync(curatedPath)) {
    console.log(`No curated data found for ${gameSlug}`);
    return;
  }

  const content = fs.readFileSync(curatedPath, 'utf-8');
  const { data: cards } = parseJsonLines<Card>(content);

  console.log(`Loaded ${cards.length} cards`);

  // Generate date range (Feb 8, 2024 → yesterday)
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dates = generateDateRange(ARCHIVE_START_DATE, yesterday);

  console.log(`Date range: ${dates[0]} → ${dates[dates.length - 1]} (${dates.length} days)`);

  // Load state
  let state = loadState(gameSlug) || {
    game: gameSlug,
    lastProcessedDate: '',
    totalDays: dates.length,
    processedDays: 0,
    failedDates: [],
  };

  // Resume from last processed date
  const datesToProcess = state.lastProcessedDate
    ? dates.filter(d => d > state.lastProcessedDate)
    : dates;

  console.log(`Dates to process: ${datesToProcess.length}`);

  if (datesToProcess.length === 0) {
    console.log('✓ All dates already processed');
    return;
  }

  // Process each date
  for (let i = 0; i < datesToProcess.length; i++) {
    const date = datesToProcess[i];

    console.log(`\n[${i + 1}/${datesToProcess.length}] Processing ${date}...`);

    try {
      const snapshots = await processPricesForDate(gameSlug, date, cards);

      if (snapshots.length > 0) {
        savePriceSnapshots(gameSlug, date, snapshots);
      }

      state.lastProcessedDate = date;
      state.processedDays++;
      saveState(state);

      // Rate limiting - don't hammer tcgcsv
      if (i < datesToProcess.length - 1) {
        await sleep(2000); // 2 second delay between dates
      }

    } catch (error) {
      console.error(`✗ Failed to process ${date}: ${error}`);
      state.failedDates.push(date);
      saveState(state);
    }
  }

  console.log(`\n✓ Backfill complete for ${gameSlug}`);
  console.log(`  Processed: ${state.processedDays}/${state.totalDays} days`);
  console.log(`  Failed: ${state.failedDates.length} days`);

  if (state.failedDates.length === 0) {
    // Clean up state file on success
    const statePath = path.join(STATE_DIR, `${gameSlug}.price-backfill.json`);
    if (fs.existsSync(statePath)) {
      fs.unlinkSync(statePath);
    }
  }
}

async function main() {
  console.log('='.repeat(80));
  console.log('HISTORICAL PRICE BACKFILL FROM TCGCSV ARCHIVES');
  console.log('='.repeat(80));
  console.log();
  console.log('Archive source: https://tcgcsv.com/archive/tcgplayer/');
  console.log(`Date range: ${ARCHIVE_START_DATE.toISOString().split('T')[0]} → present`);
  console.log();

  // Check if 7z is installed
  try {
    child_process.execSync('7z', { stdio: 'pipe' });
  } catch (error) {
    console.error('ERROR: 7-Zip is not installed or not in PATH');
    console.error('Please install 7-Zip: https://www.7-zip.org/');
    console.error('Windows: Install and add to PATH');
    console.error('Mac: brew install p7zip');
    console.error('Linux: sudo apt-get install p7zip-full');
    process.exit(1);
  }

  // Get enabled games
  const games = getAllGames().filter(game => {
    const curatedPath = path.join(CURATED_DIR, `${game.slug}.jsonl`);
    return fs.existsSync(curatedPath);
  });

  if (games.length === 0) {
    console.log('No games with curated data found.');
    return;
  }

  console.log(`Games to backfill: ${games.map(g => g.name).join(', ')}\n`);

  for (const game of games) {
    await backfillGamePrices(game.slug);
  }

  console.log('\n' + '='.repeat(80));
  console.log('BACKFILL COMPLETE');
  console.log('='.repeat(80));
  console.log('\nNext steps:');
  console.log('1. Import JSONL files into SQLite database');
  console.log('2. Set up daily price scraper for ongoing updates');
  console.log('3. Integrate with desktop app for price display');
}

main().catch(console.error);
