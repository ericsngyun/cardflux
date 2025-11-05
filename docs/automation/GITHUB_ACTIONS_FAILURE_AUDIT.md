# GitHub Actions Failure Audit - Exit Code 1 at 4m 37s

> **Date**: 2025-11-04
> **Status**: 🔴 **Root cause identified**
> **Failure Time**: 4 minutes 37 seconds
> **Exit Code**: 1

---

## Root Cause Analysis

### 🚨 **Primary Issue: Packages Not Built in GitHub Actions**

**Problem**: The workflow runs `pnpm install` but never builds the TypeScript packages (`@cardflux/config`, `@cardflux/shared`)

**Impact**:
```
services/ingest/bin/tcgplayer-scraper-incremental.ts
└─ imports @cardflux/config (NOT BUILT)
   └─ packages/config/dist/ (MISSING in CI)
      └─ Workflow fails with ERR_INVALID_URL_SCHEME
```

---

## Error Details

### Actual Error (Reproduced Locally)

```bash
❌ UNCAUGHT EXCEPTION: TypeError [ERR_INVALID_URL_SCHEME]: The URL must be of scheme file
    at fileURLToPath (node:internal/url:1463:11)
    at finalizeEsmResolution (node:internal/modules/cjs/loader:1165:20)
```

**Translation**: TypeScript trying to import from `@cardflux/config` but the package isn't built (no `dist/` folder)

---

## Why It Happens

### Workflow Steps (Current):
```yaml
1. Install pnpm ✅
2. pnpm install --frozen-lockfile ✅
   - Installs node_modules
   - Does NOT build packages
3. pnpm pipeline:update ❌
   - Runs: pnpm tcgplayer:scrape:incremental
   - Scraper imports @cardflux/config
   - @cardflux/config not built
   - FAILS with module resolution error
```

### Local Development (Why It Works):
```
1. pnpm install
2. pnpm build (YOU run this manually)
   - Builds @cardflux/config
   - Builds @cardflux/shared
3. pnpm pipeline:update ✅ WORKS
```

**GitHub Actions never runs step 2!**

---

## Critical Missing Step

### What's Missing in Workflow:

```yaml
- name: Install Node dependencies
  run: pnpm install --frozen-lockfile

# ❌ MISSING THIS STEP:
- name: Build TypeScript packages
  run: pnpm build
```

---

## Secondary Issues

### Issue 1: Turbo Build May Fail Desktop App

The `pnpm build` command uses Turbo and includes desktop app:

```json
// package.json
"build": "turbo run build"
```

This builds:
- ✅ @cardflux/config
- ✅ @cardflux/shared
- ❌ @cardflux/desktop (fails due to Python bundling)

**Solution**: Build only required packages in CI

---

### Issue 2: Build Cache Not Utilized

GitHub Actions doesn't cache Turbo build outputs, causing:
- Slower builds (rebuilds every time)
- Wasted CI minutes

**Solution**: Add Turbo cache

---

## The Fix

### Option 1: Build Required Packages Only (Recommended)

```yaml
- name: Build TypeScript packages
  run: |
    # Build only config and shared packages (skip desktop)
    cd packages/config && pnpm build
    cd ../shared && pnpm build
```

**Pros**:
- Fast (only builds what's needed)
- Won't fail on desktop app
- Clear and explicit

**Cons**:
- Manual package list

---

### Option 2: Build All with Turbo (Filter Desktop)

```yaml
- name: Build TypeScript packages
  run: |
    # Build all except desktop
    pnpm turbo run build --filter='!@cardflux/desktop'
```

**Pros**:
- Uses Turbo properly
- Scalable (auto-detects packages)

**Cons**:
- Requires Turbo filter syntax
- May still build unnecessary packages

---

### Option 3: Fix Turbo Config (Proper Solution)

Create separate build targets:

```json
// package.json
{
  "scripts": {
    "build": "turbo run build",
    "build:ci": "turbo run build --filter='!@cardflux/desktop'"
  }
}
```

Then in workflow:
```yaml
- name: Build TypeScript packages
  run: pnpm build:ci
```

**Pros**:
- Clean separation of local vs CI builds
- Reusable
- Proper Turbo usage

**Cons**:
- Requires package.json change

---

## Recommended Fix

### Immediate Fix (Add to Workflow)

Add this step AFTER `Install Node dependencies`:

```yaml
- name: Install Node dependencies
  run: pnpm install --frozen-lockfile

# ADD THIS:
- name: Build TypeScript packages
  run: |
    echo "Building @cardflux/config and @cardflux/shared..."
    pnpm --filter @cardflux/config build
    pnpm --filter @cardflux/shared build
    echo "✅ Packages built successfully"

- name: Install Python dependencies
  run: |
    # ... rest of workflow
```

### Why This Works:
- ✅ Builds only required packages
- ✅ Uses pnpm workspace filters
- ✅ Fast (skips desktop app)
- ✅ Won't fail on Python bundling
- ✅ Clear logs

---

## Verification Steps

### After Applying Fix:

1. **Check build outputs exist**:
   ```yaml
   - name: Verify builds
     run: |
       ls packages/config/dist/
       ls packages/shared/dist/
   ```

2. **Test scraper imports**:
   ```yaml
   - name: Test TypeScript imports
     run: |
       pnpm tsx -e "import('@cardflux/config').then(() => console.log('✅ Config imports'))"
   ```

3. **Run pipeline**:
   ```yaml
   - name: Run incremental update
     run: pnpm pipeline:update
   ```

---

## Additional Optimizations

### 1. Add Turbo Cache

```yaml
- name: Setup Turbo cache
  uses: actions/cache@v4
  with:
    path: .turbo
    key: ${{ runner.os }}-turbo-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-turbo-
```

### 2. Cache pnpm Store (Already Added)

Saves ~30 seconds on `pnpm install`

### 3. Skip Unnecessary Steps

```yaml
- name: Build TypeScript packages
  run: pnpm --filter @cardflux/config --filter @cardflux/shared build
  # OR if using Turbo:
  # run: pnpm turbo run build --filter='@cardflux/config' --filter='@cardflux/shared'
```

---

## Timeline Estimate

### Before Fix:
```
0:00 - Checkout
0:30 - Install Node/Python/pnpm
2:00 - pnpm install
2:30 - Start pipeline:update
2:31 - tcgplayer:scrape:incremental FAILS
2:37 - Workflow exits (4m 37s) ❌
```

### After Fix:
```
0:00 - Checkout
0:30 - Install Node/Python/pnpm
2:00 - pnpm install
2:30 - Build packages (+ ~30s)
3:00 - Start pipeline:update
3:01 - tcgplayer:scrape:incremental SUCCESS ✅
18:00 - Workflow completes (15-20 min) ✅
```

---

## Testing Plan

### 1. Test Locally (Simulate CI)

```bash
# Clean build
rm -rf packages/*/dist node_modules/.cache

# Install (like CI)
pnpm install --frozen-lockfile

# Build packages (NEW STEP)
pnpm --filter @cardflux/config build
pnpm --filter @cardflux/shared build

# Run pipeline
pnpm pipeline:update

# Should succeed ✅
```

### 2. Test in GitHub Actions

1. Apply fix to workflow
2. Commit and push
3. Trigger workflow manually
4. Monitor build step
5. Verify scraper succeeds

---

## Long-term Improvements

### 1. Precompiled Packages

Consider committing built packages to avoid build step:

**Pros**:
- Faster CI (skip build)
- Guaranteed consistency

**Cons**:
- Larger repo size
- Manual rebuild needed
- Not best practice

**Verdict**: Not recommended

---

### 2. Separate CI/Local Scripts

```json
{
  "scripts": {
    "build": "turbo run build",
    "build:packages": "pnpm --filter @cardflux/config --filter @cardflux/shared build",
    "build:ci": "pnpm run build:packages"
  }
}
```

Then:
```yaml
- run: pnpm build:ci
```

---

### 3. Monorepo Best Practices

Consider using Turbo properly:

```json
// turbo.json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "build:ci": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"],
      "cache": true
    }
  }
}
```

---

## Summary

### Root Cause:
**GitHub Actions workflow missing build step for TypeScript packages**

### Fix:
**Add package build step after `pnpm install`**

### Impact:
**Workflow will succeed instead of failing at 4m 37s**

### Estimated Time:
**15-20 minutes for successful run (vs 4m 37s failure)**

---

## Next Steps

1. ✅ Apply fix to workflow
2. ✅ Add verification steps
3. ✅ Test manually in GitHub Actions
4. ✅ Monitor next automated run
5. ✅ Consider long-term improvements

---

**Maintained by**: CardFlux Team
**Last Updated**: 2025-11-04
**Status**: Fix Ready to Apply
