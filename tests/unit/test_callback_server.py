"""Tests for OAuth callback server — timeout behavior."""

from __future__ import annotations

import pytest

from evernote_client.auth.callback_server import wait_for_callback


class TestWaitForCallbackTimeout:
    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """wait_for_callback raises TimeoutError when no callback arrives."""
        attr = "evernote_client.auth.callback_server.CALLBACK_TIMEOUT"
        monkeypatch.setattr(attr, 0.3)
        with pytest.raises(TimeoutError, match="OAuth callback not received"):
            wait_for_callback()
