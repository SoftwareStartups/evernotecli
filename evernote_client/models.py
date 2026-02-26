"""Pydantic response models for MCP tool results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


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
    created: datetime | None = None
    updated: datetime | None = None
    content_length: int | None = None

    @classmethod
    def from_thrift(cls, note: Any) -> NoteMetadata:
        """Convert a Thrift Note object to NoteMetadata."""
        return cls(
            guid=note.guid,
            title=note.title or "Untitled",
            notebook_guid=note.notebookGuid,
            tag_guids=list(note.tagGuids or []),
            created=_ts_to_dt(note.created),
            updated=_ts_to_dt(note.updated),
            content_length=getattr(note, "contentLength", None),
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
