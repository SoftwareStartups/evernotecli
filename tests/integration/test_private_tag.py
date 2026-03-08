"""Tests for private tag access control."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from evernote_client import service
from evernote_client.service import PrivateNoteError

from tests.conftest import make_note, make_search_result

PRIVATE_GUID = "tag-private"
PUBLIC_GUID = "tag-public"


@pytest.fixture()
def mock_client(reset_client: None) -> MagicMock:  # noqa: ARG001
    client = MagicMock()
    client.private_tag_guid = PRIVATE_GUID
    with patch.object(service, "get_client", return_value=client):
        yield client


# ── search_notes ─────────────────────────────────────────────────────────


class TestSearchNotesPrivate:
    def test_excludes_private_notes(self, mock_client: MagicMock) -> None:
        public = make_note("note-1", tag_guids=[PUBLIC_GUID])
        private = make_note("note-2", tag_guids=[PRIVATE_GUID])
        mock_client.search_notes.return_value = make_search_result(
            notes=[public, private], total=2
        )
        result = service.search_notes()
        assert len(result.notes) == 1
        assert result.notes[0].guid == "note-1"

    def test_adjusts_total_after_filtering(self, mock_client: MagicMock) -> None:
        public = make_note("note-1", tag_guids=[PUBLIC_GUID])
        private = make_note("note-2", tag_guids=[PRIVATE_GUID])
        mock_client.search_notes.return_value = make_search_result(
            notes=[public, private], total=5
        )
        result = service.search_notes()
        assert result.total == 4  # 5 - 1 filtered

    def test_strips_private_from_tag_filter(self, mock_client: MagicMock) -> None:
        mock_client.search_notes.return_value = make_search_result(notes=[], total=0)
        service.search_notes(tags=["private", "python"])
        _, kwargs = mock_client.search_notes.call_args
        assert kwargs["tag_names"] == ["python"]

    def test_strips_private_case_insensitive(self, mock_client: MagicMock) -> None:
        mock_client.search_notes.return_value = make_search_result(notes=[], total=0)
        service.search_notes(tags=["PRIVATE"])
        _, kwargs = mock_client.search_notes.call_args
        assert kwargs["tag_names"] is None

    def test_non_private_notes_unaffected(self, mock_client: MagicMock) -> None:
        note = make_note("note-1", tag_guids=[PUBLIC_GUID])
        mock_client.search_notes.return_value = make_search_result(
            notes=[note], total=1
        )
        result = service.search_notes()
        assert len(result.notes) == 1
        assert result.total == 1


# ── get_note ─────────────────────────────────────────────────────────────


class TestGetNotePrivate:
    def test_raises_for_private_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        with pytest.raises(PrivateNoteError):
            service.get_note("note-1")

    def test_allows_public_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        result = service.get_note("note-1")
        assert result.guid == "note-1"


# ── get_note_content ──────────────────────────────────────────────────────


class TestGetNoteContentPrivate:
    def test_raises_for_private_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        with pytest.raises(PrivateNoteError):
            service.get_note_content("note-1")

    def test_allows_public_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        mock_client.get_note_content.return_value = "# Hello"
        result = service.get_note_content("note-1")
        assert result.content == "# Hello"


# ── list_tags ─────────────────────────────────────────────────────────────


class TestListTagsPrivate:
    def test_excludes_private_tag(self, mock_client: MagicMock) -> None:
        mock_client.list_tags.return_value = [
            SimpleNamespace(guid=PRIVATE_GUID, name="private"),
            SimpleNamespace(guid=PUBLIC_GUID, name="python"),
        ]
        result = service.list_tags()
        names = [t.name for t in result]
        assert "private" not in names
        assert "python" in names

    def test_excludes_private_case_insensitive(self, mock_client: MagicMock) -> None:
        mock_client.list_tags.return_value = [
            SimpleNamespace(guid=PRIVATE_GUID, name="Private"),
            SimpleNamespace(guid=PUBLIC_GUID, name="python"),
        ]
        result = service.list_tags()
        assert len(result) == 1
        assert result[0].name == "python"


# ── untag_note ────────────────────────────────────────────────────────────


class TestUntagNotePrivate:
    def test_raises_for_private_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        with pytest.raises(PrivateNoteError):
            service.untag_note("note-1", ["python"])

    def test_raises_when_removing_private_tag(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        with pytest.raises(PrivateNoteError):
            service.untag_note("note-1", ["private"])

    def test_raises_when_removing_private_tag_case_insensitive(
        self, mock_client: MagicMock
    ) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        with pytest.raises(PrivateNoteError):
            service.untag_note("note-1", ["PRIVATE"])

    def test_allows_removing_public_tag(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        mock_client.untag_note.return_value = make_note(tag_guids=[])
        result = service.untag_note("note-1", ["python"])
        assert result.guid == "note-1"


# ── tag_note ──────────────────────────────────────────────────────────────


class TestTagNotePrivate:
    def test_raises_for_private_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        with pytest.raises(PrivateNoteError):
            service.tag_note("note-1", ["work"])

    def test_allows_tagging_public_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        mock_client.tag_note.return_value = make_note(tag_guids=[PUBLIC_GUID, "tag-2"])
        result = service.tag_note("note-1", ["work"])
        assert result.guid == "note-1"


# ── move_note ─────────────────────────────────────────────────────────────


class TestMoveNotePrivate:
    def test_raises_for_private_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        mock_client.list_notebooks.return_value = [
            SimpleNamespace(guid="nb-2", name="Archive", stack=None)
        ]
        with pytest.raises(PrivateNoteError):
            service.move_note("note-1", "Archive")

    def test_allows_moving_public_note(self, mock_client: MagicMock) -> None:
        mock_client.get_note.return_value = make_note(tag_guids=[PUBLIC_GUID])
        mock_client.list_notebooks.return_value = [
            SimpleNamespace(guid="nb-2", name="Archive", stack=None)
        ]
        mock_client.move_note.return_value = make_note(
            notebook_guid="nb-2", tag_guids=[PUBLIC_GUID]
        )
        result = service.move_note("note-1", "Archive")
        assert result.guid == "note-1"


# ── create_note ───────────────────────────────────────────────────────────


class TestCreateNotePrivate:
    def test_creating_private_note_is_allowed(self, mock_client: MagicMock) -> None:
        mock_client.create_note.return_value = make_note(tag_guids=[PRIVATE_GUID])
        result = service.create_note(title="Secret", content="body", tags=["private"])
        assert result.guid == "note-1"
        _, kwargs = mock_client.create_note.call_args
        assert kwargs["tag_names"] == ["private"]
