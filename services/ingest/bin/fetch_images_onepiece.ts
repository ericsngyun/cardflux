#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const IMAGES_DIR = path.resolve(__dirname, '../../../data/images');

interface Card {
  id?: string;
  productId?: number;
  game?: string;
  imageUrl?: string;
}

async function downloadImage(url: string, filepath: string): Promise<void> {
  const response = await axios.get(url, { responseType: 'arraybuffer', timeout: 10000 });
  fs.writeFileSync(filepath, response.data);
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

  for (let i = 0; i < lines.length; i++) {
    const card: Card = JSON.parse(lines[i]);

    if (!card.imageUrl) {
      skipped++;
      continue;
    }

    // Use productId as the card ID (TCGPlayer data format)
    const cardId = card.id || card.productId?.toString() || 'unknown';

    const ext = path.extname(new URL(card.imageUrl).pathname) || '.jpg';
    const imagePath = path.join(gameImagesDir, `${cardId}${ext}`);

    if (fs.existsSync(imagePath)) {
      skipped++;
      continue;
    }

    try {
      await downloadImage(card.imageUrl, imagePath);
      downloaded++;

      if (downloaded % 50 === 0) {
        console.log(`Progress: ${downloaded} downloaded, ${skipped} skipped, ${failed} failed (${i + 1}/${lines.length})`);
      }
    } catch (error: any) {
      failed++;
      console.error(`Failed to download ${cardId}: ${error.message}`);
    }

    // Small delay to avoid rate limiting
    if (downloaded % 10 === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  console.log('\n=== Summary ===');
  console.log(`Downloaded: ${downloaded} new images`);
  console.log(`Skipped: ${skipped} (already exist)`);
  console.log(`Failed: ${failed}`);
  console.log(`Total: ${lines.length} cards`);
}

fetchImagesForOnePiece().catch(console.error);
