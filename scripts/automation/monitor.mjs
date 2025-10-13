#!/usr/bin/env node
/**
 * CardFlux Update Monitoring Dashboard
 *
 * Shows status of automated updates, logs, and system health
 *
 * Usage:
 *   node monitor.mjs              # Show dashboard
 *   node monitor.mjs --logs       # Show recent logs
 *   node monitor.mjs --watch      # Live monitoring
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '../..');
const LOGS_DIR = path.join(ROOT_DIR, 'logs/updates');
const BACKUPS_DIR = path.join(ROOT_DIR, 'backups');
const CONFIG_FILE = path.join(ROOT_DIR, 'config/update-scheduler.json');
const STATE_FILE = path.join(ROOT_DIR, 'data/state/incremental-pipeline.state.json');

class Monitor {
  constructor() {
    this.config = this.loadConfig();
  }

  loadConfig() {
    try {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
    } catch {
      return null;
    }
  }

  getSystemStatus() {
    const status = {
      config: {
        enabled: this.config?.enabled || false,
        updateTime: this.config?.schedule?.dailyUpdateTime || 'Not configured',
        games: []
      },
      lastUpdate: null,
      nextUpdate: null,
      health: {
        indices: {},
        backups: 0,
        logs: 0
      }
    };

    // Get enabled games
    if (this.config?.games) {
      for (const [game, gameConfig] of Object.entries(this.config.games)) {
        if (gameConfig.enabled) {
          status.config.games.push(game);
        }
      }
    }

    // Check indices
    for (const game of status.config.games) {
      const indexFile = path.join(ROOT_DIR, `artifacts/faiss/${game}-dinov2/index.faiss`);
      const metadataFile = path.join(ROOT_DIR, `artifacts/metadata/embeddings/${game}-dinov2/metadata.jsonl`);

      status.health.indices[game] = {
        indexExists: fs.existsSync(indexFile),
        metadataExists: fs.existsSync(metadataFile),
        cardCount: 0,
        lastModified: null
      };

      if (status.health.indices[game].indexExists) {
        const stats = fs.statSync(indexFile);
        status.health.indices[game].lastModified = stats.mtime;
      }

      if (status.health.indices[game].metadataExists) {
        const lines = fs.readFileSync(metadataFile, 'utf-8').split('\n').filter(l => l.trim());
        status.health.indices[game].cardCount = lines.length;
      }
    }

    // Count backups
    if (fs.existsSync(BACKUPS_DIR)) {
      const backups = fs.readdirSync(BACKUPS_DIR).filter(name => {
        const stat = fs.statSync(path.join(BACKUPS_DIR, name));
        return stat.isDirectory();
      });
      status.health.backups = backups.length;
    }

    // Get last update
    if (fs.existsSync(LOGS_DIR)) {
      const logs = fs.readdirSync(LOGS_DIR)
        .filter(name => name.startsWith('update-') && name.endsWith('.log'))
        .sort()
        .reverse();

      if (logs.length > 0) {
        const lastLog = path.join(LOGS_DIR, logs[0]);
        const stats = fs.statSync(lastLog);
        status.lastUpdate = {
          time: stats.mtime,
          log: logs[0]
        };
      }

      status.health.logs = logs.length;
    }

    // Calculate next update
    if (this.config?.enabled && this.config?.schedule?.dailyUpdateTime) {
      const [hours, minutes] = this.config.schedule.dailyUpdateTime.split(':').map(Number);
      const now = new Date();
      const next = new Date();
      next.setHours(hours, minutes, 0, 0);

      if (next <= now) {
        next.setDate(next.getDate() + 1);
      }

      status.nextUpdate = next;
    }

    return status;
  }

  printDashboard() {
    const status = this.getSystemStatus();

    console.clear();
    console.log('═'.repeat(80));
    console.log('  📊 CardFlux Update Monitor');
    console.log('═'.repeat(80));
    console.log('');

    // Configuration Status
    console.log('⚙️  Configuration:');
    console.log(`  Status: ${status.config.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    console.log(`  Schedule: Daily at ${status.config.updateTime}`);
    console.log(`  Games: ${status.config.games.join(', ') || 'None'}`);
    console.log('');

    // Update Status
    console.log('🔄 Update Status:');
    if (status.lastUpdate) {
      const elapsed = Date.now() - status.lastUpdate.time;
      const hours = Math.floor(elapsed / (1000 * 60 * 60));
      console.log(`  Last Update: ${status.lastUpdate.time.toLocaleString()} (${hours}h ago)`);
      console.log(`  Log File: ${status.lastUpdate.log}`);
    } else {
      console.log(`  Last Update: Never`);
    }

    if (status.nextUpdate) {
      const timeUntil = status.nextUpdate - Date.now();
      const hoursUntil = Math.floor(timeUntil / (1000 * 60 * 60));
      const minutesUntil = Math.floor((timeUntil % (1000 * 60 * 60)) / (1000 * 60));
      console.log(`  Next Update: ${status.nextUpdate.toLocaleString()} (in ${hoursUntil}h ${minutesUntil}m)`);
    }
    console.log('');

    // Health Status
    console.log('💚 System Health:');
    console.log(`  Backups: ${status.health.backups}`);
    console.log(`  Log Files: ${status.health.logs}`);
    console.log('');

    // Game Indices
    for (const [game, health] of Object.entries(status.health.indices)) {
      const indexStatus = health.indexExists ? '✅' : '❌';
      const metaStatus = health.metadataExists ? '✅' : '❌';

      console.log(`  ${game}:`);
      console.log(`    Index: ${indexStatus}  Metadata: ${metaStatus}  Cards: ${health.cardCount}`);
      if (health.lastModified) {
        console.log(`    Last Modified: ${health.lastModified.toLocaleString()}`);
      }
    }

    console.log('');
    console.log('─'.repeat(80));
    console.log('Commands:');
    console.log('  node monitor.mjs --logs     # View recent logs');
    console.log('  node monitor.mjs --watch    # Live monitoring (refreshes every 30s)');
    console.log('  node update-orchestrator.mjs  # Run update now');
    console.log('  node rollback.mjs           # Rollback to previous version');
    console.log('─'.repeat(80));
    console.log('');
  }

  showLogs() {
    if (!fs.existsSync(LOGS_DIR)) {
      console.log('❌ No logs directory found');
      return;
    }

    const logs = fs.readdirSync(LOGS_DIR)
      .filter(name => name.startsWith('update-') && name.endsWith('.log'))
      .sort()
      .reverse()
      .slice(0, 5);

    if (logs.length === 0) {
      console.log('No logs found');
      return;
    }

    console.log('═'.repeat(80));
    console.log('  📝 Recent Update Logs');
    console.log('═'.repeat(80));
    console.log('');

    for (const log of logs) {
      const logPath = path.join(LOGS_DIR, log);
      const stats = fs.statSync(logPath);

      console.log(`\n📄 ${log} (${stats.size} bytes)`);
      console.log(`   Created: ${stats.mtime.toLocaleString()}`);
      console.log('─'.repeat(80));

      // Show last 20 lines
      const content = fs.readFileSync(logPath, 'utf-8');
      const lines = content.split('\n').slice(-20);
      console.log(lines.join('\n'));
      console.log('');
    }
  }

  async watch() {
    console.log('🔍 Live monitoring enabled. Press Ctrl+C to exit.\n');

    const refresh = () => {
      this.printDashboard();
    };

    refresh();
    setInterval(refresh, 30000); // Refresh every 30 seconds

    // Keep process alive
    process.on('SIGINT', () => {
      console.log('\n👋 Monitoring stopped.\n');
      process.exit(0);
    });
  }
}

// Main
async function main() {
  const monitor = new Monitor();
  const args = process.argv.slice(2);

  if (args.includes('--logs')) {
    monitor.showLogs();
  } else if (args.includes('--watch')) {
    await monitor.watch();
  } else {
    monitor.printDashboard();
  }
}

main().catch(error => {
  console.error('❌ Error:', error);
  process.exit(1);
});
