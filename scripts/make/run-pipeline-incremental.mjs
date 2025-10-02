#!/usr/bin/env node
import { spawn } from 'child_process';

const STEPS = [
  { name: 'normalize (incremental)', cmd: 'pnpm', args: ['pipeline:normalize:incremental'] },
  { name: 'images (incremental)', cmd: 'pnpm', args: ['pipeline:fetch-images:incremental'] },
  { name: 'sqlite', cmd: 'pnpm', args: ['pipeline:metadata'] },
  { name: 'embed (incremental)', cmd: 'pnpm', args: ['pipeline:embed:incremental'] },
  { name: 'index', cmd: 'pnpm', args: ['pipeline:index'] },
  { name: 'manifests', cmd: 'pnpm', args: ['pipeline:manifests'] },
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

  console.log('Starting CardFlux INCREMENTAL pipeline...\n');

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
  console.log(`✓ INCREMENTAL PIPELINE COMPLETED in ${duration}s`);
  console.log(`[${'='.repeat(60)}]\n`);
  console.log('This was an incremental update - only new/changed data was processed.');
  console.log('For a full rebuild, use: pnpm pipeline:all\n');
}

runPipeline().catch((error) => {
  console.error('Pipeline error:', error);
  process.exit(1);
});
