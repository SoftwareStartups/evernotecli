"""FastMCP server with Evernote tools."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from evernote_mcp.auth import get_token
from evernote_mcp.client import EvernoteClient
from evernote_mcp.config import settings
from evernote_mcp.models import (
    CreatedNote,
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)

mcp = FastMCP("evernote-mcp")

_client: EvernoteClient | None = None


def _get_client() -> EvernoteClient:
    global _client  # noqa: PLW0603
    if _client is None:
        token = get_token(settings)
        _client = EvernoteClient(token)
    return _client


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts / 1000, tz=UTC)


def _to_note_metadata(note: Any) -> NoteMetadata:
    """Convert a Thrift note object to a NoteMetadata model."""
    return NoteMetadata(
        guid=note.guid,
        title=note.title or "Untitled",
        notebook_guid=note.notebookGuid,
        tag_guids=list(note.tagGuids or []),
        created=_ts_to_dt(note.created),
        updated=_ts_to_dt(note.updated),
        content_length=getattr(note, "contentLength", None),
    )


def _resolve_notebook_guid(client: EvernoteClient, name: str) -> str | None:
    """Resolve notebook name to GUID."""
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.name == name:
            return nb.guid
    return None


# --- Read Tools ---


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
        guid=note.guid,
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
            guid=nb.guid,
            name=nb.name,
            stack=nb.stack,
        )
        for nb in notebooks
    ]


@mcp.tool()
def list_tags() -> list[TagInfo]:
    """List all tags with guid and name."""
    client = _get_client()
    tags = client.list_tags()
    return [TagInfo(guid=t.guid, name=t.name) for t in tags]


# --- Write Tools ---


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
        guid=note.guid,
        title=note.title,
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
    if not notebook_guid:
        msg = f"Notebook not found: {notebook_name}"
        raise ValueError(msg)
    note = client.move_note(guid, notebook_guid)
    return _to_note_metadata(note)


def main() -> None:
    mcp.run()
