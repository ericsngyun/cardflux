# Git Hooks for CardFlux

This directory contains Git hooks that help maintain code quality by running automated checks before commits.

## Installation

### Automatic Installation

Run the installation script for your platform:

**macOS/Linux:**
```bash
chmod +x scripts/setup/install-hooks.sh
./scripts/setup/install-hooks.sh
```

**Windows (PowerShell):**
```powershell
pwsh scripts/setup/install-hooks.ps1
```

### Manual Installation

Copy the hooks to your `.git/hooks` directory:
```bash
cp scripts/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Pre-commit Hook

The pre-commit hook runs three checks before allowing a commit:

### 1. Prettier Format Check (🎨)
Ensures all TypeScript, JavaScript, and JSON files follow consistent formatting rules.

**Fix formatting issues:**
```bash
pnpm format
```

### 2. ESLint (🔧)
Checks for code quality issues and potential bugs.

**Fix linting issues:**
```bash
pnpm lint
```

### 3. TypeScript Type Check (📘)
Validates TypeScript types across the project (only runs if TypeScript files are staged).

**Fix type errors:**
- Resolve TypeScript errors in your code
- Run `pnpm typecheck` to see all errors

## Skipping Hooks

If you need to bypass the pre-commit hooks (not recommended for production code):

```bash
git commit --no-verify
```

**When to skip:**
- Work-in-progress commits on feature branches
- Emergency hotfixes (fix properly in next commit)
- Debugging (with intention to fix before pushing)

**When NOT to skip:**
- Main branch commits
- Pull request commits
- Release commits

## Troubleshooting

### Hook doesn't run
- Check if hook is executable: `ls -la .git/hooks/pre-commit`
- Re-run installation script
- Verify you're committing from repo root

### False positives
- Ensure you've run `pnpm install` to get latest dependencies
- Clear cache: `rm -rf node_modules && pnpm install`
- Check if issue exists in CI (not just locally)

### Performance
If hooks are slow:
- Type checking entire project on every commit (expected)
- Consider running only on changed files (future improvement)
- Use `--no-verify` for WIP commits, fix before final commit

## Updating Hooks

If hooks are updated in the repository:
1. Pull latest changes
2. Re-run installation script
3. Test with a dummy commit

## Contributing

When modifying hooks:
1. Test thoroughly on all platforms (Linux, macOS, Windows)
2. Ensure hooks fail fast with clear error messages
3. Document any new checks in this README
4. Update installation scripts if needed
