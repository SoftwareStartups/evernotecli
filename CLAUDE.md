# CLAUDE.md

## Project Overview

Python-based Evernote client with MCP server and CLI (`encl`). Full read access and limited write access (create notes, tag notes, move notes). No edit/delete of existing note content.

## Commands

```bash
uv sync                              # Install dependencies
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run pyright                       # Type check
task test                            # Run unit + integration tests (no token needed)
task test:unit                       # Unit tests only
task test:integration                # Integration tests only
task test:e2e                        # E2E tests (requires EVERNOTE_TOKEN)
uv run encl --help                   # Show CLI help
uv run encl serve                    # Start MCP server
uv run encl notebooks                # List notebooks
uv run encl search "query"           # Search notes
uv run encl drain                    # Process queued write operations
task thrift                          # Regenerate Thrift clients (requires thrift compiler)
```

## Architecture

```text
evernote_client/
├── config.py          # Pydantic Settings (EVERNOTE_ env prefix)
├── models.py          # Pydantic models + NoteMetadata.from_thrift()
├── service.py         # Shared business logic (MCP + CLI)
├── auth/              # OAuth 1.0a flow (oauth.py, token_store.py, callback_server.py)
├── client/
│   ├── evernote_client.py  # High-level API client
│   ├── queue.py            # Persistent write queue (OperationQueue)
│   └── thrift.py           # Store proxy, retry, TBinaryProtocol/THttpClient fixes
├── edam/              # Generated Thrift clients — do not edit (run `task thrift`)
├── enml/              # ENML ↔ Markdown conversion (to_markdown.py, to_enml.py)
├── mcp/               # MCP server: app.py, read_tools.py, write_tools.py
└── cli/               # Click CLI: read_commands.py, write_commands.py
```

## Test Structure

```text
tests/
├── conftest.py              # Factories: make_note, make_tag, make_notebook, make_search_result
│                            # Fixtures: reset_client, mock_client
├── unit/                    # Mock at module boundary (no service layer)
├── integration/             # Service layer with mocked HTTP
└── e2e/
    └── conftest.py          # Session-scoped fixtures (token, runner, known_notebooks, …)
```

## Key Design Decisions

- Generated Thrift clients from local IDL files via `task thrift`; no evernote3 SDK dependency
- Uses ragevernote's `Store` proxy pattern with `__getattr__` auto-token-injection
- Token contains shard ID — note store URL constructed from it
- Required Thrift headers: `x-feature-version: 3`, `accept: application/x-thrift`
- Service layer (`service.py`) shared between MCP tools and CLI commands
- `NoteMetadata.from_thrift()` classmethod keeps Thrift→Pydantic conversion on the model
- Rate limit errors: write commands enqueue via `service.enqueue_write` (`encl drain` replays); read commands surface a user-friendly message via `_EvernoteGroup.invoke`

## Code Style

- Python 3.12+, managed with uv
- Ruff for linting/formatting (line length 88, double quotes)
- Pyright in standard mode

## Dependency Version Pins

Always use fully qualified versions — never floating major/minor tags:

- **Python packages** (`pyproject.toml`): use `>=X.Y.Z` lower bounds (uv resolves exact versions into `uv.lock`)
- **GitHub Actions**: always pin to exact `vX.Y.Z` tags, never `@v3` or `@main`
  - Current pins: `actions/checkout@v6.0.2`, `astral-sh/setup-uv@v7.4.0`, `actions/upload-artifact@v7.0.0`, `actions/download-artifact@v7.0.0`, `softprops/action-gh-release@v2.2.1`
  - When adding a new action or upgrading, web-search the latest release tag before pinning
