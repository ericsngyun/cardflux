/**
 * Graceful shutdown utilities for CardFlux pipeline
 * Prevents data loss when user presses Ctrl+C
 */

export interface ShutdownHandler {
  name: string;
  handler: () => Promise<void> | void;
  timeout?: number;
}

class ShutdownManager {
  private handlers: ShutdownHandler[] = [];
  private isShuttingDown = false;
  private currentOperation: string | null = null;

  constructor() {
    this.setupSignalHandlers();
  }

  /**
   * Register a cleanup handler to run on shutdown
   */
  register(handler: ShutdownHandler): void {
    this.handlers.push(handler);
  }

  /**
   * Set current operation name (for logging)
   */
  setCurrentOperation(operation: string | null): void {
    this.currentOperation = operation;
  }

  /**
   * Check if shutdown is in progress
   */
  isShutdown(): boolean {
    return this.isShuttingDown;
  }

  /**
   * Setup signal handlers for graceful shutdown
   */
  private setupSignalHandlers(): void {
    // SIGINT (Ctrl+C)
    process.on('SIGINT', async () => {
      if (this.isShuttingDown) {
        console.log('\n⚠️  Force exit requested...');
        process.exit(1);
      }

      this.isShuttingDown = true;
      console.log('\n\n' + '='.repeat(60));
      console.log('GRACEFUL SHUTDOWN INITIATED');
      console.log('='.repeat(60));

      if (this.currentOperation) {
        console.log(`Current operation: ${this.currentOperation}`);
      }

      console.log('\nPress Ctrl+C again to force exit (NOT RECOMMENDED)\n');

      await this.runShutdownHandlers();

      console.log('\n✓ Shutdown complete. All progress saved.');
      process.exit(0);
    });

    // SIGTERM (kill command)
    process.on('SIGTERM', async () => {
      console.log('\n\nSIGTERM received, shutting down gracefully...');
      this.isShuttingDown = true;

      await this.runShutdownHandlers();

      console.log('✓ Shutdown complete.');
      process.exit(0);
    });

    // Uncaught exceptions
    process.on('uncaughtException', async (error) => {
      console.error('\n\n❌ UNCAUGHT EXCEPTION:', error);
      console.error('Stack:', error.stack);

      this.isShuttingDown = true;
      console.log('\nRunning cleanup handlers...');

      await this.runShutdownHandlers();

      process.exit(1);
    });

    // Unhandled promise rejections
    process.on('unhandledRejection', async (reason, promise) => {
      console.error('\n\n❌ UNHANDLED PROMISE REJECTION:', reason);
      console.error('Promise:', promise);

      this.isShuttingDown = true;
      console.log('\nRunning cleanup handlers...');

      await this.runShutdownHandlers();

      process.exit(1);
    });
  }

  /**
   * Run all registered shutdown handlers
   */
  private async runShutdownHandlers(): Promise<void> {
    if (this.handlers.length === 0) {
      return;
    }

    console.log(`\nRunning ${this.handlers.length} cleanup handler(s)...\n`);

    for (const { name, handler, timeout = 5000 } of this.handlers) {
      try {
        console.log(`  - ${name}...`);

        // Run with timeout
        await Promise.race([
          handler(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), timeout)
          ),
        ]);

        console.log(`    ✓ ${name} complete`);
      } catch (error: any) {
        console.error(`    ✗ ${name} failed: ${error.message}`);
        // Continue with other handlers even if one fails
      }
    }
  }
}

// Singleton instance
export const shutdownManager = new ShutdownManager();

/**
 * Register a shutdown handler
 *
 * @example
 * ```ts
 * onShutdown({
 *   name: 'Save state',
 *   handler: async () => {
 *     await saveState(currentState);
 *   },
 *   timeout: 3000
 * });
 * ```
 */
export function onShutdown(handler: ShutdownHandler): void {
  shutdownManager.register(handler);
}

/**
 * Set current operation name (for logging on shutdown)
 */
export function setCurrentOperation(operation: string | null): void {
  shutdownManager.setCurrentOperation(operation);
}

/**
 * Check if shutdown is in progress
 * Use this to abort long-running operations
 */
export function isShuttingDown(): boolean {
  return shutdownManager.isShutdown();
}
