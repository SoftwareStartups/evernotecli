# Tests

## Structure

```text
tests/
├── unit/           # No external dependencies, fast
│   ├── errors/     # Error type hierarchy
│   ├── auth/       # Keychain, callback server
│   ├── client/     # Store proxy, queue, Thrift helpers
│   ├── cli/        # Command output, formatting
│   └── enml/       # ENML ↔ Markdown conversion
├── integration/    # Mocked Evernote API, full service layer
│   ├── server/     # MCP tool integration
│   └── ...         # Rate limiting, resources, tags, copy
├── e2e/            # Real Evernote API (requires EVERNOTE_TOKEN)
└── helpers/
    ├── test-data.ts   # Factories: makeNote(), makeTag(), makeNotebook(), makeSearchResult()
    └── test-utils.ts  # resetServiceClient()
```

## Running Tests

```bash
task test              # Unit + integration (no credentials needed)
task test:unit         # Unit tests only
task test:integration  # Integration tests only (mocked API)
task test:e2e          # E2E tests (requires EVERNOTE_TOKEN env var)
```

## Helpers

- **test-data.ts** — Factory functions that create valid domain objects with sensible defaults. Use `makeNote({ title: 'custom' })` to override specific fields.
- **test-utils.ts** — `resetServiceClient()` clears the singleton service client between tests.

## Conventions

- Framework: `bun:test` (Jest-compatible `describe`/`it`/`expect`)
- Test files: `*.test.ts` mirroring `src/` structure
- Test behavior and outcomes, not implementation details
- Add a unit test for every bug fix
- Tests are production code: strict types, no `any`, no shortcuts
- Unit tests must not make network calls
- Integration tests mock the Evernote API at the HTTP level
- E2E tests are gated by credential availability
