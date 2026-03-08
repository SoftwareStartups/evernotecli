"""Session-scoped fixtures for e2e tests."""

from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from click.testing import CliRunner

from evernote_client import service
from evernote_client.auth.token_store import load_cached_token
from evernote_client.cli import main
from evernote_client.config import settings


@pytest.fixture(scope="session")
def evernote_token() -> str:
    """Return a valid token or skip the session if none is configured."""
    token = settings.token or load_cached_token(settings) or ""
    if not token:
        pytest.skip("No Evernote token — run 'encl login' or set EVERNOTE_TOKEN")
    return token


@pytest.fixture(scope="session", autouse=True)
def _reset_service_client(evernote_token: str) -> Generator[None, None, None]:
    """Ensure a fresh client is created for the test session."""
    service._client = None
    yield
    service._client = None


@pytest.fixture(scope="session")
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner: CliRunner, *args: str) -> tuple[int, str]:
    """Invoke the CLI and return (exit_code, output)."""
    result = runner.invoke(main, list(args))
    return result.exit_code, result.output


@pytest.fixture(scope="session")
def known_notebooks(runner: CliRunner, evernote_token: str) -> list[dict]:  # noqa: ARG001
    code, output = _invoke(runner, "notebooks")
    assert code == 0, f"notebooks failed: {output}"
    return json.loads(output)


@pytest.fixture(scope="session")
def known_tags(runner: CliRunner, evernote_token: str) -> list[dict]:  # noqa: ARG001
    code, output = _invoke(runner, "tags")
    assert code == 0, f"tags failed: {output}"
    return json.loads(output)


@pytest.fixture(scope="session")
def created_note_guid(runner: CliRunner, evernote_token: str) -> str:  # noqa: ARG001
    """Create a test note once per session and return its guid."""
    code, output = _invoke(
        runner,
        "create",
        "E2E Test Note",
        "-c",
        "Test content from e2e CLI suite",
    )
    assert code == 0, f"create failed: {output}"
    data = json.loads(output)
    return data["guid"]
