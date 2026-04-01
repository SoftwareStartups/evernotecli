# GitHub Actions

## SHA Pinning Policy

All actions pinned to **full 40-character commit SHAs**. Tags are mutable and can be hijacked — SHAs are immutable.

Format: `uses: owner/action@<full-sha>  # v1.2.3`

Find SHA for a version:
```bash
git ls-remote --tags https://github.com/<owner>/<repo>.git 'v4*' | sort -t/ -k3 -V | tail -1
```

Always verify the SHA matches the expected release tag before updating.

## Dependency Version Pins

- **npm packages** (`package.json`): use `^X.Y.Z` (bun resolves exact into lockfile)
- When adding or upgrading a GitHub Action, web-search the latest release tag and resolve to SHA before pinning

## CI Workflow (`workflows/ci.yml`)

- Triggers: push to any branch, PRs to `main`
- Jobs: lint-and-typecheck → unit-tests → build + integration-tests (parallel after gates)
- Permissions: `contents: read` only

## Release Workflow (`workflows/release.yml`)

- Triggers: push of `v*` tags
- Verifies CI passed for the tagged commit before building
- Matrix build: linux-x64, linux-arm64, darwin-x64, darwin-arm64
- Creates GitHub release with compiled binaries
