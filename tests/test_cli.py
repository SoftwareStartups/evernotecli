"""Tests for the encl CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from evernote_client.cli import main
from evernote_client.models import (
    CreatedNote,
    NotebookInfo,
    NoteContent,
    NoteMetadata,
    SearchResult,
    TagInfo,
)


@patch("evernote_client.cli.read_commands.service")
class TestReadCommands:
    def test_search(self, mock_service: MagicMock) -> None:
        mock_service.search_notes.return_value = SearchResult(
            notes=[], total=0, offset=0, max_results=20
        )
        result = CliRunner().invoke(main, ["search", "test"])
        assert result.exit_code == 0
        mock_service.search_notes.assert_called_once()

    def test_note(self, mock_service: MagicMock) -> None:
        mock_service.get_note.return_value = NoteMetadata(
            guid="g1", title="Test"
        )
        result = CliRunner().invoke(main, ["note", "g1"])
        assert result.exit_code == 0
        assert "g1" in result.output

    def test_content(self, mock_service: MagicMock) -> None:
        mock_service.get_note_content.return_value = NoteContent(
            guid="g1", title="Test", content="# Hello"
        )
        result = CliRunner().invoke(main, ["content", "g1"])
        assert result.exit_code == 0
        assert "# Hello" in result.output

    def test_notebooks(self, mock_service: MagicMock) -> None:
        mock_service.list_notebooks.return_value = [
            NotebookInfo(guid="nb-1", name="Work", stack="Projects")
        ]
        result = CliRunner().invoke(main, ["notebooks"])
        assert result.exit_code == 0
        assert "Work" in result.output

    def test_tags(self, mock_service: MagicMock) -> None:
        mock_service.list_tags.return_value = [
            TagInfo(guid="t-1", name="python")
        ]
        result = CliRunner().invoke(main, ["tags"])
        assert result.exit_code == 0
        assert "python" in result.output


@patch("evernote_client.cli.write_commands.service")
class TestWriteCommands:
    def test_create(self, mock_service: MagicMock) -> None:
        mock_service.create_note.return_value = CreatedNote(
            guid="g1", title="New Note"
        )
        result = CliRunner().invoke(main, ["create", "New Note", "-c", "body"])
        assert result.exit_code == 0
        assert "g1" in result.output

    def test_tag(self, mock_service: MagicMock) -> None:
        mock_service.tag_note.return_value = NoteMetadata(
            guid="g1", title="Test"
        )
        result = CliRunner().invoke(main, ["tag", "g1", "python"])
        assert result.exit_code == 0

    def test_untag(self, mock_service: MagicMock) -> None:
        mock_service.untag_note.return_value = NoteMetadata(
            guid="g1", title="Test"
        )
        result = CliRunner().invoke(main, ["untag", "g1", "python"])
        assert result.exit_code == 0

    def test_move(self, mock_service: MagicMock) -> None:
        mock_service.move_note.return_value = NoteMetadata(
            guid="g1", title="Test"
        )
        result = CliRunner().invoke(main, ["move", "g1", "Archive"])
        assert result.exit_code == 0


class TestHelp:
    def test_main_help(self) -> None:
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Evernote CLI client" in result.output

    def test_search_help(self) -> None:
        result = CliRunner().invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search notes" in result.output
