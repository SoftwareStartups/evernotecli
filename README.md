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

### Private notes

Notes tagged `private` are protected at the service layer:

- **Hidden from search results** — never appear in `search` output, even with `tag:private` queries
- **Blocked from direct access** — `note` and `content` commands return an error
- **Blocked from write operations** — `tag`, `untag`, and `move` refuse to operate on private notes
- **Tag protected** — the `private` tag cannot be removed via `untag`; it is also hidden from `tags` listing
- **Creating private notes is allowed** — `create -t private` works as expected

### MCP server

```bash
uv run encl serve
```

#### Installing in Claude Code

Since this is a private repo (not a published MCP package), add it directly by path after cloning:

```bash
claude mcp add evernote -- uv --directory /path/to/evernote-client run encl serve
```

Or add it manually to `.claude/mcp.json` (project-level) or `~/.claude/mcp.json` (global):

```json
{
  "mcpServers": {
    "evernote": {
      "command": "uv",
      "args": ["--directory", "/path/to/evernote-client", "run", "encl", "serve"]
    }
  }
}
```

Replace `/path/to/evernote-client` with the absolute path to your clone. Make sure `EVERNOTE_TOKEN` is set in your environment or in a `.env` file in the project root before starting.

### Development

```bash
make check                   # lint
make format                  # format
make test                    # unit + integration tests (no token needed)
make test-unit               # unit tests only
make test-integration        # integration tests only
make test-e2e                # e2e tests (requires EVERNOTE_TOKEN)
make thrift                  # regenerate Thrift clients (requires brew install thrift)
```

For architecture and design details, see `CLAUDE.md`.
