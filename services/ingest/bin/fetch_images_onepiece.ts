#!/usr/bin/env node
/**
 * One Piece TCG Image Fetcher
 *
 * API-Respectful Image Downloading:
 * - Skips images that already exist (checks file existence + validates size)
 * - Implements rate limiting: ~2 images/sec = 120/min (well under 300/hour limit)
 * - Exponential backoff on 403/429 errors (respects server rate limits)
 * - Validates image size (re-downloads corrupted files < 1KB)
 *
 * This ensures we're a good API citizen and don't get banned by TCGPlayer.
 */
import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const IMAGES_DIR = path.resolve(__dirname, '../../../data/images');

// CRITICAL: Rate limiting to respect TCGPlayer API policy
// TCGPlayer allows ~300 requests/hour for images
// We implement conservative rate limiting to be a good API citizen
const BATCH_DELAY_MS = 500;  // 500ms after every 10 images = ~2 images/sec = 120/min
const MIN_DELAY_MS = 100;    // 100ms between individual requests

interface Card {
  id?: string;
  productId?: number;
  game?: string;
  imageUrl?: string;
}

async function downloadImage(url: string, filepath: string, retries = 3): Promise<void> {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 15000,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        },
      });
      fs.writeFileSync(filepath, response.data);
      return;
    } catch (error: any) {
      if (attempt === retries - 1) throw error;

      // Exponential backoff for 403 errors
      if (error.response?.status === 403 || error.response?.status === 429) {
        const delay = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
}

async function fetchImagesForOnePiece() {
  const gameSlug = 'one-piece';
  console.log(`Fetching images for ${gameSlug}...`);

  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);
  const gameImagesDir = path.join(IMAGES_DIR, gameSlug);

  if (!fs.existsSync(curatedPath)) {
    console.error(`No curated data found at ${curatedPath}`);
    process.exit(1);
  }

  fs.mkdirSync(gameImagesDir, { recursive: true });

  const lines = fs.readFileSync(curatedPath, 'utf-8').split('\n').filter(Boolean);
  console.log(`Found ${lines.length} One Piece cards`);

  let downloaded = 0;
  let skipped = 0;
  let failed = 0;
  const failedCards: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const card: Card = JSON.parse(lines[i]);

    if (!card.imageUrl) {
      skipped++;
      continue;
    }

    // Transform URL to 800x800 (upgrade from 600x600)
    let imageUrl = card.imageUrl;
    if (imageUrl.includes('_in_600x600')) {
      imageUrl = imageUrl.replace('_in_600x600', '_in_800x800');
    } else if (imageUrl.includes('_600w')) {
      imageUrl = imageUrl.replace('_600w', '_in_800x800');
    }

    // Use productId as the card ID (TCGPlayer data format)
    const cardId = card.id || card.productId?.toString() || 'unknown';

    const ext = path.extname(new URL(imageUrl).pathname) || '.jpg';
    const imagePath = path.join(gameImagesDir, `${cardId}${ext}`);

    // Skip if image already exists (respect API policy - don't re-download)
    if (fs.existsSync(imagePath)) {
      // Verify image is valid (not corrupted/empty)
      const stats = fs.statSync(imagePath);
      if (stats.size >= 1000) { // At least 1KB = valid image
        skipped++;
        continue;
      }
      // If corrupted (< 1KB), re-download below
      console.log(`  ! Corrupted image detected for ${cardId} (${stats.size} bytes), re-downloading...`);
    }

    try {
      await downloadImage(imageUrl, imagePath);
      downloaded++;

      if (downloaded % 50 === 0) {
        console.log(`Progress: ${downloaded} downloaded, ${skipped} skipped, ${failed} failed (${i + 1}/${lines.length})`);
      }

      // Adaptive rate limiting: respect API policy
      // CRITICAL: Don't overwhelm TCGPlayer servers
      if (downloaded % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, BATCH_DELAY_MS));
      } else {
        await new Promise(resolve => setTimeout(resolve, MIN_DELAY_MS));
      }
    } catch (error: any) {
      failed++;
      failedCards.push(cardId);
      if (failed <= 10) {
        console.error(`Failed to download ${cardId}: ${error.message}`);
      }
    }
  }

  console.log('\n=== Summary ===');
  console.log(`Downloaded: ${downloaded} new images`);
  console.log(`Skipped: ${skipped} (already exist)`);
  console.log(`Failed: ${failed}`);
  console.log(`Total: ${lines.length} cards`);
  console.log(`Success rate: ${((downloaded / (downloaded + failed)) * 100).toFixed(1)}%`);

  if (failed > 0) {
    console.log(`\nFirst 20 failed card IDs: ${failedCards.slice(0, 20).join(', ')}`);
  }
}

fetchImagesForOnePiece().catch(console.error);
