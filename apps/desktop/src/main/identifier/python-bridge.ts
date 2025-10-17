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

export class PythonIdentificationBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests = new Map<number, { resolve: Function; reject: Function }>();
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
          logger.debug('Python', message);
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

      const request: JSONRPCRequest = {
        jsonrpc: '2.0',
        id,
        method,
        params,
      };

      // Store the promise
      this.pendingRequests.set(id, { resolve, reject });

      // Send request
      const requestJson = JSON.stringify(request) + '\n';
      this.process!.stdin!.write(requestJson);

      // Set timeout (30 seconds for identification, 60 for initialization)
      const timeout = method === 'initialize' ? 60000 : 30000;
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Request timeout: ${method}`));
        }
      }, timeout);
    });
  }

  /**
   * Handle stdout data from Python process
   */
  private handleStdout(data: Buffer): void {
    this.buffer += data.toString();

    // Process complete lines
    let newlineIndex;
    while ((newlineIndex = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, newlineIndex).trim();
      this.buffer = this.buffer.slice(newlineIndex + 1);

      if (line) {
        try {
          const response: JSONRPCResponse = JSON.parse(line);
          this.handleResponse(response);
        } catch (error) {
          logger.error('PythonBridge', 'Failed to parse JSON response', error as Error, { line });
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
      logger.warn('PythonBridge', 'Received response for unknown request', { id });
      return;
    }

    this.pendingRequests.delete(id);

    if (error) {
      logger.error('PythonBridge', 'JSON-RPC error response', undefined, { id, error });
      pending.reject(new Error(error.message));
    } else {
      logger.debug('PythonBridge', 'JSON-RPC success response', { id });
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

    // Reject all pending requests
    this.pendingRequests.forEach(({ reject }) => {
      reject(new Error('Service terminated'));
    });
    this.pendingRequests.clear();
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
}
