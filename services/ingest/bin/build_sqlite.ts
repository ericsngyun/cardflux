#!/usr/bin/env node
/**
 * Build read-only SQLite snapshot from normalized CardCore data
 *
 * Creates a production-ready SQLite database with:
 * - All normalized card data from JSONL files
 * - Optimized indexes for common queries
 * - Read-only mode (immutable snapshot)
 * - SHA256 integrity checksums
 * - Version tracking
 *
 * Input: data/normalized/{game_id}.jsonl
 * Output: artifacts/metadata/cards.sqlite.ro
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import Database from 'better-sqlite3';
import { CardCore, GameId } from '@cardflux/shared/types';
import {
  logger,
  createPipelineLogger,
  onShutdown,
  setCurrentOperation,
  isShuttingDown,
} from '@cardflux/shared';

// ============================================================================
// Paths
// ============================================================================

const NORMALIZED_DIR = path.resolve(__dirname, '../../../data/normalized');
const METADATA_DIR = path.resolve(__dirname, '../../../artifacts/metadata');
const OUTPUT_DB = path.join(METADATA_DIR, 'cards.sqlite.ro');

// ============================================================================
// Schema
// ============================================================================

const SCHEMA_SQL = `
-- Cards table (CardCore schema)
CREATE TABLE IF NOT EXISTS cards (
  card_id TEXT PRIMARY KEY NOT NULL,
  game_id TEXT NOT NULL,
  set_code TEXT NOT NULL,
  set_name TEXT NOT NULL,
  collector_number TEXT NOT NULL,
  name TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  printing_id TEXT,
  artwork_hash TEXT,
  image_url TEXT,
  tcgplayer_id INTEGER,
  cardmarket_id INTEGER
) STRICT;

-- Metadata table (database info)
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
) STRICT;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cards_game_set
  ON cards(game_id, set_code);

CREATE INDEX IF NOT EXISTS idx_cards_tcgplayer
  ON cards(tcgplayer_id)
  WHERE tcgplayer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cards_name
  ON cards(name COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_cards_collector
  ON cards(game_id, set_code, collector_number);
`;

// ============================================================================
// Database Building
// ============================================================================

/**
 * Calculate SHA256 of file
 */
function calculateFileSha256(filepath: string): string {
  const content = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Load normalized cards from JSONL
 */
function loadNormalizedCards(gameId: GameId): CardCore[] {
  const normalizedPath = path.join(NORMALIZED_DIR, `${gameId}.jsonl`);

  if (!fs.existsSync(normalizedPath)) {
    logger.warn('Normalized file not found', { gameId, path: normalizedPath });
    return [];
  }

  const lines = fs.readFileSync(normalizedPath, 'utf-8')
    .split('\n')
    .filter(Boolean);

  const cards: CardCore[] = [];

  for (const line of lines) {
    try {
      const card = JSON.parse(line) as CardCore;
      cards.push(card);
    } catch (error) {
      logger.error('Failed to parse card', { line }, error as Error);
    }
  }

  logger.info(`Loaded normalized cards`, { gameId, count: cards.length });

  return cards;
}

/**
 * Create database and insert cards
 */
function buildDatabase(allCards: Map<GameId, CardCore[]>): Database.Database {
  // Remove old database
  if (fs.existsSync(OUTPUT_DB)) {
    fs.unlinkSync(OUTPUT_DB);
  }

  fs.mkdirSync(METADATA_DIR, { recursive: true });

  logger.info('Creating SQLite database', { path: OUTPUT_DB });

  const db = new Database(OUTPUT_DB);

  // Enable optimizations
  db.pragma('journal_mode = WAL');
  db.pragma('synchronous = NORMAL');
  db.pragma('cache_size = 10000');
  db.pragma('temp_store = MEMORY');

  // Create schema
  db.exec(SCHEMA_SQL);

  // Prepare insert statement
  const insertCard = db.prepare(`
    INSERT INTO cards (
      card_id, game_id, set_code, set_name, collector_number,
      name, language, printing_id, artwork_hash, image_url,
      tcgplayer_id, cardmarket_id
    ) VALUES (
      @card_id, @game_id, @set_code, @set_name, @collector_number,
      @name, @language, @printing_id, @artwork_hash, @image_url,
      @tcgplayer_id, @cardmarket_id
    )
  `);

  const insertMetadata = db.prepare(`
    INSERT INTO metadata (key, value) VALUES (?, ?)
  `);

  // Insert all cards in a transaction
  const insertMany = db.transaction((cards: CardCore[]) => {
    for (const card of cards) {
      if (isShuttingDown()) {
        break;
      }

      insertCard.run({
        card_id: card.card_id,
        game_id: card.game_id,
        set_code: card.set_code,
        set_name: card.set_name,
        collector_number: card.collector_number,
        name: card.name,
        language: card.language || 'en',
        printing_id: card.printing_id || null,
        artwork_hash: card.artwork_hash || null,
        image_url: card.image_url || null,
        tcgplayer_id: card.tcgplayer_id || null,
        cardmarket_id: card.cardmarket_id || null,
      });
    }
  });

  // Process each game
  let totalCards = 0;

  for (const [gameId, cards] of allCards.entries()) {
    setCurrentOperation(`Inserting ${gameId} cards`);
    logger.info(`Inserting cards`, { gameId, count: cards.length });

    insertMany(cards);
    totalCards += cards.length;
  }

  // Insert metadata
  insertMetadata.run('version', new Date().toISOString().slice(0, 7).replace('-', '.')); // YYYY.MM
  insertMetadata.run('created_at', new Date().toISOString());
  insertMetadata.run('total_cards', totalCards.toString());
  insertMetadata.run('games', Array.from(allCards.keys()).join(','));

  // Optimize database
  logger.info('Optimizing database...');
  db.pragma('optimize');
  db.pragma('wal_checkpoint(TRUNCATE)');

  // Make read-only
  db.pragma('query_only = ON');

  logger.info('Database build complete', {
    totalCards,
    games: allCards.size,
  });

  return db;
}

/**
 * Validate database integrity
 */
function validateDatabase(db: Database.Database): boolean {
  logger.info('Validating database integrity...');

  try {
    // Check integrity
    const integrityCheck = db.pragma('integrity_check');
    if (integrityCheck[0].integrity_check !== 'ok') {
      logger.error('Database integrity check failed', { result: integrityCheck });
      return false;
    }

    // Check card count
    const result = db.prepare('SELECT COUNT(*) as count FROM cards').get() as { count: number };
    const cardCount = result.count;

    if (cardCount === 0) {
      logger.error('Database is empty');
      return false;
    }

    logger.info('Database validation passed', { cardCount });
    return true;

  } catch (error) {
    logger.error('Database validation failed', {}, error as Error);
    return false;
  }
}

/**
 * Generate database stats
 */
function generateStats(db: Database.Database): Record<string, any> {
  const stats: Record<string, any> = {};

  // Total cards
  const totalResult = db.prepare('SELECT COUNT(*) as count FROM cards').get() as { count: number };
  stats.total_cards = totalResult.count;

  // Cards per game
  const gameStats = db.prepare(`
    SELECT game_id, COUNT(*) as count
    FROM cards
    GROUP BY game_id
    ORDER BY count DESC
  `).all() as Array<{ game_id: string; count: number }>;

  stats.cards_by_game = Object.fromEntries(
    gameStats.map(row => [row.game_id, row.count])
  );

  // Cards per set (top 10)
  const setStats = db.prepare(`
    SELECT game_id, set_code, set_name, COUNT(*) as count
    FROM cards
    GROUP BY game_id, set_code
    ORDER BY count DESC
    LIMIT 10
  `).all() as Array<{ game_id: string; set_code: string; set_name: string; count: number }>;

  stats.top_sets = setStats.map(row => ({
    game: row.game_id,
    set: row.set_code,
    name: row.set_name,
    cards: row.count,
  }));

  // Database size
  const fileStats = fs.statSync(OUTPUT_DB);
  stats.size_bytes = fileStats.size;
  stats.size_mb = (fileStats.size / (1024 * 1024)).toFixed(2);

  return stats;
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('build_sqlite');

  fs.mkdirSync(METADATA_DIR, { recursive: true });

  onShutdown({
    name: 'Close SQLite database',
    handler: () => {
      logger.info('SQLite database closed during shutdown');
    },
    timeout: 3000,
  });

  // Find all normalized files
  if (!fs.existsSync(NORMALIZED_DIR)) {
    logger.warn('Normalized directory not found. Run normalize first.');
    console.log('\n⚠️  No normalized data found.');
    console.log('   Run: pnpm --filter ingest normalize');
    return;
  }

  const normalizedFiles = fs.readdirSync(NORMALIZED_DIR)
    .filter(file => file.endsWith('.jsonl'))
    .map(file => file.replace('.jsonl', '') as GameId);

  if (normalizedFiles.length === 0) {
    logger.warn('No normalized files found');
    console.log('\n⚠️  No normalized data files found.');
    console.log('   Run: pnpm --filter ingest normalize');
    return;
  }

  pipelineLogger.info('Starting SQLite build', {
    games: normalizedFiles,
  });

  const startTime = Date.now();

  // Load all cards
  const allCards = new Map<GameId, CardCore[]>();

  for (const gameId of normalizedFiles) {
    if (isShuttingDown()) {
      logger.info('Shutdown requested, stopping...');
      break;
    }

    setCurrentOperation(`Loading ${gameId}`);

    const cards = loadNormalizedCards(gameId);

    if (cards.length > 0) {
      allCards.set(gameId, cards);
    }
  }

  if (allCards.size === 0) {
    logger.error('No cards loaded');
    console.log('\n❌ No cards found in normalized data');
    return;
  }

  // Build database
  let db: Database.Database | null = null;

  try {
    db = buildDatabase(allCards);

    // Validate
    if (!validateDatabase(db)) {
      console.log('\n❌ Database validation failed');
      process.exit(1);
    }

    // Generate stats
    const stats = generateStats(db);

    // Calculate checksum
    db.close();
    db = null;

    logger.info('Calculating database checksum...');
    const checksum = calculateFileSha256(OUTPUT_DB);

    // Save stats
    const statsPath = path.join(METADATA_DIR, 'cards.sqlite.stats.json');
    fs.writeFileSync(
      statsPath,
      JSON.stringify(
        {
          ...stats,
          sha256: checksum,
          created_at: new Date().toISOString(),
        },
        null,
        2
      )
    );

    setCurrentOperation(null);

    const duration = Math.round((Date.now() - startTime) / 1000);

    console.log('\n' + '='.repeat(70));
    console.log('SQLITE BUILD COMPLETE');
    console.log('='.repeat(70));
    console.log(`Games: ${normalizedFiles.join(', ')}`);
    console.log(`Total cards: ${stats.total_cards.toLocaleString()}`);

    for (const [game, count] of Object.entries(stats.cards_by_game as Record<string, number>)) {
      console.log(`  ${game}: ${count.toLocaleString()} cards`);
    }

    console.log(`\nDatabase size: ${stats.size_mb} MB`);
    console.log(`SHA256: ${checksum.slice(0, 16)}...`);
    console.log(`Duration: ${duration}s`);
    console.log(`\n📁 Database: ${OUTPUT_DB}`);
    console.log(`📊 Stats: ${statsPath}`);

  } catch (error) {
    logger.error('SQLite build failed', {}, error as Error);

    if (db) {
      try {
        db.close();
      } catch (closeError) {
        // Ignore close errors
      }
    }

    throw error;
  }
}

main().catch(error => {
  logger.error('SQLite build failed', {}, error);
  process.exit(1);
});
