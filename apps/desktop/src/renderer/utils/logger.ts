/**
 * Renderer Logger
 *
 * Structured logging utility for renderer process.
 * Provides consistent formatting, log levels, and integration with main process logger.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  data?: any;
}

/**
 * Format a log entry with consistent structure
 */
function formatLogEntry(level: LogLevel, module: string, message: string, data?: any): string {
  const timestamp = new Date().toISOString();
  const dataStr = data !== undefined ? ` ${JSON.stringify(data)}` : '';
  return `[${timestamp}] [${level.toUpperCase()}] [${module}] ${message}${dataStr}`;
}

/**
 * Send log to main process for centralized logging
 */
async function sendToMainProcess(entry: LogEntry): Promise<void> {
  try {
    // Check if logger IPC is available
    if (window.logger?.log) {
      await window.logger.log(entry.level, entry.module, entry.message, entry.data);
    }
  } catch (error) {
    // Fail silently - don't want logging to crash the app
    console.error('[Logger] Failed to send to main process:', error);
  }
}

/**
 * Structured logger for renderer process
 */
export const logger = {
  /**
   * Debug-level logging (verbose, development only)
   */
  debug(module: string, message: string, data?: any): void {
    const formatted = formatLogEntry('debug', module, message, data);
    console.debug(formatted);

    // Send to main process asynchronously (don't await)
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'debug',
      module,
      message,
      data,
    };
    sendToMainProcess(entry).catch(() => {
      /* ignore */
    });
  },

  /**
   * Info-level logging (normal operations)
   */
  info(module: string, message: string, data?: any): void {
    const formatted = formatLogEntry('info', module, message, data);
    console.log(formatted);

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'info',
      module,
      message,
      data,
    };
    sendToMainProcess(entry).catch(() => {
      /* ignore */
    });
  },

  /**
   * Warning-level logging (recoverable issues)
   */
  warn(module: string, message: string, data?: any): void {
    const formatted = formatLogEntry('warn', module, message, data);
    console.warn(formatted);

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'warn',
      module,
      message,
      data,
    };
    sendToMainProcess(entry).catch(() => {
      /* ignore */
    });
  },

  /**
   * Error-level logging (failures, exceptions)
   */
  error(module: string, message: string, error?: Error | any, data?: any): void {
    const errorData = error instanceof Error
      ? { message: error.message, stack: error.stack, ...data }
      : { error, ...data };

    const formatted = formatLogEntry('error', module, message, errorData);
    console.error(formatted);

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'error',
      module,
      message,
      data: errorData,
    };
    sendToMainProcess(entry).catch(() => {
      /* ignore */
    });
  },

  /**
   * Performance timing utility
   */
  time(module: string, label: string): () => void {
    const start = performance.now();

    return () => {
      const duration = performance.now() - start;
      this.debug(module, `[TIMING] ${label}`, { durationMs: duration.toFixed(2) });
    };
  },

  /**
   * Group related logs (development only)
   */
  group(module: string, label: string): void {
    if (process.env.NODE_ENV === 'development') {
      console.group(`[${module}] ${label}`);
    }
  },

  /**
   * End log group
   */
  groupEnd(): void {
    if (process.env.NODE_ENV === 'development') {
      console.groupEnd();
    }
  },
};

/**
 * Create a scoped logger for a specific module
 */
export function createModuleLogger(moduleName: string) {
  return {
    debug: (message: string, data?: any) => logger.debug(moduleName, message, data),
    info: (message: string, data?: any) => logger.info(moduleName, message, data),
    warn: (message: string, data?: any) => logger.warn(moduleName, message, data),
    error: (message: string, error?: Error | any, data?: any) =>
      logger.error(moduleName, message, error, data),
    time: (label: string) => logger.time(moduleName, label),
    group: (label: string) => logger.group(moduleName, label),
    groupEnd: () => logger.groupEnd(),
  };
}
