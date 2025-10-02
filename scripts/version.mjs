#!/usr/bin/env node
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

function getCurrentVersion() {
  const packagePath = path.join(process.cwd(), 'package.json');
  const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
  return pkg.version;
}

function bumpVersion(type = 'patch') {
  const current = getCurrentVersion();
  const [major, minor, patch] = current.split('.').map(Number);

  let newVersion;
  switch (type) {
    case 'major':
      newVersion = `${major + 1}.0.0`;
      break;
    case 'minor':
      newVersion = `${major}.${minor + 1}.0`;
      break;
    case 'patch':
    default:
      newVersion = `${major}.${minor}.${patch + 1}`;
      break;
  }

  return newVersion;
}

function updatePackageVersion(version) {
  const packagePath = path.join(process.cwd(), 'package.json');
  const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
  pkg.version = version;
  fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + '\n');
}

function gitTag(version) {
  try {
    execSync(`git tag -a v${version} -m "Release v${version}"`, { stdio: 'inherit' });
    console.log(`Created git tag v${version}`);
  } catch (error) {
    console.error('Failed to create git tag:', error.message);
  }
}

function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'patch';

  if (command === 'current') {
    console.log(getCurrentVersion());
    return;
  }

  const newVersion = bumpVersion(command);
  console.log(`Bumping version to ${newVersion}`);

  updatePackageVersion(newVersion);
  gitTag(newVersion);

  console.log(`Version updated to ${newVersion}`);
}

main();
