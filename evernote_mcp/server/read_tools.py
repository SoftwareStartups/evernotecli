"""Read-only MCP tools for Evernote."""

from __future__ import annotations

from evernote_mcp.models import (
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)

from .app import _get_client, _resolve_notebook_guid, _to_note_metadata, mcp


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
    client = _get_client()
    max_results = min(max_results, 100)

    notebook_guid = None
    if notebook_name:
        notebook_guid = _resolve_notebook_guid(client, notebook_name)

    result = client.search_notes(
        query=query,
        notebook_guid=notebook_guid,
        tag_names=tags,
        max_results=max_results,
        offset=offset,
    )

    notes = [_to_note_metadata(n) for n in (result.notes or [])]

    return SearchResult(
        notes=notes,
        total=result.totalNotes or 0,
        offset=offset,
        max_results=max_results,
    )


@mcp.tool()
def get_note(guid: str) -> NoteMetadata:
    """Get note metadata (title, tags, notebook, dates).

    Args:
        guid: Note GUID
    """
    client = _get_client()
    note = client.get_note(guid)
    return _to_note_metadata(note)


@mcp.tool()
def get_note_content(guid: str) -> NoteContent:
    """Get full note content as Markdown.

    Args:
        guid: Note GUID
    """
    client = _get_client()
    note = client.get_note(guid)
    content = client.get_note_content(guid)
    return NoteContent(
        guid=note.guid,  # type: ignore[arg-type]  # Thrift types are untyped
        title=note.title or "Untitled",
        content=content,
    )


@mcp.tool()
def list_notebooks() -> list[NotebookInfo]:
    """List all notebooks with guid, name, and stack."""
    client = _get_client()
    notebooks = client.list_notebooks()
    return [
        NotebookInfo(
            guid=nb.guid,  # type: ignore[arg-type]  # Thrift types are untyped
            name=nb.name,  # type: ignore[arg-type]
            stack=nb.stack,
        )
        for nb in notebooks
    ]


@mcp.tool()
def list_tags() -> list[TagInfo]:
    """List all tags with guid and name."""
    client = _get_client()
    tags = client.list_tags()
    return [
        TagInfo(
            guid=t.guid,  # type: ignore[arg-type]  # Thrift types are untyped
            name=t.name,  # type: ignore[arg-type]
        )
        for t in tags
    ]
