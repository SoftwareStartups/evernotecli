"""End-to-end tests for the encl CLI against the live Evernote API.

Prerequisites:
  - EVERNOTE_TOKEN env var OR a cached token from ``encl login``
  - A notebook named "encl-e2e" must exist in the account
  - A tag named "encl-e2e-test" must exist in the account

Run:
    uv run pytest -m e2e tests/e2e/test_cli.py -v
    # or with explicit token:
    EVERNOTE_TOKEN="S=s1:..." uv run pytest -m e2e tests/e2e/test_cli.py -v
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from tests.e2e.conftest import _invoke

# ---------------------------------------------------------------------------
# Known fixture data
# ---------------------------------------------------------------------------

KNOWN_NOTE_GUID = "01767038-6860-852a-4240-e1b23757e346"
E2E_NOTEBOOK_NAME = "encl-e2e"
E2E_TAG_NAME = "encl-e2e-test"


# ---------------------------------------------------------------------------
# Read tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestReadCommands:
    def test_notebooks_returns_list(self, known_notebooks: list[dict]) -> None:
        assert isinstance(known_notebooks, list)
        assert len(known_notebooks) > 0
        first = known_notebooks[0]
        assert "guid" in first
        assert "name" in first

    def test_tags_returns_list(self, known_tags: list[dict]) -> None:
        assert isinstance(known_tags, list)
        # May be empty for a new account — just check the shape if non-empty
        if known_tags:
            assert "guid" in known_tags[0]
            assert "name" in known_tags[0]

    def test_search_finds_known_note(self, runner: CliRunner) -> None:
        code, output = _invoke(runner, "search", "Dilip Kumar")
        assert code == 0, output
        data = json.loads(output)
        assert "notes" in data
        guids = [n["guid"] for n in data["notes"]]
        assert KNOWN_NOTE_GUID in guids

    def test_search_with_max_option(self, runner: CliRunner) -> None:
        code, output = _invoke(runner, "search", "", "--max", "5")
        assert code == 0, output
        data = json.loads(output)
        assert len(data["notes"]) <= 5

    def test_note_metadata(self, runner: CliRunner) -> None:
        code, output = _invoke(runner, "note", KNOWN_NOTE_GUID)
        assert code == 0, output
        data = json.loads(output)
        assert data["guid"] == KNOWN_NOTE_GUID
        assert data["title"] == "Dilip Kumar"
        assert "notebook_guid" in data
        assert "created" in data

    def test_content_returns_markdown(self, runner: CliRunner) -> None:
        code, output = _invoke(runner, "content", KNOWN_NOTE_GUID)
        assert code == 0, output
        assert output.strip(), "content should not be empty"
        assert "<?xml" not in output
        assert "<en-note>" not in output


# ---------------------------------------------------------------------------
# Write tests  (ordered; all share created_note_guid)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestWriteCommands:
    def test_create_note_output_shape(self, created_note_guid: str) -> None:
        # created_note_guid fixture already asserted exit_code == 0
        assert created_note_guid, "guid should be non-empty"

    def test_tag_adds_tag(self, runner: CliRunner, created_note_guid: str) -> None:
        code, output = _invoke(runner, "tag", created_note_guid, E2E_TAG_NAME)
        assert code == 0, output
        data = json.loads(output)
        assert data["guid"] == created_note_guid
        assert data["tag_guids"]  # non-empty list

    def test_note_reflects_added_tag(
        self, runner: CliRunner, created_note_guid: str
    ) -> None:
        code, output = _invoke(runner, "note", created_note_guid)
        assert code == 0, output
        data = json.loads(output)
        assert data["tag_guids"]

    def test_untag_removes_tag(self, runner: CliRunner, created_note_guid: str) -> None:
        code, output = _invoke(runner, "untag", created_note_guid, E2E_TAG_NAME)
        assert code == 0, output
        data = json.loads(output)
        assert data["guid"] == created_note_guid

    def test_note_reflects_removed_tag(
        self, runner: CliRunner, created_note_guid: str
    ) -> None:
        code, output = _invoke(runner, "note", created_note_guid)
        assert code == 0, output
        data = json.loads(output)
        assert data["tag_guids"] == []

    def test_move_note(
        self,
        runner: CliRunner,
        created_note_guid: str,
        known_notebooks: list[dict],
    ) -> None:
        target = next(
            (nb for nb in known_notebooks if nb["name"] == E2E_NOTEBOOK_NAME),
            None,
        )
        if target is None:
            pytest.skip(
                f"Notebook '{E2E_NOTEBOOK_NAME}' not found — create it to run this test"
            )
        code, output = _invoke(runner, "move", created_note_guid, E2E_NOTEBOOK_NAME)
        assert code == 0, output
        data = json.loads(output)
        assert data["notebook_guid"] == target["guid"]


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestErrorHandling:
    def test_note_invalid_guid(self, runner: CliRunner) -> None:
        code, _ = _invoke(runner, "note", "00000000-0000-0000-0000-000000000000")
        assert code != 0

    def test_content_invalid_guid(self, runner: CliRunner) -> None:
        code, _ = _invoke(runner, "content", "00000000-0000-0000-0000-000000000000")
        assert code != 0

    def test_move_nonexistent_notebook(
        self, runner: CliRunner, created_note_guid: str
    ) -> None:
        code, _ = _invoke(
            runner, "move", created_note_guid, "__nonexistent_notebook_xyz__"
        )
        assert code != 0
