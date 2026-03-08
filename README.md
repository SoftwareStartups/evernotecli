## Evernote Client

A Python-based Evernote client exposing both a CLI (`encl`) and a Model Context Protocol (MCP) server. Provides full read access and limited write access (create notes, tag notes, move notes). Does not edit or delete existing note content.

### Prerequisites

- **Python**: 3.12+
- **uv**: `pip install uv`
- An **Evernote API token** (OAuth flow via `encl login`)

### Setup

```bash
uv sync
uv run encl login      # authenticate via OAuth
```

### CLI usage

```bash
uv run encl --help
uv run encl search "query"               # search notes
uv run encl notebooks                    # list notebooks
uv run encl tags                         # list tags
uv run encl note <guid>                  # note metadata
uv run encl content <guid>               # note content (Markdown)
uv run encl create "Title" -c "body"     # create a note
uv run encl tag <guid> tag1 tag2         # add tags
uv run encl untag <guid> tag1            # remove tags
uv run encl move <guid> "Notebook"       # move to notebook
uv run encl drain                        # process queued writes
```

Write commands (`create`, `tag`, `untag`, `move`) automatically enqueue when rate-limited and exit 0. Run `encl drain` later to replay them.

### MCP server

```bash
uv run encl serve
```

Configure your MCP client (e.g. Claude Desktop) to run `uv run encl serve` as the server command.

### Development

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pyright           # type check
uv run pytest            # run tests
make thrift              # regenerate Thrift clients (requires brew install thrift)
```

For architecture and design details, see `CLAUDE.md`.
