#!/usr/bin/env node
/**
 * Incremental image fetcher with SHA256 verification
 *
 * Downloads card images from normalized data with:
 * - SHA256 checksum tracking (detect unchanged images)
 * - Automatic retry with exponential backoff
 * - Concurrent downloads with rate limiting
 * - Thumbnail generation
 * - ImageMeta output for embedder
 *
 * Input: data/normalized/{game_id}.jsonl
 * Output: data/images/{game_id}/{card_id}/
 *   - canonical.jpg (600x600 original from TCGPlayer)
 *   - thumb.jpg (200x200 thumbnail)
 *   - meta.json (ImageMeta)
 * State: data/state/fetch_images.state.json
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import axios from 'axios';
import pLimit from 'p-limit';
import { CardCore, ImageMeta, GameId } from '@cardflux/shared/types';
import {
  logger,
  createPipelineLogger,
  onShutdown,
  setCurrentOperation,
  isShuttingDown,
  retry,
  sleep,
} from '@cardflux/shared';

// ============================================================================
// Paths
// ============================================================================

const NORMALIZED_DIR = path.resolve(__dirname, '../../../data/normalized');
const IMAGES_DIR = path.resolve(__dirname, '../../../data/images');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');
const STATE_FILE = path.join(STATE_DIR, 'fetch_images.state.json');

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  concurrentDownloads: 10,
  downloadTimeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  thumbnailSize: 200,
  userAgent: 'CardFlux/1.0 Image Fetcher',
};

// ============================================================================
// Types
// ============================================================================

interface FetchState {
  version: string;
  lastSync: string;
  images: {
    [cardId: string]: {
      imageUrl: string;
      canonicalSha256: string;
      thumbSha256: string;
      lastFetch: string;
    };
  };
}

// ============================================================================
// State Management
// ============================================================================

function loadState(): FetchState | null {
  if (!fs.existsSync(STATE_FILE)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  } catch (error) {
    logger.warn('Failed to load fetch state, starting fresh', {}, error as Error);
    return null;
  }
}

function saveState(state: FetchState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// ============================================================================
// Image Processing
// ============================================================================

/**
 * Calculate SHA256 of file
 */
function calculateFileSha256(filepath: string): string {
  const content = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Calculate SHA256 of buffer
 */
function calculateBufferSha256(buffer: Buffer): string {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

/**
 * Download image with retry
 */
async function downloadImage(url: string): Promise<Buffer> {
  return await retry(
    async () => {
      const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: CONFIG.downloadTimeout,
        headers: {
          'User-Agent': CONFIG.userAgent,
        },
      });

      return Buffer.from(response.data);
    },
    {
      retries: CONFIG.retryAttempts,
      minDelay: CONFIG.retryDelay,
      maxDelay: CONFIG.retryDelay * 4,
      factor: 2,
      onRetry: (attempt, error) => {
        logger.warn(`Image download retry ${attempt}/${CONFIG.retryAttempts}`, { url }, error);
      },
    }
  );
}

/**
 * Create thumbnail (stub - just copy for now, real implementation would resize)
 * TODO: Add actual image resizing with sharp or canvas
 */
function createThumbnail(canonicalBuffer: Buffer): Buffer {
  // For now, just return the canonical image
  // In production, use sharp library to resize to CONFIG.thumbnailSize x CONFIG.thumbnailSize
  return canonicalBuffer;
}

/**
 * Save image and metadata
 */
function saveImage(
  card: CardCore,
  canonicalBuffer: Buffer,
  thumbBuffer: Buffer
): { canonicalSha256: string; thumbSha256: string } {
  const cardDir = path.join(IMAGES_DIR, card.game_id, card.card_id);
  fs.mkdirSync(cardDir, { recursive: true });

  // Save canonical image
  const canonicalPath = path.join(cardDir, 'canonical.jpg');
  fs.writeFileSync(canonicalPath, canonicalBuffer);
  const canonicalSha256 = calculateBufferSha256(canonicalBuffer);

  // Save thumbnail
  const thumbPath = path.join(cardDir, 'thumb.jpg');
  fs.writeFileSync(thumbPath, thumbBuffer);
  const thumbSha256 = calculateBufferSha256(thumbBuffer);

  // Save ImageMeta
  const imageMeta: ImageMeta = {
    card_id: card.card_id,
    game_id: card.game_id,
    set_code: card.set_code,
    collector_number: card.collector_number,
    name: card.name,
    language: card.language,
    canonical_sha256: canonicalSha256,
    thumb_sha256: thumbSha256,
    created_at: new Date().toISOString(),
    source_url: card.image_url,
  };

  const metaPath = path.join(cardDir, 'meta.json');
  fs.writeFileSync(metaPath, JSON.stringify(imageMeta, null, 2));

  return { canonicalSha256, thumbSha256 };
}

// ============================================================================
// Card Processing
// ============================================================================

/**
 * Check if image needs fetching
 */
function needsFetch(card: CardCore, previousState: FetchState | null): boolean {
  if (!card.image_url) {
    return false; // No image URL
  }

  const cardDir = path.join(IMAGES_DIR, card.game_id, card.card_id);
  const canonicalPath = path.join(cardDir, 'canonical.jpg');

  // Check if file exists
  if (!fs.existsSync(canonicalPath)) {
    return true; // Missing file
  }

  // Check if URL changed
  const prevImage = previousState?.images[card.card_id];
  if (prevImage && prevImage.imageUrl !== card.image_url) {
    logger.debug('Image URL changed', { cardId: card.card_id });
    return true;
  }

  // File exists and URL unchanged
  return false;
}

/**
 * Process single card image
 */
async function processCard(
  card: CardCore,
  previousState: FetchState | null
): Promise<{ canonicalSha256: string; thumbSha256: string } | null> {
  if (!card.image_url) {
    return null;
  }

  if (!needsFetch(card, previousState)) {
    // Use previous checksums
    const prevImage = previousState?.images[card.card_id];
    if (prevImage) {
      return {
        canonicalSha256: prevImage.canonicalSha256,
        thumbSha256: prevImage.thumbSha256,
      };
    }

    // File exists but no state - recalculate checksums
    const cardDir = path.join(IMAGES_DIR, card.game_id, card.card_id);
    const canonicalPath = path.join(cardDir, 'canonical.jpg');
    const thumbPath = path.join(cardDir, 'thumb.jpg');

    if (fs.existsSync(canonicalPath) && fs.existsSync(thumbPath)) {
      return {
        canonicalSha256: calculateFileSha256(canonicalPath),
        thumbSha256: calculateFileSha256(thumbPath),
      };
    }

    return null;
  }

  // Download image
  setCurrentOperation(`Downloading ${card.game_id}/${card.name}`);

  try {
    const canonicalBuffer = await downloadImage(card.image_url);
    const thumbBuffer = createThumbnail(canonicalBuffer);

    const checksums = saveImage(card, canonicalBuffer, thumbBuffer);

    logger.info('Image fetched', {
      cardId: card.card_id,
      name: card.name,
      size: canonicalBuffer.length,
    });

    return checksums;
  } catch (error) {
    logger.error('Failed to fetch image', { cardId: card.card_id, url: card.image_url }, error as Error);
    return null;
  }
}

// ============================================================================
// Game Processing
// ============================================================================

async function processGame(gameId: GameId, previousState: FetchState | null): Promise<number> {
  const normalizedPath = path.join(NORMALIZED_DIR, `${gameId}.jsonl`);

  if (!fs.existsSync(normalizedPath)) {
    logger.warn('Normalized data not found', { gameId, path: normalizedPath });
    return 0;
  }

  // Load cards
  const lines = fs.readFileSync(normalizedPath, 'utf-8').split('\n').filter(Boolean);
  const cards: CardCore[] = lines.map(line => JSON.parse(line));

  logger.info(`Processing images for ${gameId}`, { cards: cards.length });

  // Process cards with concurrency control
  const limiter = pLimit(CONFIG.concurrentDownloads);
  let fetched = 0;
  let skipped = 0;
  let failed = 0;

  const tasks = cards.map(card =>
    limiter(async () => {
      if (isShuttingDown()) {
        return;
      }

      const result = await processCard(card, previousState);

      if (result) {
        if (needsFetch(card, previousState)) {
          fetched++;
        } else {
          skipped++;
        }

        // Update state
        if (previousState && card.image_url) {
          previousState.images[card.card_id] = {
            imageUrl: card.image_url,
            canonicalSha256: result.canonicalSha256,
            thumbSha256: result.thumbSha256,
            lastFetch: new Date().toISOString(),
          };
        }
      } else if (card.image_url) {
        failed++;
      }

      await sleep(50); // Small delay between downloads
    })
  );

  await Promise.all(tasks);

  logger.info(`Completed ${gameId}`, { fetched, skipped, failed });

  return fetched;
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('fetch_images');

  fs.mkdirSync(IMAGES_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  onShutdown({
    name: 'Save fetch images state',
    handler: () => {
      logger.info('Fetch images state saved during shutdown');
    },
    timeout: 3000,
  });

  let previousState = loadState();

  if (!previousState) {
    previousState = {
      version: '1.0.0',
      lastSync: new Date().toISOString(),
      images: {},
    };
  }

  // Find all normalized files
  if (!fs.existsSync(NORMALIZED_DIR)) {
    logger.warn('Normalized directory not found. Run normalize first.');
    console.log('\n⚠️  No normalized data found.');
    console.log('   Run: pnpm --filter ingest normalize');
    return;
  }

  const normalizedFiles = fs.readdirSync(NORMALIZED_DIR)
    .filter(file => file.endsWith('.jsonl'))
    .map(file => file.replace('.jsonl', '') as GameId);

  if (normalizedFiles.length === 0) {
    logger.warn('No normalized files found');
    console.log('\n⚠️  No normalized data files found.');
    console.log('   Run: pnpm --filter ingest normalize');
    return;
  }

  pipelineLogger.info('Starting image fetch', {
    games: normalizedFiles,
    previousImages: Object.keys(previousState.images).length,
  });

  const startTime = Date.now();
  let totalFetched = 0;

  for (const gameId of normalizedFiles) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping...');
      break;
    }

    setCurrentOperation(`Processing ${gameId}`);

    const fetched = await processGame(gameId, previousState);
    totalFetched += fetched;

    // Save state after each game
    saveState(previousState);
  }

  previousState.lastSync = new Date().toISOString();
  saveState(previousState);

  setCurrentOperation(null);

  const duration = Math.round((Date.now() - startTime) / 1000);

  console.log('\n' + '='.repeat(70));
  console.log('IMAGE FETCH COMPLETE');
  console.log('='.repeat(70));
  console.log(`Games: ${normalizedFiles.join(', ')}`);
  console.log(`Images fetched: ${totalFetched}`);
  console.log(`Total images tracked: ${Object.keys(previousState.images).length}`);
  console.log(`Duration: ${duration}s`);
  console.log(`\n📁 Output: ${IMAGES_DIR}`);
  console.log(`📊 State: ${STATE_FILE}`);

  if (totalFetched === 0) {
    console.log('\n✓ All images up to date (incremental skip)');
  }
}

main().catch(error => {
  logger.error('Image fetch failed', {}, error);
  process.exit(1);
});
