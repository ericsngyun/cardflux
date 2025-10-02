#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import { getAllGames } from '@cardflux/config';

const METADATA_DIR = path.resolve(__dirname, '../../../artifacts/metadata');
const PRICE_PATCHES_DIR = path.resolve(__dirname, '../../../artifacts/price-patches');

interface PriceData {
  cardId: string;
  game: string;
  prices: {
    usd?: number;
    usdFoil?: number;
    eur?: number;
    tix?: number;
  };
  marketUrl?: string;
  lastUpdated: string;
}

async function fetchMTGPrices(): Promise<Map<string, PriceData>> {
  console.log('Fetching MTG prices from Scryfall...');
  const response = await axios.get('https://api.scryfall.com/bulk-data/default-cards');
  const bulkData = response.data;
  const downloadUrl = bulkData.download_uri;
  const cardsResponse = await axios.get(downloadUrl);

  const priceMap = new Map<string, PriceData>();

  for (const card of cardsResponse.data) {
    if (card.prices) {
      priceMap.set(card.id, {
        cardId: card.id,
        game: 'mtg',
        prices: {
          usd: card.prices.usd ? parseFloat(card.prices.usd) : undefined,
          usdFoil: card.prices.usd_foil ? parseFloat(card.prices.usd_foil) : undefined,
          eur: card.prices.eur ? parseFloat(card.prices.eur) : undefined,
          tix: card.prices.tix ? parseFloat(card.prices.tix) : undefined,
        },
        marketUrl: card.purchase_uris?.tcgplayer,
        lastUpdated: new Date().toISOString(),
      });
    }
  }

  return priceMap;
}

async function fetchPokemonPrices(): Promise<Map<string, PriceData>> {
  console.log('Fetching Pokemon prices...');
  const priceMap = new Map<string, PriceData>();

  // Pokemon TCG API includes price data
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await axios.get(`https://api.pokemontcg.io/v2/cards?page=${page}&pageSize=250`);
    const cards = response.data.data;

    for (const card of cards) {
      if (card.tcgplayer?.prices) {
        const prices = card.tcgplayer.prices;
        const normal = prices.normal || prices.holofoil || prices.reverseHolofoil;

        priceMap.set(card.id, {
          cardId: card.id,
          game: 'pokemon',
          prices: {
            usd: normal?.market,
          },
          marketUrl: card.tcgplayer.url,
          lastUpdated: new Date().toISOString(),
        });
      }
    }

    hasMore = cards.length === 250;
    page++;
  }

  return priceMap;
}

async function fetchYugiohPrices(): Promise<Map<string, PriceData>> {
  console.log('Fetching Yu-Gi-Oh prices...');
  const response = await axios.get('https://db.ygoprodeck.com/api/v7/cardinfo.php');
  const priceMap = new Map<string, PriceData>();

  for (const card of response.data.data) {
    if (card.card_prices && card.card_prices.length > 0) {
      const prices = card.card_prices[0];

      priceMap.set(card.id.toString(), {
        cardId: card.id.toString(),
        game: 'yugioh',
        prices: {
          usd: prices.tcgplayer_price ? parseFloat(prices.tcgplayer_price) : undefined,
        },
        lastUpdated: new Date().toISOString(),
      });
    }
  }

  return priceMap;
}

function savePricePatch(game: string, prices: Map<string, PriceData>) {
  const patchDir = path.join(PRICE_PATCHES_DIR, game);
  fs.mkdirSync(patchDir, { recursive: true });

  const timestamp = new Date().toISOString().split('T')[0];
  const patchPath = path.join(patchDir, `${timestamp}.jsonl`);

  const lines = Array.from(prices.values()).map(price => JSON.stringify(price));
  fs.writeFileSync(patchPath, lines.join('\n'));

  console.log(`Saved ${prices.size} price records to ${patchPath}`);

  // Update latest symlink
  const latestPath = path.join(patchDir, 'latest.jsonl');
  if (fs.existsSync(latestPath)) {
    fs.unlinkSync(latestPath);
  }
  fs.copyFileSync(patchPath, latestPath);
}

async function main() {
  fs.mkdirSync(PRICE_PATCHES_DIR, { recursive: true });

  try {
    const mtgPrices = await fetchMTGPrices();
    savePricePatch('mtg', mtgPrices);
  } catch (error) {
    console.error('Error fetching MTG prices:', error);
  }

  try {
    const pokemonPrices = await fetchPokemonPrices();
    savePricePatch('pokemon', pokemonPrices);
  } catch (error) {
    console.error('Error fetching Pokemon prices:', error);
  }

  try {
    const yugiohPrices = await fetchYugiohPrices();
    savePricePatch('yugioh', yugiohPrices);
  } catch (error) {
    console.error('Error fetching Yu-Gi-Oh prices:', error);
  }

  console.log('\nPrice patch generation complete!');
}

main().catch(console.error);
