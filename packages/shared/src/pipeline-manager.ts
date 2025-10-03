/**
 * Pipeline management with rollback, resume, and health check capabilities
 */

import * as fs from 'fs';
import * as path from 'path';
import { logger, LogLevel } from './logger.js';

export interface PipelineStep {
  name: string;
  description: string;
  command: string;
  args: string[];
  healthCheck?: () => Promise<boolean>;
  skipIfExists?: string; // Skip if this file exists
  requiredFiles?: string[]; // Files that must exist before running
}

export interface PipelineState {
  pipelineId: string;
  startTime: string;
  lastCompletedStep?: string;
  completedSteps: string[];
  failedStep?: {
    name: string;
    error: string;
    timestamp: string;
  };
  status: 'running' | 'completed' | 'failed' | 'paused';
}

export interface PipelineResult {
  success: boolean;
  completedSteps: string[];
  failedStep?: string;
  error?: string;
  duration: number;
}

export class PipelineManager {
  private stateDir: string;
  private statePath: string;
  private state: PipelineState;

  constructor(pipelineName: string, stateDir: string) {
    this.stateDir = stateDir;
    this.statePath = path.join(stateDir, `${pipelineName}.pipeline.state.json`);

    // Load or create state
    this.state = this.loadState() || {
      pipelineId: `${pipelineName}-${Date.now()}`,
      startTime: new Date().toISOString(),
      completedSteps: [],
      status: 'running',
    };
  }

  /**
   * Load pipeline state from disk
   */
  private loadState(): PipelineState | null {
    if (!fs.existsSync(this.statePath)) {
      return null;
    }

    try {
      const content = fs.readFileSync(this.statePath, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      logger.warn('Failed to load pipeline state', {}, error as Error);
      return null;
    }
  }

  /**
   * Save pipeline state to disk
   */
  private saveState(): void {
    try {
      fs.mkdirSync(this.stateDir, { recursive: true });
      fs.writeFileSync(this.statePath, JSON.stringify(this.state, null, 2));
    } catch (error) {
      logger.error('Failed to save pipeline state', {}, error as Error);
    }
  }

  /**
   * Get current pipeline state
   */
  getState(): PipelineState {
    return { ...this.state };
  }

  /**
   * Check if step was already completed
   */
  isStepCompleted(stepName: string): boolean {
    return this.state.completedSteps.includes(stepName);
  }

  /**
   * Mark step as completed
   */
  markStepCompleted(stepName: string): void {
    if (!this.state.completedSteps.includes(stepName)) {
      this.state.completedSteps.push(stepName);
    }
    this.state.lastCompletedStep = stepName;
    this.saveState();
  }

  /**
   * Mark step as failed
   */
  markStepFailed(stepName: string, error: Error): void {
    this.state.failedStep = {
      name: stepName,
      error: error.message,
      timestamp: new Date().toISOString(),
    };
    this.state.status = 'failed';
    this.saveState();
  }

  /**
   * Mark pipeline as completed
   */
  markCompleted(): void {
    this.state.status = 'completed';
    this.saveState();
  }

  /**
   * Reset pipeline state (for fresh run)
   */
  reset(): void {
    this.state = {
      pipelineId: `${path.basename(this.statePath, '.pipeline.state.json')}-${Date.now()}`,
      startTime: new Date().toISOString(),
      completedSteps: [],
      status: 'running',
    };
    this.saveState();
  }

  /**
   * Run health checks for a step
   */
  async runHealthCheck(step: PipelineStep): Promise<boolean> {
    if (!step.healthCheck) {
      return true;
    }

    try {
      logger.debug(`Running health check for ${step.name}`);
      const healthy = await step.healthCheck();
      if (!healthy) {
        logger.warn(`Health check failed for ${step.name}`);
      }
      return healthy;
    } catch (error) {
      logger.error(`Health check error for ${step.name}`, {}, error as Error);
      return false;
    }
  }

  /**
   * Check if step should be skipped
   */
  shouldSkipStep(step: PipelineStep): boolean {
    // Skip if already completed
    if (this.isStepCompleted(step.name)) {
      logger.info(`Skipping ${step.name} (already completed)`);
      return true;
    }

    // Skip if output file exists
    if (step.skipIfExists && fs.existsSync(step.skipIfExists)) {
      logger.info(`Skipping ${step.name} (output exists)`, { file: step.skipIfExists });
      return true;
    }

    return false;
  }

  /**
   * Validate step prerequisites
   */
  validatePrerequisites(step: PipelineStep): { valid: boolean; missing?: string[] } {
    if (!step.requiredFiles || step.requiredFiles.length === 0) {
      return { valid: true };
    }

    const missing = step.requiredFiles.filter(file => !fs.existsSync(file));

    if (missing.length > 0) {
      logger.error(`Prerequisites missing for ${step.name}`, { missing });
      return { valid: false, missing };
    }

    return { valid: true };
  }

  /**
   * Create rollback point
   */
  createCheckpoint(stepName: string): void {
    const checkpointPath = path.join(
      this.stateDir,
      `checkpoint-${this.state.pipelineId}-${stepName}.json`
    );

    fs.writeFileSync(
      checkpointPath,
      JSON.stringify({
        step: stepName,
        timestamp: new Date().toISOString(),
        state: this.state,
      }, null, 2)
    );

    logger.debug(`Checkpoint created`, { step: stepName, file: checkpointPath });
  }

  /**
   * Clean up old checkpoints
   */
  cleanupCheckpoints(): void {
    try {
      const checkpointPattern = new RegExp(`checkpoint-${this.state.pipelineId}-.*\\.json`);
      const files = fs.readdirSync(this.stateDir);

      for (const file of files) {
        if (checkpointPattern.test(file)) {
          fs.unlinkSync(path.join(this.stateDir, file));
        }
      }

      logger.debug('Checkpoints cleaned up');
    } catch (error) {
      logger.warn('Failed to clean up checkpoints', {}, error as Error);
    }
  }

  /**
   * Get resume point (last successful step)
   */
  getResumePoint(): string | null {
    return this.state.lastCompletedStep || null;
  }
}

/**
 * Create a health check function for file existence
 */
export function fileExistsHealthCheck(filePath: string): () => Promise<boolean> {
  return async () => fs.existsSync(filePath);
}

/**
 * Create a health check function for directory size
 */
export function directorySizeHealthCheck(
  dirPath: string,
  minSize: number
): () => Promise<boolean> {
  return async () => {
    if (!fs.existsSync(dirPath)) {
      return false;
    }

    const files = fs.readdirSync(dirPath);
    return files.length >= minSize;
  };
}
