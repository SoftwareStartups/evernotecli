# CLAUDE.md

## Project Overview

Python-based Evernote client with MCP server and CLI (`encl`). Full read access and limited write access (create notes, tag notes, move notes). No edit/delete of existing note content.

## Commands

```bash
uv sync                              # Install dependencies
uv run ruff check .                  # Lint
uv run ruff format .                 # Format
uv run pyright                       # Type check
uv run pytest                        # Run tests
uv run encl --help                   # Show CLI help
uv run encl serve                    # Start MCP server
uv run encl notebooks                # List notebooks
uv run encl search "query"           # Search notes
make thrift                          # Regenerate Thrift clients (requires thrift compiler)
```

## Architecture

```
evernote_client/
├── __init__.py
├── __main__.py              # python -m evernote_client → CLI
├── config.py                # Pydantic Settings (EVERNOTE_ env prefix)
├── models.py                # Pydantic response models + NoteMetadata.from_thrift()
├── service.py               # Shared business logic (MCP + CLI both call this)
├── auth/                    # OAuth 1.0a flow
│   ├── oauth.py
│   ├── token_store.py
│   └── callback_server.py
├── client/                  # Low-level Evernote API
│   ├── evernote_client.py   # High-level API client
│   └── thrift.py            # Store proxy, retry, TBinaryProtocol/THttpClient hotfixes
├── edam/                    # Generated Thrift clients (do not edit — run `make thrift`)
│   ├── notestore/           # NoteStore service + types
│   ├── userstore/           # UserStore service + types
│   ├── type/                # Core types (Note, Tag, Notebook, etc.)
│   ├── error/               # EDAMUserException, etc.
│   └── limits/              # Account limits constants
├── enml/                    # ENML ↔ Markdown conversion
│   ├── to_markdown.py
│   └── to_enml.py
├── mcp/                     # MCP server (thin wrappers around service)
│   ├── app.py               # FastMCP instance + main()
│   ├── read_tools.py
│   └── write_tools.py
├── cli/                     # Click CLI
│   ├── __init__.py          # Click group + main()
│   ├── read_commands.py     # search, note, content, notebooks, tags
│   └── write_commands.py    # create, tag, untag, move, login, serve
└── py.typed
```

## Key Design Decisions

- Generated Thrift clients from local IDL files (`evernote_client/thrift/*.thrift`) via `make thrift`; no evernote3 SDK dependency
- Uses ragevernote's `Store` proxy pattern with `__getattr__` auto-token-injection
- Includes evernote-backup's hotfixes for bad UTF-8 and deprecated TLS args
- Token contains shard ID — note store URL constructed from it
- Required Thrift headers: `x-feature-version: 3`, `accept: application/x-thrift`
- Service layer (`service.py`) shared between MCP tools and CLI commands
- `NoteMetadata.from_thrift()` classmethod keeps Thrift→Pydantic conversion on the model

## Code Style

- Python 3.12+, managed with uv
- Ruff for linting/formatting (line length 88, double quotes)
- Pyright in standard mode
- py.typed marker present
