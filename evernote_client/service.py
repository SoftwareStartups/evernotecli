"""Shared business logic layer for MCP and CLI."""

from __future__ import annotations

from evernote_client.auth import OAuthError, get_token
from evernote_client.client import EvernoteClient
from evernote_client.config import settings
from evernote_client.models import (
    CreatedNote,
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)

_client: EvernoteClient | None = None


def get_client() -> EvernoteClient:
    """Get or create the singleton EvernoteClient."""
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            token = get_token(settings)
        except OAuthError as e:
            msg = f"Evernote authentication failed: {e}"
            raise ValueError(msg) from e
        _client = EvernoteClient(token)
    return _client


def resolve_notebook_guid(client: EvernoteClient, name: str) -> str:
    """Resolve notebook name to GUID.

    Raises:
        ValueError: If no notebook matches the given name.
    """
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.name == name and nb.guid is not None:
            return nb.guid
    msg = f"Notebook not found: {name}"
    raise ValueError(msg)


# --- Read operations ---


def search_notes(
    query: str = "",
    notebook_name: str = "",
    tags: list[str] | None = None,
    max_results: int = 20,
    offset: int = 0,
) -> SearchResult:
    """Search notes using Evernote search grammar."""
    client = get_client()
    max_results = min(max_results, 100)

    notebook_guid = None
    if notebook_name:
        notebook_guid = resolve_notebook_guid(client, notebook_name)

    result = client.search_notes(
        query=query,
        notebook_guid=notebook_guid,
        tag_names=tags,
        max_results=max_results,
        offset=offset,
    )

    notes = [NoteMetadata.from_thrift(n) for n in (result.notes or [])]

    return SearchResult(
        notes=notes,
        total=result.totalNotes or 0,
        offset=offset,
        max_results=max_results,
    )


def get_note(guid: str) -> NoteMetadata:
    """Get note metadata."""
    client = get_client()
    note = client.get_note(guid)
    return NoteMetadata.from_thrift(note)


def get_note_content(guid: str) -> NoteContent:
    """Get full note content as Markdown."""
    client = get_client()
    note = client.get_note(guid)
    content = client.get_note_content(guid)
    assert note.guid is not None, "Note returned without GUID"
    return NoteContent(
        guid=note.guid,
        title=note.title or "Untitled",
        content=content,
    )


def list_notebooks() -> list[NotebookInfo]:
    """List all notebooks."""
    client = get_client()
    notebooks = client.list_notebooks()
    return [
        NotebookInfo(guid=nb.guid, name=nb.name, stack=nb.stack)
        for nb in notebooks
        if nb.guid is not None and nb.name is not None
    ]


def list_tags() -> list[TagInfo]:
    """List all tags."""
    client = get_client()
    tags = client.list_tags()
    return [
        TagInfo(guid=t.guid, name=t.name)
        for t in tags
        if t.guid is not None and t.name is not None
    ]


# --- Write operations ---


def create_note(
    title: str,
    content: str,
    notebook_name: str = "",
    tags: list[str] | None = None,
) -> CreatedNote:
    """Create a new note with Markdown content."""
    client = get_client()

    notebook_guid = None
    if notebook_name:
        notebook_guid = resolve_notebook_guid(client, notebook_name)

    note = client.create_note(
        title=title,
        markdown=content,
        notebook_guid=notebook_guid,
        tag_names=tags,
    )
    assert note.guid is not None and note.title is not None
    return CreatedNote(
        guid=note.guid,
        title=note.title,
        notebook_guid=note.notebookGuid,
    )


def tag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Add tags to an existing note."""
    client = get_client()
    note = client.tag_note(guid, tags)
    return NoteMetadata.from_thrift(note)


def untag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Remove tags from an existing note."""
    client = get_client()
    note = client.untag_note(guid, tags)
    return NoteMetadata.from_thrift(note)


def move_note(guid: str, notebook_name: str) -> NoteMetadata:
    """Move a note to a different notebook."""
    client = get_client()
    notebook_guid = resolve_notebook_guid(client, notebook_name)
    note = client.move_note(guid, notebook_guid)
    return NoteMetadata.from_thrift(note)
