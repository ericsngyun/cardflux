import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';

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

  constructor() {
    super();
  }

  /**
   * Start the Python identification service
   */
  async start(game: string = 'one-piece'): Promise<void> {
    if (this.process) {
      throw new Error('Service already running');
    }

    return new Promise((resolve, reject) => {
      try {
        // Find Python executable
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

        // Path to the service script
        const scriptPath = path.join(__dirname, '../python/identification_service.py');

        // Verify script exists
        if (!fs.existsSync(scriptPath)) {
          throw new Error(`Python service script not found: ${scriptPath}`);
        }

        console.log('[PythonBridge] Starting Python service:', scriptPath);

        // Spawn Python process
        this.process = spawn(pythonCmd, [scriptPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          env: {
            ...process.env,
            PYTHONUNBUFFERED: '1', // Disable output buffering
          },
        });

        // Handle stdout (JSON-RPC responses)
        this.process.stdout?.on('data', (data) => {
          this.handleStdout(data);
        });

        // Handle stderr (logs)
        this.process.stderr?.on('data', (data) => {
          console.log('[Python]', data.toString().trim());
        });

        // Handle process exit
        this.process.on('exit', (code) => {
          console.log(`[PythonBridge] Process exited with code ${code}`);
          this.cleanup();
          this.emit('exit', code);
        });

        // Handle errors
        this.process.on('error', (error) => {
          console.error('[PythonBridge] Process error:', error);
          this.cleanup();
          reject(error);
        });

        // Initialize the service
        console.log('[PythonBridge] Initializing service...');
        this.initialize(game)
          .then(() => {
            console.log('[PythonBridge] Service ready');
            this.initialized = true;
            resolve();
          })
          .catch(reject);
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
        resolve();
      });

      this.process.kill('SIGTERM');

      // Force kill after 5 seconds
      setTimeout(() => {
        if (this.process && !this.process.killed) {
          console.warn('[PythonBridge] Force killing process');
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
    options: { topK?: number; tcgHint?: string } = {}
  ): Promise<IdentifyResult> {
    if (!this.initialized) {
      throw new Error('Service not initialized');
    }

    // Increased default from 30 to 50 for better accuracy with preprocessing fixes
    return this.sendRequest('identify', {
      image_path: imagePath,
      top_k: options.topK || 50,
      tcg_hint: options.tcgHint || null,
      use_geometric: true,  // Explicitly enable geometric verification
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
          console.error('[PythonBridge] Failed to parse response:', line);
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
      console.warn('[PythonBridge] Received response for unknown request:', id);
      return;
    }

    this.pendingRequests.delete(id);

    if (error) {
      pending.reject(new Error(error.message));
    } else {
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
