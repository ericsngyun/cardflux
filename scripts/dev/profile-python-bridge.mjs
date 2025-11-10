#!/usr/bin/env node
/**
 * Python Bridge Performance Profiler
 *
 * Measures detailed timing of:
 * - Process spawn time
 * - Initialization time (model loading, FAISS loading)
 * - First identification time (cold start)
 * - Subsequent identification time (warm)
 * - Memory usage over time
 * - Response parsing overhead
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = join(__dirname, '../..');

// Test image paths
const TEST_IMAGES = [
  join(PROJECT_ROOT, 'test-images/one-piece/blackbeard.png'),
  join(PROJECT_ROOT, 'test-images/one-piece/bege.png'),
  join(PROJECT_ROOT, 'test-images/one-piece/mihawk.png'),
  join(PROJECT_ROOT, 'test-images/one-piece/yellow_event.png'),
];

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function formatTime(ms) {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

class PythonBridgeProfiler {
  constructor() {
    this.process = null;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.buffer = '';
    this.timings = {
      spawn: 0,
      initialize: 0,
      firstIdentify: 0,
      subsequentIdentify: [],
      totalTime: 0,
    };
    this.memorySnapshots = [];
  }

  async start() {
    const startTime = Date.now();

    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    log('║          PYTHON BRIDGE PERFORMANCE PROFILER              ║', 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    log('\n📊 Phase 1: Process Spawn', 'bright');
    const spawnStart = Date.now();

    return new Promise((resolve, reject) => {
      try {
        // Find Python executable and script
        const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
        const scriptPath = join(PROJECT_ROOT, 'apps/desktop/src/python/identification_service.py');

        if (!fs.existsSync(scriptPath)) {
          throw new Error(`Script not found: ${scriptPath}`);
        }

        log(`   Python: ${pythonPath}`, 'blue');
        log(`   Script: ${scriptPath}`, 'blue');

        this.process = spawn(pythonPath, [scriptPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: PROJECT_ROOT,
        });

        const spawnEnd = Date.now();
        this.timings.spawn = spawnEnd - spawnStart;
        log(`   ✓ Process spawned in ${formatTime(this.timings.spawn)}`, 'green');

        // Track memory
        this.startMemoryTracking();

        // Handle stdout
        this.process.stdout.on('data', (data) => this.handleStdout(data));

        // Handle stderr (Python logs)
        this.process.stderr.on('data', (data) => {
          const msg = data.toString().trim();
          if (msg.includes('[PY]')) {
            log(`   ${msg}`, 'yellow');
          }
        });

        // Handle exit
        this.process.on('exit', (code) => {
          log(`\n⚠️  Process exited with code ${code}`, 'red');
        });

        this.process.on('error', (error) => {
          log(`\n❌ Process error: ${error.message}`, 'red');
          reject(error);
        });

        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }

  startMemoryTracking() {
    // Take memory snapshot every 500ms
    this.memoryInterval = setInterval(() => {
      if (this.process && this.process.pid) {
        const usage = process.memoryUsage();
        this.memorySnapshots.push({
          timestamp: Date.now(),
          rss: usage.rss,
          heapUsed: usage.heapUsed,
          heapTotal: usage.heapTotal,
        });
      }
    }, 500);
  }

  async initialize() {
    log('\n📊 Phase 2: Initialization (Model + FAISS Loading)', 'bright');
    const initStart = Date.now();

    try {
      const result = await this.sendRequest('initialize', { game: 'one-piece' });
      const initEnd = Date.now();
      this.timings.initialize = initEnd - initStart;

      log(`   ✓ Initialized in ${formatTime(this.timings.initialize)}`, 'green');

      // Break down initialization time
      if (result && result.timing) {
        log('   \n   Breakdown:', 'cyan');
        Object.entries(result.timing).forEach(([key, value]) => {
          log(`     • ${key}: ${formatTime(value * 1000)}`, 'blue');
        });
      }

      return result;
    } catch (error) {
      log(`   ❌ Initialization failed: ${error.message}`, 'red');
      throw error;
    }
  }

  async runIdentificationTests() {
    log('\n📊 Phase 3: Identification Performance', 'bright');

    // Test 1: First identification (cold)
    log('\n   Test 1: First Identification (Cold Start)', 'cyan');
    const firstStart = Date.now();

    try {
      const result = await this.identifyCard(TEST_IMAGES[0]);
      const firstEnd = Date.now();
      this.timings.firstIdentify = firstEnd - firstStart;

      log(`   ✓ First identification: ${formatTime(this.timings.firstIdentify)}`, 'green');

      if (result && result.timing) {
        log('   \n   Breakdown:', 'cyan');
        Object.entries(result.timing).forEach(([key, value]) => {
          log(`     • ${key}: ${formatTime(value * 1000)}`, 'blue');
        });
      }

      log(`   \n   Result: ${result.card?.name || 'Unknown'} (${result.confidence})`, 'magenta');
    } catch (error) {
      log(`   ❌ First identification failed: ${error.message}`, 'red');
      throw error;
    }

    // Test 2: Subsequent identifications (warm)
    log('\n   Test 2: Subsequent Identifications (Warm)', 'cyan');

    for (let i = 0; i < TEST_IMAGES.length; i++) {
      const testStart = Date.now();

      try {
        const result = await this.identifyCard(TEST_IMAGES[i]);
        const testEnd = Date.now();
        const elapsed = testEnd - testStart;
        this.timings.subsequentIdentify.push(elapsed);

        log(`   ✓ Test ${i + 1}: ${formatTime(elapsed)} - ${result.card?.name || 'Unknown'}`, 'green');
      } catch (error) {
        log(`   ❌ Test ${i + 1} failed: ${error.message}`, 'red');
      }
    }

    // Test 3: Rapid fire (10 identifications)
    log('\n   Test 3: Rapid Fire (10 identifications)', 'cyan');
    const rapidStart = Date.now();
    const rapidPromises = [];

    for (let i = 0; i < 10; i++) {
      const imageIndex = i % TEST_IMAGES.length;
      rapidPromises.push(this.identifyCard(TEST_IMAGES[imageIndex]));
    }

    try {
      await Promise.all(rapidPromises);
      const rapidEnd = Date.now();
      const rapidTotal = rapidEnd - rapidStart;
      const rapidAvg = rapidTotal / 10;

      log(`   ✓ Completed 10 identifications in ${formatTime(rapidTotal)}`, 'green');
      log(`   ✓ Average: ${formatTime(rapidAvg)} per identification`, 'green');
    } catch (error) {
      log(`   ❌ Rapid fire test failed: ${error.message}`, 'red');
    }
  }

  async identifyCard(imagePath) {
    return this.sendRequest('identify', {
      image_path: imagePath,
      top_k: 50,
      use_geometric: true,
      skip_ocr: true,  // Skip OCR for speed testing
      skip_foil: true, // Skip foil for speed testing
    });
  }

  async sendRequest(method, params) {
    return new Promise((resolve, reject) => {
      const id = ++this.requestId;

      const request = {
        jsonrpc: '2.0',
        id,
        method,
        params,
      };

      const timeout = method === 'initialize' ? 120000 : 30000;
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request timeout: ${method}`));
      }, timeout);

      this.pendingRequests.set(id, { resolve, reject, timer, method });

      const requestJson = JSON.stringify(request) + '\n';
      this.process.stdin.write(requestJson);
    });
  }

  handleStdout(data) {
    const chunk = data.toString();
    this.buffer += chunk;

    let newlineIndex;
    while ((newlineIndex = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, newlineIndex).trim();
      this.buffer = this.buffer.slice(newlineIndex + 1);

      if (line) {
        try {
          const response = JSON.parse(line);
          this.handleResponse(response);
        } catch (error) {
          // Ignore parse errors (might be partial data)
        }
      }
    }
  }

  handleResponse(response) {
    const { id, result, error } = response;
    const pending = this.pendingRequests.get(id);

    if (!pending) return;

    clearTimeout(pending.timer);
    this.pendingRequests.delete(id);

    if (error) {
      pending.reject(new Error(error.message));
    } else {
      pending.resolve(result);
    }
  }

  printSummary() {
    const totalTime = this.timings.spawn + this.timings.initialize + this.timings.firstIdentify;

    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    log('║                    PERFORMANCE SUMMARY                     ║', 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    log('\n⏱️  Timing Breakdown:', 'bright');
    log(`   Process Spawn:        ${formatTime(this.timings.spawn)}`, 'blue');
    log(`   Initialization:       ${formatTime(this.timings.initialize)}`, 'blue');
    log(`   First Identification: ${formatTime(this.timings.firstIdentify)}`, 'blue');
    log(`   ${'─'.repeat(40)}`);
    log(`   Total Cold Start:     ${formatTime(totalTime)}`, 'green');

    if (this.timings.subsequentIdentify.length > 0) {
      const avg = this.timings.subsequentIdentify.reduce((a, b) => a + b, 0) / this.timings.subsequentIdentify.length;
      const min = Math.min(...this.timings.subsequentIdentify);
      const max = Math.max(...this.timings.subsequentIdentify);

      log('\n🔥 Warm Performance:', 'bright');
      log(`   Average:  ${formatTime(avg)}`, 'green');
      log(`   Min:      ${formatTime(min)}`, 'green');
      log(`   Max:      ${formatTime(max)}`, 'green');
    }

    // Memory analysis
    if (this.memorySnapshots.length > 0) {
      const avgRss = this.memorySnapshots.reduce((sum, s) => sum + s.rss, 0) / this.memorySnapshots.length;
      const maxRss = Math.max(...this.memorySnapshots.map(s => s.rss));
      const avgHeap = this.memorySnapshots.reduce((sum, s) => sum + s.heapUsed, 0) / this.memorySnapshots.length;

      log('\n💾 Memory Usage:', 'bright');
      log(`   Average RSS:  ${formatBytes(avgRss)}`, 'blue');
      log(`   Peak RSS:     ${formatBytes(maxRss)}`, 'blue');
      log(`   Average Heap: ${formatBytes(avgHeap)}`, 'blue');
    }

    // Bottleneck analysis
    log('\n🎯 Bottleneck Analysis:', 'bright');

    const bottlenecks = [];

    if (this.timings.spawn > 500) {
      bottlenecks.push({
        phase: 'Process Spawn',
        time: this.timings.spawn,
        severity: this.timings.spawn > 1000 ? '🔴 CRITICAL' : '🟡 MEDIUM',
        recommendation: 'Consider persistent worker pool',
      });
    }

    if (this.timings.initialize > 10000) {
      bottlenecks.push({
        phase: 'Initialization',
        time: this.timings.initialize,
        severity: this.timings.initialize > 30000 ? '🔴 CRITICAL' : '🟡 MEDIUM',
        recommendation: 'Preload models on app startup, cache FAISS index',
      });
    }

    if (this.timings.firstIdentify > 3000) {
      bottlenecks.push({
        phase: 'First Identification',
        time: this.timings.firstIdentify,
        severity: this.timings.firstIdentify > 5000 ? '🔴 CRITICAL' : '🟡 MEDIUM',
        recommendation: 'Warm up model with dummy inference after init',
      });
    }

    if (bottlenecks.length > 0) {
      bottlenecks.forEach(b => {
        log(`\n   ${b.severity} ${b.phase}: ${formatTime(b.time)}`, 'yellow');
        log(`      → ${b.recommendation}`, 'cyan');
      });
    } else {
      log('   ✓ No significant bottlenecks detected', 'green');
    }

    // Target vs Actual
    log('\n📊 Target vs Actual:', 'bright');
    const targets = [
      { name: 'Total Cold Start', target: 5000, actual: totalTime },
      { name: 'Warm Identification', target: 200, actual: this.timings.subsequentIdentify[0] || 0 },
    ];

    targets.forEach(t => {
      const status = t.actual <= t.target ? '✓' : '✗';
      const color = t.actual <= t.target ? 'green' : 'red';
      log(`   ${status} ${t.name}: ${formatTime(t.actual)} (target: ${formatTime(t.target)})`, color);
    });

    log('');
  }

  async cleanup() {
    if (this.memoryInterval) {
      clearInterval(this.memoryInterval);
    }

    if (this.process) {
      this.process.kill('SIGTERM');
    }
  }
}

async function main() {
  const profiler = new PythonBridgeProfiler();

  try {
    // Phase 1: Start process
    await profiler.start();

    // Phase 2: Initialize
    await profiler.initialize();

    // Phase 3: Run identification tests
    await profiler.runIdentificationTests();

    // Print summary
    profiler.printSummary();

  } catch (error) {
    log(`\n❌ Profiling failed: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  } finally {
    await profiler.cleanup();
    process.exit(0);
  }
}

main();
