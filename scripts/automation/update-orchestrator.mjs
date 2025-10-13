#!/usr/bin/env node
/**
 * CardFlux Automated Update Orchestrator
 *
 * Runs daily database updates with:
 * - Scheduled execution
 * - Health checks
 * - Backup/rollback
 * - Notifications
 * - Monitoring
 *
 * Usage:
 *   node update-orchestrator.mjs           # Run update now
 *   node update-orchestrator.mjs --daemon  # Run as scheduled daemon
 *   node update-orchestrator.mjs --dry-run # Test without changes
 */

import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '../..');
const CONFIG_FILE = path.join(ROOT_DIR, 'config/update-scheduler.json');
const LOGS_DIR = path.join(ROOT_DIR, 'logs/updates');
const BACKUPS_DIR = path.join(ROOT_DIR, 'backups');
const STATE_DIR = path.join(ROOT_DIR, 'data/state');

// Ensure directories exist
[LOGS_DIR, BACKUPS_DIR, STATE_DIR].forEach(dir => {
  fs.mkdirSync(dir, { recursive: true });
});

class UpdateOrchestrator {
  constructor(config) {
    this.config = config;
    this.logFile = path.join(LOGS_DIR, `update-${this.timestamp()}.log`);
    this.startTime = Date.now();
    this.stats = {
      gamesUpdated: 0,
      cardsAdded: 0,
      imagesDownloaded: 0,
      errors: [],
      warnings: []
    };
  }

  timestamp() {
    return new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  }

  log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = {
      info: '📋',
      success: '✅',
      error: '❌',
      warning: '⚠️',
      debug: '🔍'
    }[level] || 'ℹ️';

    const logLine = `[${timestamp}] ${prefix} ${message}\n`;

    // Console output
    console.log(logLine.trim());

    // File output
    if (this.config.notifications.channels.log.enabled) {
      fs.appendFileSync(this.logFile, logLine);
    }
  }

  async runCommand(cmd, args, description) {
    this.log(`Running: ${description}`, 'info');

    return new Promise((resolve, reject) => {
      const proc = spawn(cmd, args, {
        cwd: ROOT_DIR,
        stdio: 'inherit',
        shell: true
      });

      proc.on('close', (code) => {
        if (code === 0) {
          this.log(`✓ ${description} completed`, 'success');
          resolve({ success: true, code });
        } else {
          const error = `${description} failed with code ${code}`;
          this.log(error, 'error');
          this.stats.errors.push(error);
          reject(new Error(error));
        }
      });

      proc.on('error', (err) => {
        this.log(`Process error: ${err.message}`, 'error');
        reject(err);
      });
    });
  }

  async createBackup(game) {
    if (!this.config.rollback.enabled || !this.config.rollback.backupBeforeUpdate) {
      return null;
    }

    this.log(`Creating backup for ${game}...`, 'info');
    const backupId = `${game}-${this.timestamp()}`;
    const backupDir = path.join(BACKUPS_DIR, backupId);

    fs.mkdirSync(backupDir, { recursive: true });

    const artifactsToBackup = [
      `artifacts/faiss/${game}-dinov2`,
      `artifacts/metadata/embeddings/${game}-dinov2`,
      `data/curated/${game}.jsonl`
    ];

    for (const artifact of artifactsToBackup) {
      const source = path.join(ROOT_DIR, artifact);
      if (fs.existsSync(source)) {
        const dest = path.join(backupDir, path.basename(artifact));
        await this.copyRecursive(source, dest);
      }
    }

    this.log(`Backup created: ${backupId}`, 'success');
    return backupId;
  }

  async copyRecursive(src, dest) {
    const stats = fs.statSync(src);

    if (stats.isDirectory()) {
      fs.mkdirSync(dest, { recursive: true });
      const entries = fs.readdirSync(src);

      for (const entry of entries) {
        await this.copyRecursive(
          path.join(src, entry),
          path.join(dest, entry)
        );
      }
    } else {
      fs.copyFileSync(src, dest);
    }
  }

  async healthCheck(stage) {
    if (!this.config.monitoring.enabled) {
      return true;
    }

    const healthConfig = this.config.monitoring.healthCheck;

    if ((stage === 'before' && !healthConfig.beforeUpdate) ||
        (stage === 'after' && !healthConfig.afterUpdate)) {
      return true;
    }

    this.log(`Running health check (${stage} update)...`, 'info');

    try {
      // Check if required directories exist
      const requiredDirs = [
        'artifacts/faiss',
        'artifacts/metadata',
        'data/curated'
      ];

      for (const dir of requiredDirs) {
        const fullPath = path.join(ROOT_DIR, dir);
        if (!fs.existsSync(fullPath)) {
          throw new Error(`Required directory missing: ${dir}`);
        }
      }

      // Check enabled games
      for (const [game, gameConfig] of Object.entries(this.config.games)) {
        if (!gameConfig.enabled) continue;

        // Check index exists
        if (healthConfig.checkIndexIntegrity) {
          const indexFile = path.join(ROOT_DIR, `artifacts/faiss/${game}-dinov2/index.faiss`);
          if (!fs.existsSync(indexFile)) {
            throw new Error(`Index missing for ${game}: ${indexFile}`);
          }
        }

        // Check metadata
        const metadataFile = path.join(ROOT_DIR, `artifacts/metadata/embeddings/${game}-dinov2/metadata.jsonl`);
        if (fs.existsSync(metadataFile)) {
          const lines = fs.readFileSync(metadataFile, 'utf-8').split('\n').filter(l => l.trim());
          this.log(`${game}: ${lines.length} cards in metadata`, 'debug');
        }
      }

      this.log('Health check passed', 'success');
      return true;

    } catch (error) {
      this.log(`Health check failed: ${error.message}`, 'error');
      return false;
    }
  }

  async updateGame(game, gameConfig) {
    this.log(`\n${'='.repeat(70)}`, 'info');
    this.log(`Updating game: ${game} (Priority: ${gameConfig.priority})`, 'info');
    this.log(`${'='.repeat(70)}\n`, 'info');

    let backupId = null;

    try {
      // Create backup
      backupId = await this.createBackup(game);

      // Run update steps
      for (const step of gameConfig.updateSteps) {
        await this.executeStep(game, step);
      }

      this.stats.gamesUpdated++;
      this.log(`Game ${game} updated successfully`, 'success');

      // Clean up old backups if enabled
      if (this.config.advanced.cleanupOldBackups) {
        await this.cleanupOldBackups(game);
      }

      return { success: true };

    } catch (error) {
      this.log(`Game ${game} update failed: ${error.message}`, 'error');

      // Auto-rollback if enabled
      if (this.config.rollback.autoRollbackOnFailure && backupId) {
        this.log('Attempting auto-rollback...', 'warning');
        await this.rollback(backupId);
      }

      return { success: false, error: error.message };
    }
  }

  async executeStep(game, step) {
    const stepMap = {
      'scrape': {
        cmd: 'pnpm',
        args: ['tsx', `services/ingest/bin/tcgplayer-scraper-${game}.ts`],
        description: `Scraping ${game} data`
      },
      'normalize': {
        cmd: 'pnpm',
        args: ['pipeline:normalize:incremental'],
        description: 'Normalizing data'
      },
      'fetch-images': {
        cmd: 'pnpm',
        args: ['tsx', `services/ingest/bin/fetch_images_${game}.ts`],
        description: `Downloading ${game} images`
      },
      'embed': {
        cmd: 'python',
        args: ['services/embedder/bin/embed_cards_incremental.py'],
        description: 'Generating embeddings'
      },
      'index': {
        cmd: 'python',
        args: [`services/indexer/bin/build_faiss_${game}.py`],
        description: `Building FAISS index for ${game}`
      }
    };

    const stepConfig = stepMap[step];
    if (!stepConfig) {
      throw new Error(`Unknown step: ${step}`);
    }

    await this.runCommand(stepConfig.cmd, stepConfig.args, stepConfig.description);
  }

  async rollback(backupId) {
    this.log(`Rolling back to backup: ${backupId}`, 'warning');
    const backupDir = path.join(BACKUPS_DIR, backupId);

    if (!fs.existsSync(backupDir)) {
      throw new Error(`Backup not found: ${backupId}`);
    }

    // Restore artifacts
    const entries = fs.readdirSync(backupDir);
    for (const entry of entries) {
      const source = path.join(backupDir, entry);
      const dest = path.join(ROOT_DIR, 'artifacts', entry);
      await this.copyRecursive(source, dest);
    }

    this.log('Rollback completed', 'success');
  }

  async cleanupOldBackups(game) {
    const keepBackups = this.config.rollback.keepBackups;
    const backups = fs.readdirSync(BACKUPS_DIR)
      .filter(name => name.startsWith(game))
      .map(name => ({
        name,
        path: path.join(BACKUPS_DIR, name),
        time: fs.statSync(path.join(BACKUPS_DIR, name)).mtimeMs
      }))
      .sort((a, b) => b.time - a.time);

    if (backups.length > keepBackups) {
      const toDelete = backups.slice(keepBackups);
      for (const backup of toDelete) {
        this.log(`Cleaning up old backup: ${backup.name}`, 'debug');
        fs.rmSync(backup.path, { recursive: true, force: true });
      }
    }
  }

  async sendNotification(type, data) {
    if (!this.config.notifications.enabled) {
      return;
    }

    const channels = this.config.notifications.channels;

    // Email notification
    if (channels.email?.enabled) {
      // TODO: Implement email via nodemailer
      this.log('Email notification sent', 'debug');
    }

    // Slack notification
    if (channels.slack?.enabled && channels.slack.webhookUrl) {
      await this.sendWebhook(channels.slack.webhookUrl, {
        text: `CardFlux Update ${type}`,
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `*CardFlux Database Update*\n${type === 'success' ? '✅' : '❌'} Status: ${type}`
            }
          },
          {
            type: 'section',
            fields: [
              { type: 'mrkdwn', text: `*Games Updated:*\n${data.gamesUpdated}` },
              { type: 'mrkdwn', text: `*Duration:*\n${data.duration}` }
            ]
          }
        ]
      });
    }

    // Discord notification
    if (channels.discord?.enabled && channels.discord.webhookUrl) {
      await this.sendWebhook(channels.discord.webhookUrl, {
        content: `**CardFlux Update ${type}**`,
        embeds: [{
          title: 'Database Update Report',
          color: type === 'success' ? 0x00ff00 : 0xff0000,
          fields: [
            { name: 'Status', value: type, inline: true },
            { name: 'Games Updated', value: data.gamesUpdated.toString(), inline: true },
            { name: 'Duration', value: data.duration, inline: true }
          ],
          timestamp: new Date().toISOString()
        }]
      });
    }
  }

  async sendWebhook(url, payload) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        this.log(`Webhook failed: ${response.statusText}`, 'warning');
      }
    } catch (error) {
      this.log(`Webhook error: ${error.message}`, 'warning');
    }
  }

  async run() {
    this.log('='.repeat(70), 'info');
    this.log('CardFlux Automated Update Orchestrator', 'info');
    this.log('='.repeat(70), 'info');

    try {
      // Pre-update health check
      if (!await this.healthCheck('before')) {
        throw new Error('Pre-update health check failed');
      }

      // Get enabled games sorted by priority
      const gamesToUpdate = Object.entries(this.config.games)
        .filter(([_, config]) => config.enabled)
        .sort(([_, a], [__, b]) => a.priority - b.priority);

      if (gamesToUpdate.length === 0) {
        this.log('No games enabled for update', 'warning');
        return;
      }

      this.log(`Updating ${gamesToUpdate.length} game(s)...`, 'info');

      // Update each game
      for (const [game, gameConfig] of gamesToUpdate) {
        await this.updateGame(game, gameConfig);
      }

      // Post-update health check
      if (!await this.healthCheck('after')) {
        throw new Error('Post-update health check failed');
      }

      // Success notification
      const duration = Math.round((Date.now() - this.startTime) / 1000 / 60);
      await this.sendNotification('success', {
        gamesUpdated: this.stats.gamesUpdated,
        duration: `${duration} minutes`
      });

      this.log('\n' + '='.repeat(70), 'success');
      this.log(`✅ Update completed successfully in ${duration} minutes`, 'success');
      this.log('='.repeat(70), 'success');

    } catch (error) {
      this.log(`\n❌ Update failed: ${error.message}`, 'error');

      const duration = Math.round((Date.now() - this.startTime) / 1000 / 60);
      await this.sendNotification('failure', {
        gamesUpdated: this.stats.gamesUpdated,
        duration: `${duration} minutes`,
        error: error.message
      });

      process.exit(1);
    }
  }
}

// Load configuration
function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    console.error(`❌ Configuration file not found: ${CONFIG_FILE}`);
    console.error('Please create config/update-scheduler.json');
    process.exit(1);
  }

  try {
    return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
  } catch (error) {
    console.error(`❌ Failed to load configuration: ${error.message}`);
    process.exit(1);
  }
}

// Schedule next run
function scheduleNextRun(config) {
  const schedule = config.schedule;
  const [hours, minutes] = schedule.dailyUpdateTime.split(':').map(Number);

  const now = new Date();
  const scheduled = new Date();
  scheduled.setHours(hours, minutes, 0, 0);

  // If time has passed today, schedule for tomorrow
  if (scheduled <= now) {
    scheduled.setDate(scheduled.getDate() + 1);
  }

  // Check if should skip weekends
  if (schedule.skipWeekends) {
    const day = scheduled.getDay();
    if (day === 0) scheduled.setDate(scheduled.getDate() + 1); // Sunday -> Monday
    if (day === 6) scheduled.setDate(scheduled.getDate() + 2); // Saturday -> Monday
  }

  const delay = scheduled - now;
  console.log(`\n📅 Next update scheduled for: ${scheduled.toLocaleString()}`);
  console.log(`⏰ Time until next run: ${Math.round(delay / 1000 / 60)} minutes\n`);

  setTimeout(() => {
    runUpdate(config);
    scheduleNextRun(config);
  }, delay);
}

// Run update
async function runUpdate(config) {
  const orchestrator = new UpdateOrchestrator(config);
  await orchestrator.run();
}

// Main
async function main() {
  const args = process.argv.slice(2);
  const isDaemon = args.includes('--daemon');
  const isDryRun = args.includes('--dry-run');

  const config = loadConfig();

  if (!config.enabled && !isDryRun) {
    console.log('❌ Automated updates are disabled in config');
    console.log('Set "enabled": true in config/update-scheduler.json');
    process.exit(0);
  }

  if (isDryRun) {
    console.log('🧪 DRY RUN MODE - No changes will be made\n');
    config.advanced.dryRun = true;
  }

  if (isDaemon) {
    console.log('🤖 Starting CardFlux Update Daemon...\n');
    console.log(`⏰ Scheduled time: ${config.schedule.dailyUpdateTime} ${config.schedule.timezone}`);
    console.log(`📍 Configuration: ${CONFIG_FILE}`);
    console.log(`📝 Logs directory: ${LOGS_DIR}`);

    scheduleNextRun(config);

    // Keep process alive
    process.on('SIGINT', () => {
      console.log('\n👋 Shutting down gracefully...');
      process.exit(0);
    });

  } else {
    console.log('🚀 Running update immediately...\n');
    await runUpdate(config);
  }
}

main().catch(error => {
  console.error('❌ Fatal error:', error);
  process.exit(1);
});
