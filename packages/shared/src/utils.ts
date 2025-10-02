/**
 * Utility functions for CardFlux pipeline and desktop app.
 */

/**
 * Safe JSON parse with error handling
 * Returns null instead of throwing on invalid JSON
 */
export function safeJsonParse<T = any>(
  json: string,
  onError?: (error: Error, json: string) => void
): T | null {
  try {
    return JSON.parse(json) as T;
  } catch (error) {
    if (onError) {
      onError(error as Error, json);
    }
    return null;
  }
}

/**
 * Parse JSONL (JSON Lines) file with error handling
 * Skips corrupted lines instead of failing
 */
export function parseJsonLines<T = any>(
  content: string,
  onError?: (lineNumber: number, line: string, error: Error) => void
): { data: T[]; errors: number } {
  const lines = content.split('\n');
  const data: T[] = [];
  let errors = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Skip empty lines
    if (!line) continue;

    const parsed = safeJsonParse<T>(line, (error) => {
      errors++;
      if (onError) {
        onError(i + 1, line, error);
      }
    });

    if (parsed !== null) {
      data.push(parsed);
    }
  }

  return { data, errors };
}

/**
 * Retry a function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: {
    retries?: number;
    minDelay?: number;
    maxDelay?: number;
    factor?: number;
    onRetry?: (attempt: number, error: Error) => void;
  } = {}
): Promise<T> {
  const {
    retries = 3,
    minDelay = 1000,
    maxDelay = 30000,
    factor = 2,
    onRetry,
  } = options;

  let lastError: Error;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt === retries) {
        throw lastError;
      }

      const delay = Math.min(minDelay * Math.pow(factor, attempt), maxDelay);

      if (onRetry) {
        onRetry(attempt + 1, lastError);
      }

      await sleep(delay);
    }
  }

  throw lastError!;
}

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Clamp a number between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Check if a string is a valid URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Truncate string to max length with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength - 3) + '...';
}
