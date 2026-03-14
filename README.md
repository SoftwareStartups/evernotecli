# Evernote MCP Server & CLI (`evercli`)

A Bun-native TypeScript Evernote client exposing both a CLI (`evercli`) and a Model Context Protocol (MCP) server. Provides full read access and limited write access (create notes, tag notes, move notes). Does not edit or delete existing note content.

## Quick Start

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

## Authentication

Run `evercli login` to authenticate. If no OAuth consumer credentials are configured, you'll be prompted to paste a developer token — get one at [dev.evernote.com/get-token](https://dev.evernote.com/get-token/).

Alternatively, set the `EVERNOTE_TOKEN` environment variable directly:

```bash
export EVERNOTE_TOKEN="your-developer-token"
```

## CLI Usage

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

## Private Notes

Notes tagged `private` are protected at the service layer:

- **Hidden from search results** — never appear in `search` output, even with `tag:private` queries
- **Blocked from direct access** — `note` and `content` commands return an error
- **Blocked from write operations** — `tag`, `untag`, and `move` refuse to operate on private notes
- **Tag protected** — the `private` tag cannot be removed via `untag`; it is also hidden from `tags` listing
- **Creating private notes is allowed** — `create -t private` works as expected

## MCP Server

### Using the binary

```bash
evercli serve
```

Add to Claude Code (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "evernote": {
      "command": "/path/to/evercli",
      "args": ["serve"],
      "env": {
        "EVERNOTE_TOKEN": "your-developer-token"
      }
    }
  }
}
```

### From source

```bash
claude mcp add evernote -- bun run /path/to/evernote-client/src/index.ts serve
```

Or add manually to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "evernote": {
      "command": "bun",
      "args": ["run", "/path/to/evernote-client/src/index.ts", "serve"],
      "env": {
        "EVERNOTE_TOKEN": "your-developer-token"
      }
    }
  }
}
```

## MCP Tools

### Read Tools

#### `search_notes`

Search notes using Evernote search grammar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | No | Search query (Evernote search grammar) |
| `notebook_name` | string | No | Filter by notebook name |
| `tags` | string[] | No | Filter by tag names |
| `max_results` | integer | No | Maximum results (default: 20, max: 100) |
| `offset` | integer | No | Offset for pagination |

#### `get_note`

Get note metadata (title, tags, notebook, dates).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | string | Yes | Note GUID |

#### `get_note_content`

Get full note content as Markdown.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | string | Yes | Note GUID |

#### `list_notebooks`

List all notebooks with guid, name, and stack. No parameters.

#### `list_tags`

List all tags with guid and name. No parameters.

### Write Tools

Write operations enqueue automatically on rate limit. Run `evercli drain` to replay queued operations.

#### `create_note`

Create a new note with Markdown content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Note title |
| `content` | string | No | Note content in Markdown format |
| `notebook_name` | string | No | Target notebook name (uses default if empty) |
| `tags` | string[] | No | List of tag names to apply |

#### `tag_note`

Add tags to an existing note.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | string | Yes | Note GUID |
| `tags` | string[] | Yes | Tag names to add |

#### `untag_note`

Remove tags from an existing note.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | string | Yes | Note GUID |
| `tags` | string[] | Yes | Tag names to remove |

#### `move_note`

Move a note to a different notebook.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `guid` | string | Yes | Note GUID |
| `notebook_name` | string | Yes | Target notebook name |

## Development

### Setup

```bash
git clone https://github.com/SoftwareStartups/evernote-client.git
cd evernote-client
bun install
```

Create a `.env` file in the project root:

```dotenv
EVERNOTE_TOKEN=your-developer-token
# LOG_LEVEL=info
```

### Development Workflow

```bash
task build          # compile TypeScript
task format         # format code
task check          # lint + typecheck
task test           # unit + integration tests (no token needed)
task clean          # remove build artifacts
task all            # clean → install → build → check → test
```

### Run Locally

```bash
bun run src/index.ts --help          # show CLI help
bun run src/index.ts login           # authenticate
bun run src/index.ts serve           # start MCP server
```

## Testing

```bash
task test               # unit + integration tests (no token needed)
task test:unit          # unit tests only
task test:integration   # integration tests only
task test:e2e           # e2e tests (requires EVERNOTE_TOKEN)
task test:all           # all tests including e2e
```

- **Unit tests**: Pure logic, no service layer
- **Integration tests**: Service layer with mocked Evernote client
- **End-to-end tests**: Live API calls — requires `EVERNOTE_TOKEN`

### Releasing

Push a semver tag to trigger the release workflow. CI must pass before tagging:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The release workflow compiles all four platform binaries and publishes them to GitHub Releases automatically.
