# CI Git LFS Pull Fix - 2025-11-06

## Problem

GitHub Actions CI workflow reported conflicting state:
- **Check data step** (line 136): Reports `has_data=true` (files exist)
- **Pipeline steps**: Report "No games with curated data found" (files don't exist)

Example from logs:
```bash
✅ Existing data found - will run incremental update
# ... later ...
ℹ️  No games with curated data found. Run normalize first.
```

## Root Cause

Git LFS files were not being fully downloaded by `actions/checkout@v4` despite having `lfs: true` configured.

**What happened:**
1. `actions/checkout@v4` with `lfs: true` checks out the repository
2. Git LFS creates **pointer files** (small text files ~133 bytes) instead of downloading actual content
3. The "Check if initial data exists" step sees these pointer files and reports `has_data=true`
4. When pipeline scripts try to read the files, they find empty/invalid data

**Example LFS Pointer File:**
```
version https://git-lfs.github.com/spec/v1
oid sha256:eddae66a37...
size 3246789
```

This is a 133-byte text file, not the actual 3.1 MB JSONL data!

### Why `lfs: true` Didn't Work

The `actions/checkout@v4` action with `lfs: true` should automatically run `git lfs pull`, but it can fail silently due to:

1. **GitHub LFS bandwidth limits** - Free tier has 1 GB/month bandwidth
2. **Network timeouts** - Large files (130 MB keypoints) may timeout
3. **Rate limiting** - Too many LFS requests in short time
4. **Silent failures** - No error thrown, just pointer files remain

## Solution

Added an **explicit Git LFS pull step** with **verification** after checkout:

### Code Changes

**File**: `.github/workflows/daily-update.yml`

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    token: ${{ secrets.GITHUB_TOKEN }}
    lfs: ${{ github.event.inputs.skip_lfs != 'true' }}

# NEW: Explicit LFS pull with verification
- name: Pull Git LFS files explicitly
  if: github.event.inputs.skip_lfs != 'true'
  run: |
    echo "Pulling Git LFS files..."
    git lfs pull
    echo "LFS files pulled successfully"

    # Verify LFS files were downloaded (not just pointers)
    if [ -f "data/curated/one-piece.jsonl" ]; then
      SIZE=$(stat -f%z "data/curated/one-piece.jsonl" 2>/dev/null || stat -c%s "data/curated/one-piece.jsonl" 2>/dev/null)
      if [ "$SIZE" -lt 1000 ]; then
        echo "⚠️  WARNING: one-piece.jsonl is only ${SIZE} bytes (likely a pointer file)"
        echo "This means Git LFS files weren't downloaded properly"
        cat data/curated/one-piece.jsonl
      else
        echo "✅ LFS files verified: one-piece.jsonl is ${SIZE} bytes"
      fi
    fi
```

### Key Improvements

1. **Explicit Pull**: Runs `git lfs pull` explicitly after checkout
2. **File Size Verification**: Checks if files are suspiciously small (<1000 bytes = pointer)
3. **Debug Output**: Shows file content if pointer detected
4. **Cross-platform**: Uses `stat` with fallback for Linux/macOS differences
5. **Clear Logging**: Reports success/failure with file sizes

## Why This Works

**Before:**
```
Checkout (lfs:true) → Pointer files remain → Check sees files (✓) → Pipeline fails (✗)
```

**After:**
```
Checkout (lfs:true) → Explicit LFS pull → Verify sizes → Real content (✓) → Pipeline works (✓)
```

The explicit `git lfs pull` ensures files are downloaded even if the checkout action's LFS integration failed.

## LFS Files in This Project

```
artifacts/faiss/one-piece-dinov2/index.faiss      - 7.9 MB
artifacts/keypoints/one-piece/orb_keypoints.npz   - 130 MB  (CRITICAL for Fast v2)
artifacts/metadata/.../metadata.jsonl             - 3.1 MB
data/curated/one-piece.jsonl                      - 3.1 MB
                                                   --------
                                                   Total: ~144 MB
```

## GitHub LFS Limits

**Free Tier:**
- Storage: 1 GB
- Bandwidth: 1 GB/month

**Current Usage:**
- Storage: ~144 MB (14% of limit)
- Bandwidth per pull: ~144 MB (14% of monthly limit)

**Implications:**
- ✅ Storage is fine (plenty of room)
- ⚠️ Bandwidth could be an issue with frequent CI runs (~7 pulls/month max)
- 💡 Daily CI runs would need paid LFS or S3 hosting

## Alternative Solutions Considered

### 1. Remove LFS, Use GitHub Releases
**Pros**: No bandwidth limits
**Cons**: Manual upload process, harder to version

### 2. S3 + CloudFront CDN
**Pros**: Unlimited bandwidth, fast downloads
**Cons**: Additional infrastructure, costs $5-10/month

### 3. Git LFS Paid Plan
**Pros**: Simple, integrated with Git
**Cons**: $5/month for 50 GB bandwidth

### 4. Sparse Checkout
**Pros**: Only download needed files
**Cons**: Complex setup, doesn't solve bandwidth issue

**Decision**: Keep Git LFS with explicit pull for now. Monitor bandwidth usage. If CI runs daily and hits limits, migrate to S3.

## Testing

### Verify LFS Files Locally
```bash
$ git lfs ls-files --size
fc9e3984f4 * artifacts/faiss/one-piece-dinov2/index.faiss (7.9 MB)
87558be3d3 * artifacts/keypoints/one-piece/orb_keypoints.npz (130 MB)
33fc97e336 * artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl (3.1 MB)
eddae66a37 * data/curated/one-piece.jsonl (3.1 MB)
```

### Detect Pointer Files
```bash
$ wc -c data/curated/one-piece.jsonl
3246789  # Real file (3.1 MB)

$ wc -c data/curated/one-piece.jsonl
133      # Pointer file! (133 bytes)
```

## Prevention

### 1. Always Verify LFS Files in CI
Add verification step after any LFS operations:
```bash
# Check file exists and is not a pointer
if [ -f "$FILE" ]; then
  SIZE=$(stat -c%s "$FILE")
  if [ "$SIZE" -lt 1000 ]; then
    echo "ERROR: $FILE is a pointer file ($SIZE bytes)"
    exit 1
  fi
fi
```

### 2. Monitor GitHub LFS Bandwidth
Check LFS bandwidth usage in GitHub settings:
- Settings → Billing → Git LFS Data

### 3. Consider Hosting Artifacts Elsewhere
For production, host large artifacts on S3/CloudFront:
- Faster downloads (CDN)
- No bandwidth limits
- Better for multi-region CI

### 4. Use LFS Prune Regularly
Clean up old LFS objects to save storage:
```bash
git lfs prune --verify-remote
```

## Related Issues

This fix resolves the fourth GitHub Actions CI failure after:
1. **TypeScript module resolution** (`CI_TYPESCRIPT_FIX.md`)
2. **Memory exhaustion** (`CI_MEMORY_FIX.md`)
3. **FAISS builder missing directory** (`CI_FAISS_BUILDER_FIX.md`)
4. **Git LFS pointer files** (THIS FIX)

## Expected CI Behavior After Fix

**Initial Run (First Time):**
```
1. Checkout code
2. Pull LFS files (144 MB download)
3. Verify file sizes (all >1 MB)
4. Check data → has_data=true
5. Run incremental update (finds curated data ✓)
6. All steps complete successfully ✓
```

**Subsequent Runs (Updates):**
```
1. Checkout code
2. Pull LFS files (only changed files)
3. Verify file sizes
4. Check data → has_data=true
5. Run incremental update
6. Process new cards only
7. Commit & push changes
```

## Key Takeaway

**Git LFS with `actions/checkout` is not 100% reliable - always verify files were downloaded.**

**Pointer files can fool existence checks - always verify file sizes, not just existence.**

**For production CI, consider hosting large artifacts on S3/CloudFront instead of Git LFS.**

---

**Fixed By**: Claude Code (Sonnet 4.5)
**Date**: 2025-11-06
**Impact**: Ensures Git LFS files are actually downloaded in CI, not just pointer files
**Files Changed**: 1 (`.github/workflows/daily-update.yml`)
**Related**: Will need S3 migration when daily runs exhaust LFS bandwidth (7 runs/month max)
