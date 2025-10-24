# AWS Deployment Guide - CardFlux Cloud Pipeline

**Date**: 2025-10-22
**Goal**: Deploy centralized data pipeline to AWS (S3 + CloudFront + GitHub Actions)
**Architecture**: Hybrid on-device recognition with cloud content delivery

---

## 🎯 Architecture Overview

Your **Technical Architecture Blueprint** is **excellent** and aligns perfectly with our current implementation! Here's how we'll map it to AWS:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLOUD INFRASTRUCTURE (AWS)                    │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ GitHub Actions (Daily Cron: 2 AM UTC)                          │ │
│  │                                                                  │ │
│  │  1. Scraper (pull_tcgcsv.ts)                                   │ │
│  │     → Fetch from tcgcsv.com (ETag, rate-limited)               │ │
│  │     → Incremental only                                          │ │
│  │                                                                  │ │
│  │  2. Image Canonicalization (fetch_images.ts)                   │ │
│  │     → Download high-quality PNGs                                │ │
│  │     → Resize to 1024px max, pad to 1024x736                    │ │
│  │     → Normalize: CLAHE, white balance                           │ │
│  │                                                                  │ │
│  │  3. Feature Generation (embedder service)                      │ │
│  │     → DINOv2 ViT-S/14: 384-dim embeddings                      │ │
│  │     → ORB: 1500 features per card                              │ │
│  │     → AKAZE: Fallback for low-texture cards                    │ │
│  │     → pHash + HSV histograms                                    │ │
│  │                                                                  │ │
│  │  4. FAISS Indexing (indexer service)                           │ │
│  │     → Desktop: HNSW32, float16                                  │ │
│  │     → Mobile: IVF4096,PQ32x8 (future)                          │ │
│  │                                                                  │ │
│  │  5. Content Pack Builder (publisher service)                   │ │
│  │     → Generate manifest.json (SemVer + checksums)              │ │
│  │     → Create .tar.gz archives                                   │ │
│  │     → Upload to S3                                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ AWS S3 (us-east-1)                                              │ │
│  │   Bucket: cardflux-databases                                    │ │
│  │                                                                  │ │
│  │   databases/                                                    │ │
│  │     manifest.json        ← Version info for all games           │ │
│  │     one-piece/                                                  │ │
│  │       v2025.01.22/                                              │ │
│  │         manifest.json    ← Game-specific metadata              │ │
│  │         images.tar.gz    ← 400 MB canonical images             │ │
│  │         faiss.index      ← 7 MB HNSW index                     │ │
│  │         metadata.tar.gz  ← 7 MB embeddings + features          │ │
│  │         delta/                                                  │ │
│  │           from-2025.01.17.tar.gz  ← Delta pack                 │ │
│  │     pokemon/             ← Future                               │ │
│  │     magic/               ← Future                               │ │
│  │                                                                  │ │
│  │   state/                 ← Pipeline state for incremental       │ │
│  │     pull_tcgcsv.state.json                                      │ │
│  │     embeddings.state.json                                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ CloudFront CDN (Global Edge Locations)                          │ │
│  │   Distribution ID: E1234567890ABC                               │ │
│  │   Domain: https://d1234567890.cloudfront.net                   │ │
│  │   Origin: cardflux-databases.s3.us-east-1.amazonaws.com        │ │
│  │   Cache: manifest.json (5 min), archives (1 year)              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTPS (CloudFront)
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
                  ▼               ▼               ▼
            ┌──────────┐    ┌──────────┐   ┌──────────┐
            │ Desktop  │    │ Desktop  │   │ Desktop  │
            │ App #1   │    │ App #2   │   │ App #N   │
            └──────────┘    └──────────┘   └──────────┘

            All apps sync from CDN (no direct TCGPlayer API)
            On-device recognition: 200ms avg latency
```

---

## 📋 Phase 1: AWS Account Setup

### 1.1 Create AWS Account

**If you don't have an AWS account:**
```bash
1. Go to https://aws.amazon.com/free/
2. Click "Create a Free Account"
3. Complete registration (credit card required, but Free Tier covers our usage)
```

**Free Tier Limits** (12 months):
- ✅ S3: 5 GB storage, 20,000 GET requests, 2,000 PUT requests/month
- ✅ CloudFront: 1 TB data transfer out, 10,000,000 HTTP requests/month
- ✅ GitHub Actions: Free (2,000 minutes/month for private repos)

**Our Usage** (estimate):
- S3: ~500 MB (One Piece only), grows to ~5 GB with 5 games
- CloudFront: ~100 GB/month (100 users × 1 GB/month)
- **Cost**: $0/month (Free Tier), then ~$20/month after 12 months

---

### 1.2 Create IAM User for GitHub Actions

**Security Best Practice**: Don't use root credentials!

```bash
# Step 1: Create IAM user via AWS Console
1. Go to IAM → Users → Add User
2. User name: github-actions-cardflux
3. Access type: ☑ Programmatic access (Access key ID + Secret)
4. Click "Next: Permissions"

# Step 2: Attach policies
1. Click "Attach existing policies directly"
2. Select:
   ☑ AmazonS3FullAccess
   ☑ CloudFrontFullAccess
3. Click "Next: Tags" → "Next: Review" → "Create User"

# Step 3: Save credentials
⚠️ CRITICAL: Download the CSV with:
   - Access Key ID: AKIAIOSFODNN7EXAMPLE
   - Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

Store these in GitHub Secrets (next section)
```

---

### 1.3 Create S3 Bucket

```bash
# Option A: AWS Console (Recommended)
1. Go to S3 → Create Bucket
2. Bucket name: cardflux-databases
3. Region: us-east-1 (US East N. Virginia)
4. Block Public Access: ☑ Keep all 4 checkboxes CHECKED (CloudFront will access privately)
5. Versioning: ☐ Disable (we use SemVer instead)
6. Encryption: ☑ Enable (SSE-S3)
7. Click "Create Bucket"

# Option B: AWS CLI (Advanced)
aws s3 mb s3://cardflux-databases --region us-east-1
aws s3api put-public-access-block \
  --bucket cardflux-databases \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

### 1.4 Create CloudFront Distribution

```bash
# Step 1: Go to CloudFront → Create Distribution
Origin Settings:
  - Origin Domain: cardflux-databases.s3.us-east-1.amazonaws.com
  - Origin Path: /databases (important!)
  - Name: S3-cardflux-databases
  - Origin Access: ☑ Origin Access Control (OAC) - Recommended
    → Create new OAC → Save
  - Enable Origin Shield: ☐ No (unnecessary for our scale)

Default Cache Behavior:
  - Viewer Protocol Policy: ☑ Redirect HTTP to HTTPS
  - Allowed HTTP Methods: ☑ GET, HEAD (read-only)
  - Cache Policy: CachingOptimized
  - Custom Headers: (none needed)

Distribution Settings:
  - Price Class: Use All Edge Locations (best performance)
  - Alternate Domain Names (CNAME): (leave empty for now, use CloudFront domain)
  - Default Root Object: manifest.json

Click "Create Distribution"

# Step 2: Update S3 Bucket Policy
⚠️ CloudFront will show a warning banner:
"The S3 bucket policy needs to be updated"

Click the "Copy Policy" button and:
1. Go to S3 → cardflux-databases → Permissions → Bucket Policy
2. Paste the policy
3. Click "Save changes"

# Step 3: Note your CloudFront Domain
Distribution Domain Name: d1234567890.cloudfront.net
⚠️ Save this! You'll use it in data-manager.ts

# Step 4: Wait for deployment (5-10 minutes)
Status will change: In Progress → Deployed
```

**CloudFront Cache Settings** (Important!):
```
Object: databases/manifest.json
  - TTL: 300 seconds (5 minutes) ← Frequent checks

Object: databases/one-piece/v*/images.tar.gz
  - TTL: 31536000 seconds (1 year) ← Immutable, versioned

Object: databases/one-piece/v*/faiss.index
  - TTL: 31536000 seconds (1 year) ← Immutable, versioned
```

---

## 📋 Phase 2: GitHub Repository Setup

### 2.1 Add GitHub Secrets

```bash
# Go to: Your Repo → Settings → Secrets and variables → Actions → New repository secret

Add 3 secrets:

1. AWS_ACCESS_KEY_ID
   Value: AKIAIOSFODNN7EXAMPLE (from IAM user creation)

2. AWS_SECRET_ACCESS_KEY
   Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY (from IAM user)

3. CLOUDFRONT_DISTRIBUTION_ID
   Value: E1234567890ABC (from CloudFront distribution)
```

---

### 2.2 Create GitHub Actions Workflow

**File**: `.github/workflows/data-pipeline.yml`

```yaml
name: Daily Data Pipeline

on:
  schedule:
    # Run daily at 2 AM UTC (off-peak)
    - cron: '0 2 * * *'
  workflow_dispatch: # Manual trigger

env:
  AWS_REGION: us-east-1
  S3_BUCKET: cardflux-databases

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 180 # 3 hours max

    steps:
      # ==========================================
      # SETUP
      # ==========================================
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Node dependencies
        run: pnpm install --frozen-lockfile

      - name: Install Python dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      # ==========================================
      # RESTORE STATE FROM S3
      # ==========================================
      - name: Download previous pipeline state
        run: |
          mkdir -p data/state
          aws s3 sync s3://${{ env.S3_BUCKET }}/state/ data/state/ || echo "No previous state found"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ env.AWS_REGION }}

      # ==========================================
      # DATA PIPELINE
      # ==========================================
      - name: 1. Pull TCGPlayer data (incremental)
        run: |
          pnpm --filter @cardflux/ingest run pull:tcgcsv
        env:
          RATE_LIMIT_DELAY: 1000 # 1 req/sec to be nice to TCGPlayer

      - name: 2. Fetch card images (incremental)
        run: |
          pnpm --filter @cardflux/ingest run fetch:images
        timeout-minutes: 60

      - name: 3. Generate DINOv2 embeddings (new cards only)
        run: |
          pnpm --filter @cardflux/embedder run embed
        env:
          BATCH_SIZE: 16 # Lower for CPU
          DEVICE: cpu
        timeout-minutes: 60

      - name: 4. Build FAISS indexes
        run: |
          pnpm --filter @cardflux/indexer run build
        timeout-minutes: 30

      - name: 5. Generate content packs
        run: |
          pnpm --filter @cardflux/publisher run package
        timeout-minutes: 30

      # ==========================================
      # PUBLISH TO S3
      # ==========================================
      - name: 6. Upload to S3
        run: |
          pnpm --filter @cardflux/publisher run publish
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ env.AWS_REGION }}
          S3_BUCKET: ${{ env.S3_BUCKET }}
        timeout-minutes: 60

      - name: 7. Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/databases/manifest.json"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ env.AWS_REGION }}

      # ==========================================
      # SAVE STATE TO S3
      # ==========================================
      - name: 8. Upload pipeline state
        if: always()
        run: |
          aws s3 sync data/state/ s3://${{ env.S3_BUCKET }}/state/
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ env.AWS_REGION }}

      # ==========================================
      # NOTIFICATIONS
      # ==========================================
      - name: Notify on success
        if: success()
        run: |
          echo "✅ Pipeline completed successfully"
          # TODO: Send Slack/email notification

      - name: Notify on failure
        if: failure()
        run: |
          echo "❌ Pipeline failed! Check logs."
          # TODO: Send Slack/email notification with error details
```

---

## 📋 Phase 3: Publisher Service Implementation

### 3.1 Create Publisher Package

**File**: `services/publisher/bin/package_content.ts`

```typescript
#!/usr/bin/env node
/**
 * Package content packs for distribution
 * Creates versioned .tar.gz archives with manifests
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import * as tar from 'tar';
import { logger } from '@cardflux/shared';

const DATA_DIR = path.resolve(__dirname, '../../../data');
const ARTIFACTS_DIR = path.resolve(__dirname, '../../../artifacts');
const DIST_DIR = path.resolve(__dirname, '../../../dist/content-packs');

interface GameManifest {
  game: string;
  version: string; // SemVer: YYYY.MM.DD
  cardCount: number;
  buildDate: string;
  files: {
    images: FileInfo;
    faiss: FileInfo;
    metadata: FileInfo;
  };
}

interface FileInfo {
  path: string;
  size: number;
  checksum: string; // sha256:hex
  url: string; // Will be filled by publisher
}

async function packageGame(game: string): Promise<GameManifest> {
  logger.info('Packaging', `Game: ${game}`);

  const version = new Date().toISOString().split('T')[0].replace(/-/g, '.');
  const gameDir = path.join(DIST_DIR, game, `v${version}`);

  // Create output directory
  fs.mkdirSync(gameDir, { recursive: true });

  // 1. Package images
  const imagesDir = path.join(DATA_DIR, 'images', game);
  const imagesTarPath = path.join(gameDir, 'images.tar.gz');

  logger.info('Packaging', `Creating ${imagesTarPath}`);
  await tar.c(
    {
      gzip: { level: 9 },
      file: imagesTarPath,
      cwd: path.dirname(imagesDir),
      portable: true,
    },
    [path.basename(imagesDir)]
  );

  // 2. Copy FAISS index
  const faissIndexSrc = path.join(ARTIFACTS_DIR, 'faiss', `${game}-dinov2`, 'index.faiss');
  const faissIndexDest = path.join(gameDir, 'faiss.index');
  fs.copyFileSync(faissIndexSrc, faissIndexDest);

  // 3. Package metadata (embeddings, orb descriptors, etc.)
  const metadataDir = path.join(ARTIFACTS_DIR, 'metadata', 'embeddings', `${game}-dinov2`);
  const metadataTarPath = path.join(gameDir, 'metadata.tar.gz');

  await tar.c(
    {
      gzip: { level: 9 },
      file: metadataTarPath,
      cwd: path.dirname(metadataDir),
      portable: true,
    },
    [path.basename(metadataDir)]
  );

  // 4. Calculate checksums and file info
  const files = {
    images: await getFileInfo(imagesTarPath, `databases/${game}/v${version}/images.tar.gz`),
    faiss: await getFileInfo(faissIndexDest, `databases/${game}/v${version}/faiss.index`),
    metadata: await getFileInfo(metadataTarPath, `databases/${game}/v${version}/metadata.tar.gz`),
  };

  // 5. Count cards
  const curatedFile = path.join(DATA_DIR, 'curated', `${game}.jsonl`);
  const cardCount = fs.readFileSync(curatedFile, 'utf-8').trim().split('\n').length;

  // 6. Create game manifest
  const manifest: GameManifest = {
    game,
    version,
    cardCount,
    buildDate: new Date().toISOString(),
    files,
  };

  const manifestPath = path.join(gameDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  logger.info('Packaging', `✓ Game packaged: ${game} v${version}`, {
    cardCount,
    totalSize: files.images.size + files.faiss.size + files.metadata.size,
  });

  return manifest;
}

async function getFileInfo(filePath: string, s3Key: string): Promise<FileInfo> {
  const stats = fs.statSync(filePath);
  const checksum = await calculateSHA256(filePath);

  return {
    path: s3Key,
    size: stats.size,
    checksum: `sha256:${checksum}`,
    url: `https://d1234567890.cloudfront.net/${s3Key}`, // Placeholder, update later
  };
}

async function calculateSHA256(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);

    stream.on('data', (data) => hash.update(data));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

async function generateMasterManifest(games: GameManifest[]): Promise<void> {
  const masterManifest: Record<string, GameManifest> = {};

  for (const game of games) {
    masterManifest[game.game] = game;
  }

  const manifestPath = path.join(DIST_DIR, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(masterManifest, null, 2));

  logger.info('Packaging', `✓ Master manifest created: ${manifestPath}`);
}

async function main() {
  logger.info('Packaging', 'Starting content pack builder');

  const enabledGames = ['one-piece']; // Add more as needed

  const manifests: GameManifest[] = [];

  for (const game of enabledGames) {
    const manifest = await packageGame(game);
    manifests.push(manifest);
  }

  await generateMasterManifest(manifests);

  logger.info('Packaging', '✓ All content packs built successfully');
}

main().catch((error) => {
  logger.error('Packaging', 'Fatal error', error);
  process.exit(1);
});
```

---

### 3.2 Create S3 Publisher

**File**: `services/publisher/bin/publish_to_s3.ts`

```typescript
#!/usr/bin/env node
/**
 * Upload content packs to S3
 */

import * as fs from 'fs';
import * as path from 'path';
import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import { CloudFrontClient, CreateInvalidationCommand } from '@aws-sdk/client-cloudfront';
import { logger } from '@cardflux/shared';

const DIST_DIR = path.resolve(__dirname, '../../../dist/content-packs');
const S3_BUCKET = process.env.S3_BUCKET || 'cardflux-databases';
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';
const CLOUDFRONT_DISTRIBUTION_ID = process.env.CLOUDFRONT_DISTRIBUTION_ID;

const s3 = new S3Client({ region: AWS_REGION });
const cloudfront = new CloudFrontClient({ region: AWS_REGION });

async function uploadFile(localPath: string, s3Key: string): Promise<void> {
  // Check if file already exists (skip if immutable version)
  try {
    await s3.send(new HeadObjectCommand({ Bucket: S3_BUCKET, Key: s3Key }));
    logger.info('Upload', `Skipping (already exists): ${s3Key}`);
    return;
  } catch (error) {
    // File doesn't exist, proceed with upload
  }

  const fileStream = fs.createReadStream(localPath);
  const stats = fs.statSync(localPath);

  logger.info('Upload', `Uploading: ${s3Key} (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);

  await s3.send(
    new PutObjectCommand({
      Bucket: S3_BUCKET,
      Key: s3Key,
      Body: fileStream,
      ContentType: getContentType(localPath),
      CacheControl: getCacheControl(s3Key),
      Metadata: {
        'upload-date': new Date().toISOString(),
      },
    })
  );

  logger.info('Upload', `✓ Uploaded: ${s3Key}`);
}

function getContentType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  const contentTypes: Record<string, string> = {
    '.json': 'application/json',
    '.tar.gz': 'application/gzip',
    '.gz': 'application/gzip',
    '.faiss': 'application/octet-stream',
  };
  return contentTypes[ext] || 'application/octet-stream';
}

function getCacheControl(s3Key: string): string {
  // Manifest: short cache (5 minutes)
  if (s3Key.endsWith('manifest.json')) {
    return 'public, max-age=300, must-revalidate';
  }

  // Versioned files: immutable, cache forever (1 year)
  if (s3Key.includes('/v20')) {
    return 'public, max-age=31536000, immutable';
  }

  // Default: 1 hour
  return 'public, max-age=3600';
}

async function uploadGame(game: string, version: string): Promise<void> {
  const gameDir = path.join(DIST_DIR, game, `v${version}`);

  if (!fs.existsSync(gameDir)) {
    throw new Error(`Game directory not found: ${gameDir}`);
  }

  logger.info('Upload', `Uploading game: ${game} v${version}`);

  // Upload all files in game directory
  const files = fs.readdirSync(gameDir);

  for (const file of files) {
    const localPath = path.join(gameDir, file);
    const s3Key = `databases/${game}/v${version}/${file}`;

    await uploadFile(localPath, s3Key);
  }
}

async function uploadMasterManifest(): Promise<void> {
  const manifestPath = path.join(DIST_DIR, 'manifest.json');
  await uploadFile(manifestPath, 'databases/manifest.json');
}

async function invalidateCloudFront(): Promise<void> {
  if (!CLOUDFRONT_DISTRIBUTION_ID) {
    logger.warn('Upload', 'CLOUDFRONT_DISTRIBUTION_ID not set, skipping invalidation');
    return;
  }

  logger.info('Upload', 'Invalidating CloudFront cache');

  await cloudfront.send(
    new CreateInvalidationCommand({
      DistributionId: CLOUDFRONT_DISTRIBUTION_ID,
      InvalidationBatch: {
        CallerReference: Date.now().toString(),
        Paths: {
          Quantity: 1,
          Items: ['/databases/manifest.json'],
        },
      },
    })
  );

  logger.info('Upload', '✓ CloudFront cache invalidated');
}

async function main() {
  logger.info('Upload', 'Starting S3 upload');

  // Read master manifest to get games and versions
  const manifestPath = path.join(DIST_DIR, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

  // Upload each game
  for (const [game, gameManifest] of Object.entries(manifest)) {
    await uploadGame(game, (gameManifest as any).version);
  }

  // Upload master manifest
  await uploadMasterManifest();

  // Invalidate CloudFront cache
  await invalidateCloudFront();

  logger.info('Upload', '✓ All files uploaded successfully');
}

main().catch((error) => {
  logger.error('Upload', 'Fatal error', error);
  process.exit(1);
});
```

---

### 3.3 Add package.json Scripts

**File**: `services/publisher/package.json`

```json
{
  "name": "@cardflux/publisher",
  "version": "1.0.0",
  "scripts": {
    "package": "tsx bin/package_content.ts",
    "publish": "tsx bin/publish_to_s3.ts"
  },
  "dependencies": {
    "@aws-sdk/client-s3": "^3.450.0",
    "@aws-sdk/client-cloudfront": "^3.450.0",
    "@cardflux/shared": "workspace:*",
    "tar": "^6.2.0"
  },
  "devDependencies": {
    "@types/tar": "^6.1.10",
    "tsx": "^4.7.0"
  }
}
```

---

## 📋 Phase 4: Update Desktop App

### 4.1 Update CDN URL

**File**: `apps/desktop/src/main/core/data-manager.ts`

```typescript
// Line 23-24: Update these URLs
const CDN_BASE_URL = 'https://d1234567890.cloudfront.net'; // ← YOUR CloudFront domain
const FALLBACK_CDN_URL = 'https://github.com/cardflux/cardflux-data/releases/latest/download';
```

---

### 4.2 Add Auto-Update Check on Startup

**File**: `apps/desktop/src/main/index.ts`

```typescript
// After line 102 (after dataManager.initialize())

// Check for updates on startup
const currentGame = 'one-piece'; // TODO: Get from user settings

if (dataManager.isUpdateAvailable(currentGame)) {
  const latestVersion = dataManager.manifest?.[currentGame]?.version;
  const installedVersion = dataManager.getInstalledVersion(currentGame);

  logger.info('App', 'Update available', {
    game: currentGame,
    installed: installedVersion,
    latest: latestVersion,
  });

  // Notify renderer
  mainWindow?.webContents.send('update-available', {
    game: currentGame,
    installed: installedVersion,
    latest: latestVersion,
  });
}
```

---

## 📋 Phase 5: Testing

### 5.1 Test GitHub Actions Workflow (Manually)

```bash
# Step 1: Push workflow to GitHub
git add .github/workflows/data-pipeline.yml
git commit -m "feat: Add GitHub Actions data pipeline workflow"
git push

# Step 2: Trigger manual run
1. Go to GitHub repo → Actions tab
2. Click "Daily Data Pipeline"
3. Click "Run workflow" → "Run workflow"
4. Wait 30-60 minutes for completion

# Step 3: Check S3 bucket
aws s3 ls s3://cardflux-databases/databases/ --recursive

Expected output:
databases/manifest.json
databases/one-piece/v2025.01.22/manifest.json
databases/one-piece/v2025.01.22/images.tar.gz
databases/one-piece/v2025.01.22/faiss.index
databases/one-piece/v2025.01.22/metadata.tar.gz
```

---

### 5.2 Test Desktop App Sync

```bash
# Step 1: Build desktop app
cd apps/desktop
pnpm build:dev

# Step 2: Start app
pnpm start

# Step 3: Check logs
# Look for:
# "DataManager: Manifest loaded" (success)
# "DataManager: Update available" (if newer version exists)

# Step 4: Trigger manual download (if update available)
# Click "Download Update" button in UI
# Monitor progress in logs
```

---

### 5.3 Verify CloudFront Distribution

```bash
# Test manifest download
curl -I https://d1234567890.cloudfront.net/databases/manifest.json

Expected headers:
HTTP/2 200
x-cache: Miss from cloudfront (first request)
x-cache: Hit from cloudfront (subsequent requests)
cache-control: public, max-age=300, must-revalidate

# Test content pack download
curl -I https://d1234567890.cloudfront.net/databases/one-piece/v2025.01.22/faiss.index

Expected headers:
HTTP/2 200
x-cache: Hit from cloudfront
cache-control: public, max-age=31536000, immutable
```

---

## 📊 Cost Breakdown

### AWS Free Tier (First 12 Months):
- ✅ S3: 5 GB storage, 20,000 GET, 2,000 PUT/month
- ✅ CloudFront: 1 TB transfer, 10,000,000 requests/month
- ✅ **Total**: $0/month

### After Free Tier:
- S3 Storage: 5 GB × $0.023/GB = $0.12/month
- S3 Requests: 100 users × 10 GET/day × 30 days × $0.0004/1000 = $0.12/month
- CloudFront: 100 GB transfer × $0.085/GB = $8.50/month
- **Total**: **~$9/month** for 100 users

### At Scale (1,000 users):
- S3: ~$1/month
- CloudFront: 1 TB transfer × $0.085/GB = $87/month
- **Total**: **~$88/month** for 1,000 users

---

## ✅ Deployment Checklist

### AWS Setup:
- [ ] AWS account created
- [ ] IAM user created with S3 + CloudFront permissions
- [ ] Access keys generated and saved
- [ ] S3 bucket created (`cardflux-databases`, us-east-1)
- [ ] CloudFront distribution created and deployed
- [ ] S3 bucket policy updated for CloudFront OAC

### GitHub Setup:
- [ ] GitHub secrets added (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CLOUDFRONT_DISTRIBUTION_ID)
- [ ] Workflow file created (`.github/workflows/data-pipeline.yml`)
- [ ] Workflow tested manually and succeeded

### Code Setup:
- [ ] Publisher package created (`services/publisher/`)
- [ ] `package_content.ts` implemented
- [ ] `publish_to_s3.ts` implemented
- [ ] Desktop app CDN URL updated
- [ ] Auto-update check added to app startup

### Testing:
- [ ] GitHub Actions workflow runs successfully
- [ ] Files appear in S3 bucket
- [ ] CloudFront serves files correctly
- [ ] Desktop app downloads manifest successfully
- [ ] Desktop app can download and install updates

---

## 🚀 Go Live!

Once all checklist items are complete:

1. **Schedule daily runs**: GitHub Actions will run automatically at 2 AM UTC
2. **Monitor first few runs**: Check logs for any errors
3. **Deploy desktop app**: Release new version with CloudFront URL
4. **Announce to users**: "Automatic updates now available!"

---

**Estimated Time**: 1-2 days to complete full deployment
**Difficulty**: Medium (mostly configuration, minimal coding)
**Risk**: Low (can rollback easily, Free Tier covers testing)

Ready to deploy? Let me know if you need help with any specific step!
