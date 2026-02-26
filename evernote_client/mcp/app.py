"""FastMCP server instance."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("evernote-client")


def main() -> None:
    mcp.run()
