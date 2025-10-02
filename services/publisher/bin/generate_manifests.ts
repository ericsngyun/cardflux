#!/usr/bin/env node
import * as fs from 'fs';
import * as path from 'path';
import { getAllGames } from '@cardflux/config';

const FAISS_DIR = path.resolve(__dirname, '../../../artifacts/faiss');
const MANIFESTS_DIR = path.resolve(__dirname, '../../../artifacts/manifests');
const METADATA_DIR = path.resolve(__dirname, '../../../artifacts/metadata');

interface Manifest {
  version: string;
  game: string;
  timestamp: string;
  files: {
    index: {
      path: string;
      size: number;
      checksum: string;
    };
    metadata: {
      path: string;
      size: number;
      checksum: string;
    };
    sqlite?: {
      path: string;
      size: number;
      checksum: string;
    };
  };
  stats: {
    totalCards: number;
    dimension: number;
  };
}

function getFileSize(filepath: string): number {
  return fs.statSync(filepath).size;
}

function generateChecksum(filepath: string): string {
  const crypto = require('crypto');
  const data = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(data).digest('hex');
}

function countLines(filepath: string): number {
  const content = fs.readFileSync(filepath, 'utf-8');
  return content.split('\n').filter(Boolean).length;
}

function generateManifestForGame(gameSlug: string, version: string): Manifest {
  const gameFaissDir = path.join(FAISS_DIR, gameSlug);
  const indexPath = path.join(gameFaissDir, 'index.faiss');
  const metadataPath = path.join(gameFaissDir, 'metadata.jsonl');
  const sqlitePath = path.join(METADATA_DIR, 'cards.db');

  const totalCards = countLines(metadataPath);

  const manifest: Manifest = {
    version,
    game: gameSlug,
    timestamp: new Date().toISOString(),
    files: {
      index: {
        path: `faiss/${gameSlug}/index.faiss`,
        size: getFileSize(indexPath),
        checksum: generateChecksum(indexPath),
      },
      metadata: {
        path: `faiss/${gameSlug}/metadata.jsonl`,
        size: getFileSize(metadataPath),
        checksum: generateChecksum(metadataPath),
      },
    },
    stats: {
      totalCards,
      dimension: 512, // CLIP dimension
    },
  };

  if (fs.existsSync(sqlitePath)) {
    manifest.files.sqlite = {
      path: 'metadata/cards.db',
      size: getFileSize(sqlitePath),
      checksum: generateChecksum(sqlitePath),
    };
  }

  return manifest;
}

function main() {
  const version = process.env.VERSION || '0.1.0';

  fs.mkdirSync(MANIFESTS_DIR, { recursive: true });

  const games = getAllGames();
  const manifests: Record<string, Manifest> = {};

  for (const game of games) {
    const gameFaissDir = path.join(FAISS_DIR, game.slug);

    if (!fs.existsSync(gameFaissDir)) {
      console.log(`No FAISS index found for ${game.slug}, skipping...`);
      continue;
    }

    console.log(`Generating manifest for ${game.slug}...`);
    const manifest = generateManifestForGame(game.slug, version);
    manifests[game.slug] = manifest;

    // Save individual manifest
    const manifestPath = path.join(MANIFESTS_DIR, `${game.slug}.json`);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log(`Saved manifest to ${manifestPath}`);
  }

  // Save combined manifest
  const combinedManifestPath = path.join(MANIFESTS_DIR, 'manifest.json');
  fs.writeFileSync(combinedManifestPath, JSON.stringify(manifests, null, 2));
  console.log(`\nSaved combined manifest to ${combinedManifestPath}`);
}

main();
