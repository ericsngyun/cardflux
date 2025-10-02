#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import { getAllGames } from '@cardflux/config';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const IMAGES_DIR = path.resolve(__dirname, '../../../data/images');

interface Card {
  id: string;
  game: string;
  imageUrl?: string;
}

async function downloadImage(url: string, filepath: string): Promise<void> {
  const response = await axios.get(url, { responseType: 'arraybuffer' });
  fs.writeFileSync(filepath, response.data);
}

async function fetchImagesForGame(gameSlug: string) {
  console.log(`Fetching images for ${gameSlug}...`);

  const curatedPath = path.join(CURATED_DIR, `${gameSlug}.jsonl`);
  const gameImagesDir = path.join(IMAGES_DIR, gameSlug);

  fs.mkdirSync(gameImagesDir, { recursive: true });

  const lines = fs.readFileSync(curatedPath, 'utf-8').split('\n').filter(Boolean);
  let downloaded = 0;

  for (const line of lines) {
    const card: Card = JSON.parse(line);

    if (!card.imageUrl) continue;

    const ext = path.extname(new URL(card.imageUrl).pathname) || '.jpg';
    const imagePath = path.join(gameImagesDir, `${card.id}${ext}`);

    if (fs.existsSync(imagePath)) {
      continue; // Skip if already downloaded
    }

    try {
      await downloadImage(card.imageUrl, imagePath);
      downloaded++;

      if (downloaded % 100 === 0) {
        console.log(`Downloaded ${downloaded} images...`);
      }
    } catch (error) {
      console.error(`Failed to download image for card ${card.id}:`, error);
    }
  }

  console.log(`Downloaded ${downloaded} new images for ${gameSlug}`);
}

async function main() {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });

  const games = getAllGames();

  for (const game of games) {
    await fetchImagesForGame(game.slug);
  }

  console.log('Image fetching complete!');
}

main().catch(console.error);
