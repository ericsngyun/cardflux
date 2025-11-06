# CI TypeScript Build Fix - 2025-11-06

## Problem

GitHub Actions CI was failing at the "Build TypeScript packages" step with the following errors:

```
Error: bin/build_sqlite_tcgplayer.ts(9,38): error TS2307: Cannot find module '@cardflux/config/tcgplayer-config' or its corresponding type declarations.
  There are types at '/home/runner/work/cardflux/cardflux/services/ingest/node_modules/@cardflux/config/dist/tcgplayer-config.d.ts', but this result could not be resolved under your current 'moduleResolution' setting. Consider updating to 'node16', 'nodenext', or 'bundler'.

Error: bin/build_sqlite.ts(20,34): error TS2307: Cannot find module '@cardflux/shared/types' or its corresponding type declarations.
```

## Root Cause

The TypeScript configuration in `services/ingest/tsconfig.json` was using the **legacy `moduleResolution: "node"`** setting, which doesn't understand:
1. **Package.json `exports` field** - Modern way to define package entry points
2. **Subpath exports** - Allowing imports like `@cardflux/shared/types`

The `@cardflux/config` and `@cardflux/shared` packages use modern package.json `exports` to define multiple entry points, which the old Node resolver couldn't handle.

## Solution

### Part 1: Update TypeScript Module Resolution

**File**: `services/ingest/tsconfig.json`

**Changed**:
```json
{
  "compilerOptions": {
    "module": "commonjs",           // OLD
    "moduleResolution": "node"      // OLD
  }
}
```

**To**:
```json
{
  "compilerOptions": {
    "module": "node16",             // NEW
    "moduleResolution": "node16"    // NEW
  }
}
```

**Why Node16?**
- Supports package.json `exports` field
- Understands subpath exports (`@cardflux/shared/types`)
- Compatible with CommonJS output (needed for our build)
- Modern standard for Node.js TypeScript projects

### Part 2: Add Missing Subpath Exports

**File**: `packages/shared/package.json`

**Added**:
```json
{
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "default": "./dist/index.js"
    },
    "./types": {                      // NEW
      "types": "./dist/types.d.ts",
      "default": "./dist/types.js"
    },
    "./schemas": {                    // NEW
      "types": "./dist/schemas.d.ts",
      "default": "./dist/schemas.js"
    }
  }
}
```

**Why?**
Code was importing `@cardflux/shared/types` and `@cardflux/shared/schemas`, but the package.json only exported the root `.` entry point. With `moduleResolution: "node16"`, TypeScript strictly enforces that all imports must be explicitly declared in `exports`.

### Part 3: Fix Buffer Type Issue

**File**: `services/ingest/bin/fetch_images_incremental.ts:102`

**Changed**:
```typescript
const buffer = Buffer.from(response.data);  // OLD - TypeScript error
```

**To**:
```typescript
const buffer = Buffer.isBuffer(response.data)
  ? response.data
  : Buffer.from(response.data as ArrayBuffer);  // NEW - type-safe
```

**Why?**
With stricter type checking from `node16`, TypeScript couldn't infer that `response.data` could be either `Buffer | ArrayBuffer`. The fix explicitly handles both cases.

## Testing

Build now succeeds locally:
```bash
$ cd packages/shared && pnpm build
✅ Success

$ cd services/ingest && pnpm build
✅ Success
```

## What This Fixes

✅ **Fixed**: `@cardflux/config/tcgplayer-config` imports
✅ **Fixed**: `@cardflux/shared/types` imports
✅ **Fixed**: `@cardflux/shared/schemas` imports
✅ **Fixed**: Buffer type safety in image fetcher
✅ **Ready**: GitHub Actions CI should now pass

## Prevention

To prevent this issue in the future:

### 1. Always Use Modern Module Resolution
All TypeScript projects should use:
```json
{
  "compilerOptions": {
    "module": "node16",           // or "nodenext"
    "moduleResolution": "node16"  // or "nodenext"
  }
}
```

Never use `"moduleResolution": "node"` (legacy).

### 2. Declare All Subpath Exports
When creating a package that exports multiple files:
```json
{
  "exports": {
    ".": "./dist/index.js",
    "./foo": "./dist/foo.js",     // Explicitly declare each subpath
    "./bar": "./dist/bar.js"
  }
}
```

Don't rely on implicit file resolution.

### 3. Test Builds in CI Environment
Always test TypeScript compilation in CI with strict settings to catch these issues early.

### 4. Use TypeScript 5.0+ Features
Modern TypeScript has better error messages for module resolution issues. Keep TypeScript up to date.

## Related Issues

This fix resolves the GitHub Actions failure that occurred after pushing commits:
- `5801831` - data: Update One Piece card database with OP13 sets
- `e02ca31` - feat(embeddings): Regenerate DINOv2 embeddings and FAISS index
- `8f82a6c` - perf(keypoints): Regenerate ORB keypoints cache
- `32e343c` - test: Add comprehensive test results
- `efe27be` - chore: Update Claude Code auto-allow permissions

## Key Takeaway

**The old `"moduleResolution": "node"` setting is deprecated and doesn't support modern package.json `exports`.**

**Always use `"moduleResolution": "node16"` or `"nodenext"` for new TypeScript projects.**

---

**Fixed By**: Claude Code (Sonnet 4.5)
**Date**: 2025-11-06
**Impact**: Unblocks GitHub Actions CI pipeline
**Files Changed**: 3 (tsconfig.json, package.json, fetch_images_incremental.ts)
