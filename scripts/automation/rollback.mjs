#!/usr/bin/env node
/**
 * CardFlux Manual Rollback Utility
 *
 * Restores database to a previous backup
 *
 * Usage:
 *   node rollback.mjs                    # List available backups
 *   node rollback.mjs <backup-id>        # Rollback to specific backup
 *   node rollback.mjs --latest           # Rollback to most recent backup
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import * as readline from 'readline';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '../..');
const BACKUPS_DIR = path.join(ROOT_DIR, 'backups');
const ARTIFACTS_DIR = path.join(ROOT_DIR, 'artifacts');

class RollbackManager {
  constructor() {
    if (!fs.existsSync(BACKUPS_DIR)) {
      console.error('❌ Backups directory not found:', BACKUPS_DIR);
      process.exit(1);
    }
  }

  listBackups() {
    const backups = fs.readdirSync(BACKUPS_DIR)
      .map(name => {
        const backupPath = path.join(BACKUPS_DIR, name);
        const stats = fs.statSync(backupPath);

        if (!stats.isDirectory()) return null;

        // Parse backup name (format: game-YYYY-MM-DDTHH-MM-SS)
        const match = name.match(/^(.+?)-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})$/);
        const game = match ? match[1] : 'unknown';
        const timestamp = match ? match[2].replace(/-/g, ':').replace('T', ' ') : 'unknown';

        return {
          id: name,
          game,
          timestamp,
          created: stats.mtime,
          size: this.getDirectorySize(backupPath)
        };
      })
      .filter(Boolean)
      .sort((a, b) => b.created - a.created);

    return backups;
  }

  getDirectorySize(dirPath) {
    let totalSize = 0;

    const walk = (dir) => {
      const files = fs.readdirSync(dir);

      for (const file of files) {
        const filePath = path.join(dir, file);
        const stats = fs.statSync(filePath);

        if (stats.isDirectory()) {
          walk(filePath);
        } else {
          totalSize += stats.size;
        }
      }
    };

    walk(dirPath);
    return totalSize;
  }

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  }

  printBackups() {
    const backups = this.listBackups();

    if (backups.length === 0) {
      console.log('No backups found.');
      return;
    }

    console.log('\n📦 Available Backups:\n');
    console.log('─'.repeat(80));
    console.log('ID'.padEnd(35), 'Game'.padEnd(15), 'Created'.padEnd(20), 'Size');
    console.log('─'.repeat(80));

    for (const backup of backups) {
      console.log(
        backup.id.padEnd(35),
        backup.game.padEnd(15),
        backup.created.toLocaleString().padEnd(20),
        this.formatSize(backup.size)
      );
    }

    console.log('─'.repeat(80));
    console.log(`\nTotal: ${backups.length} backup(s)\n`);
  }

  async rollback(backupId) {
    const backupPath = path.join(BACKUPS_DIR, backupId);

    if (!fs.existsSync(backupPath)) {
      console.error(`❌ Backup not found: ${backupId}`);
      process.exit(1);
    }

    console.log('\n⚠️  ROLLBACK WARNING');
    console.log('═'.repeat(60));
    console.log(`This will restore the database from backup: ${backupId}`);
    console.log('Current data will be OVERWRITTEN.');
    console.log('═'.repeat(60));
    console.log('');

    const confirmed = await this.confirm('Are you sure you want to continue?');

    if (!confirmed) {
      console.log('\n❌ Rollback cancelled.\n');
      process.exit(0);
    }

    console.log('\n🔄 Starting rollback...\n');

    try {
      // Create a backup of current state before rollback
      console.log('📦 Creating safety backup of current state...');
      const safetyBackup = await this.createSafetyBackup();
      console.log(`✓ Safety backup created: ${safetyBackup}\n`);

      // Restore from backup
      const entries = fs.readdirSync(backupPath);

      for (const entry of entries) {
        const source = path.join(backupPath, entry);
        const dest = path.join(ARTIFACTS_DIR, entry);

        console.log(`📁 Restoring: ${entry}`);

        // Remove current data
        if (fs.existsSync(dest)) {
          fs.rmSync(dest, { recursive: true, force: true });
        }

        // Copy backup data
        await this.copyRecursive(source, dest);
        console.log(`  ✓ Restored`);
      }

      console.log('\n✅ Rollback completed successfully!');
      console.log(`\n📌 Safety backup saved at: ${safetyBackup}`);
      console.log('   You can delete this after verifying the rollback.\n');

    } catch (error) {
      console.error('\n❌ Rollback failed:', error.message);
      process.exit(1);
    }
  }

  async createSafetyBackup() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const backupId = `safety-${timestamp}`;
    const backupPath = path.join(BACKUPS_DIR, backupId);

    fs.mkdirSync(backupPath, { recursive: true });

    const artifactDirs = fs.readdirSync(ARTIFACTS_DIR);

    for (const dir of artifactDirs) {
      const source = path.join(ARTIFACTS_DIR, dir);
      const dest = path.join(backupPath, dir);

      if (fs.statSync(source).isDirectory()) {
        await this.copyRecursive(source, dest);
      }
    }

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

  async confirm(question) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise((resolve) => {
      rl.question(`${question} (yes/no): `, (answer) => {
        rl.close();
        resolve(answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y');
      });
    });
  }
}

// Main
async function main() {
  const manager = new RollbackManager();
  const args = process.argv.slice(2);

  console.log('═'.repeat(60));
  console.log('CardFlux Rollback Utility');
  console.log('═'.repeat(60));

  if (args.length === 0) {
    // List backups
    manager.printBackups();
    console.log('Usage:');
    console.log('  node rollback.mjs <backup-id>    # Rollback to specific backup');
    console.log('  node rollback.mjs --latest       # Rollback to most recent backup');
    console.log('');
    return;
  }

  let backupId = args[0];

  if (backupId === '--latest') {
    const backups = manager.listBackups();
    if (backups.length === 0) {
      console.error('\n❌ No backups available\n');
      process.exit(1);
    }
    backupId = backups[0].id;
    console.log(`\nUsing latest backup: ${backupId}\n`);
  }

  await manager.rollback(backupId);
}

main().catch(error => {
  console.error('❌ Error:', error);
  process.exit(1);
});
