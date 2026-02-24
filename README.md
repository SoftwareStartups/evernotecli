## Evernote MCP Server

A Python-based Model Context Protocol (MCP) server that connects tools/agents to your Evernote account. It provides read-only access to existing notes plus limited write actions (create notes, tag notes, move notes), but does not edit or delete existing note content.

### Prerequisites

- **Python**: 3.12+
- **uv**: for dependency management (`pip install uv`)
- An **Evernote API token** (see `evernote_mcp/auth.py` and your Evernote developer settings)

### Setup

```bash
make install
```

### Development

Common commands:

- **Format**: `make format`
- **Lint & Type check**: `make check`
- **Tests**: `make test`
- **Run MCP server (dev)**: `make serve`

### Using the MCP Inspector (`make serve`)

`make serve` launches the MCP Inspector for **manual, local testing** and starts a local proxy that requires a session token.

1. Run `make serve`.
2. In the terminal output, copy the **Session token** (or use the printed “Open inspector with token pre-filled” link).
3. In the Inspector UI:
   - Open the printed URL that includes `MCP_PROXY_AUTH_TOKEN=...`, or
   - Expand **Configuration** and paste the token into the proxy auth/session token field.
4. Click **Connect**, then browse the available **Tools** and run calls to verify behavior.

### Notes

For project architecture and design details, see `CLAUDE.md` and the `evernote_mcp/` package.
