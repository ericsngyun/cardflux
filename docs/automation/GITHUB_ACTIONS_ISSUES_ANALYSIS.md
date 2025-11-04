# GitHub Actions Daily Update - Issues Analysis & Fixes

> **Date**: 2025-11-04
> **Status**: 🔴 **Workflow has critical issues**
> **User Report**: Receiving failure notifications on phone

---

## Critical Issues Identified

### ❌ **Issue #1: Missing Git LFS Pull**

**Problem**: Workflow checks out code but never pulls LFS files

**Line**: 30-34 in daily-update.yml
```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    token: ${{ secrets.GITHUB_TOKEN }}
    # ❌ MISSING: lfs: true
```

**Impact**:
- artifacts/faiss/one-piece-dinov2/index.faiss NOT downloaded (7.3 MB LFS file)
- artifacts/keypoints/one-piece/orb_keypoints.npz NOT downloaded (120 MB LFS file)
- Line 89 check fails: `[ -f "artifacts/faiss/one-piece-dinov2/index.faiss" ]` returns false
- Workflow incorrectly thinks data doesn't exist
- Runs full scrape instead of incremental update
- **Causes unnecessary work and potential failures**

**Fix**:
```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    token: ${{ secrets.GITHUB_TOKEN }}
    lfs: true  # ✅ ADD THIS
```

---

### ❌ **Issue #2: Wrong Python File Path**

**Problem**: Incremental pipeline uses wrong embedder script

**Line**: 110 in daily-update.yml (first-time full scrape)
```yaml
python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py
```

**Line**: 22 in package.json (incremental pipeline)
```json
"pipeline:embed:incremental": "python services/embedder/bin/embed_cards_incremental.py"
```

**Actual files**:
```
services/embedder/bin/
├── embed_cards.py
├── embed_cards_incremental.py  ← Generic (not One Piece specific)
├── embed_onepiece.py
├── embed_onepiece_dinov2.py
├── embed_onepiece_dinov2_fast.py
├── embed_onepiece_dinov2_optimized.py
└── embed_onepiece_dinov2_with_preprocessing.py  ← One Piece specific
```

**Impact**:
- Full scrape uses One Piece specific script ✅
- Incremental pipeline uses generic script that may not work for One Piece ❌
- **Inconsistent embedding generation**
- Potential failures during incremental updates

**Fix**: Use correct One Piece embedder in pipeline or make generic embedder work

---

### ❌ **Issue #3: Pipeline Commands Don't Match Package.json**

**Problem**: Workflow uses commands that don't exist

**Line**: 104 in daily-update.yml
```bash
cd services/ingest && pnpm tsx bin/tcgplayer-scraper-onepiece.ts
```

**Should be** (from package.json line 28):
```bash
pnpm tcgplayer:scrape  # OR: pnpm tsx services/ingest/bin/tcgplayer-scraper.ts
```

**Impact**:
- May work but inconsistent with project conventions
- Harder to maintain
- `cd` changes directory, making subsequent commands fragile

---

### ❌ **Issue #4: Requirements.txt File Doesn't Exist**

**Problem**: Workflow tries to install from non-existent file

**Line**: 58 in daily-update.yml
```yaml
pip install -r services/embedder/requirements.txt || true
```

**Actual location**: `requirements.txt` (root directory, not services/embedder/)

**Impact**:
- Command fails silently (`|| true`)
- May miss important dependencies
- EasyOCR might not be installed correctly

**Fix**: Use correct path
```yaml
pip install -r requirements.txt || true
```

---

### ⚠️ **Issue #5: No Git LFS Quota Management**

**Problem**: No handling of LFS bandwidth/storage limits

**GitHub LFS Free Tier**:
- Storage: 1 GB
- Bandwidth: 1 GB/month

**Current LFS Usage**:
- Keypoints: 120 MB
- Index: 7.3 MB
- Embeddings: 7.4 MB
- **Total: ~135 MB per game**

**Impact**:
- Daily workflow: ~135 MB download + ~135 MB upload = 270 MB/day
- Monthly: 270 MB × 30 = 8.1 GB bandwidth needed
- **Exceeds free tier by 8x** 🚨

**Calculation**:
- Each workflow run:
  1. `git checkout` with `lfs: true` → Download 135 MB
  2. `git push` → Upload modified LFS files (if changed)
  3. Daily updates typically change index + embeddings = ~15 MB uploads

**Realistic Monthly Bandwidth**:
- Downloads: 135 MB × 30 runs = 4.05 GB
- Uploads: 15 MB × 30 runs = 450 MB
- **Total: ~4.5 GB/month** (exceeds 1 GB free tier)

**Solutions**:
1. **Remove LFS files from repo** - Store artifacts elsewhere (S3, Releases, etc.)
2. **Upgrade to Git LFS Data Packs** - $5/month per 50 GB
3. **Reduce LFS usage** - Only track critical files
4. **Skip LFS downloads** if artifacts haven't changed

---

### ⚠️ **Issue #6: Cron Schedule Runs Twice Daily**

**Problem**: Two cron schedules run independently

**Line**: 9-10 in daily-update.yml
```yaml
- cron: '0 21 * * *'  # Summer schedule (PDT)
- cron: '0 22 * * *'  # Winter schedule (PST)
```

**Impact**:
- **Both cron jobs are active year-round**
- Workflow runs at 21:00 UTC **AND** 22:00 UTC every day
- **Two updates per day instead of one**
- Doubles bandwidth usage
- Unnecessary load on TCGPlayer API

**Fix**: Use single cron schedule in UTC, adjust for DST manually when needed

---

### ⚠️ **Issue #7: No Rate Limiting for TCGPlayer API**

**Problem**: No protection against hitting API rate limits

**Impact**:
- TCGPlayer may rate limit or block excessive requests
- No backoff/retry logic
- Workflow fails if rate limited

**Fix**: Add retry logic with exponential backoff

---

### ⚠️ **Issue #8: First-Time Scraper Uses Wrong Commands**

**Problem**: First-time scrape changes directories

**Line**: 104-108 in daily-update.yml
```bash
cd services/ingest && pnpm tsx bin/tcgplayer-scraper-onepiece.ts
cd services/ingest && pnpm tsx bin/fetch_images_onepiece.ts
```

**Issues**:
1. `cd` is fragile and changes working directory
2. Doesn't match package.json conventions
3. No error handling between commands

**Better approach**:
```bash
pnpm tsx services/ingest/bin/tcgplayer-scraper-onepiece.ts
pnpm tsx services/ingest/bin/fetch_images_onepiece.ts
```

---

## Failure Scenarios

### Scenario 1: LFS Files Not Downloaded
```
❌ Check if initial data exists
   → artifacts/faiss/one-piece-dinov2/index.faiss NOT FOUND
   → Triggers "Run initial full scrape"
   → Takes 30-60 minutes instead of 5 minutes
   → May hit API rate limits
   → Workflow times out or fails
```

### Scenario 2: LFS Bandwidth Exceeded
```
❌ Git LFS quota exceeded
   → git push fails with LFS bandwidth error
   → Changes not committed
   → Workflow fails
   → Data pipeline incomplete
```

### Scenario 3: Wrong Embedder Script
```
❌ Incremental pipeline runs generic embedder
   → embed_cards_incremental.py doesn't know about One Piece preprocessing
   → Embeddings don't match preprocessing (bilateral filter + contrast)
   → FAISS index corrupted
   → Identification accuracy drops
```

---

## Priority Fix List

### 🚨 **CRITICAL** (Must fix immediately)

1. **Add Git LFS pull**
   ```yaml
   lfs: true
   ```

2. **Fix LFS bandwidth issue**
   - Remove LFS tracking for large files
   - OR: Skip LFS downloads if not needed
   - OR: Use GitHub Releases for artifacts

3. **Fix cron schedule** (only one run per day)
   ```yaml
   - cron: '0 21 * * *'  # 2 PM PDT / 3 PM PST
   ```

### ⚠️ **HIGH** (Should fix soon)

4. **Fix embedder script path**
   - Use One Piece specific embedder consistently

5. **Fix requirements.txt path**
   ```yaml
   pip install -r requirements.txt
   ```

6. **Fix scraper commands**
   - Use pnpm scripts consistently

### 📝 **MEDIUM** (Nice to have)

7. Add API rate limiting
8. Add retry logic
9. Improve error handling
10. Add workflow status badge

---

## Recommended Solution: Remove LFS from Artifacts

**Problem**: Git LFS is expensive and causes workflow failures

**Solution**: Store artifacts outside Git LFS

### Option A: GitHub Releases (Recommended)

**Pros**:
- Free unlimited storage
- Simple API
- Versioned artifacts
- No bandwidth limits

**Workflow**:
1. Pipeline generates artifacts locally
2. Create GitHub Release (e.g., `artifacts-2025-11-04`)
3. Upload artifacts as release assets
4. Update workflow to download from latest release

**Implementation**:
```yaml
- name: Download artifacts from latest release
  run: |
    gh release download latest --pattern 'artifacts-*.tar.gz'
    tar -xzf artifacts-*.tar.gz
```

### Option B: External Storage (S3, Cloudflare R2)

**Pros**:
- Very cheap ($0.02/GB)
- Fast CDN delivery
- No GitHub limits

**Cons**:
- Requires external account
- More complex setup

### Option C: Keep LFS but Reduce Usage

**Strategy**:
1. Only track FAISS index (7.3 MB) - small enough
2. Remove keypoints from LFS (120 MB) - too large
3. Regenerate keypoints in workflow (45 seconds)

**Monthly bandwidth**: 7.3 MB × 30 × 2 = 438 MB < 1 GB ✅

---

## Fixed Workflow (Recommended Changes)

I'll create a fixed version with all critical issues resolved.

---

**Next Steps**:
1. Review issues and prioritize fixes
2. Choose LFS solution (Releases vs External Storage vs Reduce Usage)
3. Apply fixes to workflow
4. Test workflow manually
5. Monitor next automated run

---

**Maintained by**: CardFlux Team
**Last Updated**: 2025-11-04
**Status**: Issues Identified, Fixes Pending
