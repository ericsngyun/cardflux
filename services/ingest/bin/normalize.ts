#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import { getAllGames, GameConfig } from '@cardflux/config';

const RAW_DIR = path.resolve(__dirname, '../../../data/raw');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');

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

async function fetchGameData(config: GameConfig): Promise<any[]> {
  console.log(`Fetching data for ${config.name}...`);

  if (config.source.type === 'bulk') {
    const response = await axios.get(config.source.url);
    const bulkData = response.data;
    const downloadUrl = bulkData.download_uri;
    const cardsResponse = await axios.get(downloadUrl);
    return cardsResponse.data;
  } else {
    const response = await axios.get(config.source.url);
    return response.data.data || response.data;
  }
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

async function processGame(config: GameConfig) {
  try {
    const rawData = await fetchGameData(config);

    // Save raw data
    const rawPath = path.join(RAW_DIR, `${config.slug}.json`);
    fs.writeFileSync(rawPath, JSON.stringify(rawData, null, 2));
    console.log(`Saved raw data to ${rawPath}`);

    // Normalize data
    const normalizedCards = rawData.map((card: any) => normalizeCard(card, config));

    // Save curated data
    const curatedPath = path.join(CURATED_DIR, `${config.slug}.jsonl`);
    const jsonlData = normalizedCards.map((card: Card) => JSON.stringify(card)).join('\n');
    fs.writeFileSync(curatedPath, jsonlData);
    console.log(`Saved ${normalizedCards.length} normalized cards to ${curatedPath}`);

  } catch (error) {
    console.error(`Error processing ${config.name}:`, error);
    throw error;
  }
}

async function main() {
  // Ensure directories exist
  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(CURATED_DIR, { recursive: true });

  const games = getAllGames();

  for (const game of games) {
    await processGame(game);
  }

  console.log('Normalization complete!');
}

main().catch(console.error);
