/**
 * Structured logging system for CardFlux Desktop
 *
 * Provides consistent logging across the application with:
 * - Log levels (DEBUG, INFO, WARN, ERROR)
 * - Timestamps
 * - Component-specific context
 * - File logging (future: Sentry integration)
 */

import * as fs from 'fs';
import * as path from 'path';
import { app } from 'electron';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

interface LogEntry {
  timestamp: string;
  level: string;
  component: string;
  message: string;
  data?: any;
  error?: Error;
}

class Logger {
  private logLevel: LogLevel = LogLevel.INFO;
  private logFilePath: string | null = null;
  private writeStream: fs.WriteStream | null = null;
  private readonly MAX_LOG_FILES = 7; // Keep last 7 files
  private readonly MAX_LOG_SIZE = 10 * 1024 * 1024; // 10 MB per file
  private currentLogSize = 0;

  constructor() {
    // Enable file logging in production OR if explicitly enabled
    const enableLogging = app.isPackaged || process.env.ENABLE_FILE_LOGGING === 'true';

    if (enableLogging) {
      this.enableFileLogging();
    }
  }

  /**
   * Enable logging to file with rotation
   */
  private async enableFileLogging(): Promise<void> {
    try {
      const logDir = path.join(app.getPath('userData'), 'logs');

      // Ensure log directory exists (async)
      await fs.promises.mkdir(logDir, { recursive: true });

      // Clean up old log files (async)
      await this.rotateLogFiles(logDir);

      // Create log file with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      this.logFilePath = path.join(logDir, `cardflux-${timestamp}.log`);

      // Check existing file size if it exists
      try {
        const stats = await fs.promises.stat(this.logFilePath);
        this.currentLogSize = stats.size;
      } catch {
        this.currentLogSize = 0; // File doesn't exist yet
      }

      this.writeStream = fs.createWriteStream(this.logFilePath, { flags: 'a' });

      console.log(`[Logger] File logging enabled: ${this.logFilePath}`);
    } catch (error) {
      console.error('Failed to enable file logging:', error);
    }
  }

  /**
   * Rotate log files - delete old logs, keep last N files
   */
  private async rotateLogFiles(logDir: string): Promise<void> {
    try {
      const files = await fs.promises.readdir(logDir);
      const logFiles = await Promise.all(
        files
          .filter(file => file.startsWith('cardflux-') && file.endsWith('.log'))
          .map(async file => {
            const filePath = path.join(logDir, file);
            const stats = await fs.promises.stat(filePath);
            return {
              name: file,
              path: filePath,
              time: stats.mtime.getTime(),
              size: stats.size,
            };
          })
      );

      // Sort by newest first
      logFiles.sort((a, b) => b.time - a.time);

      // Delete files beyond MAX_LOG_FILES
      if (logFiles.length > this.MAX_LOG_FILES) {
        const filesToDelete = logFiles.slice(this.MAX_LOG_FILES);
        console.log(`[Logger] Rotating logs: keeping ${this.MAX_LOG_FILES}, deleting ${filesToDelete.length}`);

        for (const file of filesToDelete) {
          try {
            await fs.promises.unlink(file.path);
            console.log(`[Logger] Deleted old log file: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`);
          } catch (error) {
            console.error(`[Logger] Failed to delete ${file.name}:`, error);
          }
        }
      }
    } catch (error) {
      console.error('[Logger] Failed to rotate log files:', error);
    }
  }

  /**
   * Set the minimum log level
   */
  setLogLevel(level: LogLevel): void {
    this.logLevel = level;
  }

  /**
   * Log a debug message
   */
  debug(component: string, message: string, data?: any): void {
    this.log(LogLevel.DEBUG, component, message, data);
  }

  /**
   * Log an info message
   */
  info(component: string, message: string, data?: any): void {
    this.log(LogLevel.INFO, component, message, data);
  }

  /**
   * Log a warning
   */
  warn(component: string, message: string, data?: any): void {
    this.log(LogLevel.WARN, component, message, data);
  }

  /**
   * Log an error
   */
  error(component: string, message: string, error?: Error, data?: any): void {
    this.log(LogLevel.ERROR, component, message, data, error);
  }

  /**
   * Core logging method
   */
  private log(
    level: LogLevel,
    component: string,
    message: string,
    data?: any,
    error?: Error
  ): void {
    if (level < this.logLevel) {
      return;
    }

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: LogLevel[level],
      component,
      message,
      data,
      error,
    };

    // Console output with colors
    this.logToConsole(entry);

    // File output (JSON lines)
    if (this.writeStream) {
      this.logToFile(entry);
    }
  }

  /**
   * Log to console with colors
   */
  private logToConsole(entry: LogEntry): void {
    const levelColors: Record<string, string> = {
      DEBUG: '\x1b[36m', // Cyan
      INFO: '\x1b[32m',  // Green
      WARN: '\x1b[33m',  // Yellow
      ERROR: '\x1b[31m', // Red
    };

    const reset = '\x1b[0m';
    const color = levelColors[entry.level] || reset;

    const timestamp = entry.timestamp.split('T')[1].split('.')[0];
    const prefix = `${color}[${entry.level}]${reset} ${timestamp} [${entry.component}]`;

    if (entry.level === 'ERROR' && entry.error) {
      console.error(prefix, entry.message);
      console.error(entry.error);
      if (entry.data) {
        console.error('Data:', entry.data);
      }
    } else if (entry.level === 'WARN') {
      console.warn(prefix, entry.message, entry.data || '');
    } else {
      console.log(prefix, entry.message, entry.data || '');
    }
  }

  /**
   * Log to file (JSON lines format) with size-based rotation
   */
  private logToFile(entry: LogEntry): void {
    if (!this.writeStream) {
      return;
    }

    try {
      const logLine = JSON.stringify({
        ...entry,
        error: entry.error ? {
          message: entry.error.message,
          stack: entry.error.stack,
        } : undefined,
      });

      const lineSize = Buffer.byteLength(logLine + '\n', 'utf8');

      // Check if we need to rotate based on size
      if (this.currentLogSize + lineSize > this.MAX_LOG_SIZE && this.logFilePath) {
        console.log(`[Logger] Log file size limit reached (${(this.currentLogSize / 1024 / 1024).toFixed(2)}MB), rotating...`);

        // Close current stream
        this.writeStream.end();

        // Create new log file with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const logDir = path.dirname(this.logFilePath);
        this.logFilePath = path.join(logDir, `cardflux-${timestamp}.log`);

        // Open new stream
        this.writeStream = fs.createWriteStream(this.logFilePath, { flags: 'a' });
        this.currentLogSize = 0;

        // Async rotate old files (don't wait)
        this.rotateLogFiles(logDir).catch(err =>
          console.error('[Logger] Failed to rotate old log files:', err)
        );
      }

      this.writeStream.write(logLine + '\n');
      this.currentLogSize += lineSize;
    } catch (error) {
      console.error('Failed to write log:', error);
    }
  }

  /**
   * Close the logger and flush logs
   */
  close(): Promise<void> {
    return new Promise((resolve) => {
      if (this.writeStream) {
        this.writeStream.end(() => {
          this.writeStream = null;
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}

// Singleton instance
export const logger = new Logger();

// Set log level from environment
if (process.env.NODE_ENV === 'development') {
  logger.setLogLevel(LogLevel.DEBUG);
}
