# Source Code

## Module Guide

- **index.ts** — CLI entry point (shebang + run)
- **config.ts** — Environment-based configuration (`EVERNOTE_` prefix)
- **logger.ts** — Pino logger (stderr transport, never stdout)
- **models.ts** — Zod schemas + `noteMetadataFromThrift()` converter
- **errors.ts** — Typed error hierarchy
- **service.ts** — Shared business logic used by both MCP server and CLI commands

### auth/

OAuth 1.0a flow: `oauth.ts` (flow logic), `token-store.ts` (OS keychain persistence), `callback-server.ts` (local HTTP server for OAuth redirect).

### client/

Thrift-backed Evernote API client:
- **evernote-client.ts** — High-level operations (search, get, create, tag, move)
- **store.ts** — Store proxy with `Proxy` auto-token-injection + exponential backoff retry + EDAM error conversion
- **queue.ts** — Persistent JSON-backed write queue for rate-limited operations
- **thrift-helpers.ts** — Thrift client creation, token shard parsing for note store URL

### edam/

Generated Thrift clients — **do not edit**. Regenerate with `task thrift` from `thrift/` IDL files.

### enml/

ENML (Evernote Markup Language) conversion: `to-markdown.ts`, `to-enml.ts`, `types.ts`. Uses `fast-xml-parser` (Bun has no built-in XML parser).

### server/

MCP server: `index.ts` (server setup), `read-tools.ts` (search, get notes/notebooks), `write-tools.ts` (create, tag, move).

### cli/

Clerc CLI framework: `app.ts` (command registration), `format.ts` (output formatting), `commands/*.ts` (individual commands).

## Key Patterns

- **Service layer sharing:** `service.ts` provides all business logic — both MCP tools and CLI commands delegate to it, never calling the client directly
- **Store proxy:** `Proxy` object auto-injects auth token into every Thrift call + retries with exponential backoff on transient errors
- **Token → shard:** Evernote tokens contain the shard ID; note store URL is constructed from it at runtime
- **Required Thrift headers:** `x-feature-version: 3`, `accept: application/x-thrift`
- **Rate limit handling:** Write commands enqueue via `service.enqueueWrite()` when rate-limited; `evercli drain` replays the queue
- **Model conversion:** `noteMetadataFromThrift()` centralizes Thrift→domain model mapping
