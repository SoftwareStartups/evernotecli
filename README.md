## evercli

A Bun-native TypeScript Evernote client exposing both a CLI (`evercli`) and a Model Context Protocol (MCP) server. Provides full read access and limited write access (create notes, tag notes, move notes). Does not edit or delete existing note content.

### Prerequisites

- **Bun**: 1.3+
- An **Evernote API token** (OAuth flow via `evercli login`)

### Setup

```bash
bun install
bun run src/index.ts login      # authenticate via OAuth
```

### CLI usage

```bash
bun run src/index.ts --help
bun run src/index.ts search "query"               # search notes
bun run src/index.ts notebooks                    # list notebooks
bun run src/index.ts tags                         # list tags
bun run src/index.ts note <guid>                  # note metadata
bun run src/index.ts content <guid>               # note content (Markdown)
bun run src/index.ts create "Title" -c "body"     # create a note
bun run src/index.ts tag <guid> tag1 tag2         # add tags
bun run src/index.ts untag <guid> tag1            # remove tags
bun run src/index.ts move <guid> "Notebook"       # move to notebook
bun run src/index.ts drain                        # process queued writes
```

Write commands (`create`, `tag`, `untag`, `move`) automatically enqueue when rate-limited and exit 0. Run `evercli drain` later to replay them.

### Private notes

Notes tagged `private` are protected at the service layer:

- **Hidden from search results** — never appear in `search` output, even with `tag:private` queries
- **Blocked from direct access** — `note` and `content` commands return an error
- **Blocked from write operations** — `tag`, `untag`, and `move` refuse to operate on private notes
- **Tag protected** — the `private` tag cannot be removed via `untag`; it is also hidden from `tags` listing
- **Creating private notes is allowed** — `create -t private` works as expected

### MCP server

```bash
bun run src/index.ts serve
```

#### Installing in Claude Code

Since this is a private repo (not a published MCP package), add it directly by path after cloning:

```bash
claude mcp add evernote -- bun run /path/to/evernote-client/src/index.ts serve
```

Or add it manually to `.claude/mcp.json` (project-level) or `~/.claude/mcp.json` (global):

```json
{
  "mcpServers": {
    "evernote": {
      "command": "bun",
      "args": ["run", "/path/to/evernote-client/src/index.ts", "serve"]
    }
  }
}
```

Replace `/path/to/evernote-client` with the absolute path to your clone. Make sure `EVERNOTE_TOKEN` is set in your environment or in a `.env` file in the project root before starting.

### Development

```bash
task check                   # lint + typecheck
task format                  # format
task test                    # unit + integration tests (no token needed)
task test:unit               # unit tests only
task test:integration        # integration tests only
task test:e2e                # e2e tests (requires EVERNOTE_TOKEN)
task thrift                  # regenerate Thrift clients (requires brew install thrift)
task compile                 # build standalone binary
```

For architecture and design details, see `CLAUDE.md`.
