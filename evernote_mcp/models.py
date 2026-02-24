"""Pydantic response models for MCP tool results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
