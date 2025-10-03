#!/usr/bin/env node
/**
 * Build SQLite database with TCGplayer data including prices
 */

import * as fs from 'fs';
import * as path from 'path';
import Database from 'better-sqlite3';
import { getEnabledCategories } from '@cardflux/config/tcgplayer-config';
import { parseJsonLines, logger } from '@cardflux/shared';
import type { TCGCard } from '@cardflux/config/tcgplayer-config';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const ARTIFACTS_DIR = path.resolve(__dirname, '../../../artifacts/metadata');

function createDatabase(dbPath: string): Database.Database {
  const db = new Database(dbPath);

  // Enable WAL mode for better concurrency
  db.pragma('journal_mode = WAL');

  db.exec(`
    -- Main cards table
    CREATE TABLE IF NOT EXISTS cards (
      product_id INTEGER PRIMARY KEY,
      category_id INTEGER NOT NULL,
      category_name TEXT NOT NULL,
      group_id INTEGER NOT NULL,
      group_name TEXT NOT NULL,
      name TEXT NOT NULL,
      clean_name TEXT NOT NULL,
      image_url TEXT,
      tcgplayer_url TEXT,
      rarity TEXT,
      card_number TEXT,
      sub_type TEXT,
      oracle_text TEXT,
      modified_on TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Prices table (separate for normal and foil)
    CREATE TABLE IF NOT EXISTS prices (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_id INTEGER NOT NULL,
      finish TEXT NOT NULL CHECK(finish IN ('normal', 'foil')),
      low_price REAL,
      mid_price REAL,
      high_price REAL,
      market_price REAL,
      direct_low_price REAL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (product_id) REFERENCES cards(product_id),
      UNIQUE(product_id, finish)
    );

    -- Indexes for fast lookups
    CREATE INDEX IF NOT EXISTS idx_cards_category ON cards(category_id);
    CREATE INDEX IF NOT EXISTS idx_cards_group ON cards(group_id);
    CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);
    CREATE INDEX IF NOT EXISTS idx_cards_clean_name ON cards(clean_name);
    CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity);
    CREATE INDEX IF NOT EXISTS idx_prices_product ON prices(product_id);
    CREATE INDEX IF NOT EXISTS idx_prices_finish ON prices(finish);

    -- Full-text search for card names
    CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
      name,
      clean_name,
      oracle_text,
      content=cards,
      content_rowid=product_id
    );

    -- Triggers to keep FTS in sync
    CREATE TRIGGER IF NOT EXISTS cards_fts_insert AFTER INSERT ON cards BEGIN
      INSERT INTO cards_fts(rowid, name, clean_name, oracle_text)
      VALUES (new.product_id, new.name, new.clean_name, new.oracle_text);
    END;

    CREATE TRIGGER IF NOT EXISTS cards_fts_delete AFTER DELETE ON cards BEGIN
      DELETE FROM cards_fts WHERE rowid = old.product_id;
    END;

    CREATE TRIGGER IF NOT EXISTS cards_fts_update AFTER UPDATE ON cards BEGIN
      DELETE FROM cards_fts WHERE rowid = old.product_id;
      INSERT INTO cards_fts(rowid, name, clean_name, oracle_text)
      VALUES (new.product_id, new.name, new.clean_name, new.oracle_text);
    END;
  `);

  return db;
}

function insertCards(db: Database.Database, cards: TCGCard[], categoryName: string): { inserted: number; failed: number } {
  const insertCard = db.prepare(`
    INSERT OR REPLACE INTO cards (
      product_id, category_id, category_name, group_id, group_name,
      name, clean_name, image_url, tcgplayer_url,
      rarity, card_number, sub_type, oracle_text, modified_on
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertPrice = db.prepare(`
    INSERT OR REPLACE INTO prices (
      product_id, finish, low_price, mid_price, high_price, market_price, direct_low_price
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `);

  const stats = { inserted: 0, failed: 0 };

  // Transaction for atomicity
  const insertGameCards = db.transaction((cards: TCGCard[]) => {
    for (const card of cards) {
      // Validate required fields
      if (!card.productId) {
        throw new Error(`Invalid productId for card: ${card.name}`);
      }

      // Insert card
      insertCard.run(
        card.productId,
        card.categoryId,
        card.categoryName,
        card.groupId,
        card.groupName,
        card.name,
        card.cleanName || card.name.toLowerCase().replace(/[^a-z0-9]/g, ' ').trim(),
        card.imageUrl || null,
        card.url || null,
        card.rarity || null,
        card.number || null,
        card.subType || null,
        card.oracleText || null,
        card.modifiedOn || null
      );

      // Insert normal price if exists
      if (card.prices.normal) {
        insertPrice.run(
          card.productId,
          'normal',
          card.prices.normal.low,
          card.prices.normal.mid,
          card.prices.normal.high,
          card.prices.normal.market,
          card.prices.normal.directLow
        );
      }

      // Insert foil price if exists
      if (card.prices.foil) {
        insertPrice.run(
          card.productId,
          'foil',
          card.prices.foil.low,
          card.prices.foil.mid,
          card.prices.foil.high,
          card.prices.foil.market,
          card.prices.foil.directLow
        );
      }

      stats.inserted++;
    }
  });

  try {
    insertGameCards(cards);
    logger.info(`Inserted ${stats.inserted} cards for ${categoryName} in transaction`);
  } catch (error: any) {
    logger.error(`Transaction failed for ${categoryName}: ${error.message}`);
    stats.failed = cards.length;
    stats.inserted = 0;
    throw error;
  }

  return stats;
}

function main() {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });

  const dbPath = path.join(ARTIFACTS_DIR, 'cards.db');
  const db = createDatabase(dbPath);

  const categories = getEnabledCategories();
  let totalInserted = 0;
  let totalFailed = 0;

  for (const category of categories) {
    const curatedPath = path.join(
      CURATED_DIR,
      `${category.name.toLowerCase().replace(/\s+/g, '-')}.jsonl`
    );

    if (!fs.existsSync(curatedPath)) {
      logger.warn(`No curated data found for ${category.name}`, { file: curatedPath });
      continue;
    }

    logger.info(`Processing ${category.name}...`);

    const content = fs.readFileSync(curatedPath, 'utf-8');
    const { data: cards, errors: parseErrors } = parseJsonLines<TCGCard>(content, (lineNumber, line, error) => {
      logger.warn(`Skipping corrupted line ${lineNumber}`, { error: error.message });
    });

    if (parseErrors > 0) {
      logger.warn(`Skipped ${parseErrors} corrupted lines in ${category.name}`);
    }

    const { inserted, failed } = insertCards(db, cards, category.name);
    totalInserted += inserted;
    totalFailed += failed;

    if (failed === 0) {
      logger.info(`✓ ${category.name}: ${inserted} cards, ${parseErrors} corrupted lines skipped`);
    } else {
      logger.error(`✗ ${category.name}: ${failed} cards failed`);
    }
  }

  db.close();

  console.log('\n' + '='.repeat(60));
  console.log('DATABASE BUILD COMPLETE');
  console.log('='.repeat(60));
  console.log(`Database: ${dbPath}`);
  console.log(`Total cards: ${totalInserted.toLocaleString()}`);
  console.log(`Failed: ${totalFailed}`);
  console.log('\nSupported queries:');
  console.log('  - Full-text search on card names and text');
  console.log('  - Filter by category, group, rarity');
  console.log('  - Join cards with prices (normal/foil)');
}

main();
