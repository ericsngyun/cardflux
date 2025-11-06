# CI GitHub Actions Permissions Fix - 2025-11-06

## Problem

GitHub Actions workflow successfully creates commits but fails to push with **403 Forbidden** error:

```
Pushing changes to main...
remote: Write access to repository not granted.
fatal: unable to access 'https://github.com/ericsngyun/cardflux/': The requested URL returned error: 403
Error: Process completed with exit code 128.
```

The workflow completes all steps successfully:
1. ✅ Scrape data
2. ✅ Normalize cards
3. ✅ Download images
4. ✅ Build database
5. ✅ Generate embeddings
6. ✅ Build indices
7. ✅ Generate manifests
8. ✅ Commit changes locally
9. ❌ **Push fails with 403**

## Root Cause

**GitHub Actions `GITHUB_TOKEN` has read-only permissions by default.**

### Default Token Permissions

Since GitHub's [September 2023 security update](https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/), all workflows default to **read-only** permissions:

```yaml
permissions:
  contents: read      # Default
  pull-requests: read # Default
  issues: read        # Default
```

### Why Our Workflow Needs Write

The workflow needs to:
1. **Commit** updated card data
2. **Push** commits back to the main branch
3. Both require `contents: write` permission

### What Happened

```
Workflow → git commit (✓ succeeds, local only)
        → git push origin main (✗ fails, needs write permission)
        → 403 Forbidden
```

## Solution

Add explicit **write permissions** to the workflow job:

### Code Changes

**File**: `.github/workflows/daily-update.yml`

**Before:**
```yaml
jobs:
  update-database:
    runs-on: ubuntu-latest
    timeout-minutes: 240

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
```

**After:**
```yaml
jobs:
  update-database:
    runs-on: ubuntu-latest
    timeout-minutes: 240

    # Grant write permissions for pushing commits
    permissions:
      contents: write  # Allow git push

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
```

### Why This Works

The `permissions.contents: write` grants the `GITHUB_TOKEN` the ability to:
- ✅ Push commits to branches
- ✅ Create/update/delete files
- ✅ Create/update/delete branches
- ✅ Create/update/delete tags

## Security Considerations

### Is This Safe?

**YES** - The permission is safe because:

1. **Scoped to workflow only**: Only this workflow has write access, not all workflows
2. **No fork access**: Workflows from forked PRs cannot use this permission
3. **Scheduled/manual only**: Only runs on schedule or manual trigger (not on untrusted PR events)
4. **Audit trail**: All commits clearly marked as automated with bot author
5. **Revocable**: Can be removed at any time if concerns arise

### Permission Scope

The `contents: write` permission allows:
- ✅ Push to repository branches
- ✅ Create/modify/delete files
- ❌ Does NOT allow: Modify workflow files (requires separate permission)
- ❌ Does NOT allow: Access secrets from forks
- ❌ Does NOT allow: Modify repository settings

### Best Practices Followed

1. **Minimal permissions**: Only grant `contents: write`, nothing more
2. **Job-scoped**: Permission only applies to this job, not entire workflow
3. **Clear commit attribution**: Uses "CardFlux Bot" author with clear messages
4. **Documented**: This file explains why permission is needed

## Alternative Solutions Considered

### 1. Personal Access Token (PAT)
**Pros**: More control, can have longer expiry
**Cons**: Requires manual setup, security risk if leaked, needs rotation
**Decision**: REJECTED - GITHUB_TOKEN is simpler and more secure

### 2. Deploy Keys
**Pros**: Repository-specific, secure
**Cons**: Complex setup, requires manual key management
**Decision**: REJECTED - Overkill for automated updates

### 3. GitHub App
**Pros**: Fine-grained permissions, best practice for production
**Cons**: Requires app creation, installation, complex setup
**Decision**: FUTURE - Consider if we need more advanced features

### 4. Read-only workflow + Manual merge
**Pros**: No write permissions needed
**Cons**: Defeats purpose of automation, requires human intervention
**Decision**: REJECTED - Automation is the goal

## Testing

After applying this fix, the next workflow run should:

```
✅ Checkout code
✅ Pull LFS files
✅ Check data
✅ Run incremental update
✅ Commit changes
✅ Push changes (NO MORE 403!)
✅ Workflow succeeds
```

## Verification

To verify the fix is working:

1. **Check workflow runs**: Actions tab → Daily Card Database Update
2. **Look for successful push**: Should see "Changes committed and pushed" in logs
3. **Check commits**: Should see automated commits from "CardFlux Bot"
4. **No 403 errors**: Push step completes successfully

## Related GitHub Documentation

- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
- [Default Permissions Update](https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/)
- [Permission Scopes](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)

## Related Issues

This fix resolves the sixth GitHub Actions CI error after:
1. **TypeScript module resolution** (`CI_TYPESCRIPT_FIX.md`)
2. **Memory exhaustion** (`CI_MEMORY_FIX.md`)
3. **FAISS builder missing directory** (`CI_FAISS_BUILDER_FIX.md`)
4. **Git LFS pointer files** (`CI_GIT_LFS_FIX.md`)
5. **Gitignore temporary files** (`CI_GITIGNORE_FIX.md`)
6. **GitHub token permissions** (THIS FIX)

## Key Takeaway

**Always explicitly set `permissions:` in GitHub Actions workflows that need to write to the repository.**

**The default read-only permissions are a security best practice, but workflows that push commits need explicit `contents: write` permission.**

**Use minimal permissions - only grant what's needed for the workflow to function.**

---

**Fixed By**: Claude Code (Sonnet 4.5)
**Date**: 2025-11-06
**Impact**: Allows CI workflow to push automated database updates to the repository
**Files Changed**: 1 (`.github/workflows/daily-update.yml`)
**Security**: Safe - permission is scoped to workflow only, no fork access
