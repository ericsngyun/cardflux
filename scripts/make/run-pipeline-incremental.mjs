#!/usr/bin/env node
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STATE_DIR = path.resolve(__dirname, '../../data/state');
const STATE_FILE = path.join(STATE_DIR, 'incremental-pipeline.state.json');

const STEPS = [
  { name: 'normalize', cmd: 'pnpm', args: ['pipeline:normalize:incremental'] },
  { name: 'images', cmd: 'pnpm', args: ['pipeline:fetch-images:incremental'] },
  { name: 'sqlite', cmd: 'pnpm', args: ['pipeline:metadata'] },
  { name: 'embed', cmd: 'pnpm', args: ['pipeline:embed:incremental'] },
  { name: 'index', cmd: 'pnpm', args: ['pipeline:index'] },
  { name: 'manifests', cmd: 'pnpm', args: ['pipeline:manifests'] },
];

// Load pipeline state
function loadState() {
  if (!fs.existsSync(STATE_FILE)) {
    return { completedSteps: [], lastRun: null };
  }

  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
  } catch (error) {
    console.warn('⚠️  Failed to load pipeline state, starting fresh');
    return { completedSteps: [], lastRun: null };
  }
}

// Save pipeline state
function saveState(state) {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// Create checkpoint before each step
function createCheckpoint(stepName, completedSteps) {
  const checkpoint = {
    step: stepName,
    completedSteps,
    timestamp: new Date().toISOString(),
  };

  const checkpointFile = path.join(STATE_DIR, `checkpoint-${stepName}.json`);
  fs.writeFileSync(checkpointFile, JSON.stringify(checkpoint, null, 2));
}

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
        console.log(`\n✓ Step ${step.name} completed successfully`);
        resolve();
      } else {
        reject(new Error(`Step ${step.name} failed with code ${code}`));
      }
    });

    // Handle pipeline interruption
    process.on('SIGINT', () => {
      console.log(`\n\n⚠️  Pipeline interrupted during: ${step.name}`);
      console.log('State has been saved. Resume with: pnpm pipeline:update\n');
      proc.kill('SIGTERM');
      process.exit(130);
    });
  });
}

async function runPipeline() {
  const startTime = Date.now();
  const state = loadState();

  console.log('Starting CardFlux INCREMENTAL pipeline...\n');

  if (state.completedSteps.length > 0) {
    console.log('📋 Resuming from previous run:');
    console.log(`   Completed steps: ${state.completedSteps.join(', ')}`);
    console.log(`   Last run: ${state.lastRun}\n`);
  }

  const completedSteps = [...state.completedSteps];

  for (const step of STEPS) {
    // Skip already completed steps
    if (completedSteps.includes(step.name)) {
      console.log(`⏭️  Skipping ${step.name} (already completed)\n`);
      continue;
    }

    try {
      // Create checkpoint before running step
      createCheckpoint(step.name, completedSteps);

      await runStep(step);

      // Mark step as completed
      completedSteps.push(step.name);
      saveState({
        completedSteps,
        lastRun: new Date().toISOString(),
        lastCompletedStep: step.name,
      });

    } catch (error) {
      console.error(`\n❌ Pipeline failed at step: ${step.name}`);
      console.error(`   Error: ${error.message}`);

      // Save failure state
      saveState({
        completedSteps,
        lastRun: new Date().toISOString(),
        failedStep: step.name,
        error: error.message,
      });

      console.error('\n📌 State saved. To resume, run: pnpm pipeline:update\n');
      process.exit(1);
    }
  }

  const duration = Math.round((Date.now() - startTime) / 1000);

  // Clean up state file on successful completion
  if (fs.existsSync(STATE_FILE)) {
    fs.unlinkSync(STATE_FILE);
  }

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
