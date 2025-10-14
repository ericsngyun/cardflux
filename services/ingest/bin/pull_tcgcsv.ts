#!/usr/bin/env node
/**
 * TCGPlayer data fetcher with ETag-based incremental updates
 *
 * Fetches card data from tcgcsv.com API with:
 * - ETag conditional requests (HTTP 304 Not Modified)
 * - SHA256 checksum verification
 * - Per-group incremental state tracking
 * - Rate limiting and retry logic
 * - Graceful shutdown handling
 *
 * Output: data/raw/tcgplayer/{category}/{group}.json
 * State: data/state/pull_tcgcsv.state.json
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import axios, { AxiosError } from 'axios';
import pLimit from 'p-limit';
import {
  TCGCSV_CONFIG,
  getEnabledCategories,
  type TCGCategory,
  type TCGGroup,
  type TCGProduct,
  type TCGPrice,
} from '@cardflux/config/tcgplayer-config';
import {
  sleep,
  retry,
  logger,
  createPipelineLogger,
  onShutdown,
  setCurrentOperation,
  isShuttingDown,
} from '@cardflux/shared';

// ============================================================================
// Paths
// ============================================================================

const RAW_DIR = path.resolve(__dirname, '../../../data/raw/tcgplayer');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');
const STATE_FILE = path.join(STATE_DIR, 'pull_tcgcsv.state.json');

// ============================================================================
// Types
// ============================================================================

interface GroupState {
  categoryId: number;
  categoryName: string;
  groupId: number;
  groupName: string;
  lastModified?: string; // From API group.modifiedOn
  lastSync: string; // ISO8601 timestamp
  etag?: string; // HTTP ETag header
  productsChecksum: string; // SHA256 of products array
  pricesChecksum: string; // SHA256 of prices array
  productCount: number;
}

interface PullState {
  version: string; // State schema version
  lastSync: string; // Last successful run
  groups: GroupState[];
}

interface FetchResult {
  products: TCGProduct[];
  prices: TCGPrice[];
  productsEtag?: string;
  pricesEtag?: string;
  changed: boolean;
}

// ============================================================================
// State Management
// ============================================================================

function loadState(): PullState | null {
  if (!fs.existsSync(STATE_FILE)) {
    return null;
  }

  try {
    const state: PullState = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    return state;
  } catch (error) {
    logger.warn('Failed to load pull state, starting fresh', {}, error as Error);
    return null;
  }
}

function saveState(state: PullState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  logger.debug('State saved', { groups: state.groups.length });
}

function getGroupState(state: PullState | null, categoryId: number, groupId: number): GroupState | undefined {
  if (!state) return undefined;
  return state.groups.find(g => g.categoryId === categoryId && g.groupId === groupId);
}

function calculateChecksum(data: any): string {
  const hash = crypto.createHash('sha256');
  hash.update(JSON.stringify(data));
  return hash.digest('hex');
}

// ============================================================================
// HTTP Fetching with ETag Support
// ============================================================================

const rateLimiter = pLimit(TCGCSV_CONFIG.rateLimit.requestsPerSecond);

/**
 * Fetch with ETag conditional request support
 */
async function fetchWithETag<T>(
  url: string,
  etag?: string
): Promise<{ data: T | null; etag?: string; changed: boolean }> {
  await sleep(200); // Rate limiting

  return await retry(
    async () => {
      const headers: Record<string, string> = {
        ...TCGCSV_CONFIG.request.headers,
        'User-Agent': TCGCSV_CONFIG.request.userAgent,
      };

      // Add ETag for conditional request
      if (etag) {
        headers['If-None-Match'] = etag;
      }

      try {
        const response = await axios.get(url, {
          timeout: TCGCSV_CONFIG.request.timeout,
          headers,
          validateStatus: (status) => status === 200 || status === 304,
        });

        // 304 Not Modified - data unchanged
        if (response.status === 304) {
          logger.debug('Data unchanged (304 Not Modified)', { url });
          return { data: null, etag, changed: false };
        }

        // Validate API response structure
        if (!response.data.success) {
          throw new Error(`API error: ${JSON.stringify(response.data.errors || response.data)}`);
        }

        return {
          data: response.data.results as T,
          etag: response.headers['etag'],
          changed: true,
        };
      } catch (error) {
        if ((error as AxiosError).response?.status === 304) {
          return { data: null, etag, changed: false };
        }
        throw error;
      }
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

// ============================================================================
// TCGPlayer API
// ============================================================================

async function fetchGroups(categoryId: number): Promise<TCGGroup[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/groups`;
  const { data } = await fetchWithETag<TCGGroup[]>(url);

  if (!data) {
    throw new Error('Failed to fetch groups - got 304 but expected data');
  }

  return data;
}

async function fetchGroupData(
  category: TCGCategory,
  group: TCGGroup,
  previousState?: GroupState
): Promise<FetchResult> {
  setCurrentOperation(`Fetching ${category.name} - ${group.name}`);

  if (isShuttingDown()) {
    return { products: [], prices: [], changed: false };
  }

  // Check if modifiedOn indicates no changes
  if (previousState?.lastModified && group.modifiedOn) {
    const prevDate = new Date(previousState.lastModified).getTime();
    const currDate = new Date(group.modifiedOn).getTime();

    if (currDate <= prevDate) {
      logger.debug(`Group unchanged (modifiedOn: ${group.modifiedOn})`, {
        category: category.name,
        group: group.name,
      });
      // Still return empty to skip, we'll use previous data
      return { products: [], prices: [], changed: false };
    }
  }

  // Fetch products and prices in parallel
  const productsUrl = `${TCGCSV_CONFIG.baseUrl}/${category.categoryId}/${group.groupId}/products`;
  const pricesUrl = `${TCGCSV_CONFIG.baseUrl}/${category.categoryId}/${group.groupId}/prices`;

  const [productsResult, pricesResult] = await Promise.all([
    fetchWithETag<TCGProduct[]>(productsUrl, previousState?.etag),
    fetchWithETag<TCGPrice[]>(pricesUrl, previousState?.etag),
  ]);

  // Check if either changed
  if (!productsResult.changed && !pricesResult.changed) {
    logger.debug('Group data unchanged (ETags match)', {
      category: category.name,
      group: group.name,
    });
    return { products: [], prices: [], changed: false };
  }

  // If changed, verify checksums
  const products = productsResult.data || [];
  const prices = pricesResult.data || [];

  const productsChecksum = calculateChecksum(products);
  const pricesChecksum = calculateChecksum(prices);

  // Compare checksums with previous state
  if (
    previousState &&
    productsChecksum === previousState.productsChecksum &&
    pricesChecksum === previousState.pricesChecksum
  ) {
    logger.debug('Group data unchanged (checksums match)', {
      category: category.name,
      group: group.name,
    });
    return { products: [], prices: [], changed: false };
  }

  logger.info(`Fetched group data`, {
    category: category.name,
    group: group.name,
    products: products.length,
    prices: prices.length,
  });

  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenGroups);

  return {
    products,
    prices,
    productsEtag: productsResult.etag,
    pricesEtag: pricesResult.etag,
    changed: true,
  };
}

// ============================================================================
// File Output
// ============================================================================

function saveGroupData(
  category: TCGCategory,
  group: TCGGroup,
  products: TCGProduct[],
  prices: TCGPrice[]
): void {
  const categoryDir = path.join(RAW_DIR, category.name.toLowerCase().replace(/\s+/g, '-'));
  fs.mkdirSync(categoryDir, { recursive: true });

  const filename = `${group.groupId}_${group.name.replace(/[^a-z0-9]/gi, '_')}.json`;
  const filepath = path.join(categoryDir, filename);

  fs.writeFileSync(
    filepath,
    JSON.stringify(
      {
        categoryId: category.categoryId,
        categoryName: category.name,
        groupId: group.groupId,
        groupName: group.name,
        modifiedOn: group.modifiedOn,
        fetchedAt: new Date().toISOString(),
        products,
        prices,
      },
      null,
      2
    )
  );

  logger.debug('Saved group data', { filepath });
}

// ============================================================================
// Category Processing
// ============================================================================

async function processCategory(
  category: TCGCategory,
  previousState: PullState | null
): Promise<GroupState[]> {
  setCurrentOperation(`Processing category: ${category.name}`);
  logger.info(`Fetching groups for ${category.name}...`);

  const groups = await fetchGroups(category.categoryId);
  logger.info(`Found ${groups.length} groups for ${category.name}`);

  const newGroupStates: GroupState[] = [];
  let updatedCount = 0;
  let unchangedCount = 0;

  // Process groups with rate limiting
  const tasks = groups.map(group =>
    rateLimiter(async () => {
      if (isShuttingDown()) {
        return;
      }

      const prevState = getGroupState(previousState, category.categoryId, group.groupId);
      const result = await fetchGroupData(category, group, prevState);

      if (!result.changed) {
        // Keep previous state
        if (prevState) {
          newGroupStates.push(prevState);
          unchangedCount++;
        }
        return;
      }

      // Save new data
      saveGroupData(category, group, result.products, result.prices);
      updatedCount++;

      // Create new state
      newGroupStates.push({
        categoryId: category.categoryId,
        categoryName: category.name,
        groupId: group.groupId,
        groupName: group.name,
        lastModified: group.modifiedOn,
        lastSync: new Date().toISOString(),
        etag: result.productsEtag,
        productsChecksum: calculateChecksum(result.products),
        pricesChecksum: calculateChecksum(result.prices),
        productCount: result.products.length,
      });
    })
  );

  await Promise.all(tasks);

  if (updatedCount > 0) {
    logger.info(`✓ ${category.name}: ${updatedCount} updated, ${unchangedCount} unchanged`);
  } else {
    logger.info(`✓ ${category.name}: All ${unchangedCount} groups up to date`);
  }

  await sleep(TCGCSV_CONFIG.rateLimit.delayBetweenCategories);

  return newGroupStates;
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('pull_tcgcsv');

  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  onShutdown({
    name: 'Save pull state',
    handler: () => {
      logger.info('Pull state saved during shutdown');
    },
    timeout: 3000,
  });

  const previousState = loadState();
  const enabledCategories = getEnabledCategories();

  if (enabledCategories.length === 0) {
    logger.warn('No enabled categories in tcgplayer-config.ts');
    console.log('\n⚠️  No categories enabled. Check packages/config/src/tcgplayer-config.ts');
    return;
  }

  if (previousState) {
    pipelineLogger.info('Resuming from previous state', {
      lastSync: previousState.lastSync,
      groups: previousState.groups.length,
    });
  } else {
    pipelineLogger.info('Starting fresh pull (no previous state)');
  }

  const startTime = Date.now();
  const newState: PullState = {
    version: '1.0.0',
    lastSync: new Date().toISOString(),
    groups: [],
  };

  let totalUpdated = 0;
  let totalUnchanged = 0;

  for (const category of enabledCategories) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping...');
      break;
    }

    try {
      const groupStates = await processCategory(category, previousState);

      const updatedGroups = groupStates.filter(g => {
        const prev = getGroupState(previousState, g.categoryId, g.groupId);
        return !prev || g.lastSync !== prev.lastSync;
      });

      totalUpdated += updatedGroups.length;
      totalUnchanged += groupStates.length - updatedGroups.length;

      newState.groups.push(...groupStates);
      saveState(newState);
    } catch (error) {
      logger.error(`Failed to process ${category.name}`, {}, error as Error);
      throw error;
    }
  }

  setCurrentOperation(null);

  const duration = Math.round((Date.now() - startTime) / 1000);

  console.log('\n' + '='.repeat(70));
  console.log('TCGCSV PULL COMPLETE');
  console.log('='.repeat(70));
  console.log(`Categories: ${enabledCategories.map(c => c.name).join(', ')}`);
  console.log(`Groups updated: ${totalUpdated}`);
  console.log(`Groups unchanged: ${totalUnchanged} (skipped via ETag/checksum)`);
  console.log(`Total groups: ${newState.groups.length}`);
  console.log(`Duration: ${duration}s`);

  if (totalUnchanged > 0) {
    const savedPercent = Math.round((totalUnchanged / (totalUpdated + totalUnchanged)) * 100);
    console.log(`\n⚡ Time saved: ~${savedPercent}% (incremental update)`);
  }

  console.log(`\n📁 Raw data: ${RAW_DIR}`);
  console.log(`📊 State file: ${STATE_FILE}`);
}

main().catch(error => {
  logger.error('Pull failed', {}, error);
  process.exit(1);
});
