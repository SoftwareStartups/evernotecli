"""Shared test fixtures and factory helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from evernote_client import service

# ── Factories ────────────────────────────────────────────────────────────────


def make_note(
    guid: str = "note-1",
    title: str = "Test Note",
    notebook_guid: str = "nb-1",
    tag_guids: list[str] | None = None,
    created: int = 1700000000000,
    updated: int = 1700000001000,
    content_length: int = 42,
) -> SimpleNamespace:
    return SimpleNamespace(
        guid=guid,
        title=title,
        notebookGuid=notebook_guid,
        tagGuids=tag_guids or [],
        created=created,
        updated=updated,
        contentLength=content_length,
    )


def make_tag(guid: str = "tag-1", name: str = "TestTag") -> SimpleNamespace:
    return SimpleNamespace(guid=guid, name=name)


def make_notebook(
    guid: str = "nb-1", name: str = "My Notebook", stack: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(guid=guid, name=name, stack=stack)


def make_search_result(
    notes: list[SimpleNamespace] | None = None, total: int = 1
) -> SimpleNamespace:
    return SimpleNamespace(notes=notes or [make_note()], totalNotes=total)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_client() -> None:
    """Reset the cached service client between tests."""
    service._client = None
    yield
    service._client = None


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock EvernoteClient and patch get_client to return it."""
    client = MagicMock()
    with patch.object(service, "get_client", return_value=client):
        yield client
