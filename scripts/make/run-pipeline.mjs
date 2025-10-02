#!/usr/bin/env node
import { spawn } from 'child_process';
import path from 'path';

const STEPS = [
  { name: 'normalize', cmd: 'pnpm', args: ['--filter', '@cardflux/ingest', 'normalize'] },
  { name: 'images', cmd: 'pnpm', args: ['--filter', '@cardflux/ingest', 'fetch-images'] },
  { name: 'sqlite', cmd: 'pnpm', args: ['--filter', '@cardflux/ingest', 'build-sqlite'] },
  { name: 'embed', cmd: 'pnpm', args: ['--filter', '@cardflux/embedder', 'embed'] },
  { name: 'index', cmd: 'pnpm', args: ['--filter', '@cardflux/indexer', 'build-index'] },
  { name: 'manifests', cmd: 'pnpm', args: ['--filter', '@cardflux/publisher', 'generate-manifests'] },
  { name: 'prices', cmd: 'pnpm', args: ['--filter', '@cardflux/pricefeed', 'build-patch'] },
];

function runStep(step) {
  return new Promise((resolve, reject) => {
    console.log(`\n[${'='.repeat(60)}]`);
    console.log(`Running step: ${step.name}`);
    console.log(`[${'='.repeat(60)}]\n`);

    const proc = spawn(step.cmd, step.args, {
      stdio: 'inherit',
      shell: true,
    });

    proc.on('close', (code) => {
      if (code === 0) {
        console.log(`\nStep ${step.name} completed successfully`);
        resolve();
      } else {
        reject(new Error(`Step ${step.name} failed with code ${code}`));
      }
    });
  });
}

async function runPipeline() {
  const startTime = Date.now();

  console.log('Starting CardFlux pipeline...\n');

  for (const step of STEPS) {
    try {
      await runStep(step);
    } catch (error) {
      console.error(`\nPipeline failed at step: ${step.name}`);
      console.error(error.message);
      process.exit(1);
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);
  console.log(`\n[${'='.repeat(60)}]`);
  console.log(`Pipeline completed successfully in ${duration}s`);
  console.log(`[${'='.repeat(60)}]\n`);
}

runPipeline().catch((error) => {
  console.error('Pipeline error:', error);
  process.exit(1);
});
