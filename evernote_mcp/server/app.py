"""FastMCP server instance, client management, and helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

from evernote_mcp.auth import OAuthError, get_token
from evernote_mcp.client import EvernoteClient
from evernote_mcp.config import settings
from evernote_mcp.edam.type.ttypes import Note
from evernote_mcp.models import NoteMetadata

mcp = FastMCP("evernote-mcp")

_client: EvernoteClient | None = None


def _get_client() -> EvernoteClient:
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            token = get_token(settings)
        except OAuthError as e:
            msg = f"Evernote authentication failed: {e}"
            raise ValueError(msg) from e
        _client = EvernoteClient(token)
    return _client


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts / 1000, tz=UTC)


def _to_note_metadata(note: Note) -> NoteMetadata:
    """Convert a Thrift note object to a NoteMetadata model."""
    return NoteMetadata(
        guid=note.guid,  # type: ignore[arg-type]  # Thrift types are untyped
        title=note.title or "Untitled",
        notebook_guid=note.notebookGuid,
        tag_guids=list(note.tagGuids or []),
        created=_ts_to_dt(note.created),
        updated=_ts_to_dt(note.updated),
        content_length=getattr(note, "contentLength", None),
    )


def _resolve_notebook_guid(client: EvernoteClient, name: str) -> str:
    """Resolve notebook name to GUID.

    Raises:
        ValueError: If no notebook matches the given name.
    """
    notebooks = client.list_notebooks()
    for nb in notebooks:
        if nb.name == name:
            return nb.guid  # type: ignore[return-value]  # Thrift types are untyped
    msg = f"Notebook not found: {name}"
    raise ValueError(msg)


def main() -> None:
    mcp.run()
