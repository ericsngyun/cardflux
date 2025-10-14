#!/usr/bin/env node
/**
 * Generate Index and Model Manifests
 *
 * Scans built artifacts and generates validated manifests:
 * - IndexManifest: References to FAISS shards, SQLite DB, model manifest
 * - Calculates SHA256 checksums for integrity verification
 * - Validates against Zod schemas
 * - Outputs version-stamped manifests
 *
 * Input:
 *   - artifacts/faiss/{game_id}/shards/{set_code}/
 *   - artifacts/metadata/cards.sqlite.ro
 *
 * Output:
 *   - artifacts/manifests/index_manifest.json
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { GameId, IndexManifest, IndexShardEntry } from '@cardflux/shared/types';
import { IndexManifestSchema } from '@cardflux/shared/schemas';
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

const REPO_ROOT = path.resolve(__dirname, '../../..');
const FAISS_DIR = path.join(REPO_ROOT, 'artifacts', 'faiss');
const METADATA_DIR = path.join(REPO_ROOT, 'artifacts', 'metadata');
const MANIFESTS_DIR = path.join(REPO_ROOT, 'artifacts', 'manifests');

// ============================================================================
// Utilities
// ============================================================================

/**
 * Calculate SHA256 of file
 */
function calculateFileSha256(filepath: string): string {
  const content = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Convert Windows path to POSIX for manifests
 */
function toPosixPath(filepath: string): string {
  const relativePath = path.relative(REPO_ROOT, filepath);
  return relativePath.split(path.sep).join('/');
}

/**
 * Get file size
 */
function getFileSize(filepath: string): number {
  return fs.statSync(filepath).size;
}

// ============================================================================
// FAISS Shard Discovery
// ============================================================================

interface ShardFiles {
  indexPath: string;
  idsPath: string;
  metaPath: string;
  gameId: GameId;
  setCode: string;
}

/**
 * Find all FAISS shards
 */
function discoverFaissShards(): ShardFiles[] {
  const shards: ShardFiles[] = [];

  if (!fs.existsSync(FAISS_DIR)) {
    logger.warn('FAISS directory not found', { path: FAISS_DIR });
    return shards;
  }

  // Scan artifacts/faiss/{game_id}/shards/{set_code}/
  const gameDirs = fs.readdirSync(FAISS_DIR, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name as GameId);

  for (const gameId of gameDirs) {
    const shardsDir = path.join(FAISS_DIR, gameId, 'shards');

    if (!fs.existsSync(shardsDir)) {
      logger.debug('No shards directory', { gameId });
      continue;
    }

    const setDirs = fs.readdirSync(shardsDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    for (const setCode of setDirs) {
      const setDir = path.join(shardsDir, setCode);
      const indexPath = path.join(setDir, 'index.faiss');
      const idsPath = path.join(setDir, 'ids.json');
      const metaPath = path.join(setDir, 'meta.json');

      // Validate all required files exist
      if (!fs.existsSync(indexPath) || !fs.existsSync(idsPath) || !fs.existsSync(metaPath)) {
        logger.warn('Incomplete shard', { gameId, setCode, setDir });
        continue;
      }

      shards.push({
        indexPath,
        idsPath,
        metaPath,
        gameId,
        setCode,
      });
    }
  }

  logger.info('Discovered FAISS shards', { count: shards.length });

  return shards;
}

/**
 * Build shard entry with checksums
 */
function buildShardEntry(shard: ShardFiles): IndexShardEntry {
  logger.debug('Processing shard', { gameId: shard.gameId, setCode: shard.setCode });

  // Calculate checksums
  const indexSha256 = calculateFileSha256(shard.indexPath);
  const idsSha256 = calculateFileSha256(shard.idsPath);
  const metaSha256 = calculateFileSha256(shard.metaPath);

  // Load meta.json to get vector count
  const meta = JSON.parse(fs.readFileSync(shard.metaPath, 'utf-8'));
  const vectorCount = meta.vector_count || 0;

  return {
    game_id: shard.gameId,
    set_code: shard.setCode,
    index_path: toPosixPath(shard.indexPath),
    ids_path: toPosixPath(shard.idsPath),
    meta_path: toPosixPath(shard.metaPath),
    index_sha256: indexSha256,
    ids_sha256: idsSha256,
    meta_sha256: metaSha256,
    vector_count: vectorCount,
  };
}

// ============================================================================
// Metadata Discovery
// ============================================================================

/**
 * Find metadata snapshot (SQLite database)
 */
function discoverMetadataSnapshot(): { path: string; sha256: string; size_bytes: number } | null {
  const dbPath = path.join(METADATA_DIR, 'cards.sqlite.ro');

  if (!fs.existsSync(dbPath)) {
    logger.warn('Metadata snapshot not found', { path: dbPath });
    return null;
  }

  return {
    path: toPosixPath(dbPath),
    sha256: calculateFileSha256(dbPath),
    size_bytes: getFileSize(dbPath),
  };
}

// ============================================================================
// Manifest Generation
// ============================================================================

/**
 * Generate version string (vYYYY.MM format)
 */
function generateVersion(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `v${year}.${month}`;
}

/**
 * Generate index manifest
 */
function generateIndexManifest(): IndexManifest {
  logger.info('Generating index manifest...');

  setCurrentOperation('Discovering artifacts');

  // Discover shards
  const shardFiles = discoverFaissShards();

  if (shardFiles.length === 0) {
    throw new Error('No FAISS shards found. Run: python services/indexer/bin/build_faiss.py');
  }

  // Build shard entries
  const shards: IndexShardEntry[] = [];

  for (const shard of shardFiles) {
    if (isShuttingDown()) {
      break;
    }

    const entry = buildShardEntry(shard);
    shards.push(entry);
  }

  // Discover metadata
  const metadataSnapshot = discoverMetadataSnapshot();

  if (!metadataSnapshot) {
    throw new Error('Metadata snapshot not found. Run: pnpm --filter ingest build-sqlite');
  }

  // Extract unique games
  const games = Array.from(new Set(shards.map(s => s.game_id))).sort();

  // Build manifest
  const manifest: IndexManifest = {
    schema_version: '1.0.0',
    version: generateVersion(),
    created_at: new Date().toISOString(),
    games,
    shards,
    metadata_snapshot: metadataSnapshot,
    models_manifest: {
      path: 'artifacts/models/model_manifest.json',
      sha256: '0000000000000000000000000000000000000000000000000000000000000000', // Placeholder
    },
  };

  logger.info('Index manifest generated', {
    games: manifest.games.length,
    shards: manifest.shards.length,
    version: manifest.version,
  });

  return manifest;
}

/**
 * Validate manifest against Zod schema
 */
function validateManifest(manifest: IndexManifest): void {
  logger.info('Validating manifest with Zod...');

  try {
    IndexManifestSchema.parse(manifest);
    logger.info('✅ Manifest validation passed');
  } catch (error: any) {
    logger.error('❌ Manifest validation failed', {}, error);
    throw new Error(`Manifest validation failed: ${error.message}`);
  }
}

/**
 * Save manifest to disk
 */
function saveManifest(manifest: IndexManifest): string {
  fs.mkdirSync(MANIFESTS_DIR, { recursive: true });

  const manifestPath = path.join(MANIFESTS_DIR, 'index_manifest.json');

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  logger.info('Manifest saved', { path: manifestPath });

  return manifestPath;
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('generate_manifests');

  onShutdown({
    name: 'Cleanup manifest generation',
    handler: () => {
      logger.info('Manifest generation interrupted');
    },
    timeout: 1000,
  });

  pipelineLogger.info('Starting manifest generation');

  const startTime = Date.now();

  try {
    // Generate manifest
    const manifest = generateIndexManifest();

    // Validate
    validateManifest(manifest);

    // Save
    const manifestPath = saveManifest(manifest);

    setCurrentOperation(null);

    const duration = Math.round((Date.now() - startTime) / 1000);

    console.log('\n' + '='.repeat(70));
    console.log('MANIFEST GENERATION COMPLETE');
    console.log('='.repeat(70));
    console.log(`Version: ${manifest.version}`);
    console.log(`Games: ${manifest.games.join(', ')}`);
    console.log(`Shards: ${manifest.shards.length}`);
    console.log(`Metadata: ${manifest.metadata_snapshot.path}`);
    console.log(`Metadata SHA256: ${manifest.metadata_snapshot.sha256.slice(0, 16)}...`);
    console.log(`Duration: ${duration}s`);
    console.log(`\n📁 Manifest: ${manifestPath}`);

    // Summary stats
    const totalVectors = manifest.shards.reduce((sum, s) => sum + s.vector_count, 0);
    console.log(`\n📊 Stats:`);
    console.log(`  Total vectors: ${totalVectors.toLocaleString()}`);

    for (const game of manifest.games) {
      const gameShards = manifest.shards.filter(s => s.game_id === game);
      const gameVectors = gameShards.reduce((sum, s) => sum + s.vector_count, 0);
      console.log(`  ${game}: ${gameShards.length} shards, ${gameVectors.toLocaleString()} vectors`);
    }

  } catch (error) {
    logger.error('Manifest generation failed', {}, error as Error);
    console.log('\n❌ Manifest generation failed');
    console.log(`   Error: ${(error as Error).message}`);
    process.exit(1);
  }
}

main().catch(error => {
  logger.error('Manifest generation failed', {}, error);
  process.exit(1);
});
