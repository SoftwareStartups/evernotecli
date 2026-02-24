# CLAUDE.md

## Project Overview

Python-based Evernote MCP server with full read access and limited write access (create notes, tag notes, move notes). No edit/delete of existing note content.

## Commands

```bash
uv sync                              # Install dependencies
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run pyright                       # Type check
uv run pytest                        # Run tests
uv run mcp dev evernote_mcp/server.py  # Start MCP dev server
```

## Architecture

```
evernote_mcp/
├── __init__.py
├── __main__.py          # python -m evernote_mcp
├── server.py            # FastMCP server + tool registration
├── config.py            # Pydantic Settings
├── auth.py              # OAuth 1.0a flow
├── client.py            # Thrift client (Store proxy, retry, hotfixes)
├── enml.py              # ENML ↔ Markdown conversion
└── models.py            # Pydantic response models
```

## Key Design Decisions

- Bypasses SDK client wrapper; constructs Thrift clients directly
- Uses ragevernote's `Store` proxy pattern with `__getattr__` auto-token-injection
- Includes evernote-backup's hotfixes for bad UTF-8 and deprecated TLS args
- Token contains shard ID — note store URL constructed from it
- Required Thrift headers: `x-feature-version: 3`, `accept: application/x-thrift`

## Code Style

- Python 3.12+, managed with uv
- Ruff for linting/formatting (line length 88, double quotes)
- Pyright in standard mode
- py.typed marker present
