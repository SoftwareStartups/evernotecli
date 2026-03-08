"""Shared business logic layer for MCP and CLI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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


class PrivateNoteError(PermissionError):
    """Raised when an operation targets a note tagged 'private'."""


_client: EvernoteClient | None = None


def get_client() -> EvernoteClient:
    """Get or create the singleton EvernoteClient."""
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            token = get_token(settings)
        except OAuthError:
            raise
        _client = EvernoteClient(token)
    return _client


def _is_private(tag_guids: list[str]) -> bool:
    guid = get_client().private_tag_guid
    return guid is not None and guid in tag_guids


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

    # Strip "private" from tag filters to prevent direct targeting
    safe_tags = ([t for t in tags if t.lower() != "private"] if tags else tags) or None

    result = client.search_notes(
        query=query,
        notebook_guid=notebook_guid,
        tag_names=safe_tags,
        max_results=max_results,
        offset=offset,
    )

    all_notes = [NoteMetadata.from_thrift(n) for n in (result.notes or [])]
    notes = [n for n in all_notes if not _is_private(n.tag_guids)]
    filtered = len(all_notes) - len(notes)

    return SearchResult(
        notes=notes,
        total=max(0, (result.totalNotes or 0) - filtered),
        offset=offset,
        max_results=max_results,
    )


def get_note(guid: str) -> NoteMetadata:
    """Get note metadata."""
    client = get_client()
    note = client.get_note(guid)
    if _is_private(note.tagGuids or []):
        raise PrivateNoteError(guid)
    return NoteMetadata.from_thrift(note)


def get_note_content(guid: str) -> NoteContent:
    """Get full note content as Markdown."""
    client = get_client()
    note = client.get_note(guid)
    if _is_private(note.tagGuids or []):
        raise PrivateNoteError(guid)
    content = client.get_note_content(guid)
    if note.guid is None:
        raise ValueError("Note returned without GUID")
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
        if t.guid is not None and t.name is not None and t.name.lower() != "private"
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
    if note.guid is None or note.title is None:
        raise ValueError("Created note missing GUID or title")
    return CreatedNote(
        guid=note.guid,
        title=note.title,
        notebook_guid=note.notebookGuid,
    )


def tag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Add tags to an existing note."""
    if any(t.lower() == "private" for t in tags):
        raise PrivateNoteError("Cannot add 'private' tag")
    client = get_client()
    existing = client.get_note(guid)
    if _is_private(existing.tagGuids or []):
        raise PrivateNoteError(guid)
    note = client.tag_note(guid, tags)
    return NoteMetadata.from_thrift(note)


def untag_note(guid: str, tags: list[str]) -> NoteMetadata:
    """Remove tags from an existing note."""
    if any(t.lower() == "private" for t in tags):
        raise PrivateNoteError("Cannot remove 'private' tag")
    client = get_client()
    existing = client.get_note(guid)
    if _is_private(existing.tagGuids or []):
        raise PrivateNoteError(guid)
    note = client.untag_note(guid, tags)
    return NoteMetadata.from_thrift(note)


def move_note(guid: str, notebook_name: str) -> NoteMetadata:
    """Move a note to a different notebook."""
    client = get_client()
    notebook_guid = resolve_notebook_guid(client, notebook_name)
    existing = client.get_note(guid)
    if _is_private(existing.tagGuids or []):
        raise PrivateNoteError(guid)
    note = client.move_note(guid, notebook_guid)
    return NoteMetadata.from_thrift(note)


# --- Write queue ---

_WRITE_DISPATCHER: dict[str, Callable[..., Any]] = {
    "create_note": create_note,
    "tag_note": tag_note,
    "untag_note": untag_note,
    "move_note": move_note,
}


def enqueue_write(operation: str, **params: Any) -> None:
    """Persist a write operation for later execution."""
    from evernote_client.client.queue import OperationQueue

    OperationQueue(settings.queue_path).put(operation, **params)


def pending_write_count() -> int:
    """Return the number of pending queued write operations."""
    from evernote_client.client.queue import OperationQueue

    return OperationQueue(settings.queue_path).size()


def drain_pending_writes() -> int:
    """Process all queued write operations. Returns count processed."""
    from evernote_client.client.queue import OperationQueue

    queue = OperationQueue(settings.queue_path)
    if queue.is_empty():
        return 0
    results = queue.process_all(_WRITE_DISPATCHER)
    return len(results)
