#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import axios from 'axios';
import { getAllGames } from '@cardflux/config';
import {parse JsonLines, sleep, retry, safeJsonParse } from '@cardflux/shared';
import pLimit from 'p-limit';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const IMAGES_DIR = path.resolve(__dirname, '../../../data/images');
const STATE_DIR = path.resolve(__dirname, '../../../data/state');

// CRITICAL: Respect API rate limits to avoid getting banned
// Scryfall: 10 req/sec, TCGPlayer: 300 req/hour
const CONCURRENT_DOWNLOADS = 3;  // Conservative to avoid rate limiting
const MIN_DELAY_MS = 150;  // Minimum 150ms between requests = ~6 req/sec
const limit = pLimit(CONCURRENT_DOWNLOADS);

interface Card {
  id: string;
  game: string;
  name: string;
  imageUrl?: string;
}

interface ImageState {
  game: string;
  totalImages: number;
  lastSync: string;
  imageHashes: Record<string, string>; // cardId -> imageUrlHash
}

/**
 * Load image sync state
 */
function loadImageState(gameSlug: string): ImageState | null {
  const statePath = path.join(STATE_DIR, `${gameSlug}.images.state.json`);

  if (!fs.existsSync(statePath)) {
    return null;
  }

  const content = fs.readFileSync(statePath, 'utf-8');
  const state = safeJsonParse<ImageState>(content, (error) => {
    console.warn(`Failed to parse image state for ${gameSlug}:`, error.message);
  });

  return state;
}

/**
 * Save image sync state
 */
function saveImageState(state: ImageState): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const statePath = path.join(STATE_DIR, `${state.game}.images.state.json`);
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

/**
 * Hash URL to detect if image URL changed
 */
function hashUrl(url: string): string {
  return crypto.createHash('md5').update(url).digest('hex').substring(0, 8);
}

/**
 * Download image with retries and rate limiting
 */
async function downloadImage(
  url: string,
  filepath: string
): Promise<boolean> {
  // Rate limiting: enforce minimum delay between requests
  await sleep(MIN_DELAY_MS);

  return await retry(
    async () => {
      const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 30000, // 30 second timeout
        headers: {
          'User-Agent': 'CardFlux/1.0 (contact@cardflux.app)', // Be a good citizen
          'X-Requested-With': 'CardFlux',
        },
      });

      // Check for rate limiting
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers['retry-after'] || '60');
        console.warn(`Rate limited, waiting ${retryAfter}s`);
        await sleep(retryAfter * 1000);
        throw new Error('Rate limited, retrying...');
      }

      // Verify response is valid
      if (!Buffer.isBuffer(response.data) && !(response.data instanceof ArrayBuffer)) {
        throw new Error('Invalid response: not an image');
      }

      const buffer = Buffer.from(response.data);

      // Verify minimum size (corrupted images are usually tiny)
      if (buffer.length < 1000) {
        throw new Error(`Image too small: ${buffer.length} bytes, likely corrupted`);
      }

      // Verify maximum size (prevent DoS)
      if (buffer.length > 10_000_000) {
        throw new Error(`Image too large: ${buffer.length} bytes`);
      }

      // Write atomically to avoid corruption if interrupted
      const tempPath = `${filepath}.tmp`;
      fs.writeFileSync(tempPath, buffer);
      fs.renameSync(tempPath, filepath);  // Atomic on POSIX systems

      return true;
    },
    {
      retries: 3,
      minDelay: 1000,
      maxDelay: 10000,
      factor: 2,
      onRetry: (attempt, error) => {
        console.warn(`Download retry ${attempt}/3 for ${url}: ${error.message}`);
      },
    }
  );
}

/**
 * Get list of cards that need image downloads
 */
function getCardsNeedingImages(
  cards: Card[],
  gameImagesDir: string,
  previousState: ImageState | null
): Card[] {
  const needDownload: Card[] = [];

  for (const card of cards) {
    if (!card.imageUrl) continue;

    const ext = path.extname(new URL(card.imageUrl).pathname) || '.jpg';
    const imagePath = path.join(gameImagesDir, `${card.id}${ext}`);

    // Check if image exists
    if (!fs.existsSync(imagePath)) {
      needDownload.push(card);
      continue;
    }

    // Check if image URL changed
    const currentHash = hashUrl(card.imageUrl);
    const previousHash = previousState?.imageHashes[card.id];

    if (previousHash && previousHash !== currentHash) {
      console.log(`  ↻ Image URL changed for ${card.name}`);
      needDownload.push(card);
      continue;
    }

    // Check if file is corrupted (0 bytes or very small)
    const stats = fs.statSync(imagePath);
    if (stats.size < 1000) { // Less than 1KB is suspicious
      console.log(`  ! Corrupted image detected for ${card.name} (${stats.size} bytes)`);
      needDownload.push(card);
    }
  }

  return needDownload;
}

async function fetchImagesForGameIncremental(gameSlug: string) {
  console.log(`\nChecking images for ${gameSlug}...`);

  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);
  const gameImagesDir = path.join(IMAGES_DIR, gameSlug);

  if (!fs.existsSync(curatedPath)) {
    console.log(`No curated data found for ${gameSlug}, skipping...`);
    return { new: 0, skipped: 0, failed: 0 };
  }

  fs.mkdirSync(gameImagesDir, { recursive: true });

  // Load cards with safe JSON parsing
  const content = fs.readFileSync(curatedPath, 'utf-8');
  const { data: cards, errors: parseErrors } = parseJsonLines<Card>(content, (lineNumber, line, error) => {
    console.warn(`Skipping corrupted line ${lineNumber} in ${gameSlug}: ${error.message}`);
  });

  if (parseErrors > 0) {
    console.warn(`⚠️  Skipped ${parseErrors} corrupted lines`);
  }

  // Load previous state
  const previousState = loadImageState(gameSlug);

  // Determine which cards need downloads
  const needDownload = getCardsNeedingImages(cards, gameImagesDir, previousState);

  if (needDownload.length === 0) {
    console.log(`✓ All ${cards.length} images up to date`);
    return { new: 0, skipped: cards.length, failed: 0 };
  }

  console.log(`Found ${cards.length} total cards, ${needDownload.length} need download`);

  // Download missing/changed images with concurrency control
  const stats = { new: 0, skipped: cards.length - needDownload.length, failed: 0 };
  const imageHashes: Record<string, string> = previousState?.imageHashes || {};

  const downloadTasks = needDownload.map((card, index) =>
    limit(async () => {
      if (!card.imageUrl) return;

      const ext = path.extname(new URL(card.imageUrl).pathname) || '.jpg';
      const imagePath = path.join(gameImagesDir, `${card.id}${ext}`);

      const success = await downloadImage(card.imageUrl, imagePath);

      if (success) {
        stats.new++;
        imageHashes[card.id] = hashUrl(card.imageUrl);

        if ((stats.new + stats.failed) % 50 === 0) {
          console.log(`  Progress: ${stats.new + stats.failed}/${needDownload.length} (${stats.failed} failed)`);
        }
      } else {
        stats.failed++;
      }
    })
  );

  await Promise.all(downloadTasks);

  console.log(`\n✓ ${gameSlug}:`);
  console.log(`  Downloaded: ${stats.new}`);
  console.log(`  Skipped (up to date): ${stats.skipped}`);
  console.log(`  Failed: ${stats.failed}`);

  // Save state
  saveImageState({
    game: gameSlug,
    totalImages: cards.filter(c => c.imageUrl).length,
    lastSync: new Date().toISOString(),
    imageHashes,
  });

  return stats;
}

async function main() {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
  fs.mkdirSync(STATE_DIR, { recursive: true });

  const games = getAllGames();
  const totalStats = { new: 0, skipped: 0, failed: 0 };

  const startTime = Date.now();

  for (const game of games) {
    const stats = await fetchImagesForGameIncremental(game.slug);
    totalStats.new += stats.new;
    totalStats.skipped += stats.skipped;
    totalStats.failed += stats.failed;
  }

  const duration = Math.round((Date.now() - startTime) / 1000);

  console.log('\n' + '='.repeat(60));
  console.log('INCREMENTAL IMAGE SYNC COMPLETE');
  console.log('='.repeat(60));
  console.log(`Total images: ${totalStats.new + totalStats.skipped}`);
  console.log(`Downloaded: ${totalStats.new}`);
  console.log(`Skipped (up to date): ${totalStats.skipped}`);
  console.log(`Failed: ${totalStats.failed}`);
  console.log(`Duration: ${duration}s`);
  console.log(`\nTime saved: ${totalStats.skipped} images (~${Math.round(totalStats.skipped / 250)} minutes)`);
}

main().catch(console.error);
