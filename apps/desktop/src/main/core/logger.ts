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
  private readonly MAX_LOG_FILES = 7; // Keep last 7 days
  // Reserved for future log rotation by size
  // private readonly MAX_LOG_SIZE = 10 * 1024 * 1024; // 10 MB per file

  constructor() {
    // In production, enable file logging
    if (!app.isPackaged && process.env.NODE_ENV !== 'development') {
      this.enableFileLogging();
    }
  }

  /**
   * Enable logging to file with rotation
   */
  private enableFileLogging(): void {
    try {
      const logDir = path.join(app.getPath('userData'), 'logs');

      if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
      }

      // Clean up old log files
      this.rotateLogFiles(logDir);

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      this.logFilePath = path.join(logDir, `cardflux-${timestamp}.log`);

      this.writeStream = fs.createWriteStream(this.logFilePath, { flags: 'a' });

      this.info('Logger', 'File logging enabled', { path: this.logFilePath });
    } catch (error) {
      console.error('Failed to enable file logging:', error);
    }
  }

  /**
   * Rotate log files - delete old logs, keep last N files
   */
  private rotateLogFiles(logDir: string): void {
    try {
      const files = fs.readdirSync(logDir)
        .filter(file => file.startsWith('cardflux-') && file.endsWith('.log'))
        .map(file => ({
          name: file,
          path: path.join(logDir, file),
          time: fs.statSync(path.join(logDir, file)).mtime.getTime(),
        }))
        .sort((a, b) => b.time - a.time); // Sort by newest first

      // Delete files beyond MAX_LOG_FILES
      if (files.length > this.MAX_LOG_FILES) {
        const filesToDelete = files.slice(this.MAX_LOG_FILES);
        filesToDelete.forEach(file => {
          try {
            fs.unlinkSync(file.path);
            console.log(`[Logger] Deleted old log file: ${file.name}`);
          } catch (error) {
            console.error(`[Logger] Failed to delete ${file.name}:`, error);
          }
        });
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
   * Log to file (JSON lines format)
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

      this.writeStream.write(logLine + '\n');
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
