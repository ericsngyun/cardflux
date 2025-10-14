#!/usr/bin/env node
/**
 * Normalize TCGPlayer data to unified CardCore schema
 *
 * Transforms raw TCGPlayer data to CardCore with:
 * - Deterministic SHA1 card_id: SHA1(game_id|set_code|collector_number|language|artwork_hash?)
 * - Sealed product filtering (booster boxes, etc.)
 * - Language defaulting (en)
 * - Incremental processing with state tracking
 *
 * Input: data/raw/tcgplayer/{category}/*.json
 * Output: data/normalized/{game_id}.jsonl
 * State: data/state/normalize.state.json
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import {
  TCGCSV_CONFIG,
  getEnabledCategories,
  isSealedProduct,
  type TCGCategory,
  type TCGCard,
  type TCGProduct,
} from '@cardflux/config/tcgplayer-config';
import { CardCore, GameId } from '@cardflux/shared/types';
import {
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
const NORMALIZED_DIR = path.resolve(__dirname, '../../../data/normalized');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');
const STATE_FILE = path.join(STATE_DIR, 'normalize.state.json');

// ============================================================================
// Types
// ============================================================================

interface GroupFileData {
  categoryId: number;
  categoryName: string;
  groupId: number;
  groupName: string;
  modifiedOn?: string;
  fetchedAt: string;
  products: TCGProduct[];
  prices: any[];
}

interface NormalizeState {
  version: string;
  lastSync: string;
  processedFiles: {
    path: string;
    checksum: string;
    cardCount: number;
  }[];
}

// ============================================================================
// Game ID Mapping
// ============================================================================

const CATEGORY_TO_GAME_ID: Record<number, GameId> = {
  1: 'mtg', // Magic
  2: 'yugioh', // Yu-Gi-Oh!
  3: 'pokemon', // Pokemon
  17: 'cardfight-vanguard', // Cardfight!! Vanguard
  19: 'final-fantasy', // Final Fantasy
  24: 'final-fantasy', // Final Fantasy (duplicate?)
  26: 'digimon', // Digimon
  28: 'dragon-ball-super', // Dragon Ball Super
  58: 'flesh-and-blood', // Flesh and Blood
  68: 'onepiece', // One Piece Card Game
  80: 'lorcana', // Lorcana
};

// ============================================================================
// State Management
// ============================================================================

function loadState(): NormalizeState | null {
  if (!fs.existsSync(STATE_FILE)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  } catch (error) {
    logger.warn('Failed to load normalize state, starting fresh', {}, error as Error);
    return null;
  }
}

function saveState(state: NormalizeState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function calculateFileChecksum(filepath: string): string {
  const content = fs.readFileSync(filepath, 'utf-8');
  return crypto.createHash('sha256').update(content).digest('hex');
}

// ============================================================================
// Card ID Generation
// ============================================================================

/**
 * Generate deterministic SHA1 card_id
 * Format: SHA1(game_id|set_code|collector_number|language|artwork_hash?)
 */
function generateCardId(
  gameId: GameId,
  setCode: string,
  collectorNumber: string,
  language: string = 'en',
  artworkHash?: string
): string {
  const parts = [gameId, setCode, collectorNumber, language];

  if (artworkHash) {
    parts.push(artworkHash);
  }

  const data = parts.join('|');
  return crypto.createHash('sha1').update(data).digest('hex');
}

// ============================================================================
// TCGPlayer to CardCore Transformation
// ============================================================================

/**
 * Extract set code from group name or product data
 * Different games have different patterns
 */
function extractSetCode(groupName: string, product: TCGProduct, gameId: GameId): string {
  // One Piece: Group name is the set (e.g., "Starter Deck - Straw Hat Crew [ST-01]")
  // Extract code from brackets if present
  const bracketMatch = groupName.match(/\[([A-Z0-9-]+)\]/);
  if (bracketMatch) {
    return bracketMatch[1];
  }

  // Fallback: use groupId as set code
  return `SET-${product.groupId}`;
}

/**
 * Extract collector number from product
 */
function extractCollectorNumber(product: TCGProduct): string | null {
  // Check extended data for Number field
  if (product.extendedData) {
    const numberField = product.extendedData.find(item => item.name === 'Number');
    if (numberField?.value) {
      return numberField.value;
    }
  }

  // Sealed products don't have collector numbers
  return null;
}

/**
 * Transform TCGProduct to CardCore
 */
function transformToCardCore(
  product: TCGProduct,
  groupName: string,
  categoryId: number
): CardCore | null {
  const gameId = CATEGORY_TO_GAME_ID[categoryId];

  if (!gameId) {
    logger.warn('Unknown category ID', { categoryId, productId: product.productId });
    return null;
  }

  // Filter sealed products
  if (isSealedProduct(product)) {
    logger.debug('Skipping sealed product', { name: product.name });
    return null;
  }

  // Extract collector number
  const collectorNumber = extractCollectorNumber(product);

  if (!collectorNumber) {
    logger.debug('Skipping product without collector number', {
      name: product.name,
      productId: product.productId,
    });
    return null;
  }

  // Extract set code
  const setCode = extractSetCode(groupName, product, gameId);

  // Default language to English
  const language = 'en';

  // Generate deterministic card_id
  const cardId = generateCardId(gameId, setCode, collectorNumber, language);

  // Build CardCore
  const cardCore: CardCore = {
    card_id: cardId,
    game_id: gameId,
    set_code: setCode,
    set_name: groupName,
    collector_number: collectorNumber,
    name: product.name,
    language,
    printing_id: `tcgplayer_${product.productId}`,
    image_url: product.imageUrl,
    tcgplayer_id: product.productId,
  };

  return cardCore;
}

// ============================================================================
// File Processing
// ============================================================================

function findRawFiles(): string[] {
  const files: string[] = [];

  if (!fs.existsSync(RAW_DIR)) {
    return files;
  }

  // Find all category directories
  const categories = fs.readdirSync(RAW_DIR, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

  for (const category of categories) {
    const categoryDir = path.join(RAW_DIR, category);
    const groupFiles = fs.readdirSync(categoryDir)
      .filter(file => file.endsWith('.json'))
      .map(file => path.join(categoryDir, file));

    files.push(...groupFiles);
  }

  return files;
}

function processFile(filepath: string, previousState: NormalizeState | null): CardCore[] {
  const checksum = calculateFileChecksum(filepath);

  // Check if already processed
  if (previousState) {
    const prevFile = previousState.processedFiles.find(f => f.path === filepath);
    if (prevFile && prevFile.checksum === checksum) {
      logger.debug('File unchanged, skipping', { filepath });
      return [];
    }
  }

  const data: GroupFileData = JSON.parse(fs.readFileSync(filepath, 'utf-8'));

  const cards: CardCore[] = [];

  for (const product of data.products) {
    if (isShuttingDown()) {
      break;
    }

    const cardCore = transformToCardCore(product, data.groupName, data.categoryId);

    if (cardCore) {
      cards.push(cardCore);
    }
  }

  logger.info(`Processed file`, {
    filepath: path.basename(filepath),
    products: data.products.length,
    cards: cards.length,
    filtered: data.products.length - cards.length,
  });

  return cards;
}

// ============================================================================
// Output
// ============================================================================

function saveNormalizedCards(cards: Map<GameId, CardCore[]>): void {
  fs.mkdirSync(NORMALIZED_DIR, { recursive: true });

  for (const [gameId, gameCards] of cards.entries()) {
    const outputPath = path.join(NORMALIZED_DIR, `${gameId}.jsonl`);

    // Sort by card_id for deterministic output
    const sortedCards = gameCards.sort((a, b) => a.card_id.localeCompare(b.card_id));

    const jsonl = sortedCards.map(card => JSON.stringify(card)).join('\n');
    fs.writeFileSync(outputPath, jsonl);

    logger.info(`Saved normalized cards`, {
      gameId,
      count: gameCards.length,
      path: outputPath,
    });
  }
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('normalize');

  fs.mkdirSync(NORMALIZED_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  onShutdown({
    name: 'Save normalize state',
    handler: () => {
      logger.info('Normalize state saved during shutdown');
    },
    timeout: 3000,
  });

  const previousState = loadState();
  const rawFiles = findRawFiles();

  if (rawFiles.length === 0) {
    logger.warn('No raw files found. Run pull-tcgcsv first.');
    console.log('\n⚠️  No raw TCGPlayer data found.');
    console.log('   Run: pnpm --filter ingest pull-tcgcsv');
    return;
  }

  pipelineLogger.info('Starting normalization', {
    files: rawFiles.length,
    previousState: previousState ? 'found' : 'none',
  });

  const startTime = Date.now();

  // Group cards by game_id
  const cardsByGame = new Map<GameId, CardCore[]>();
  const processedFiles: { path: string; checksum: string; cardCount: number }[] = [];

  let totalCards = 0;
  let filesProcessed = 0;
  let filesSkipped = 0;

  for (const filepath of rawFiles) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping...');
      break;
    }

    setCurrentOperation(`Processing ${path.basename(filepath)}`);

    const cards = processFile(filepath, previousState);

    if (cards.length === 0) {
      filesSkipped++;
      // Still track in state
      const checksum = calculateFileChecksum(filepath);
      const prevFile = previousState?.processedFiles.find(f => f.path === filepath);
      processedFiles.push({
        path: filepath,
        checksum,
        cardCount: prevFile?.cardCount || 0,
      });
      continue;
    }

    filesProcessed++;

    // Group by game_id
    for (const card of cards) {
      if (!cardsByGame.has(card.game_id)) {
        cardsByGame.set(card.game_id, []);
      }
      cardsByGame.get(card.game_id)!.push(card);
    }

    totalCards += cards.length;

    processedFiles.push({
      path: filepath,
      checksum: calculateFileChecksum(filepath),
      cardCount: cards.length,
    });
  }

  // Deduplicate cards within each game (by card_id)
  for (const [gameId, cards] of cardsByGame.entries()) {
    const uniqueCards = new Map<string, CardCore>();

    for (const card of cards) {
      // Keep the latest version if duplicate
      uniqueCards.set(card.card_id, card);
    }

    cardsByGame.set(gameId, Array.from(uniqueCards.values()));

    const duplicatesRemoved = cards.length - uniqueCards.size;
    if (duplicatesRemoved > 0) {
      logger.info(`Removed duplicates`, { gameId, duplicates: duplicatesRemoved });
    }
  }

  // Save normalized cards
  saveNormalizedCards(cardsByGame);

  // Save state
  const newState: NormalizeState = {
    version: '1.0.0',
    lastSync: new Date().toISOString(),
    processedFiles,
  };
  saveState(newState);

  setCurrentOperation(null);

  const duration = Math.round((Date.now() - startTime) / 1000);

  console.log('\n' + '='.repeat(70));
  console.log('NORMALIZATION COMPLETE');
  console.log('='.repeat(70));
  console.log(`Files processed: ${filesProcessed}`);
  console.log(`Files skipped: ${filesSkipped} (unchanged)`);
  console.log(`Total cards: ${totalCards}`);

  for (const [gameId, cards] of cardsByGame.entries()) {
    console.log(`  ${gameId}: ${cards.length.toLocaleString()} cards`);
  }

  console.log(`Duration: ${duration}s`);
  console.log(`\n📁 Output: ${NORMALIZED_DIR}`);
  console.log(`📊 State: ${STATE_FILE}`);
}

main().catch(error => {
  logger.error('Normalization failed', {}, error);
  process.exit(1);
});
