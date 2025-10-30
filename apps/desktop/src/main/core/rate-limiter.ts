/**
 * Rate Limiter
 *
 * Implements sliding window rate limiting to prevent DoS attacks via IPC request spam.
 * Each endpoint can have its own rate limit configuration.
 */

import { logger } from './logger';

interface RateLimitConfig {
  /** Maximum number of requests allowed in the window */
  maxRequests: number;
  /** Time window in milliseconds */
  windowMs: number;
  /** Optional custom error message */
  message?: string;
}

interface RequestRecord {
  timestamp: number;
}

/**
 * Sliding window rate limiter
 */
export class RateLimiter {
  private requests = new Map<string, RequestRecord[]>();

  constructor(private config: RateLimitConfig) {}

  /**
   * Check if request should be allowed
   * @param key - Unique identifier for the client/endpoint (e.g., endpoint name)
   * @returns true if allowed, false if rate limit exceeded
   */
  checkLimit(key: string): boolean {
    const now = Date.now();
    const windowStart = now - this.config.windowMs;

    // Get existing requests for this key
    let keyRequests = this.requests.get(key) || [];

    // Remove requests outside the current window
    keyRequests = keyRequests.filter(req => req.timestamp > windowStart);

    // Check if limit exceeded
    if (keyRequests.length >= this.config.maxRequests) {
      const oldestRequest = keyRequests[0];
      const timeUntilReset = Math.ceil((oldestRequest.timestamp + this.config.windowMs - now) / 1000);

      logger.warn('RateLimiter', `Rate limit exceeded for ${key}`, {
        limit: this.config.maxRequests,
        windowMs: this.config.windowMs,
        currentCount: keyRequests.length,
        resetIn: `${timeUntilReset}s`,
      });

      return false;
    }

    // Add current request
    keyRequests.push({ timestamp: now });
    this.requests.set(key, keyRequests);

    return true;
  }

  /**
   * Get current request count for a key
   */
  getCurrentCount(key: string): number {
    const now = Date.now();
    const windowStart = now - this.config.windowMs;
    const keyRequests = this.requests.get(key) || [];
    return keyRequests.filter(req => req.timestamp > windowStart).length;
  }

  /**
   * Reset rate limit for a key
   */
  reset(key: string): void {
    this.requests.delete(key);
  }

  /**
   * Cleanup old requests (call periodically to prevent memory leaks)
   */
  cleanup(): void {
    const now = Date.now();
    const cutoff = now - this.config.windowMs * 2; // Keep 2x window for safety

    for (const [key, requests] of this.requests.entries()) {
      const filtered = requests.filter(req => req.timestamp > cutoff);

      if (filtered.length === 0) {
        this.requests.delete(key);
      } else if (filtered.length < requests.length) {
        this.requests.set(key, filtered);
      }
    }

    const keysCount = this.requests.size;
    const totalRequests = Array.from(this.requests.values()).reduce((sum, reqs) => sum + reqs.length, 0);

    logger.debug('RateLimiter', 'Cleanup complete', {
      trackedKeys: keysCount,
      totalRequests,
    });
  }
}

/**
 * Create a rate limiter middleware for IPC handlers
 */
export function createRateLimitMiddleware(config: RateLimitConfig) {
  const limiter = new RateLimiter(config);

  // Cleanup every minute
  const cleanupInterval = setInterval(() => {
    limiter.cleanup();
  }, 60000);

  // Cleanup on process exit
  process.on('exit', () => {
    clearInterval(cleanupInterval);
  });

  return {
    limiter,
    /**
     * Wrap an IPC handler with rate limiting
     */
    wrap: <T extends (...args: any[]) => Promise<any>>(
      endpoint: string,
      handler: T
    ): T => {
      return (async (...args: any[]) => {
        // Check rate limit
        if (!limiter.checkLimit(endpoint)) {
          const message = config.message || 'Rate limit exceeded. Please slow down.';
          return { success: false, error: message, rateLimited: true };
        }

        // Call original handler
        return handler(...args);
      }) as T;
    },
  };
}
