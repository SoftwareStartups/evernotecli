"""Write MCP tools for Evernote."""

from __future__ import annotations

from evernote_client import service
from evernote_client.models import CreatedNote, NoteMetadata
from evernote_client.service import PrivateNoteError

from .app import mcp


@mcp.tool()
def create_note(
    title: str,
    content: str,
    notebook_name: str = "",
    tags: list[str] | None = None,
) -> CreatedNote:
    """Create a new note with Markdown content.

    Args:
        title: Note title
        content: Note content in Markdown format
        notebook_name: Target notebook name (uses default if empty)
        tags: List of tag names to apply
    """
    return service.create_note(
        title=title,
        content=content,
        notebook_name=notebook_name,
        tags=tags,
    )


@mcp.tool()
def tag_note(guid: str, tags: list[str]) -> NoteMetadata | str:
    """Add tags to an existing note.

    Args:
        guid: Note GUID
        tags: Tag names to add
    """
    try:
        return service.tag_note(guid, tags)
    except PrivateNoteError:
        return "Access denied: note is private."


@mcp.tool()
def untag_note(guid: str, tags: list[str]) -> NoteMetadata | str:
    """Remove tags from an existing note.

    Args:
        guid: Note GUID
        tags: Tag names to remove
    """
    try:
        return service.untag_note(guid, tags)
    except PrivateNoteError:
        return "Access denied: note is private."


@mcp.tool()
def move_note(guid: str, notebook_name: str) -> NoteMetadata | str:
    """Move a note to a different notebook.

    Args:
        guid: Note GUID
        notebook_name: Target notebook name
    """
    try:
        return service.move_note(guid, notebook_name)
    except PrivateNoteError:
        return "Access denied: note is private."
