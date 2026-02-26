"""Tests for OAuth callback server — timeout behavior."""

from __future__ import annotations

import pytest

from evernote_mcp.auth.callback_server import (
    CALLBACK_TIMEOUT,
    wait_for_callback,
)


class TestWaitForCallbackTimeout:
    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """wait_for_callback raises TimeoutError when no callback arrives."""
        monkeypatch.setattr("evernote_mcp.auth.callback_server.CALLBACK_TIMEOUT", 0.3)
        with pytest.raises(TimeoutError, match="OAuth callback not received"):
            wait_for_callback()

    def test_timeout_constant_is_5_minutes(self) -> None:
        assert CALLBACK_TIMEOUT == 300
