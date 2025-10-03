#!/usr/bin/env node
/**
 * Complete local development pipeline
 * Runs entire pipeline locally for testing
 */

import { spawn } from 'child_process';

const STEPS = [
  {
    name: 'Scrape TCGplayer (test mode)',
    cmd: 'node',
    args: ['scripts/dev/test-scraper.mjs'],
    description: 'Fetch card data from tcgcsv.com (limited)',
  },
  {
    name: 'Validate data',
    cmd: 'tsx',
    args: ['services/ingest/bin/validate-data.ts'],
    description: 'Check data quality and integrity',
  },
  {
    name: 'Build database',
    cmd: 'pnpm',
    args: ['tcgplayer:db'],
    description: 'Create SQLite with prices',
  },
  {
    name: 'Fetch images',
    cmd: 'tsx',
    args: ['services/ingest/bin/fetch_images_incremental.ts'],
    description: 'Download card images',
  },
  {
    name: 'Generate embeddings',
    cmd: 'python',
    args: ['services/embedder/bin/embed_cards_incremental.py'],
    description: 'Create CLIP embeddings',
  },
  {
    name: 'Build FAISS index',
    cmd: 'python',
    args: ['services/indexer/bin/build_faiss.py'],
    description: 'Create search index',
  },
  {
    name: 'Generate manifests',
    cmd: 'tsx',
    args: ['services/publisher/bin/generate_manifests.ts'],
    description: 'Create version manifests',
  },
];

function runStep(step) {
  return new Promise((resolve, reject) => {
    console.log(`\n[${'='.repeat(60)}]`);
    console.log(`Step: ${step.name}`);
    console.log(`Description: ${step.description}`);
    console.log(`[${'='.repeat(60)}]\n`);

    const proc = spawn(step.cmd, step.args, {
      stdio: 'inherit',
      shell: true,
    });

    proc.on('close', (code) => {
      if (code === 0) {
        console.log(`\n✅ ${step.name} completed`);
        resolve();
      } else {
        reject(new Error(`${step.name} failed with code ${code}`));
      }
    });
  });
}

async function runPipeline() {
  const startTime = Date.now();

  console.log('🚀 Starting LOCAL DEVELOPMENT PIPELINE\n');
  console.log('This will run the entire pipeline locally for testing.');
  console.log('Using limited data to speed up development.\n');

  for (const step of STEPS) {
    try {
      await runStep(step);
    } catch (error) {
      console.error(`\n❌ Pipeline failed at: ${step.name}`);
      console.error(error.message);
      console.error('\nTroubleshooting:');
      console.error('1. Check logs above for specific error');
      console.error('2. Ensure Python dependencies installed');
      console.error('3. Verify network connectivity');
      console.error('4. Run individual step: pnpm dev:validate\n');
      process.exit(1);
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);

  console.log(`\n[${'='.repeat(60)}]`);
  console.log(`✅ LOCAL PIPELINE COMPLETED in ${duration}s`);
  console.log(`[${'='.repeat(60)}]`);
  console.log('\n📁 Output files:');
  console.log('  - data/curated/*.jsonl (card data)');
  console.log('  - artifacts/metadata/cards.db (database)');
  console.log('  - artifacts/faiss/*/index.faiss (search indices)');
  console.log('  - artifacts/manifests/*.json (version info)');
  console.log('\n🎯 Next steps:');
  console.log('  - Test desktop app: cd apps/desktop && pnpm dev');
  console.log('  - Run full scrape: pnpm tcgplayer:scrape');
  console.log('  - Deploy to cloud: See TCGPLAYER_MIGRATION.md\n');
}

runPipeline().catch((error) => {
  console.error('Pipeline error:', error);
  process.exit(1);
});
