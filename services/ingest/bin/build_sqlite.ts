#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import Database from 'better-sqlite3';
import { getAllGames } from '@cardflux/config';
import { parseJsonLines } from '@cardflux/shared';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');
const ARTIFACTS_DIR = path.resolve(__dirname, '../../../artifacts/metadata');

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

function createDatabase(dbPath: string): Database.Database {
  const db = new Database(dbPath);

  db.exec(`
    CREATE TABLE IF NOT EXISTS cards (
      id TEXT PRIMARY KEY,
      game TEXT NOT NULL,
      name TEXT NOT NULL,
      set TEXT,
      rarity TEXT,
      type TEXT,
      image_url TEXT,
      raw_data TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_game ON cards(game);
    CREATE INDEX IF NOT EXISTS idx_name ON cards(name);
    CREATE INDEX IF NOT EXISTS idx_set ON cards(set);
    CREATE INDEX IF NOT EXISTS idx_rarity ON cards(rarity);
  `);

  return db;
}

function insertCards(db: Database.Database, cards: Card[], game: string): { inserted: number; failed: number } {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO cards (id, game, name, set, rarity, type, image_url, raw_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const stats = { inserted: 0, failed: 0, errors: [] as any[] };

  // Wrap entire game insertion in a transaction for atomicity
  const insertGameCards = db.transaction((cards: Card[]) => {
    for (const card of cards) {
      // Validate required fields
      if (!card.id || card.id.length > 100) {
        throw new Error('Invalid id: must be 1-100 characters');
      }
      if (!card.game || card.game.length > 50) {
        throw new Error('Invalid game: must be 1-50 characters');
      }
      if (!card.name || card.name.length > 500) {
        throw new Error('Invalid name: must be 1-500 characters');
      }

      // Validate optional fields
      if (card.set && card.set.length > 100) {
        throw new Error('Invalid set: max 100 characters');
      }
      if (card.rarity && card.rarity.length > 50) {
        throw new Error('Invalid rarity: max 50 characters');
      }
      if (card.type && card.type.length > 100) {
        throw new Error('Invalid type: max 100 characters');
      }
      if (card.imageUrl && card.imageUrl.length > 2000) {
        throw new Error('Invalid imageUrl: max 2000 characters');
      }

      // Sanitize and validate raw_data
      const rawData = JSON.stringify(card.rawData);
      if (rawData.length > 100000) {
        throw new Error('rawData too large: max 100KB');
      }

      insert.run(
        card.id,
        card.game,
        card.name,
        card.set || null,
        card.rarity || null,
        card.type || null,
        card.imageUrl || null,
        rawData
      );

      stats.inserted++;
    }
  });

  try {
    // Execute transaction - all or nothing
    insertGameCards(cards);
    console.log(`✓ ${game}: Inserted ${stats.inserted} cards in transaction`);
  } catch (error: any) {
    // Transaction rolled back automatically
    console.error(`❌ Transaction failed for ${game}: ${error.message}`);
    console.error(`   All ${cards.length} cards rolled back`);
    stats.failed = cards.length;
    stats.inserted = 0;

    stats.errors.push({
      game,
      totalCards: cards.length,
      error: error.message,
    });
  }

  return { inserted: stats.inserted, failed: stats.failed };
}

function main() {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });

  const dbPath = path.join(ARTIFACTS_DIR, 'cards.db');
  const db = createDatabase(dbPath);

  const games = getAllGames();

  for (const game of games) {
    const curatedPath = path.join(CURATED_DIR, `${game.slug}.jsonl`);

    if (!fs.existsSync(curatedPath)) {
      console.log(`No curated data found for ${game.slug}, skipping...`);
      continue;
    }

    console.log(`Inserting cards for ${game.name}...`);

    // Use safe JSON parsing
    const content = fs.readFileSync(curatedPath, 'utf-8');
    const { data: cards, errors: parseErrors } = parseJsonLines<Card>(content, (lineNumber, line, error) => {
      console.warn(`Skipping corrupted line ${lineNumber}: ${error.message}`);
    });

    if (parseErrors > 0) {
      console.warn(`⚠️  Skipped ${parseErrors} corrupted lines in ${game.slug}.jsonl`);
    }

    const { inserted, failed } = insertCards(db, cards, game.slug);
    if (failed === 0) {
      console.log(`✓ ${game.slug}: Inserted ${inserted} cards (${parseErrors} corrupted lines skipped)`);
    } else {
      console.error(`⚠️  ${game.slug}: ${failed} cards failed to insert`);
    }
  }

  db.close();
  console.log(`Database created at ${dbPath}`);
}

main();
