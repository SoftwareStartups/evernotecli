"""Tests for service layer and MCP tools."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from evernote_client import service
from evernote_client.auth import OAuthError
from evernote_client.models import (
    CreatedNote,
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_note(
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


def _make_notebook(
    guid: str = "nb-1", name: str = "My Notebook", stack: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(guid=guid, name=name, stack=stack)


def _make_tag(guid: str = "tag-1", name: str = "python") -> SimpleNamespace:
    return SimpleNamespace(guid=guid, name=name)


def _make_search_result(
    notes: list[SimpleNamespace] | None = None, total: int = 1
) -> SimpleNamespace:
    return SimpleNamespace(notes=notes or [_make_note()], totalNotes=total)


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the cached client between tests."""
    service._client = None
    yield
    service._client = None


@pytest.fixture()
def mock_client():
    """Return a MagicMock EvernoteClient and patch get_client to return it."""
    client = MagicMock()
    with patch.object(service, "get_client", return_value=client):
        yield client


# ── Auth / get_client ────────────────────────────────────────────────────


class TestGetClient:
    def test_creates_client_on_first_call(self) -> None:
        with (
            patch.object(service, "get_token", return_value="tok"),
            patch.object(service, "EvernoteClient") as cls,
        ):
            cls.return_value = MagicMock()
            result = service.get_client()
            cls.assert_called_once_with("tok")
            assert result is cls.return_value

    def test_caches_client(self) -> None:
        with (
            patch.object(service, "get_token", return_value="tok"),
            patch.object(service, "EvernoteClient") as cls,
        ):
            cls.return_value = MagicMock()
            first = service.get_client()
            second = service.get_client()
            assert first is second
            cls.assert_called_once()

    def test_oauth_error_raises_value_error(self) -> None:
        with (
            patch.object(service, "get_token", side_effect=OAuthError("bad token")),
            pytest.raises(ValueError, match="authentication failed"),
        ):
            service.get_client()


# ── resolve_notebook_guid ────────────────────────────────────────────────


class TestResolveNotebookGuid:
    def test_resolves_existing_name(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [
            _make_notebook("nb-1", "Work"),
            _make_notebook("nb-2", "Personal"),
        ]
        result = service.resolve_notebook_guid(mock_client, "Personal")
        assert result == "nb-2"

    def test_raises_when_not_found(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [_make_notebook("nb-1", "Work")]
        with pytest.raises(ValueError, match="Notebook not found: Missing"):
            service.resolve_notebook_guid(mock_client, "Missing")


# ── Read operations ──────────────────────────────────────────────────────


class TestSearchNotes:
    def test_returns_search_result(self, mock_client: MagicMock) -> None:
        mock_client.search_notes.return_value = _make_search_result()
        result = service.search_notes(query="test")
        assert isinstance(result, SearchResult)
        assert len(result.notes) == 1
        assert result.notes[0].guid == "note-1"

    def test_caps_max_results_at_100(self, mock_client: MagicMock) -> None:
        mock_client.search_notes.return_value = _make_search_result(notes=[], total=0)
        service.search_notes(query="test", max_results=500)
        _, kwargs = mock_client.search_notes.call_args
        assert kwargs["max_results"] == 100

    def test_filters_by_notebook(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [_make_notebook("nb-1", "Work")]
        mock_client.search_notes.return_value = _make_search_result(notes=[], total=0)
        service.search_notes(query="", notebook_name="Work")
        _, kwargs = mock_client.search_notes.call_args
        assert kwargs["notebook_guid"] == "nb-1"

    def test_notebook_not_found_raises(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = []
        with pytest.raises(ValueError, match="Notebook not found"):
            service.search_notes(query="", notebook_name="Missing")

    def test_empty_notebook_name_passes_none(self, mock_client: MagicMock) -> None:
        mock_client.search_notes.return_value = _make_search_result(notes=[], total=0)
        service.search_notes(query="test", notebook_name="")
        _, kwargs = mock_client.search_notes.call_args
        assert kwargs["notebook_guid"] is None


class TestGetNote:
    def test_returns_metadata(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = _make_note()
        result = service.get_note("note-1")
        assert isinstance(result, NoteMetadata)
        assert result.guid == "note-1"
        assert result.title == "Test Note"


class TestGetNoteContent:
    def test_returns_content(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = _make_note()
        mock_client.get_note_content.return_value = "# Hello"
        result = service.get_note_content("note-1")
        assert isinstance(result, NoteContent)
        assert result.guid == "note-1"
        assert result.content == "# Hello"


class TestListNotebooks:
    def test_returns_notebook_infos(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [
            _make_notebook("nb-1", "Work", "Projects"),
            _make_notebook("nb-2", "Personal"),
        ]
        result = service.list_notebooks()
        assert len(result) == 2
        assert all(isinstance(nb, NotebookInfo) for nb in result)
        assert result[0].stack == "Projects"
        assert result[1].stack is None


class TestListTags:
    def test_returns_tag_infos(self, mock_client: MagicMock) -> None:
        mock_client.list_tags.return_value = [
            _make_tag("tag-1", "python"),
            _make_tag("tag-2", "coding"),
        ]
        result = service.list_tags()
        assert len(result) == 2
        assert all(isinstance(t, TagInfo) for t in result)
        assert result[0].name == "python"


# ── Write operations ─────────────────────────────────────────────────────


class TestCreateNote:
    def test_creates_and_returns(self, mock_client: MagicMock) -> None:
        mock_client.create_note.return_value = _make_note()
        result = service.create_note(title="Test", content="body")
        assert isinstance(result, CreatedNote)
        assert result.guid == "note-1"
        mock_client.create_note.assert_called_once_with(
            title="Test",
            markdown="body",
            notebook_guid=None,
            tag_names=None,
        )

    def test_resolves_notebook(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [_make_notebook("nb-1", "Work")]
        mock_client.create_note.return_value = _make_note()
        service.create_note(title="T", content="c", notebook_name="Work")
        _, kwargs = mock_client.create_note.call_args
        assert kwargs["notebook_guid"] == "nb-1"

    def test_notebook_not_found_raises(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = []
        with pytest.raises(ValueError, match="Notebook not found"):
            service.create_note(title="T", content="c", notebook_name="Missing")

    def test_passes_tags(self, mock_client: MagicMock) -> None:
        mock_client.create_note.return_value = _make_note()
        service.create_note(title="T", content="c", tags=["a", "b"])
        _, kwargs = mock_client.create_note.call_args
        assert kwargs["tag_names"] == ["a", "b"]


class TestTagNote:
    def test_delegates_to_client(self, mock_client: MagicMock) -> None:
        mock_client.tag_note.return_value = _make_note(tag_guids=["tag-1"])
        result = service.tag_note("note-1", ["python"])
        assert isinstance(result, NoteMetadata)
        mock_client.tag_note.assert_called_once_with("note-1", ["python"])


class TestUntagNote:
    def test_delegates_to_client(self, mock_client: MagicMock) -> None:
        mock_client.untag_note.return_value = _make_note()
        result = service.untag_note("note-1", ["python"])
        assert isinstance(result, NoteMetadata)
        mock_client.untag_note.assert_called_once_with("note-1", ["python"])


class TestMoveNote:
    def test_moves_note(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = [_make_notebook("nb-2", "Archive")]
        mock_client.move_note.return_value = _make_note(notebook_guid="nb-2")
        result = service.move_note("note-1", "Archive")
        assert isinstance(result, NoteMetadata)
        mock_client.move_note.assert_called_once_with("note-1", "nb-2")

    def test_notebook_not_found_raises(self, mock_client: MagicMock) -> None:
        mock_client.list_notebooks.return_value = []
        with pytest.raises(ValueError, match="Notebook not found"):
            service.move_note("note-1", "Missing")
