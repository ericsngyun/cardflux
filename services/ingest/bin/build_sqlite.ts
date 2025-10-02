#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import Database from 'better-sqlite3';
import { getAllGames } from '@cardflux/config';

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

function insertCards(db: Database.Database, cards: Card[]) {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO cards (id, game, name, set, rarity, type, image_url, raw_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertMany = db.transaction((cards: Card[]) => {
    for (const card of cards) {
      insert.run(
        card.id,
        card.game,
        card.name,
        card.set,
        card.rarity,
        card.type,
        card.imageUrl,
        JSON.stringify(card.rawData)
      );
    }
  });

  insertMany(cards);
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

    const lines = fs.readFileSync(curatedPath, 'utf-8').split('\n').filter(Boolean);
    const cards: Card[] = lines.map(line => JSON.parse(line));

    insertCards(db, cards);
    console.log(`Inserted ${cards.length} cards for ${game.slug}`);
  }

  db.close();
  console.log(`Database created at ${dbPath}`);
}

main();
