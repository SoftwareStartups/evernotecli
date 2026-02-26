"""Tests for token store — load/save with file permissions."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from evernote_mcp.auth.token_store import load_cached_token, save_token
from evernote_mcp.config import Settings


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(token_path=tmp_path / "token.json")


class TestLoadCachedToken:
    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        assert load_cached_token(s) is None

    def test_returns_token_when_valid(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        s.token_path.write_text(json.dumps({"token": "abc123"}))
        assert load_cached_token(s) == "abc123"

    def test_returns_none_on_corrupt_json(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        s.token_path.write_text("not json")
        assert load_cached_token(s) is None

    def test_returns_none_when_key_missing(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        s.token_path.write_text(json.dumps({"other": "value"}))
        assert load_cached_token(s) is None


class TestSaveToken:
    def test_saves_and_loads(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        save_token(s, "my-token")
        assert load_cached_token(s) == "my-token"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        s = Settings(token_path=tmp_path / "deep" / "nested" / "token.json")
        save_token(s, "tok")
        assert s.token_path.exists()

    def test_file_permissions_are_restricted(self, tmp_path: Path) -> None:
        s = _make_settings(tmp_path)
        save_token(s, "secret-token")
        mode = s.token_path.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600
