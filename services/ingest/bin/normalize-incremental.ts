#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import axios from 'axios';
import { getAllGames, GameConfig } from '@cardflux/config';
import { onShutdown, setCurrentOperation, isShuttingDown } from '@cardflux/shared';

const RAW_DIR = path.resolve(__dirname, '../../../data/raw');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');

interface Card {
  id: string;
  game: string;
  name: string;
  set?: string;
  rarity?: string;
  type?: string;
  imageUrl?: string;
  rawData: any;
}

interface SyncState {
  game: string;
  lastSync: string;
  lastETag?: string;
  totalCards: number;
  checksum: string;
}

/**
 * Load previous sync state for a game
 */
function loadSyncState(gameSlug: string): SyncState | null {
  const statePath = path.join(STATE_DIR, `${gameSlug}.state.json`);

  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
  } catch (error) {
    console.warn(`Failed to load sync state for ${gameSlug}:`, error);
    return null;
  }
}

/**
 * Save sync state for a game
 */
function saveSyncState(state: SyncState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, `${state.game}.state.json`);
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Calculate checksum of API response to detect changes
 */
function calculateChecksum(data: any): string {
  const hash = crypto.createHash('sha256');
  hash.update(JSON.stringify(data));
  return hash.digest('hex');
}

/**
 * Fetch game data with conditional requests (ETags)
 */
async function fetchGameDataIncremental(
  config: GameConfig,
  previousState: SyncState | null
): Promise<{ data: any[]; changed: boolean; etag?: string }> {
  console.log(`Fetching data for ${config.name}...`);

  const headers: any = {};

  // Use ETag for conditional requests (if API supports it)
  if (previousState?.lastETag) {
    headers['If-None-Match'] = previousState.lastETag;
  }

  try {
    if (config.source.type === 'bulk') {
      const response = await axios.get(config.source.url, { headers });

      // 304 Not Modified - no changes
      if (response.status === 304) {
        console.log(`No changes detected for ${config.name} (ETag match)`);
        return { data: [], changed: false };
      }

      const bulkData = response.data;
      const downloadUrl = bulkData.download_uri;
      const cardsResponse = await axios.get(downloadUrl);

      return {
        data: cardsResponse.data,
        changed: true,
        etag: response.headers['etag'],
      };
    } else {
      const response = await axios.get(config.source.url, { headers });

      if (response.status === 304) {
        console.log(`No changes detected for ${config.name} (ETag match)`);
        return { data: [], changed: false };
      }

      const data = response.data.data || response.data;

      return {
        data,
        changed: true,
        etag: response.headers['etag'],
      };
    }
  } catch (error: any) {
    if (error.response?.status === 304) {
      console.log(`No changes detected for ${config.name} (304 Not Modified)`);
      return { data: [], changed: false };
    }
    throw error;
  }
}

/**
 * Load existing curated data
 */
function loadExistingCards(gameSlug: string): Map<string, Card> {
  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);
  const existingCards = new Map<string, Card>();

  if (!fs.existsSync(curatedPath)) {
    return existingCards;
  }

  const lines = fs.readFileSync(curatedPath, 'utf-8').split('\n').filter(Boolean);

  for (const line of lines) {
    try {
      const card: Card = JSON.parse(line);
      existingCards.set(card.id, card);
    } catch (error) {
      console.warn(`Failed to parse card:`, error);
    }
  }

  return existingCards;
}

function normalizeCard(rawCard: any, config: GameConfig): Card {
  const getValue = (obj: any, path: string): any => {
    return path.split('.').reduce((acc, part) => {
      if (part.includes('[')) {
        const [field, index] = part.split(/[\[\]]/).filter(Boolean);
        return acc?.[field]?.[parseInt(index)];
      }
      return acc?.[part];
    }, obj);
  };

  return {
    id: getValue(rawCard, config.schema.id),
    game: config.slug,
    name: getValue(rawCard, config.schema.name),
    set: config.schema.set ? getValue(rawCard, config.schema.set) : undefined,
    rarity: config.schema.rarity ? getValue(rawCard, config.schema.rarity) : undefined,
    type: config.schema.type ? getValue(rawCard, config.schema.type) : undefined,
    imageUrl: config.schema.image ? getValue(rawCard, config.schema.image) : undefined,
    rawData: rawCard,
  };
}

/**
 * Detect changes between old and new card data
 */
function detectChanges(
  oldCard: Card | undefined,
  newCard: Card
): { type: 'new' | 'updated' | 'unchanged'; changes?: string[] } {
  if (!oldCard) {
    return { type: 'new' };
  }

  const changes: string[] = [];

  // Check for meaningful changes
  if (oldCard.name !== newCard.name) changes.push('name');
  if (oldCard.set !== newCard.set) changes.push('set');
  if (oldCard.rarity !== newCard.rarity) changes.push('rarity');
  if (oldCard.imageUrl !== newCard.imageUrl) changes.push('imageUrl');

  if (changes.length === 0) {
    return { type: 'unchanged' };
  }

  return { type: 'updated', changes };
}

async function processGameIncremental(config: GameConfig) {
  setCurrentOperation(`Processing ${config.name}`);

  try {
    const previousState = loadSyncState(config.slug);

    // Check for shutdown signal
    if (isShuttingDown()) {
      console.log(`\n⚠️  Shutdown requested, stopping ${config.slug} processing...`);
      return { new: 0, updated: 0, unchanged: previousState?.totalCards || 0 };
    }

    const { data: rawData, changed, etag } = await fetchGameDataIncremental(config, previousState);

    // If no changes detected via ETag, we're done!
    if (!changed) {
      console.log(`✓ ${config.name}: Up to date (skipped ${previousState?.totalCards || 0} cards)`);
      return { new: 0, updated: 0, unchanged: previousState?.totalCards || 0 };
    }

    // Calculate checksum to detect actual content changes
    const checksum = calculateChecksum(rawData);

    if (previousState && previousState.checksum === checksum) {
      console.log(`✓ ${config.name}: Content unchanged (checksum match)`);
      return { new: 0, updated: 0, unchanged: previousState.totalCards };
    }

    console.log(`Processing ${rawData.length} cards from API...`);

    // Save raw data
    const rawPath = path.join(RAW_DIR, `${config.slug}.json`);
    fs.writeFileSync(rawPath, JSON.stringify(rawData, null, 2));

    // Load existing cards
    const existingCards = loadExistingCards(config.slug);
    console.log(`Found ${existingCards.size} existing cards`);

    // Normalize new data and detect changes
    const normalizedCards: Card[] = [];
    const stats = { new: 0, updated: 0, unchanged: 0 };

    for (const rawCard of rawData) {
      // Check for shutdown every 1000 cards
      if (stats.new + stats.updated + stats.unchanged % 1000 === 0 && isShuttingDown()) {
        console.log(`\n⚠️  Shutdown requested during processing, saving partial state...`);

        // Save what we have so far
        const curatedPath = path.join(CURATED_DIR, `${config.slug}.jsonl`);
        const jsonlData = normalizedCards.map((card: Card) => JSON.stringify(card)).join('\n');
        fs.writeFileSync(curatedPath, jsonlData);

        saveSyncState({
          game: config.slug,
          lastSync: new Date().toISOString(),
          lastETag: etag,
          totalCards: normalizedCards.length,
          checksum: calculateChecksum(normalizedCards),
        });

        console.log(`✓ Saved ${normalizedCards.length} cards before shutdown`);
        return stats;
      }

      const normalized = normalizeCard(rawCard, config);
      const existing = existingCards.get(normalized.id);

      const changeDetection = detectChanges(existing, normalized);

      switch (changeDetection.type) {
        case 'new':
          stats.new++;
          console.log(`  + New card: ${normalized.name}`);
          break;
        case 'updated':
          stats.updated++;
          console.log(`  ↻ Updated card: ${normalized.name} (${changeDetection.changes?.join(', ')})`);
          break;
        case 'unchanged':
          stats.unchanged++;
          break;
      }

      normalizedCards.push(normalized);
    }

    // Save curated data
    const curatedPath = path.join(CURATED_DIR, `${config.slug}.jsonl`);
    const jsonlData = normalizedCards.map((card: Card) => JSON.stringify(card)).join('\n');
    fs.writeFileSync(curatedPath, jsonlData);

    console.log(`\n✓ ${config.name}:`);
    console.log(`  Total: ${normalizedCards.length} cards`);
    console.log(`  New: ${stats.new}`);
    console.log(`  Updated: ${stats.updated}`);
    console.log(`  Unchanged: ${stats.unchanged}`);

    // Save sync state
    saveSyncState({
      game: config.slug,
      lastSync: new Date().toISOString(),
      lastETag: etag,
      totalCards: normalizedCards.length,
      checksum,
    });

    return stats;
  } catch (error) {
    console.error(`Error processing ${config.name}:`, error);
    throw error;
  }
}

async function main() {
  // Ensure directories exist
  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(CURATED_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  // Register shutdown handler
  onShutdown({
    name: 'Save normalization state',
    handler: () => {
      console.log('State already saved during processing');
    },
    timeout: 3000,
  });

  const games = getAllGames();
  const totalStats = { new: 0, updated: 0, unchanged: 0 };

  for (const game of games) {
    if (isShuttingDown()) {
      console.log('\n⚠️  Shutdown requested, stopping pipeline...');
      break;
    }

    const stats = await processGameIncremental(game);
    totalStats.new += stats.new;
    totalStats.updated += stats.updated;
    totalStats.unchanged += stats.unchanged;
  }

  setCurrentOperation(null);

  console.log('\n' + '='.repeat(60));
  console.log('INCREMENTAL SYNC COMPLETE');
  console.log('='.repeat(60));
  console.log(`Total cards: ${totalStats.new + totalStats.updated + totalStats.unchanged}`);
  console.log(`New: ${totalStats.new}`);
  console.log(`Updated: ${totalStats.updated}`);
  console.log(`Unchanged: ${totalStats.unchanged}`);
  console.log(`\nTime saved: ~${Math.round(totalStats.unchanged / 25000 * 100)}% of full rebuild`);
}

main().catch(console.error);
