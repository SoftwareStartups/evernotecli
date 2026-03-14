## evercli

A Bun-native TypeScript Evernote client exposing both a CLI (`evercli`) and a Model Context Protocol (MCP) server. Provides full read access and limited write access (create notes, tag notes, move notes). Does not edit or delete existing note content.

### Quick start

Download the latest binary for your platform from [GitHub Releases](https://github.com/SoftwareStartups/evernote-client/releases/latest):

```bash
# macOS (Apple Silicon)
curl -Lo evercli https://github.com/SoftwareStartups/evernote-client/releases/latest/download/evercli-darwin-arm64

# macOS (Intel)
curl -Lo evercli https://github.com/SoftwareStartups/evernote-client/releases/latest/download/evercli-darwin-x64

# Linux (arm64)
curl -Lo evercli https://github.com/SoftwareStartups/evernote-client/releases/latest/download/evercli-linux-arm64

# Linux (x64)
curl -Lo evercli https://github.com/SoftwareStartups/evernote-client/releases/latest/download/evercli-linux-x64

chmod +x evercli
./evercli login
```

### Authentication

Run `evercli login` to authenticate. If no OAuth consumer credentials are configured, you'll be prompted to paste a developer token — get one at [dev.evernote.com/get-token](https://dev.evernote.com/get-token/).

Alternatively, set the `EVERNOTE_TOKEN` environment variable directly:

```bash
export EVERNOTE_TOKEN="your-developer-token"
```

### CLI usage

```bash
evercli --help
evercli search "query"               # search notes
evercli notebooks                    # list notebooks
evercli tags                         # list tags
evercli note <guid>                  # note metadata
evercli content <guid>               # note content (Markdown)
evercli create "Title" -c "body"     # create a note
evercli tag <guid> tag1 tag2         # add tags
evercli untag <guid> tag1            # remove tags
evercli move <guid> "Notebook"       # move to notebook
evercli drain                        # process queued writes
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

#### Using the binary

```bash
evercli serve
```

Add to Claude Code (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "evernote": {
      "command": "/path/to/evercli",
      "args": ["serve"]
    }
  }
}
```

#### From source

```bash
claude mcp add evernote -- bun run /path/to/evernote-client/src/index.ts serve
```

Or add manually to `.claude/mcp.json`:

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

Make sure `EVERNOTE_TOKEN` is set in your environment or in a `.env` file in the project root before starting.

### Development

```bash
git clone https://github.com/SoftwareStartups/evernote-client.git
cd evernote-client
bun install
bun run src/index.ts login           # authenticate
bun run src/index.ts --help          # show CLI help
```

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
