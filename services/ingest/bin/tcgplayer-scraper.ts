#!/usr/bin/env node
/**
 * Unified TCGplayer scraper using tcgcsv.com API
 * Fetches categories, groups, products, and prices
 */

import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import {
  TCGCSV_CONFIG,
  getEnabledCategories,
  getCategoryById,
  mergeProductAndPrices,
  isSealedProduct,
  type TCGCategory,
  type TCGGroup,
  type TCGProduct,
  type TCGPrice,
  type TCGCard,
} from '@cardflux/config/tcgplayer-config';
import {
  sleep,
  retry,
  logger,
  createPipelineLogger,
  onShutdown,
  setCurrentOperation,
  isShuttingDown,
  formatBytes,
} from '@cardflux/shared';
import pLimit from 'p-limit';

const RAW_DIR = path.resolve(__dirname, '../../../data/raw/tcgplayer');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');

// Rate limiting
const limit = pLimit(TCGCSV_CONFIG.rateLimit.requestsPerSecond);

interface ScrapeState {
  lastSync: string;
  categories: Array<{
    categoryId: number;
    lastModified: string;
    groupCount: number;
    productCount: number;
  }>;
}

/**
 * Fetch with retry and rate limiting
 */
async function fetchWithRetry<T>(url: string): Promise<T> {
  await sleep(200); // Base rate limiting

  return await retry(
    async () => {
      const response = await axios.get(url, {
        timeout: TCGCSV_CONFIG.request.timeout,
        headers: {
          ...TCGCSV_CONFIG.request.headers,
          'User-Agent': TCGCSV_CONFIG.request.userAgent,
        },
      });

      if (!response.data.success) {
        throw new Error(`API error: ${JSON.stringify(response.data.errors)}`);
      }

      return response.data.results as T;
    },
    {
      retries: TCGCSV_CONFIG.rateLimit.maxRetries,
      minDelay: TCGCSV_CONFIG.rateLimit.retryDelay,
      maxDelay: TCGCSV_CONFIG.rateLimit.retryDelay * Math.pow(TCGCSV_CONFIG.rateLimit.backoffMultiplier, 3),
      factor: TCGCSV_CONFIG.rateLimit.backoffMultiplier,
      onRetry: (attempt, error) => {
        logger.warn(`Retry ${attempt}/${TCGCSV_CONFIG.rateLimit.maxRetries}`, { url }, error);
      },
    }
  );
}

/**
 * Fetch all groups for a category
 */
async function fetchGroups(categoryId: number): Promise<TCGGroup[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/groups`;
  logger.info(`Fetching groups for category ${categoryId}`, { url });

  const groups = await fetchWithRetry<TCGGroup[]>(url);
  logger.info(`Found ${groups.length} groups`, { categoryId });

  return groups;
}

/**
 * Fetch products for a specific group
 */
async function fetchProducts(categoryId: number, groupId: number): Promise<TCGProduct[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/products`;

  const products = await fetchWithRetry<TCGProduct[]>(url);
  return products;
}

/**
 * Fetch prices for a specific group
 */
async function fetchPrices(categoryId: number, groupId: number): Promise<TCGPrice[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/prices`;

  const prices = await fetchWithRetry<TCGPrice[]>(url);
  return prices;
}

/**
 * Fetch and merge products + prices for a group
 */
async function fetchGroupData(
  category: TCGCategory,
  group: TCGGroup
): Promise<TCGCard[]> {
  setCurrentOperation(`Fetching ${category.name} - ${group.name}`);

  // Check for shutdown
  if (isShuttingDown()) {
    logger.info('Shutdown requested, skipping group', {
      category: category.name,
      group: group.name,
    });
    return [];
  }

  logger.info(`Processing group: ${group.name}`, {
    categoryId: category.categoryId,
    groupId: group.groupId,
  });

  // Fetch products and prices in parallel
  const [products, prices] = await Promise.all([
    fetchProducts(category.categoryId, group.groupId),
    fetchPrices(category.categoryId, group.groupId),
  ]);

  logger.info(`Fetched ${products.length} products, ${prices.length} price entries`, {
    category: category.name,
    group: group.name,
  });

  // Create price lookup map
  const priceMap = new Map<number, TCGPrice[]>();
  for (const price of prices) {
    if (!priceMap.has(price.productId)) {
      priceMap.set(price.productId, []);
    }
    priceMap.get(price.productId)!.push(price);
  }

  // Filter out sealed products and merge with prices
  const cards: TCGCard[] = products
    .filter(product => !isSealedProduct(product))
    .map(product => {
      const productPrices = priceMap.get(product.productId) || [];
      const card = mergeProductAndPrices(product, productPrices);

      // Add category and group names
      card.categoryName = category.name;
      card.groupName = group.name;

      return card;
    });

  logger.info(`Filtered to ${cards.length} cards (removed ${products.length - cards.length} sealed products)`, {
    category: category.name,
    group: group.name,
  });

  // Save raw data
  const rawDir = path.join(RAW_DIR, category.name.toLowerCase().replace(/\s+/g, '-'));
  fs.mkdirSync(rawDir, { recursive: true });

  fs.writeFileSync(
    path.join(rawDir, `${group.groupId}_${group.name.replace(/[^a-z0-9]/gi, '_')}.json`),
    JSON.stringify({ products, prices, merged: cards }, null, 2)
  );

  // Delay between groups to be polite
  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenGroups);

  return cards;
}

/**
 * Scrape all data for a category
 */
async function scrapeCategory(category: TCGCategory): Promise<TCGCard[]> {
  setCurrentOperation(`Scraping ${category.name}`);

  logger.info(`Starting scrape for ${category.name}`, {
    categoryId: category.categoryId,
  });

  // Fetch all groups
  const groups = await fetchGroups(category.categoryId);

  if (groups.length === 0) {
    logger.warn(`No groups found for ${category.name}`);
    return [];
  }

  // Fetch all group data with rate limiting
  const allCards: TCGCard[] = [];
  const tasks = groups.map((group) =>
    limit(async () => {
      const cards = await fetchGroupData(category, group);
      allCards.push(...cards);
      return cards.length;
    })
  );

  await Promise.all(tasks);

  logger.info(`Scraped ${allCards.length} cards for ${category.name}`, {
    categoryId: category.categoryId,
    groupCount: groups.length,
  });

  // Save curated data (JSONL format)
  const curatedPath = path.join(
    CURATED_DIR,
    `${category.name.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );
  const jsonlData = allCards.map(card => JSON.stringify(card)).join('\n');
  fs.writeFileSync(curatedPath, jsonlData);

  logger.info(`Saved curated data`, { file: curatedPath, size: formatBytes(jsonlData.length) });

  // Delay between categories
  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenCategories);

  return allCards;
}

/**
 * Load scrape state
 */
function loadState(): ScrapeState | null {
  const statePath = path.join(STATE_DIR, 'tcgplayer-scrape.state.json');

  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
  } catch (error) {
    logger.warn('Failed to load scrape state', {}, error as Error);
    return null;
  }
}

/**
 * Save scrape state
 */
function saveState(state: ScrapeState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, 'tcgplayer-scrape.state.json');
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Main scraper
 */
async function main() {
  const pipelineLogger = createPipelineLogger('tcgplayer-scraper');

  // Ensure directories
  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(CURATED_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  // Register shutdown handler
  onShutdown({
    name: 'Save scraper state',
    handler: () => {
      logger.info('State saved during processing');
    },
    timeout: 3000,
  });

  const enabledCategories = getEnabledCategories();
  pipelineLogger.info(`Starting TCGplayer scraper`, {
    categories: enabledCategories.map(c => c.name),
  });

  const startTime = Date.now();
  const state: ScrapeState = {
    lastSync: new Date().toISOString(),
    categories: [],
  };

  for (const category of enabledCategories) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping scraper');
      break;
    }

    try {
      const cards = await scrapeCategory(category);

      state.categories.push({
        categoryId: category.categoryId,
        lastModified: new Date().toISOString(),
        groupCount: 0, // Will be updated
        productCount: cards.length,
      });

      saveState(state);
    } catch (error) {
      logger.error(`Failed to scrape ${category.name}`, { categoryId: category.categoryId }, error as Error);
      throw error;
    }
  }

  setCurrentOperation(null);

  const duration = Math.round((Date.now() - startTime) / 1000);
  const totalCards = state.categories.reduce((sum, c) => sum + c.productCount, 0);

  pipelineLogger.info('TCGplayer scrape complete', {
    duration: `${duration}s`,
    totalCards,
    categories: state.categories.length,
  });

  console.log('\n' + '='.repeat(60));
  console.log('TCGPLAYER SCRAPE COMPLETE');
  console.log('='.repeat(60));
  console.log(`Total cards: ${totalCards.toLocaleString()}`);
  console.log(`Categories: ${state.categories.length}`);
  console.log(`Duration: ${duration}s`);
}

main().catch(error => {
  logger.error('Scraper failed', {}, error);
  process.exit(1);
});
