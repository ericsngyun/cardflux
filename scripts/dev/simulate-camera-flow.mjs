#!/usr/bin/env node
/**
 * Camera Flow Simulator
 *
 * Simulates the complete camera → detection → identification flow:
 * 1. Camera captures frame
 * 2. Card detection checks quality
 * 3. When ready, triggers identification
 * 4. Measures end-to-end latency
 *
 * This tests the REAL user experience flow.
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
];

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

class CameraFlowSimulator {
  constructor(useOptimized = true) {
    this.process = null;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.buffer = '';
    this.useOptimized = useOptimized;
    this.flowResults = [];
  }

  async start() {
    const scriptName = this.useOptimized
      ? 'optimized_identification_service.py'
      : 'identification_service.py';

    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    log(`║          CAMERA FLOW SIMULATOR (${this.useOptimized ? 'OPTIMIZED' : 'BASELINE'})              ║`, 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    log(`\n🎥 Simulating real-world camera identification flow`, 'bright');
    log(`   Using: ${scriptName}`, 'blue');

    return new Promise((resolve, reject) => {
      try {
        const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
        const scriptPath = join(PROJECT_ROOT, `apps/desktop/src/python/${scriptName}`);

        if (!fs.existsSync(scriptPath)) {
          throw new Error(`Script not found: ${scriptPath}`);
        }

        this.process = spawn(pythonPath, [scriptPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          cwd: PROJECT_ROOT,
        });

        this.process.stdout.on('data', (data) => this.handleStdout(data));
        this.process.stderr.on('data', (data) => {
          const msg = data.toString().trim();
          if (msg.includes('[PY')) {
            log(`   ${msg}`, 'yellow');
          }
        });

        this.process.on('exit', (code) => {
          log(`\n⚠️  Process exited with code ${code}`, 'red');
        });

        this.process.on('error', (error) => {
          reject(error);
        });

        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }

  async initialize() {
    log('\n📊 Phase 1: Service Initialization', 'bright');
    const initStart = Date.now();

    try {
      const result = await this.sendRequest('initialize', { game: 'one-piece' });
      const initEnd = Date.now();
      const initTime = initEnd - initStart;

      log(`   ✓ Initialized in ${formatTime(initTime)}`, 'green');

      if (result.timing) {
        log('   \n   Breakdown:', 'cyan');
        log(`     • Load Identifier: ${formatTime(result.timing.load_identifier_ms)}`, 'blue');
        log(`     • Load Detector: ${formatTime(result.timing.load_detector_ms)}`, 'blue');
        log(`     • Model Warmup: ${formatTime(result.timing.warmup_ms)}`, 'blue');

        if (result.warmup) {
          log(`\n     Warmup Details:`, 'cyan');
          log(`       - Inferences: ${result.warmup.num_warmup_inferences}`, 'blue');
          log(`       - First: ${formatTime(result.warmup.first_warmup_ms)}`, 'blue');
          if (result.warmup.second_warmup_ms) {
            log(`       - Second: ${formatTime(result.warmup.second_warmup_ms)}`, 'blue');
          }
          log(`       - Average: ${formatTime(result.warmup.avg_warmup_time_ms)}`, 'blue');
        }
      }

      return result;
    } catch (error) {
      log(`   ❌ Initialization failed: ${error.message}`, 'red');
      throw error;
    }
  }

  async simulateCameraFlow(imagePath, testNumber) {
    log(`\n🎬 Flow ${testNumber}: Simulating Camera Capture → Detection → Identification`, 'bright');
    log(`   Image: ${imagePath.split('/').pop()}`, 'blue');

    const flowStart = Date.now();
    const flow = {
      image: imagePath.split('/').pop(),
      steps: [],
    };

    try {
      // Step 1: Camera captures frame (simulated - no delay in test)
      log(`\n   Step 1: Camera Frame Captured`, 'cyan');
      const captureTime = Date.now();
      flow.steps.push({
        name: 'capture',
        timestamp: captureTime - flowStart,
      });

      // Step 2: Card Detection (simulated with base64 encode)
      log(`   Step 2: Running Card Detection...`, 'cyan');
      const detectionStart = Date.now();

      // Read image and encode to base64 (simulates camera frame)
      const imageBuffer = fs.readFileSync(imagePath);
      const base64Image = imageBuffer.toString('base64');

      const detectionResult = await this.sendRequest('detect_card', {
        image_data: base64Image,
      });

      const detectionTime = Date.now() - detectionStart;
      flow.steps.push({
        name: 'detection',
        timestamp: Date.now() - flowStart,
        duration: detectionTime,
        result: detectionResult,
      });

      log(`     ✓ Detection: ${formatTime(detectionTime)}`, 'green');
      log(`       Status: ${detectionResult.status}`, 'blue');
      log(`       Confidence: ${(detectionResult.confidence * 100).toFixed(1)}%`, 'blue');
      log(`       Quality: ${(detectionResult.qualityScore * 100).toFixed(1)}%`, 'blue');
      log(`       Ready: ${detectionResult.isReady ? 'YES' : 'NO'}`, detectionResult.isReady ? 'green' : 'yellow');

      if (!detectionResult.isReady) {
        log(`     ⚠️  Card not ready for capture`, 'yellow');
        log(`       Warnings: ${detectionResult.warnings.join(', ')}`, 'yellow');
        return null;
      }

      // Step 3: User sees "Ready" indicator (simulated - 100ms reaction time)
      const userReactionMs = 100;
      await new Promise(resolve => setTimeout(resolve, userReactionMs));

      // Step 4: Trigger Identification
      log(`\n   Step 3: Triggering Identification...`, 'cyan');
      const identifyStart = Date.now();

      const identifyResult = await this.sendRequest('identify', {
        image_path: imagePath,
        top_k: 50,
        use_geometric: true,
        skip_ocr: true,
        skip_foil: true,
      });

      const identifyTime = Date.now() - identifyStart;
      flow.steps.push({
        name: 'identification',
        timestamp: Date.now() - flowStart,
        duration: identifyTime,
        result: identifyResult,
      });

      log(`     ✓ Identification: ${formatTime(identifyTime)}`, 'green');
      log(`       Card: ${identifyResult.card.name}`, 'magenta');
      log(`       Confidence: ${identifyResult.confidence}`, 'magenta');
      log(`       Score: ${identifyResult.scores.final.toFixed(4)}`, 'blue');

      if (identifyResult.timing) {
        log(`\n       Timing Breakdown:`, 'cyan');
        log(`         • Feature Extraction: ${formatTime(identifyResult.timing.feature_extraction_ms)}`, 'blue');
        log(`         • Visual Search: ${formatTime(identifyResult.timing.visual_search_ms)}`, 'blue');
        log(`         • Geometric Verify: ${formatTime(identifyResult.timing.geometric_verify_ms)}`, 'blue');
      }

      // Total flow time
      const flowEnd = Date.now();
      const totalFlowTime = flowEnd - flowStart;
      flow.totalTime = totalFlowTime;

      log(`\n   ✅ Complete Flow: ${formatTime(totalFlowTime)}`, 'green');
      log(`      User Perception: ${formatTime(totalFlowTime - userReactionMs)} (excluding reaction time)`, 'blue');

      return flow;

    } catch (error) {
      log(`   ❌ Flow failed: ${error.message}`, 'red');
      flow.error = error.message;
      return flow;
    }
  }

  async runAllFlows() {
    log('\n📊 Phase 2: Camera Flow Tests', 'bright');

    for (let i = 0; i < TEST_IMAGES.length; i++) {
      const result = await this.simulateCameraFlow(TEST_IMAGES[i], i + 1);
      if (result) {
        this.flowResults.push(result);
      }

      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  printSummary() {
    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    log('║                  CAMERA FLOW SUMMARY                       ║', 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    if (this.flowResults.length === 0) {
      log('\n❌ No successful flows to summarize', 'red');
      return;
    }

    const totalTimes = this.flowResults.map(f => f.totalTime);
    const detectionTimes = this.flowResults
      .map(f => f.steps.find(s => s.name === 'detection'))
      .filter(s => s)
      .map(s => s.duration);
    const identificationTimes = this.flowResults
      .map(f => f.steps.find(s => s.name === 'identification'))
      .filter(s => s)
      .map(s => s.duration);

    const avgTotal = totalTimes.reduce((a, b) => a + b, 0) / totalTimes.length;
    const avgDetection = detectionTimes.reduce((a, b) => a + b, 0) / detectionTimes.length;
    const avgIdentification = identificationTimes.reduce((a, b) => a + b, 0) / identificationTimes.length;

    log('\n⏱️  End-to-End Latency (User Experience):', 'bright');
    log(`   Average Total: ${formatTime(avgTotal)}`, 'green');
    log(`   Min Total: ${formatTime(Math.min(...totalTimes))}`, 'blue');
    log(`   Max Total: ${formatTime(Math.max(...totalTimes))}`, 'blue');

    log('\n📊 Pipeline Breakdown:', 'bright');
    log(`   Detection: ${formatTime(avgDetection)} avg`, 'blue');
    log(`   Identification: ${formatTime(avgIdentification)} avg`, 'blue');
    log(`   User Reaction: ~100ms (simulated)`, 'blue');

    // UX Analysis
    log('\n🎯 User Experience Analysis:', 'bright');

    const excellent = avgTotal < 500;
    const good = avgTotal < 1000;
    const acceptable = avgTotal < 2000;

    if (excellent) {
      log('   ✅ EXCELLENT - Feels instant (<500ms)', 'green');
    } else if (good) {
      log('   ✅ GOOD - Feels responsive (<1s)', 'green');
    } else if (acceptable) {
      log('   ⚠️  ACCEPTABLE - Noticeable delay (<2s)', 'yellow');
    } else {
      log('   ❌ POOR - Feels sluggish (>2s)', 'red');
    }

    // Recommendations
    log('\n💡 Optimization Opportunities:', 'bright');

    if (avgDetection > 100) {
      log(`   • Detection is slow (${formatTime(avgDetection)}) - consider optimization`, 'yellow');
    }

    if (avgIdentification > 200) {
      log(`   • Identification is slow (${formatTime(avgIdentification)}) - warmup may help`, 'yellow');
    } else {
      log(`   ✓ Identification is fast (${formatTime(avgIdentification)})`, 'green');
    }

    if (avgTotal > 1000) {
      log(`   • Total flow >1s - user will perceive delay`, 'yellow');
    } else {
      log(`   ✓ Total flow <1s - user will perceive as instant`, 'green');
    }
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

      this.pendingRequests.set(id, { resolve, reject, timer });

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
          // Ignore parse errors
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

  async cleanup() {
    if (this.process) {
      this.process.kill('SIGTERM');
    }
  }
}

async function main() {
  const useOptimized = process.argv.includes('--optimized');
  const simulator = new CameraFlowSimulator(useOptimized);

  try {
    await simulator.start();
    await simulator.initialize();
    await simulator.runAllFlows();
    simulator.printSummary();

  } catch (error) {
    log(`\n❌ Simulation failed: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  } finally {
    await simulator.cleanup();
    process.exit(0);
  }
}

main();
