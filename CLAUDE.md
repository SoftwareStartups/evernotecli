# evercli

Bun-native TypeScript Evernote client with MCP server and CLI (`evercli`). Full read access and limited write access (create notes, tag notes, move notes). No edit/delete of existing note content. See `.github/CLAUDE.md` for CI/release and SHA pinning policy.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `EVERNOTE_TOKEN` | — | API token (overrides stored credentials) |
| `EVERNOTE_CONSUMER_KEY` | — | OAuth consumer key (for `evercli login` OAuth flow) |
| `EVERNOTE_CONSUMER_SECRET` | — | OAuth consumer secret (for `evercli login` OAuth flow) |
| `EVERNOTE_QUEUE_PATH` | `~/.config/evercli/queue` | Write queue backing store |
| `LOG_LEVEL` | `info` | Pino log level (output goes to stderr) |

Credentials are stored in `~/.config/evercli/config.json` via `evercli login`.

## Commands

```bash
# Setup
bun install                          # Install dependencies
task build                           # Compile TypeScript to build/
task clean                           # Remove build/ and dist/

# Quality
task lint                            # Lint with Biome
task format                          # Format with Biome (write)
task check                           # Lint + typecheck

# Tests
task test                            # Unit + integration tests (no token needed)
task test:unit                       # Unit tests only
task test:integration                # Integration tests only
task test:e2e                        # E2E tests (requires EVERNOTE_TOKEN)

# Pipelines
task ci                              # Full CI locally: clean→install→format:check→check→build→test

# Release
task compile                         # Build standalone binary for current platform
task thrift                          # Regenerate Thrift clients (requires Apache thrift compiler)

# Auth
bun run src/index.ts login           # Interactive login (OAuth or developer token)
bun run src/index.ts login --token T # Non-interactive login
bun run src/index.ts logout          # Remove stored credentials

# Run (dev, without compiling)
bun run src/index.ts --help          # Show CLI help
bun run src/index.ts serve           # Start MCP server
bun run src/index.ts search "query"  # Search notes
bun run src/index.ts notebooks       # List notebooks
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

## Key Design Decisions

- Generated Thrift clients from local IDL files via Apache `thrift --gen js:node,ts`; uses `thrift` npm package as runtime
- Store proxy pattern with Proxy auto-token-injection + retry with exponential backoff
- Token contains shard ID — note store URL constructed from it
- Required Thrift headers: `x-feature-version: 3`, `accept: application/x-thrift`
- Service layer (`service.ts`) shared between MCP tools and CLI commands
- `noteMetadataFromThrift()` keeps Thrift→model conversion centralized
- Rate limit errors: write commands enqueue via `service.enqueueWrite` (`evercli drain` replays); read commands surface a user-friendly message
- ENML parsing uses `fast-xml-parser` (Bun has no built-in XML parser)
