/**
 * Pipeline status API for desktop app integration
 * Provides real-time pipeline status and progress tracking
 */

import * as fs from 'fs';
import * as path from 'path';
import { logger } from './logger.js';

export interface PipelineProgress {
  pipelineId: string;
  name: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'paused';
  currentStep?: string;
  totalSteps: number;
  completedSteps: number;
  progress: number; // 0-100
  startTime?: string;
  endTime?: string;
  duration?: number;
  error?: string;
  logs?: string[];
}

export interface StepProgress {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  progress: number; // 0-100
  startTime?: string;
  endTime?: string;
  duration?: number;
  error?: string;
  details?: Record<string, any>;
}

export class PipelineStatusManager {
  private statusFile: string;
  private status: PipelineProgress;
  private steps: Map<string, StepProgress> = new Map();

  constructor(pipelineName: string, statusDir: string, totalSteps: number) {
    this.statusFile = path.join(statusDir, `${pipelineName}.status.json`);

    this.status = {
      pipelineId: `${pipelineName}-${Date.now()}`,
      name: pipelineName,
      status: 'idle',
      totalSteps,
      completedSteps: 0,
      progress: 0,
      logs: [],
    };
  }

  /**
   * Start pipeline execution
   */
  start(): void {
    this.status.status = 'running';
    this.status.startTime = new Date().toISOString();
    this.save();

    logger.info('Pipeline started', {
      pipeline: this.status.name,
      pipelineId: this.status.pipelineId,
    });
  }

  /**
   * Start a pipeline step
   */
  startStep(stepName: string): void {
    const step: StepProgress = {
      name: stepName,
      status: 'running',
      progress: 0,
      startTime: new Date().toISOString(),
    };

    this.steps.set(stepName, step);
    this.status.currentStep = stepName;
    this.save();

    logger.info('Step started', {
      pipeline: this.status.name,
      step: stepName,
    });
  }

  /**
   * Update step progress
   */
  updateStepProgress(stepName: string, progress: number, details?: Record<string, any>): void {
    const step = this.steps.get(stepName);
    if (!step) return;

    step.progress = Math.min(100, Math.max(0, progress));
    if (details) {
      step.details = { ...step.details, ...details };
    }

    this.save();
  }

  /**
   * Complete a step
   */
  completeStep(stepName: string, details?: Record<string, any>): void {
    const step = this.steps.get(stepName);
    if (!step) return;

    step.status = 'completed';
    step.progress = 100;
    step.endTime = new Date().toISOString();

    if (step.startTime) {
      step.duration = new Date(step.endTime).getTime() - new Date(step.startTime).getTime();
    }

    if (details) {
      step.details = { ...step.details, ...details };
    }

    this.status.completedSteps++;
    this.status.progress = Math.round((this.status.completedSteps / this.status.totalSteps) * 100);

    this.save();

    logger.info('Step completed', {
      pipeline: this.status.name,
      step: stepName,
      duration: step.duration,
    });
  }

  /**
   * Fail a step
   */
  failStep(stepName: string, error: Error): void {
    const step = this.steps.get(stepName);
    if (!step) return;

    step.status = 'failed';
    step.error = error.message;
    step.endTime = new Date().toISOString();

    if (step.startTime) {
      step.duration = new Date(step.endTime).getTime() - new Date(step.startTime).getTime();
    }

    this.status.status = 'failed';
    this.status.error = `Step '${stepName}' failed: ${error.message}`;
    this.status.endTime = new Date().toISOString();

    this.save();

    logger.error('Step failed', {
      pipeline: this.status.name,
      step: stepName,
    }, error);
  }

  /**
   * Skip a step
   */
  skipStep(stepName: string, reason: string): void {
    const step: StepProgress = {
      name: stepName,
      status: 'skipped',
      progress: 100,
      details: { reason },
    };

    this.steps.set(stepName, step);
    this.status.completedSteps++;
    this.status.progress = Math.round((this.status.completedSteps / this.status.totalSteps) * 100);

    this.save();

    logger.info('Step skipped', {
      pipeline: this.status.name,
      step: stepName,
      reason,
    });
  }

  /**
   * Complete pipeline
   */
  complete(): void {
    this.status.status = 'completed';
    this.status.endTime = new Date().toISOString();

    if (this.status.startTime) {
      this.status.duration = new Date(this.status.endTime).getTime() - new Date(this.status.startTime).getTime();
    }

    this.save();

    logger.info('Pipeline completed', {
      pipeline: this.status.name,
      duration: this.status.duration,
    });

    // Clean up status file after completion
    setTimeout(() => this.cleanup(), 5000);
  }

  /**
   * Fail pipeline
   */
  fail(error: Error): void {
    this.status.status = 'failed';
    this.status.error = error.message;
    this.status.endTime = new Date().toISOString();

    if (this.status.startTime) {
      this.status.duration = new Date(this.status.endTime).getTime() - new Date(this.status.startTime).getTime();
    }

    this.save();

    logger.error('Pipeline failed', {
      pipeline: this.status.name,
      duration: this.status.duration,
    }, error);
  }

  /**
   * Pause pipeline
   */
  pause(): void {
    this.status.status = 'paused';
    this.save();

    logger.info('Pipeline paused', {
      pipeline: this.status.name,
    });
  }

  /**
   * Add log entry
   */
  addLog(message: string): void {
    if (!this.status.logs) {
      this.status.logs = [];
    }

    // Keep last 100 log entries
    this.status.logs.push(`[${new Date().toISOString()}] ${message}`);
    if (this.status.logs.length > 100) {
      this.status.logs.shift();
    }

    this.save();
  }

  /**
   * Get current status
   */
  getStatus(): PipelineProgress {
    return {
      ...this.status,
    };
  }

  /**
   * Get step statuses
   */
  getSteps(): StepProgress[] {
    return Array.from(this.steps.values());
  }

  /**
   * Save status to file
   */
  private save(): void {
    try {
      const dir = path.dirname(this.statusFile);
      fs.mkdirSync(dir, { recursive: true });

      const data = {
        ...this.status,
        steps: Array.from(this.steps.values()),
      };

      fs.writeFileSync(this.statusFile, JSON.stringify(data, null, 2));
    } catch (error) {
      logger.warn('Failed to save pipeline status', {}, error as Error);
    }
  }

  /**
   * Clean up status file
   */
  cleanup(): void {
    try {
      if (fs.existsSync(this.statusFile)) {
        fs.unlinkSync(this.statusFile);
        logger.debug('Pipeline status file cleaned up', {
          file: this.statusFile,
        });
      }
    } catch (error) {
      logger.warn('Failed to cleanup status file', {}, error as Error);
    }
  }

  /**
   * Load status from file
   */
  static load(statusFile: string): PipelineProgress | null {
    try {
      if (!fs.existsSync(statusFile)) {
        return null;
      }

      const content = fs.readFileSync(statusFile, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      logger.warn('Failed to load pipeline status', {}, error as Error);
      return null;
    }
  }

  /**
   * Get all active pipelines
   */
  static getActivePipelines(statusDir: string): PipelineProgress[] {
    try {
      if (!fs.existsSync(statusDir)) {
        return [];
      }

      const files = fs.readdirSync(statusDir)
        .filter(f => f.endsWith('.status.json'));

      const statuses: PipelineProgress[] = [];

      for (const file of files) {
        const status = PipelineStatusManager.load(path.join(statusDir, file));
        if (status) {
          statuses.push(status);
        }
      }

      return statuses;
    } catch (error) {
      logger.warn('Failed to get active pipelines', {}, error as Error);
      return [];
    }
  }
}
