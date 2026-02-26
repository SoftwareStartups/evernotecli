"""Write MCP tools for Evernote."""

from __future__ import annotations

from evernote_mcp.models import CreatedNote, NoteMetadata

from .app import _get_client, _resolve_notebook_guid, _to_note_metadata, mcp


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
    client = _get_client()

    notebook_guid = None
    if notebook_name:
        notebook_guid = _resolve_notebook_guid(client, notebook_name)

    note = client.create_note(
        title=title,
        markdown=content,
        notebook_guid=notebook_guid,
        tag_names=tags,
    )
    return CreatedNote(
        guid=note.guid,  # type: ignore[arg-type]  # Thrift types are untyped
        title=note.title,  # type: ignore[arg-type]
        notebook_guid=note.notebookGuid,
    )


@mcp.tool()
def tag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Add tags to an existing note.

    Args:
        guid: Note GUID
        tags: Tag names to add
    """
    client = _get_client()
    note = client.tag_note(guid, tags)
    return _to_note_metadata(note)


@mcp.tool()
def untag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Remove tags from an existing note.

    Args:
        guid: Note GUID
        tags: Tag names to remove
    """
    client = _get_client()
    note = client.untag_note(guid, tags)
    return _to_note_metadata(note)


@mcp.tool()
def move_note(guid: str, notebook_name: str) -> NoteMetadata:
    """Move a note to a different notebook.

    Args:
        guid: Note GUID
        notebook_name: Target notebook name
    """
    client = _get_client()
    notebook_guid = _resolve_notebook_guid(client, notebook_name)
    note = client.move_note(guid, notebook_guid)
    return _to_note_metadata(note)
