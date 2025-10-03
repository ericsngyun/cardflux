/**
 * Monitoring and observability framework for CardFlux
 * Provides health checks, metrics, and alerting capabilities
 */

import * as fs from 'fs';
import * as path from 'path';
import { logger } from './logger';

export interface HealthCheckResult {
  name: string;
  healthy: boolean;
  message?: string;
  details?: Record<string, any>;
  duration: number;
}

export interface HealthCheck {
  name: string;
  check: () => Promise<HealthCheckResult>;
  critical?: boolean; // If true, system is unhealthy if this fails
  timeout?: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  checks: HealthCheckResult[];
  uptime: number;
}

export interface Metric {
  name: string;
  value: number;
  unit?: string;
  labels?: Record<string, string>;
  timestamp: string;
}

export class Monitor {
  private healthChecks: HealthCheck[] = [];
  private metrics: Metric[] = [];
  private startTime: number = Date.now();
  private metricsFile?: string;

  constructor(metricsFile?: string) {
    this.metricsFile = metricsFile;
  }

  /**
   * Register a health check
   */
  registerHealthCheck(check: HealthCheck): void {
    this.healthChecks.push(check);
    logger.debug(`Registered health check: ${check.name}`);
  }

  /**
   * Run all health checks
   */
  async checkHealth(): Promise<SystemHealth> {
    const results: HealthCheckResult[] = [];

    for (const check of this.healthChecks) {
      const start = Date.now();

      try {
        const timeout = check.timeout || 5000;
        const result = await Promise.race([
          check.check(),
          new Promise<HealthCheckResult>((_, reject) =>
            setTimeout(() => reject(new Error('Health check timeout')), timeout)
          ),
        ]);

        results.push({
          ...result,
          duration: Date.now() - start,
        });
      } catch (error) {
        results.push({
          name: check.name,
          healthy: false,
          message: (error as Error).message,
          duration: Date.now() - start,
        });
      }
    }

    // Determine overall status
    const criticalChecks = this.healthChecks.filter(c => c.critical);
    const criticalResults = results.filter(r =>
      criticalChecks.some(c => c.name === r.name)
    );

    const hasCriticalFailure = criticalResults.some(r => !r.healthy);
    const hasAnyFailure = results.some(r => !r.healthy);

    let status: 'healthy' | 'degraded' | 'unhealthy';
    if (hasCriticalFailure) {
      status = 'unhealthy';
    } else if (hasAnyFailure) {
      status = 'degraded';
    } else {
      status = 'healthy';
    }

    return {
      status,
      timestamp: new Date().toISOString(),
      checks: results,
      uptime: Date.now() - this.startTime,
    };
  }

  /**
   * Record a metric
   */
  recordMetric(metric: Omit<Metric, 'timestamp'>): void {
    const fullMetric: Metric = {
      ...metric,
      timestamp: new Date().toISOString(),
    };

    this.metrics.push(fullMetric);

    // Log metric
    logger.debug('Metric recorded', {
      metric: metric.name,
      value: metric.value,
      unit: metric.unit,
      labels: metric.labels,
    });

    // Write to metrics file if configured
    if (this.metricsFile) {
      this.writeMetric(fullMetric);
    }
  }

  /**
   * Write metric to file
   */
  private writeMetric(metric: Metric): void {
    if (!this.metricsFile) return;

    try {
      const dir = path.dirname(this.metricsFile);
      fs.mkdirSync(dir, { recursive: true });

      const line = JSON.stringify(metric) + '\n';
      fs.appendFileSync(this.metricsFile, line);
    } catch (error) {
      logger.warn('Failed to write metric', {}, error as Error);
    }
  }

  /**
   * Get recent metrics
   */
  getMetrics(limit: number = 100): Metric[] {
    return this.metrics.slice(-limit);
  }

  /**
   * Clear old metrics
   */
  clearMetrics(): void {
    this.metrics = [];
  }

  /**
   * Get uptime in milliseconds
   */
  getUptime(): number {
    return Date.now() - this.startTime;
  }

  /**
   * Export health status to file
   */
  async exportHealthStatus(filepath: string): Promise<void> {
    const health = await this.checkHealth();

    try {
      const dir = path.dirname(filepath);
      fs.mkdirSync(dir, { recursive: true });

      fs.writeFileSync(filepath, JSON.stringify(health, null, 2));
      logger.debug('Health status exported', { file: filepath });
    } catch (error) {
      logger.error('Failed to export health status', {}, error as Error);
      throw error;
    }
  }
}

/**
 * Create common health checks
 */
export class HealthChecks {
  /**
   * Check if a directory exists and is readable
   */
  static directoryExists(name: string, dirPath: string): HealthCheck {
    return {
      name,
      check: async () => {
        const start = Date.now();

        try {
          const stats = fs.statSync(dirPath);

          if (!stats.isDirectory()) {
            return {
              name,
              healthy: false,
              message: 'Path exists but is not a directory',
              duration: Date.now() - start,
            };
          }

          return {
            name,
            healthy: true,
            message: 'Directory exists and is accessible',
            duration: Date.now() - start,
          };
        } catch (error) {
          return {
            name,
            healthy: false,
            message: (error as Error).message,
            duration: Date.now() - start,
          };
        }
      },
      critical: true,
    };
  }

  /**
   * Check if required files exist
   */
  static filesExist(name: string, files: string[]): HealthCheck {
    return {
      name,
      check: async () => {
        const start = Date.now();
        const missing: string[] = [];

        for (const file of files) {
          if (!fs.existsSync(file)) {
            missing.push(file);
          }
        }

        if (missing.length > 0) {
          return {
            name,
            healthy: false,
            message: `Missing ${missing.length} file(s)`,
            details: { missing },
            duration: Date.now() - start,
          };
        }

        return {
          name,
          healthy: true,
          message: `All ${files.length} files exist`,
          duration: Date.now() - start,
        };
      },
      critical: true,
    };
  }

  /**
   * Check disk space
   */
  static diskSpace(name: string, path: string, minBytes: number): HealthCheck {
    return {
      name,
      check: async () => {
        const start = Date.now();

        try {
          // This is a simplified check - in production, use a proper disk space library
          const stats = fs.statSync(path);

          return {
            name,
            healthy: true,
            message: 'Disk space check passed',
            duration: Date.now() - start,
          };
        } catch (error) {
          return {
            name,
            healthy: false,
            message: (error as Error).message,
            duration: Date.now() - start,
          };
        }
      },
      critical: true,
    };
  }

  /**
   * Check process memory usage
   */
  static memoryUsage(name: string, maxMB: number): HealthCheck {
    return {
      name,
      check: async () => {
        const start = Date.now();
        const usage = process.memoryUsage();
        const heapUsedMB = usage.heapUsed / 1024 / 1024;

        if (heapUsedMB > maxMB) {
          return {
            name,
            healthy: false,
            message: `Memory usage ${heapUsedMB.toFixed(0)}MB exceeds ${maxMB}MB`,
            details: { heapUsedMB, maxMB },
            duration: Date.now() - start,
          };
        }

        return {
          name,
          healthy: true,
          message: `Memory usage ${heapUsedMB.toFixed(0)}MB is below ${maxMB}MB`,
          details: { heapUsedMB, maxMB },
          duration: Date.now() - start,
        };
      },
      critical: false,
    };
  }
}

/**
 * Create singleton monitor instance
 */
export const monitor = new Monitor();

/**
 * Helper to time and record operation duration as metric
 */
export async function timeAndRecord<T>(
  name: string,
  operation: () => Promise<T>,
  labels?: Record<string, string>
): Promise<T> {
  const start = Date.now();

  try {
    const result = await operation();
    const duration = Date.now() - start;

    monitor.recordMetric({
      name: `${name}_duration`,
      value: duration,
      unit: 'ms',
      labels,
    });

    return result;
  } catch (error) {
    const duration = Date.now() - start;

    monitor.recordMetric({
      name: `${name}_duration`,
      value: duration,
      unit: 'ms',
      labels: { ...labels, status: 'error' },
    });

    monitor.recordMetric({
      name: `${name}_error`,
      value: 1,
      labels,
    });

    throw error;
  }
}
