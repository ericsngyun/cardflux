import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import { logger } from '../core/logger';
import { ResourceManager } from '../core/resource-manager';

interface IdentifyResult {
  success: boolean;
  card: {
    name: string;
    productId: number;
    number: string;
    set: string;
    rarity: string;
    imageUrl: string;
    url: string;
    prices: any;
  };
  confidence: string;
  scores: any;
  features: {
    foil: boolean;
    foilType: string;
    cardNumber: string | null;
  };
  timing: any;
  topMatches: Array<{
    name: string;
    score: number;
    number: string;
    rarity: string;
  }>;
}

interface JSONRPCRequest {
  jsonrpc: string;
  id: number;
  method: string;
  params?: any;
}

interface JSONRPCResponse {
  jsonrpc: string;
  id: number;
  result?: any;
  error?: {
    code: number;
    message: string;
  };
}

interface PendingRequest {
  resolve: Function;
  reject: Function;
  timer: NodeJS.Timeout;
  method: string;
  timestamp: number;
}

export class PythonIdentificationBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests = new Map<number, PendingRequest>();
  private initialized = false;
  private buffer = '';
  private resourceManager: ResourceManager;

  constructor() {
    super();
    this.resourceManager = ResourceManager.getInstance();
    logger.info('PythonBridge', 'Instance created');
  }

  /**
   * Start the Python identification service
   */
  async start(game: string = 'one-piece'): Promise<void> {
    if (this.process) {
      logger.warn('PythonBridge', 'Service already running');
      throw new Error('Service already running');
    }

    logger.info('PythonBridge', 'Starting Python service', { game });

    return new Promise((resolve, reject) => {
      try {
        // Get bundled Python paths from ResourceManager
        const paths = this.resourceManager.getPaths();
        const pythonExecutable = paths.pythonExecutable;
        const scriptPath = this.resourceManager.getServiceScriptPath();

        // Verify script exists
        if (!fs.existsSync(scriptPath)) {
          const error = new Error(`Python service script not found: ${scriptPath}`);
          logger.error('PythonBridge', 'Script not found', error);
          throw error;
        }

        logger.info('PythonBridge', 'Python executable', { pythonExecutable });
        logger.info('PythonBridge', 'Service script', { scriptPath });

        // Get Python environment (includes PYTHONPATH, PYTHONHOME, etc.)
        const pythonEnv = this.resourceManager.getPythonEnvironment();

        // Spawn Python process with bundled runtime
        this.process = spawn(pythonExecutable, [scriptPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          env: pythonEnv,
        });

        logger.debug('PythonBridge', 'Python process spawned', {
          pid: this.process.pid,
        });

        // Handle stdout (JSON-RPC responses)
        this.process.stdout?.on('data', (data) => {
          this.handleStdout(data);
        });

        // Handle stderr (logs from Python)
        this.process.stderr?.on('data', (data) => {
          const message = data.toString().trim();
          // Log all Python stderr output to help debug initialization issues
          if (message.includes('Error') || message.includes('Traceback') || message.includes('Exception')) {
            logger.error('Python', message);
          } else {
            logger.debug('Python', message);
          }
        });

        // Handle process exit
        this.process.on('exit', (code) => {
          logger.warn('PythonBridge', `Process exited with code ${code}`);
          this.cleanup();
          this.emit('exit', code);
        });

        // Handle errors
        this.process.on('error', (error) => {
          logger.error('PythonBridge', 'Process spawn error', error);
          this.cleanup();
          reject(error);
        });

        // Initialize the service
        logger.info('PythonBridge', 'Initializing service');
        this.initialize(game)
          .then(() => {
            logger.info('PythonBridge', 'Service ready');
            this.initialized = true;
            resolve();
          })
          .catch((error) => {
            logger.error('PythonBridge', 'Initialization failed', error);
            reject(error);
          });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Stop the Python service
   */
  async stop(): Promise<void> {
    if (!this.process) {
      return;
    }

    return new Promise((resolve) => {
      if (!this.process) {
        resolve();
        return;
      }

      this.process.once('exit', () => {
        logger.info('PythonBridge', 'Process stopped gracefully');
        resolve();
      });

      logger.info('PythonBridge', 'Sending SIGTERM to Python process');
      this.process.kill('SIGTERM');

      // Force kill after 5 seconds
      setTimeout(() => {
        if (this.process && !this.process.killed) {
          logger.warn('PythonBridge', 'Force killing process with SIGKILL');
          this.process.kill('SIGKILL');
        }
      }, 5000);
    });
  }

  /**
   * Initialize the identification system
   */
  private async initialize(game: string): Promise<any> {
    return this.sendRequest('initialize', { game });
  }

  /**
   * Identify a card from an image file
   */
  async identifyCard(
    imagePath: string,
    options: {
      topK?: number;
      tcgHint?: string;
      useGeometric?: boolean;
      skipOCR?: boolean;
      skipFoil?: boolean;
    } = {}
  ): Promise<IdentifyResult> {
    if (!this.initialized) {
      const error = new Error('Service not initialized');
      logger.error('PythonBridge', 'Identify called before initialization', error);
      throw error;
    }

    logger.debug('PythonBridge', 'Identifying card', { imagePath, options });

    // Increased default from 30 to 50 for better accuracy with preprocessing fixes
    return this.sendRequest('identify', {
      image_path: imagePath,
      top_k: options.topK || 50,
      tcg_hint: options.tcgHint || null,
      use_geometric: options.useGeometric !== undefined ? options.useGeometric : true,
      skip_ocr: options.skipOCR !== undefined ? options.skipOCR : false,
      skip_foil: options.skipFoil !== undefined ? options.skipFoil : false,
    });
  }

  /**
   * Identify a card from multiple frames with fusion (V2 feature)
   */
  async identifyCardMultiFrame(
    imagePaths: string[],
    options: {
      topK?: number;
      tcgHint?: string;
      useGeometric?: boolean;
    } = {}
  ): Promise<IdentifyResult & {
    multiFrame?: {
      numFrames: number;
      fusionVotes: number;
      agreementRate: number;
      confidenceBoost: boolean;
    };
  }> {
    if (!this.initialized) {
      const error = new Error('Service not initialized');
      logger.error('PythonBridge', 'identifyMultiFrame called before initialization', error);
      throw error;
    }

    logger.debug('PythonBridge', 'Identifying card (multi-frame)', { 
      numFrames: imagePaths.length,
      options 
    });

    return this.sendRequest('identify_multi_frame', {
      image_paths: imagePaths,
      top_k: options.topK || 50,
      tcg_hint: options.tcgHint || null,
      use_geometric: options.useGeometric !== undefined ? options.useGeometric : true,
    });
  }

  /**
   * Detect card in a video frame (base64 encoded)
   */
  async detectCard(imageData: string): Promise<{
    status: string;
    confidence: number;
    qualityScore: number;
    warnings: string[];
    isReady: boolean;
    bbox: [number, number, number, number] | null;
  }> {
    if (!this.initialized) {
      throw new Error('Service not initialized');
    }

    return this.sendRequest('detect_card', {
      image_data: imageData,
    });
  }

  /**
   * Get service status
   */
  async getStatus(): Promise<{ initialized: boolean; ready: boolean }> {
    if (!this.process) {
      return { initialized: false, ready: false };
    }

    return this.sendRequest('status', {});
  }

  /**
   * Send a JSON-RPC request to the Python service
   */
  private async sendRequest(method: string, params: any): Promise<any> {
    if (!this.process || !this.process.stdin) {
      throw new Error('Service not running');
    }

    return new Promise((resolve, reject) => {
      const id = ++this.requestId;

      // Check for request ID collision (should never happen, but be safe)
      if (this.pendingRequests.has(id)) {
        logger.error('PythonBridge', 'Request ID collision detected!', undefined, { id });
        reject(new Error(`Request ID collision: ${id}`));
        return;
      }

      const request: JSONRPCRequest = {
        jsonrpc: '2.0',
        id,
        method,
        params,
      };

      // Set timeout (20 seconds for identification, 60 for initialization)
      // Reduced from 30s to 20s since we're optimizing performance
      // Detection should be fast (5s timeout)
      const timeout = method === 'initialize' ? 60000 : method === 'detect_card' ? 5000 : 20000;
      const timer = setTimeout(() => {
        const pending = this.pendingRequests.get(id);
        if (pending) {
          // CRITICAL FIX: Clear timer BEFORE rejecting to prevent memory leak
          clearTimeout(timer);
          this.pendingRequests.delete(id);
          const elapsed = Date.now() - pending.timestamp;
          logger.error('PythonBridge', `Request timeout after ${elapsed}ms`, undefined, {
            id,
            method,
            timeout,
          });
          reject(new Error(`Request timeout: ${method} (${elapsed}ms > ${timeout}ms)`));
        }
      }, timeout);

      // Store the promise with timer reference
      this.pendingRequests.set(id, {
        resolve,
        reject,
        timer,
        method,
        timestamp: Date.now(),
      });

      // Send request
      const requestJson = JSON.stringify(request) + '\n';
      this.process!.stdin!.write(requestJson);

      logger.debug('PythonBridge', 'Request sent', { id, method, timeout });
    });
  }

  /**
   * Handle stdout data from Python process
   */
  private handleStdout(data: Buffer): void {
    const chunk = data.toString();
    logger.debug('PythonBridge', 'Received stdout chunk', {
      length: chunk.length,
      preview: chunk.substring(0, 100),
    });

    this.buffer += chunk;

    // Process complete lines
    let newlineIndex;
    while ((newlineIndex = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, newlineIndex).trim();
      this.buffer = this.buffer.slice(newlineIndex + 1);

      if (line) {
        logger.debug('PythonBridge', 'Processing line from stdout', {
          length: line.length,
          preview: line.substring(0, 100),
        });

        try {
          const response: JSONRPCResponse = JSON.parse(line);
          logger.debug('PythonBridge', 'Parsed JSON response', {
            id: response.id,
            hasResult: !!response.result,
            hasError: !!response.error,
          });
          this.handleResponse(response);
        } catch (error) {
          logger.error('PythonBridge', 'Failed to parse JSON response', error as Error, {
            line: line.substring(0, 200),
            fullLength: line.length,
          });
        }
      }
    }
  }

  /**
   * Handle a JSON-RPC response
   */
  private handleResponse(response: JSONRPCResponse): void {
    const { id, result, error } = response;

    const pending = this.pendingRequests.get(id);
    if (!pending) {
      // Response for unknown request - either timed out or already processed
      logger.warn('PythonBridge', 'Received response for unknown request (may have timed out)', {
        id,
        hasError: !!error,
      });
      return;
    }

    // Clear the timeout timer to prevent memory leak
    clearTimeout(pending.timer);

    // Calculate response time
    const elapsed = Date.now() - pending.timestamp;

    // Remove from pending
    this.pendingRequests.delete(id);

    if (error) {
      logger.error('PythonBridge', 'JSON-RPC error response', undefined, {
        id,
        method: pending.method,
        elapsed: `${elapsed}ms`,
        error,
      });
      pending.reject(new Error(error.message));
    } else {
      logger.debug('PythonBridge', 'JSON-RPC success response', {
        id,
        method: pending.method,
        elapsed: `${elapsed}ms`,
      });
      pending.resolve(result);
    }
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    this.process = null;
    this.initialized = false;
    this.buffer = '';

    // Reject all pending requests and clear their timers
    this.pendingRequests.forEach((pending, id) => {
      clearTimeout(pending.timer);
      pending.reject(new Error('Service terminated'));
      logger.debug('PythonBridge', 'Cleaned up pending request', {
        id,
        method: pending.method,
        age: `${Date.now() - pending.timestamp}ms`,
      });
    });
    this.pendingRequests.clear();

    logger.info('PythonBridge', 'Cleanup complete');
  }

  /**
   * Check if service is running
   */
  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }

  /**
   * Check if service is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Get pending requests count (for debugging/monitoring)
   */
  getPendingRequestsCount(): number {
    return this.pendingRequests.size;
  }

  /**
   * Get pending requests info (for debugging)
   */
  getPendingRequestsInfo(): Array<{ id: number; method: string; age: number }> {
    const now = Date.now();
    return Array.from(this.pendingRequests.entries()).map(([id, pending]) => ({
      id,
      method: pending.method,
      age: now - pending.timestamp,
    }));
  }
}
