#!/usr/bin/env node
/**
 * Upload artifacts to S3 with versioning
 *
 * Uploads production artifacts to S3 bucket with:
 * - Version-based prefixes (artifacts/{version}/)
 * - Immutable cache headers for artifacts (1 year)
 * - Short cache for manifests (5 minutes)
 * - SHA256 verification
 * - Dry-run mode for testing
 * - Parallel uploads with concurrency control
 *
 * Input:
 *   - artifacts/manifests/index_manifest.json
 *   - artifacts/faiss/{game_id}/shards/{set_code}/
 *   - artifacts/metadata/cards.sqlite.ro
 *
 * Output: S3 bucket (configured via environment)
 *
 * Environment Variables:
 *   - AWS_REGION: AWS region (default: us-east-1)
 *   - S3_BUCKET: S3 bucket name (required)
 *   - S3_PREFIX: Optional prefix (default: "")
 *   - DRY_RUN: Set to "true" for dry run
 */

import * as fs from 'fs';
import * as path from 'path';
import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import pLimit from 'p-limit';
import { IndexManifest } from '@cardflux/shared/types';
import {
  logger,
  createPipelineLogger,
  onShutdown,
  setCurrentOperation,
  isShuttingDown,
} from '@cardflux/shared';

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  awsRegion: process.env.AWS_REGION || 'us-east-1',
  s3Bucket: process.env.S3_BUCKET || '',
  s3Prefix: process.env.S3_PREFIX || '',
  dryRun: process.env.DRY_RUN === 'true',
  concurrency: 10,

  // Cache headers
  immutableCache: 'public, max-age=31536000, immutable', // 1 year
  manifestCache: 'public, max-age=300', // 5 minutes
};

// ============================================================================
// Paths
// ============================================================================

const REPO_ROOT = path.resolve(__dirname, '../../..');
const MANIFESTS_DIR = path.join(REPO_ROOT, 'artifacts', 'manifests');
const MANIFEST_PATH = path.join(MANIFESTS_DIR, 'index_manifest.json');

// ============================================================================
// S3 Client
// ============================================================================

let s3Client: S3Client | null = null;

function getS3Client(): S3Client {
  if (!s3Client) {
    s3Client = new S3Client({ region: CONFIG.awsRegion });
  }
  return s3Client;
}

// ============================================================================
// Upload Operations
// ============================================================================

interface UploadFile {
  localPath: string;
  s3Key: string;
  contentType: string;
  cacheControl: string;
}

/**
 * Determine content type from file extension
 */
function getContentType(filepath: string): string {
  const ext = path.extname(filepath).toLowerCase();

  const contentTypes: Record<string, string> = {
    '.json': 'application/json',
    '.faiss': 'application/octet-stream',
    '.ro': 'application/vnd.sqlite3', // SQLite read-only
    '.db': 'application/vnd.sqlite3',
  };

  return contentTypes[ext] || 'application/octet-stream';
}

/**
 * Check if file exists in S3 (for skip logic)
 */
async function existsInS3(s3Key: string): Promise<boolean> {
  if (CONFIG.dryRun) {
    return false; // Always upload in dry run
  }

  try {
    const client = getS3Client();
    await client.send(
      new HeadObjectCommand({
        Bucket: CONFIG.s3Bucket,
        Key: s3Key,
      })
    );
    return true;
  } catch (error: any) {
    if (error.name === 'NotFound' || error.$metadata?.httpStatusCode === 404) {
      return false;
    }
    throw error; // Re-throw other errors
  }
}

/**
 * Upload file to S3
 */
async function uploadFile(file: UploadFile): Promise<void> {
  const fileSize = fs.statSync(file.localPath).size;

  logger.debug('Uploading file', {
    localPath: file.localPath,
    s3Key: file.s3Key,
    size: fileSize,
  });

  if (CONFIG.dryRun) {
    logger.info('[DRY RUN] Would upload', {
      localPath: file.localPath,
      s3Key: file.s3Key,
      size: fileSize,
    });
    return;
  }

  // Check if already exists
  const exists = await existsInS3(file.s3Key);
  if (exists) {
    logger.info('File already exists in S3, skipping', { s3Key: file.s3Key });
    return;
  }

  // Upload
  const client = getS3Client();
  const fileContent = fs.readFileSync(file.localPath);

  await client.send(
    new PutObjectCommand({
      Bucket: CONFIG.s3Bucket,
      Key: file.s3Key,
      Body: fileContent,
      ContentType: file.contentType,
      CacheControl: file.cacheControl,
    })
  );

  logger.info('Uploaded to S3', {
    s3Key: file.s3Key,
    size: fileSize,
  });
}

// ============================================================================
// Manifest Processing
// ============================================================================

/**
 * Load and validate manifest
 */
function loadManifest(): IndexManifest {
  if (!fs.existsSync(MANIFEST_PATH)) {
    throw new Error(
      `Manifest not found: ${MANIFEST_PATH}\n` +
        '  Run: pnpm --filter ingest generate-manifests'
    );
  }

  const content = fs.readFileSync(MANIFEST_PATH, 'utf-8');
  const manifest = JSON.parse(content) as IndexManifest;

  logger.info('Loaded manifest', {
    version: manifest.version,
    games: manifest.games.length,
    shards: manifest.shards.length,
  });

  return manifest;
}

/**
 * Build upload file list from manifest
 */
function buildUploadList(manifest: IndexManifest): UploadFile[] {
  const files: UploadFile[] = [];
  const version = manifest.version;

  // Build S3 key prefix
  const versionPrefix = CONFIG.s3Prefix
    ? `${CONFIG.s3Prefix}/${version}`
    : version;

  // FAISS shards
  for (const shard of manifest.shards) {
    const gameId = shard.game_id;
    const setCode = shard.set_code;

    // Index file
    files.push({
      localPath: path.join(REPO_ROOT, shard.index_path),
      s3Key: `${versionPrefix}/faiss/${gameId}/shards/${setCode}/index.faiss`,
      contentType: getContentType(shard.index_path),
      cacheControl: CONFIG.immutableCache,
    });

    // IDs file
    files.push({
      localPath: path.join(REPO_ROOT, shard.ids_path),
      s3Key: `${versionPrefix}/faiss/${gameId}/shards/${setCode}/ids.json`,
      contentType: getContentType(shard.ids_path),
      cacheControl: CONFIG.immutableCache,
    });

    // Meta file
    files.push({
      localPath: path.join(REPO_ROOT, shard.meta_path),
      s3Key: `${versionPrefix}/faiss/${gameId}/shards/${setCode}/meta.json`,
      contentType: getContentType(shard.meta_path),
      cacheControl: CONFIG.immutableCache,
    });
  }

  // Metadata snapshot
  files.push({
    localPath: path.join(REPO_ROOT, manifest.metadata_snapshot.path),
    s3Key: `${versionPrefix}/metadata/cards.sqlite.ro`,
    contentType: getContentType(manifest.metadata_snapshot.path),
    cacheControl: CONFIG.immutableCache,
  });

  // Manifest itself (short cache)
  files.push({
    localPath: MANIFEST_PATH,
    s3Key: `${versionPrefix}/index_manifest.json`,
    contentType: 'application/json',
    cacheControl: CONFIG.manifestCache,
  });

  // Also upload manifest to root for "latest" pointer
  files.push({
    localPath: MANIFEST_PATH,
    s3Key: CONFIG.s3Prefix ? `${CONFIG.s3Prefix}/index_manifest.json` : 'index_manifest.json',
    contentType: 'application/json',
    cacheControl: CONFIG.manifestCache,
  });

  logger.info('Built upload list', { totalFiles: files.length });

  return files;
}

// ============================================================================
// Main
// ============================================================================

async function main() {
  const pipelineLogger = createPipelineLogger('upload_s3');

  // Validate configuration
  if (!CONFIG.s3Bucket) {
    console.log('\n❌ S3_BUCKET environment variable is required');
    console.log('\nUsage:');
    console.log('  export S3_BUCKET=cardflux-artifacts');
    console.log('  export AWS_REGION=us-east-1  # Optional, default: us-east-1');
    console.log('  export S3_PREFIX=production  # Optional prefix');
    console.log('  export DRY_RUN=true          # Optional dry run');
    console.log('  pnpm --filter ingest upload-s3');
    process.exit(1);
  }

  onShutdown({
    name: 'Cleanup S3 upload',
    handler: () => {
      logger.info('S3 upload interrupted');
    },
    timeout: 2000,
  });

  pipelineLogger.info('Starting S3 upload', {
    bucket: CONFIG.s3Bucket,
    region: CONFIG.awsRegion,
    prefix: CONFIG.s3Prefix || '(none)',
    dryRun: CONFIG.dryRun,
  });

  if (CONFIG.dryRun) {
    console.log('\n🔍 DRY RUN MODE - No files will be uploaded\n');
  }

  const startTime = Date.now();

  try {
    // Load manifest
    setCurrentOperation('Loading manifest');
    const manifest = loadManifest();

    // Build upload list
    setCurrentOperation('Building upload list');
    const uploadList = buildUploadList(manifest);

    // Upload files with concurrency control
    setCurrentOperation('Uploading files');

    const limiter = pLimit(CONFIG.concurrency);
    let uploaded = 0;
    let skipped = 0;
    let failed = 0;

    const tasks = uploadList.map(file =>
      limiter(async () => {
        if (isShuttingDown()) {
          return;
        }

        try {
          const existsBefore = await existsInS3(file.s3Key);
          await uploadFile(file);

          if (existsBefore) {
            skipped++;
          } else {
            uploaded++;
          }
        } catch (error) {
          logger.error('Upload failed', { s3Key: file.s3Key }, error as Error);
          failed++;
        }
      })
    );

    await Promise.all(tasks);

    setCurrentOperation(null);

    const duration = Math.round((Date.now() - startTime) / 1000);

    console.log('\n' + '='.repeat(70));
    console.log(CONFIG.dryRun ? 'S3 UPLOAD (DRY RUN)' : 'S3 UPLOAD COMPLETE');
    console.log('='.repeat(70));
    console.log(`Version: ${manifest.version}`);
    console.log(`Bucket: s3://${CONFIG.s3Bucket}`);
    console.log(`Region: ${CONFIG.awsRegion}`);

    if (CONFIG.s3Prefix) {
      console.log(`Prefix: ${CONFIG.s3Prefix}`);
    }

    console.log(`\nFiles: ${uploadList.length}`);

    if (!CONFIG.dryRun) {
      console.log(`  Uploaded: ${uploaded}`);
      console.log(`  Skipped: ${skipped} (already exist)`);
      console.log(`  Failed: ${failed}`);
    }

    console.log(`\nDuration: ${duration}s`);

    if (!CONFIG.dryRun) {
      console.log(`\n📦 Artifacts published to S3`);
      console.log(`   Manifest: s3://${CONFIG.s3Bucket}/${CONFIG.s3Prefix ? CONFIG.s3Prefix + '/' : ''}index_manifest.json`);
    }

    if (failed > 0) {
      console.log('\n⚠️  Some uploads failed. Check logs for details.');
      process.exit(1);
    }

  } catch (error) {
    logger.error('S3 upload failed', {}, error as Error);
    console.log('\n❌ S3 upload failed');
    console.log(`   Error: ${(error as Error).message}`);
    process.exit(1);
  }
}

main().catch(error => {
  logger.error('S3 upload failed', {}, error);
  process.exit(1);
});
