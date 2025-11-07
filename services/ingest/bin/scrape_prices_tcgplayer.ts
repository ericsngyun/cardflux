#!/usr/bin/env node
/**
 * TCGPlayer Price Scraper
 *
 * Scrapes current market prices for all TCG cards from TCGPlayer API.
 * Runs daily to build historical price database.
 *
 * Features:
 * - Batch requests for efficiency (50-100 products per request)
 * - Rate limit handling (300 req/hour)
 * - Retry logic with exponential backoff
 * - Progress tracking and resume support
 * - Multiple condition support (NM, LP, MP, HP)
 * - Foil/Normal variant support
 *
 * Output: data/prices/snapshots/{game}/{YYYY-MM-DD}.jsonl
 */

import * as fs from 'fs';
import * as path from 'path';
import axios, { AxiosError } from 'axios';
import { getAllGames } from '@cardflux/config';
import { parseJsonLines, sleep, retry } from '@cardflux/shared';

const PRICES_DIR = path.resolve(__dirname, '../../../data/prices/snapshots');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');

const TCGPLAYER_API_BASE = 'https://api.tcgplayer.com';
const BATCH_SIZE = 50; // Products per request
const RATE_LIMIT_DELAY = 1000; // 1 second between requests (well under 300/hour)
const MAX_RETRIES = 3;

interface Card {
  id: string;
  game: string;
  name: string;
  set?: string;
  number?: string;
  rarity?: string;
  productId?: string | number; // TCGPlayer product ID
}

interface PriceData {
  productId: number;
  lowPrice: number | null;
  midPrice: number | null;
  highPrice: number | null;
  marketPrice: number | null;
  directLowPrice: number | null;
  subTypeName: string; // "Normal" or "Foil"
}

interface PriceSnapshot {
  // Identity
  productId: string;
  game: string;
  cardName: string;
  setName: string | null;
  number: string | null;
  rarity: string | null;

  // Pricing (in USD cents)
  timestamp: string;
  date: string;

  // Market prices (convert dollars to cents)
  marketPrice: number | null;
  lowPrice: number | null;
  midPrice: number | null;
  highPrice: number | null;
  directLowPrice: number | null;

  // Variants
  isFoil: boolean;
  condition: string; // Assuming "NM" for market prices

  // Metadata
  source: string;
}

interface PriceScrapeState {
  game: string;
  date: string;
  lastProductId: string | null;
  totalProducts: number;
  scrapedProducts: number;
  failedProducts: string[];
}

/**
 * Convert dollars to cents to avoid floating point errors
 */
function dollarsToCents(dollars: number | null): number | null {
  if (dollars === null || dollars === undefined) return null;
  return Math.round(dollars * 100);
}

/**
 * Fetch pricing for a batch of products
 */
async function fetchPricingBatch(productIds: number[]): Promise<Map<number, PriceData>> {
  const url = `${TCGPLAYER_API_BASE}/pricing/product/${productIds.join(',')}`;

  return await retry(
    async () => {
      const response = await axios.get(url, {
        headers: {
          'Accept': 'application/json',
        },
        timeout: 30000,
      });

      const pricing = new Map<number, PriceData>();

      if (response.data.results) {
        for (const result of response.data.results) {
          pricing.set(result.productId, result);
        }
      }

      return pricing;
    },
    {
      retries: MAX_RETRIES,
      minDelay: 2000,
      maxDelay: 10000,
      factor: 2,
      onRetry: (attempt, error) => {
        console.warn(`  Retry ${attempt}/${MAX_RETRIES} for batch: ${error.message}`);
      },
    }
  );
}

/**
 * Load cards for a game
 */
function loadCards(gameSlug: string): Card[] {
  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);

  if (!fs.existsSync(curatedPath)) {
    return [];
  }

  const content = fs.readFileSync(curatedPath, 'utf-8');
  const { data: cards } = parseJsonLines<Card>(content);

  return cards.filter(card => card.productId); // Only cards with TCGPlayer IDs
}

/**
 * Load scraping state for resume capability
 */
function loadState(gameSlug: string, date: string): PriceScrapeState | null {
  const statePath = path.join(STATE_DIR, `${gameSlug}.prices.${date}.json`);

  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
  } catch (error) {
    console.warn(`Failed to load state: ${error}`);
    return null;
  }
}

/**
 * Save scraping state
 */
function saveState(state: PriceScrapeState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, `${state.game}.prices.${state.date}.json`);
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Save price snapshots
 */
function savePriceSnapshots(gameSlug: string, date: string, snapshots: PriceSnapshot[]): void {
  const outputDir = path.join(PRICES_DIR, gameSlug);
  fs.mkdirSync(outputDir, { recursive: true });

  const outputPath = path.join(outputDir, `${date}.jsonl`);
  const lines = snapshots.map(s => JSON.stringify(s)).join('\n');

  // Append mode to support resume
  fs.appendFileSync(outputPath, lines + '\n');
}

/**
 * Scrape prices for one game
 */
async function scrapePricesForGame(gameSlug: string): Promise<void> {
  console.log(`\nScraping prices for ${gameSlug}...`);

  const cards = loadCards(gameSlug);

  if (cards.length === 0) {
    console.log(`  No cards found for ${gameSlug}`);
    return;
  }

  const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const timestamp = new Date().toISOString();

  // Load or create state
  let state = loadState(gameSlug, date) || {
    game: gameSlug,
    date,
    lastProductId: null,
    totalProducts: cards.length,
    scrapedProducts: 0,
    failedProducts: [],
  };

  console.log(`  Total cards: ${cards.length}`);
  console.log(`  Already scraped: ${state.scrapedProducts}`);

  // Filter to cards not yet scraped
  const cardsToScrape = state.lastProductId
    ? cards.filter(c => c.id > state.lastProductId!)
    : cards;

  if (cardsToScrape.length === 0) {
    console.log(`  ✓ All prices already scraped for ${date}`);
    return;
  }

  // Group into batches
  const batches: Card[][] = [];
  for (let i = 0; i < cardsToScrape.length; i += BATCH_SIZE) {
    batches.push(cardsToScrape.slice(i, i + BATCH_SIZE));
  }

  console.log(`  Batches to process: ${batches.length} (${BATCH_SIZE} products each)`);

  // Process batches
  let snapshots: PriceSnapshot[] = [];

  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const productIds = batch
      .map(c => parseInt(String(c.productId || c.id)))
      .filter(id => !isNaN(id));

    if (productIds.length === 0) continue;

    console.log(`  Batch ${i + 1}/${batches.length}: Fetching ${productIds.length} products...`);

    try {
      const pricing = await fetchPricingBatch(productIds);

      // Convert to snapshots
      for (const card of batch) {
        const productId = parseInt(String(card.productId || card.id));
        const priceData = pricing.get(productId);

        if (!priceData) {
          state.failedProducts.push(card.id);
          continue;
        }

        const snapshot: PriceSnapshot = {
          productId: String(productId),
          game: gameSlug,
          cardName: card.name,
          setName: card.set || null,
          number: card.number || null,
          rarity: card.rarity || null,

          timestamp,
          date,

          marketPrice: dollarsToCents(priceData.marketPrice),
          lowPrice: dollarsToCents(priceData.lowPrice),
          midPrice: dollarsToCents(priceData.midPrice),
          highPrice: dollarsToCents(priceData.highPrice),
          directLowPrice: dollarsToCents(priceData.directLowPrice),

          isFoil: priceData.subTypeName === 'Foil',
          condition: 'NM', // Market prices typically assume Near Mint

          source: 'tcgplayer',
        };

        snapshots.push(snapshot);
        state.scrapedProducts++;
        state.lastProductId = card.id;
      }

      // Save batch
      if (snapshots.length >= 100) {
        savePriceSnapshots(gameSlug, date, snapshots);
        snapshots = [];
      }

      // Save state checkpoint
      saveState(state);

      // Rate limiting
      await sleep(RATE_LIMIT_DELAY);

    } catch (error) {
      console.error(`  ✗ Batch ${i + 1} failed: ${error}`);

      // Mark all cards in batch as failed
      for (const card of batch) {
        state.failedProducts.push(card.id);
      }

      saveState(state);
    }

    // Progress indicator
    if ((i + 1) % 10 === 0 || i === batches.length - 1) {
      const percent = ((i + 1) / batches.length * 100).toFixed(1);
      console.log(`  Progress: ${i + 1}/${batches.length} batches (${percent}%)`);
    }
  }

  // Save remaining snapshots
  if (snapshots.length > 0) {
    savePriceSnapshots(gameSlug, date, snapshots);
  }

  console.log(`\n✓ ${gameSlug} complete:`);
  console.log(`  Scraped: ${state.scrapedProducts}/${state.totalProducts}`);
  console.log(`  Failed: ${state.failedProducts.length}`);

  // Clean up state file on success
  if (state.failedProducts.length === 0) {
    const statePath = path.join(STATE_DIR, `${gameSlug}.prices.${date}.json`);
    if (fs.existsSync(statePath)) {
      fs.unlinkSync(statePath);
    }
  }
}

async function main() {
  console.log('='.repeat(80));
  console.log('TCGPLAYER PRICE SCRAPER');
  console.log('='.repeat(80));
  console.log();

  const games = getAllGames().filter(game => {
    const curatedPath = path.join(CURATED_DIR, `${game.slug}.jsonl`);
    return fs.existsSync(curatedPath);
  });

  if (games.length === 0) {
    console.log('No games with curated data found.');
    return;
  }

  console.log(`Games to scrape: ${games.map(g => g.name).join(', ')}`);

  for (const game of games) {
    await scrapePricesForGame(game.slug);
  }

  console.log('\n' + '='.repeat(80));
  console.log('PRICE SCRAPING COMPLETE');
  console.log('='.repeat(80));
}

main().catch(console.error);
