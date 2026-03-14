# CLAUDE.md

## Project Overview

Bun-native TypeScript Evernote client with MCP server and CLI (`evercli`). Full read access and limited write access (create notes, tag notes, move notes). No edit/delete of existing note content.

## Commands

```bash
bun install                          # Install dependencies
task build                           # Compile TypeScript to build/
task clean                           # Remove build/ and dist/
task lint                            # Lint with Biome
task format                          # Format with Biome (write)
task format:check                    # Check formatting (no write)
task typecheck                       # Type check with TypeScript
task check                           # Lint + typecheck
task test                            # Run unit + integration tests (no token needed)
task test:unit                       # Unit tests only
task test:integration                # Integration tests only
task test:e2e                        # E2E tests (requires EVERNOTE_TOKEN)
task test:all                        # All tests including e2e
task ci                              # Full CI pipeline locally (clean→format:check→check→build→test)
task thrift                          # Regenerate Thrift clients (requires thrift compiler)
task compile                         # Build standalone binary (current platform)
task compile:all                     # Build binaries for all platforms
bun run src/index.ts --help          # Show CLI help
bun run src/index.ts serve           # Start MCP server
bun run src/index.ts notebooks       # List notebooks
bun run src/index.ts search "query"  # Search notes
bun run src/index.ts drain           # Process queued write operations
```

## Architecture

```text
src/
├── index.ts           # CLI entry point
├── config.ts          # Environment-based configuration (EVERNOTE_ env prefix)
├── logger.ts          # Pino logger (stderr transport)
├── models.ts          # Zod schemas + noteMetadataFromThrift()
├── errors.ts          # Error type hierarchy
├── service.ts         # Shared business logic (MCP + CLI)
├── auth/              # OAuth 1.0a flow (oauth.ts, token-store.ts, callback-server.ts)
├── client/
│   ├── evernote-client.ts  # High-level API client
│   ├── queue.ts            # Persistent write queue (JSON-backed)
│   ├── store.ts            # Store proxy, retry, EDAM error conversion
│   └── thrift-helpers.ts   # Thrift client creation, token shard parsing
├── edam/              # Generated Thrift clients — do not edit (run `task thrift`)
├── enml/              # ENML ↔ Markdown conversion (to-markdown.ts, to-enml.ts, types.ts)
├── server/            # MCP server: index.ts, read-tools.ts, write-tools.ts
└── cli/               # Clerc CLI: app.ts, format.ts, commands/*.ts
```

## Test Structure

```text
tests/
├── helpers/                 # Factories: makeNote, makeTag, makeNotebook, makeSearchResult
│   ├── test-data.ts
│   └── test-utils.ts
├── unit/                    # Pure logic tests (no service layer)
├── integration/             # Service layer with mocked client
└── e2e/                     # Live API tests (requires EVERNOTE_TOKEN)
```

## Key Design Decisions

- Generated Thrift clients from local IDL files via Apache `thrift --gen js:node,ts`; uses `thrift` npm package as runtime
- Store proxy pattern with Proxy auto-token-injection + retry with exponential backoff
- Token contains shard ID — note store URL constructed from it
- Required Thrift headers: `x-feature-version: 3`, `accept: application/x-thrift`
- Service layer (`service.ts`) shared between MCP tools and CLI commands
- `noteMetadataFromThrift()` keeps Thrift→model conversion centralized
- Rate limit errors: write commands enqueue via `service.enqueueWrite` (`evercli drain` replays); read commands surface a user-friendly message
- ENML parsing uses `fast-xml-parser` (Bun has no built-in XML parser)

## Code Style

- TypeScript strict mode, ES2022 target, NodeNext modules
- Biome for linting/formatting (indent 2, single quotes, semicolons, trailing commas es5)
- Bun runtime and test runner

## Dependency Version Pins

Always use fully qualified versions — never floating major/minor tags:

- **npm packages** (`package.json`): use `^X.Y.Z` (bun resolves exact into lockfile)
- **GitHub Actions**: always pin to exact `vX.Y.Z` tags, never `@v3` or `@main`
  - Current pins: `actions/checkout@v6.0.2`, `oven-sh/setup-bun@v2.1.3`, `actions/cache@v5.0.3`, `actions/upload-artifact@v7.0.0`, `actions/download-artifact@v8.0.1`, `softprops/action-gh-release@v2.5.0`
  - When adding a new action or upgrading, web-search the latest release tag before pinning
