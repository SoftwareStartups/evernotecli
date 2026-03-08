"""Pydantic response models for MCP tool results."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from evernote_client.edam.notestore.ttypes import NoteMetadata as ThriftNoteMetadata
from evernote_client.edam.type.ttypes import Note


def _ts_to_dt(ts: int | None) -> datetime | None:
    """Convert millisecond timestamp to UTC datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts / 1000, tz=UTC)


class NotebookInfo(BaseModel):
    guid: str
    name: str
    stack: str | None = None


class TagInfo(BaseModel):
    guid: str
    name: str


class NoteMetadata(BaseModel):
    guid: str
    title: str
    notebook_guid: str | None = None
    tag_guids: list[str] = []
    tag_names: list[str] = []
    created: datetime | None = None
    updated: datetime | None = None
    content_length: int | None = None

    @classmethod
    def from_thrift(cls, note: Note | ThriftNoteMetadata) -> NoteMetadata:
        """Convert a Thrift Note object to NoteMetadata."""
        if note.guid is None:
            raise ValueError("Note returned without GUID")
        tag_names: list[str] = []
        if isinstance(note, Note) and note.tagNames:
            tag_names = [n for n in note.tagNames if n]
        return cls(
            guid=note.guid,
            title=note.title or "Untitled",
            notebook_guid=note.notebookGuid,
            tag_guids=list(note.tagGuids or []),
            tag_names=tag_names,
            created=_ts_to_dt(note.created),
            updated=_ts_to_dt(note.updated),
            content_length=note.contentLength,
        )


class SearchResult(BaseModel):
    notes: list[NoteMetadata]
    total: int
    offset: int
    max_results: int


class NoteContent(BaseModel):
    guid: str
    title: str
    content: str


class CreatedNote(BaseModel):
    guid: str
    title: str
    notebook_guid: str | None = None
