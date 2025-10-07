#!/usr/bin/env node
/**
 * Scrape ONLY One Piece TCG cards from tcgcsv.com
 * Fast test to validate category 68 and sealed product filtering
 */

import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import {
  TCGCSV_CONFIG,
  getCategoryById,
  mergeProductAndPrices,
  isSealedProduct,
  type TCGCategory,
  type TCGGroup,
  type TCGProduct,
  type TCGPrice,
  type TCGCard,
} from '@cardflux/config/tcgplayer-config';
import { sleep, logger } from '@cardflux/shared';

const RAW_DIR = path.resolve(__dirname, '../../../data/raw/tcgplayer');
const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');

const ONE_PIECE_CATEGORY_ID = 68;

async function fetchWithRetry<T>(url: string): Promise<T> {
  await sleep(200);

  const response = await axios.get(url, {
    timeout: 30000,
    headers: {
      'Accept': 'application/json',
      'User-Agent': 'CardFlux/1.0',
    },
  });

  if (!response.data.success) {
    throw new Error(`API error: ${JSON.stringify(response.data.errors)}`);
  }

  return response.data.results as T;
}

async function fetchGroups(categoryId: number): Promise<TCGGroup[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/groups`;
  console.log(`Fetching groups from ${url}...`);

  const groups = await fetchWithRetry<TCGGroup[]>(url);
  console.log(`Found ${groups.length} groups`);

  return groups;
}

async function fetchProducts(categoryId: number, groupId: number): Promise<TCGProduct[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/products`;
  return await fetchWithRetry<TCGProduct[]>(url);
}

async function fetchPrices(categoryId: number, groupId: number): Promise<TCGPrice[]> {
  const url = `${TCGCSV_CONFIG.baseUrl}/${categoryId}/${groupId}/prices`;
  return await fetchWithRetry<TCGPrice[]>(url);
}

async function fetchGroupData(
  category: TCGCategory,
  group: TCGGroup
): Promise<TCGCard[]> {
  console.log(`Processing: ${group.name}`);

  const [products, prices] = await Promise.all([
    fetchProducts(category.categoryId, group.groupId),
    fetchPrices(category.categoryId, group.groupId),
  ]);

  console.log(`  Fetched ${products.length} products, ${prices.length} price entries`);

  // Filter out sealed products (booster boxes, starter decks, cases, etc.)
  const cardProducts = products.filter(p => !isSealedProduct(p));
  const filteredCount = products.length - cardProducts.length;
  console.log(`  Filtered to ${cardProducts.length} cards (removed ${filteredCount} sealed products)`);

  // Create price lookup
  const priceMap = new Map<number, TCGPrice[]>();
  for (const price of prices) {
    if (!priceMap.has(price.productId)) {
      priceMap.set(price.productId, []);
    }
    priceMap.get(price.productId)!.push(price);
  }

  // Merge products with prices
  const cards: TCGCard[] = cardProducts.map(product => {
    const productPrices = priceMap.get(product.productId) || [];
    const card = mergeProductAndPrices(product, productPrices);
    card.categoryName = 'One Piece Card Game'; // Correct name for category 68
    card.groupName = group.name;
    return card;
  });

  await sleep(500); // Rate limiting

  return cards;
}

async function main() {
  console.log('\n=== Scraping One Piece TCG (Category 68) ===\n');

  const category = getCategoryById(ONE_PIECE_CATEGORY_ID);
  if (!category) {
    console.error('ERROR: One Piece category not found in config!');
    process.exit(1);
  }

  console.log(`Category: ${category.name} (ID: ${category.categoryId})`);

  // Fetch groups
  const groups = await fetchGroups(category.categoryId);

  // Fetch all group data
  let allCards: TCGCard[] = [];

  for (let i = 0; i < groups.length; i++) {
    const group = groups[i];
    console.log(`\n[${i + 1}/${groups.length}] ${group.name}`);

    try {
      const cards = await fetchGroupData(category, group);
      allCards = allCards.concat(cards);
      console.log(`  Total cards so far: ${allCards.length}`);
    } catch (error: any) {
      console.error(`  ERROR: Failed to fetch group: ${error.message}`);
    }
  }

  // Save curated data
  fs.mkdirSync(CURATED_DIR, { recursive: true });

  const curatedPath = path.join(CURATED_DIR, 'one-piece.jsonl');
  const jsonlData = allCards.map(card => JSON.stringify(card)).join('\n');
  fs.writeFileSync(curatedPath, jsonlData);

  console.log(`\n=== Summary ===`);
  console.log(`Total groups: ${groups.length}`);
  console.log(`Total cards: ${allCards.length}`);
  console.log(`Saved to: ${curatedPath}`);

  // Show sample cards
  console.log(`\n=== Sample Cards ===`);
  allCards.slice(0, 5).forEach(card => {
    console.log(`- ${card.name} (${card.groupName}) - ${card.rarity || 'Unknown'}`);
  });
}

main().catch(console.error);
