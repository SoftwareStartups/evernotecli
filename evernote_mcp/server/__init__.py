"""FastMCP server with Evernote tools."""

# Side-effect imports: register @mcp.tool() decorated functions.
from . import read_tools as read_tools  # noqa: F401
from . import write_tools as write_tools  # noqa: F401
from .app import main, mcp  # noqa: F401

__all__ = ["main", "mcp"]
