#!/usr/bin/env node
/**
 * Incremental TCGplayer scraper with smart update detection
 * Only fetches data that has changed since last run
 */

import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import {
  TCGCSV_CONFIG,
  getEnabledCategories,
  mergeProductAndPrices,
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

const limit = pLimit(TCGCSV_CONFIG.rateLimit.requestsPerSecond);

interface GroupState {
  categoryId: number;
  groupId: number;
  groupName: string;
  lastModified: string;
  productCount: number;
  checksum: string;
}

interface IncrementalState {
  lastSync: string;
  groups: GroupState[];
  stats: {
    totalGroups: number;
    totalProducts: number;
    lastDuration: number;
  };
}

/**
 * Calculate checksum for data
 */
function calculateChecksum(data: any): string {
  const crypto = require('crypto');
  return crypto.createHash('sha256').update(JSON.stringify(data)).digest('hex');
}

/**
 * Fetch with retry and rate limiting
 */
async function fetchWithRetry<T>(url: string): Promise<T> {
  await sleep(200);

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
 * Load incremental state
 */
function loadState(): IncrementalState | null {
  const statePath = path.join(STATE_DIR, 'tcgplayer-incremental.state.json');

  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
  } catch (error) {
    logger.warn('Failed to load incremental state', {}, error as Error);
    return null;
  }
}

/**
 * Save incremental state
 */
function saveState(state: IncrementalState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, 'tcgplayer-incremental.state.json');
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Check if group needs update
 */
function needsUpdate(group: TCGGroup, previousState: GroupState | undefined): boolean {
  if (!previousState) {
    return true; // New group
  }

  // Check if modifiedOn changed
  if (group.modifiedOn && previousState.lastModified) {
    const currentDate = new Date(group.modifiedOn).getTime();
    const previousDate = new Date(previousState.lastModified).getTime();

    if (currentDate > previousDate) {
      logger.info(`Group updated: ${group.name}`, {
        previous: previousState.lastModified,
        current: group.modifiedOn,
      });
      return true;
    }
  }

  return false;
}

/**
 * Fetch groups for category
 */
async function fetchGroups(categoryId: number): Promise<TCGGroup[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/groups`;
  const groups = await fetchWithRetry<TCGGroup[]>(url);
  return groups;
}

/**
 * Fetch products for group
 */
async function fetchProducts(categoryId: number, groupId: number): Promise<TCGProduct[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/products`;
  return await fetchWithRetry<TCGProduct[]>(url);
}

/**
 * Fetch prices for group
 */
async function fetchPrices(categoryId: number, groupId: number): Promise<TCGPrice[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/prices`;
  return await fetchWithRetry<TCGPrice[]>(url);
}

/**
 * Fetch and merge group data
 */
async function fetchGroupData(
  category: TCGCategory,
  group: TCGGroup
): Promise<{ cards: TCGCard[]; checksum: string }> {
  setCurrentOperation(`Fetching ${category.name} - ${group.name}`);

  if (isShuttingDown()) {
    return { cards: [], checksum: '' };
  }

  const [products, prices] = await Promise.all([
    fetchProducts(category.categoryId, group.groupId),
    fetchPrices(category.categoryId, group.groupId),
  ]);

  logger.info(`Fetched ${products.length} products, ${prices.length} price entries`, {
    category: category.name,
    group: group.name,
  });

  // Create price map
  const priceMap = new Map<number, TCGPrice[]>();
  for (const price of prices) {
    if (!priceMap.has(price.productId)) {
      priceMap.set(price.productId, []);
    }
    priceMap.get(price.productId)!.push(price);
  }

  // Merge cards
  const cards: TCGCard[] = products.map(product => {
    const productPrices = priceMap.get(product.productId) || [];
    const card = mergeProductAndPrices(product, productPrices);
    card.categoryName = category.name;
    card.groupName = group.name;
    return card;
  });

  // Calculate checksum
  const checksum = calculateChecksum(cards);

  // Save raw data
  const rawDir = path.join(RAW_DIR, category.name.toLowerCase().replace(/\s+/g, '-'));
  fs.mkdirSync(rawDir, { recursive: true });

  fs.writeFileSync(
    path.join(rawDir, `${group.groupId}_${group.name.replace(/[^a-z0-9]/gi, '_')}.json`),
    JSON.stringify({ products, prices, merged: cards, checksum }, null, 2)
  );

  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenGroups);

  return { cards, checksum };
}

/**
 * Load existing curated data
 */
function loadExistingCards(categoryName: string): Map<number, TCGCard> {
  const curatedPath = path.join(
    CURATED_DIR,
    `${categoryName.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );

  const existingCards = new Map<number, TCGCard>();

  if (!fs.existsSync(curatedPath)) {
    return existingCards;
  }

  const lines = fs.readFileSync(curatedPath, 'utf-8').split('\n').filter(Boolean);

  for (const line of lines) {
    try {
      const card: TCGCard = JSON.parse(line);
      existingCards.set(card.productId, card);
    } catch (error) {
      logger.warn('Failed to parse existing card', {}, error as Error);
    }
  }

  return existingCards;
}

/**
 * Incremental scrape for category
 */
async function scrapeCategoryIncremental(
  category: TCGCategory,
  previousState: IncrementalState | null
): Promise<{ cards: TCGCard[]; updatedGroups: GroupState[] }> {
  setCurrentOperation(`Incremental scrape: ${category.name}`);

  logger.info(`Starting incremental scrape for ${category.name}`);

  // Fetch all groups
  const groups = await fetchGroups(category.categoryId);

  // Load existing cards
  const existingCards = loadExistingCards(category.name);
  logger.info(`Loaded ${existingCards.size} existing cards for ${category.name}`);

  // Find groups that need updates
  const groupsToUpdate: TCGGroup[] = [];
  const previousGroupStates = new Map(
    (previousState?.groups || [])
      .filter(g => g.categoryId === category.categoryId)
      .map(g => [g.groupId, g])
  );

  for (const group of groups) {
    const prevState = previousGroupStates.get(group.groupId);

    if (needsUpdate(group, prevState)) {
      groupsToUpdate.push(group);
    } else {
      logger.debug(`Skipping unchanged group: ${group.name}`);
    }
  }

  if (groupsToUpdate.length === 0) {
    logger.info(`✓ ${category.name}: All groups up to date (${groups.length} groups)`);
    return { cards: Array.from(existingCards.values()), updatedGroups: [] };
  }

  logger.info(`Updating ${groupsToUpdate.length}/${groups.length} groups for ${category.name}`);

  // Fetch updated groups
  const updatedGroupStates: GroupState[] = [];
  const newCardsMap = new Map<number, TCGCard>();

  const tasks = groupsToUpdate.map(group =>
    limit(async () => {
      const { cards, checksum } = await fetchGroupData(category, group);

      // Add to new cards map
      for (const card of cards) {
        newCardsMap.set(card.productId, card);
      }

      // Track state
      updatedGroupStates.push({
        categoryId: category.categoryId,
        groupId: group.groupId,
        groupName: group.name,
        lastModified: group.modifiedOn || new Date().toISOString(),
        productCount: cards.length,
        checksum,
      });
    })
  );

  await Promise.all(tasks);

  // Merge with existing cards
  const finalCards = new Map<number, TCGCard>(existingCards);
  for (const [productId, card] of newCardsMap) {
    finalCards.set(productId, card); // Overwrite existing
  }

  // Save curated data
  const curatedPath = path.join(
    CURATED_DIR,
    `${category.name.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );
  const jsonlData = Array.from(finalCards.values())
    .map(card => JSON.stringify(card))
    .join('\n');
  fs.writeFileSync(curatedPath, jsonlData);

  logger.info(`✓ ${category.name}: Updated ${groupsToUpdate.length} groups, ${newCardsMap.size} new/changed cards`);

  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenCategories);

  return { cards: Array.from(finalCards.values()), updatedGroups: updatedGroupStates };
}

/**
 * Main incremental scraper
 */
async function main() {
  const pipelineLogger = createPipelineLogger('tcgplayer-incremental');

  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(CURATED_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  onShutdown({
    name: 'Save incremental state',
    handler: () => {
      logger.info('State saved during processing');
    },
    timeout: 3000,
  });

  const previousState = loadState();
  const enabledCategories = getEnabledCategories();

  if (previousState) {
    pipelineLogger.info('Resuming from previous state', {
      lastSync: previousState.lastSync,
      groups: previousState.groups.length,
    });
  } else {
    pipelineLogger.info('Starting fresh scrape (no previous state)');
  }

  const startTime = Date.now();
  const newState: IncrementalState = {
    lastSync: new Date().toISOString(),
    groups: [],
    stats: {
      totalGroups: 0,
      totalProducts: 0,
      lastDuration: 0,
    },
  };

  let totalUpdated = 0;
  let totalSkipped = 0;

  for (const category of enabledCategories) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping scraper');
      break;
    }

    try {
      const { cards, updatedGroups } = await scrapeCategoryIncremental(category, previousState);

      // Merge group states (keep unchanged groups from previous state)
      const previousGroupStates = (previousState?.groups || [])
        .filter(g => g.categoryId === category.categoryId);

      const updatedGroupIds = new Set(updatedGroups.map(g => g.groupId));
      const unchangedGroups = previousGroupStates.filter(g => !updatedGroupIds.has(g.groupId));

      newState.groups.push(...updatedGroups, ...unchangedGroups);
      newState.stats.totalProducts += cards.length;

      totalUpdated += updatedGroups.length;
      totalSkipped += unchangedGroups.length;

      saveState(newState);
    } catch (error) {
      logger.error(`Failed to scrape ${category.name}`, {}, error as Error);
      throw error;
    }
  }

  setCurrentOperation(null);

  const duration = Math.round((Date.now() - startTime) / 1000);
  newState.stats.lastDuration = duration;
  newState.stats.totalGroups = newState.groups.length;

  saveState(newState);

  console.log('\n' + '='.repeat(60));
  console.log('INCREMENTAL SCRAPE COMPLETE');
  console.log('='.repeat(60));
  console.log(`Groups updated: ${totalUpdated}`);
  console.log(`Groups skipped: ${totalSkipped} (unchanged)`);
  console.log(`Total products: ${newState.stats.totalProducts.toLocaleString()}`);
  console.log(`Duration: ${duration}s`);
  console.log(`\nTime saved vs full scrape: ~${Math.round((totalSkipped / (totalUpdated + totalSkipped)) * 100)}%`);
}

main().catch(error => {
  logger.error('Incremental scraper failed', {}, error);
  process.exit(1);
});
