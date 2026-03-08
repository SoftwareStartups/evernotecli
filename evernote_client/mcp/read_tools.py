"""Read-only MCP tools for Evernote."""

from __future__ import annotations

from evernote_client import service
from evernote_client.models import (
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)
from evernote_client.service import PrivateNoteError

from .app import mcp


@mcp.tool()
def search_notes(
    query: str = "",
    notebook_name: str = "",
    tags: list[str] | None = None,
    max_results: int = 20,
    offset: int = 0,
) -> SearchResult:
    """Search notes using Evernote search grammar.

    Args:
        query: Search query (Evernote search grammar)
        notebook_name: Filter by notebook name
        tags: Filter by tag names
        max_results: Maximum number of results (default 20, max 100)
        offset: Offset for pagination
    """
    return service.search_notes(
        query=query,
        notebook_name=notebook_name,
        tags=tags,
        max_results=max_results,
        offset=offset,
    )


@mcp.tool()
def get_note(guid: str) -> NoteMetadata | str:
    """Get note metadata (title, tags, notebook, dates).

    Args:
        guid: Note GUID
    """
    try:
        return service.get_note(guid)
    except PrivateNoteError:
        return "Access denied: note is private."


@mcp.tool()
def get_note_content(guid: str) -> NoteContent | str:
    """Get full note content as Markdown.

    Args:
        guid: Note GUID
    """
    try:
        return service.get_note_content(guid)
    except PrivateNoteError:
        return "Access denied: note is private."


@mcp.tool()
def list_notebooks() -> list[NotebookInfo]:
    """List all notebooks with guid, name, and stack."""
    return service.list_notebooks()


@mcp.tool()
def list_tags() -> list[TagInfo]:
    """List all tags with guid and name."""
    return service.list_tags()
