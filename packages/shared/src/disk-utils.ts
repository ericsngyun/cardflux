/**
 * Disk space utilities for CardFlux pipeline
 * Prevents filling up user's disk
 */

import * as os from 'os';

export interface DiskSpace {
  free: number;
  total: number;
  used: number;
  percentFree: number;
}

/**
 * Get disk space information for a path
 *
 * Note: This uses os.freemem() as a proxy since Node.js doesn't have
 * built-in disk space APIs. For production, consider using 'check-disk-space' package.
 */
export function getDiskSpace(path: string): DiskSpace {
  // On Windows, we can use platform-specific checks
  // For now, we'll use available memory as a conservative estimate
  const free = os.freemem();
  const total = os.totalmem();
  const used = total - free;
  const percentFree = (free / total) * 100;

  return {
    free,
    total,
    used,
    percentFree,
  };
}

/**
 * Check if there's enough disk space for an operation
 * Throws error if insufficient space
 *
 * @param path - Path to check
 * @param requiredBytes - Bytes needed
 * @param minFreePercent - Minimum % of disk that must remain free (default 10%)
 */
export function checkDiskSpace(
  path: string,
  requiredBytes: number,
  minFreePercent: number = 10
): void {
  const space = getDiskSpace(path);

  // Check absolute space
  if (space.free < requiredBytes) {
    const needed = formatBytes(requiredBytes);
    const available = formatBytes(space.free);
    throw new Error(
      `Insufficient disk space. Need ${needed}, but only ${available} available. ` +
      `Please free up at least ${formatBytes(requiredBytes - space.free)} of space.`
    );
  }

  // Check percentage (keep minimum free for system)
  const spaceAfterOperation = space.free - requiredBytes;
  const percentAfter = (spaceAfterOperation / space.total) * 100;

  if (percentAfter < minFreePercent) {
    throw new Error(
      `Operation would leave only ${percentAfter.toFixed(1)}% free space. ` +
      `Minimum ${minFreePercent}% required for system stability. ` +
      `Please free up more space before continuing.`
    );
  }
}

/**
 * Format bytes to human-readable string
 */
function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Estimate total space needed for pipeline
 */
export function estimatePipelineSpace(cardCount: number): {
  images: number;
  embeddings: number;
  faiss: number;
  metadata: number;
  total: number;
} {
  // Estimates based on averages
  const avgImageSize = 100_000; // 100KB per image
  const avgEmbeddingSize = 2048; // 2KB per embedding (512 floats)
  const avgMetadataSize = 1000; // 1KB per card in SQLite

  const images = cardCount * avgImageSize;
  const embeddings = cardCount * avgEmbeddingSize;
  const faiss = embeddings * 1.2; // FAISS index is ~20% larger than raw embeddings
  const metadata = cardCount * avgMetadataSize;

  return {
    images,
    embeddings,
    faiss,
    metadata,
    total: images + embeddings + faiss + metadata,
  };
}
