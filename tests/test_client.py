"""Tests for Evernote client — Store proxy, token parsing, retry."""

from __future__ import annotations

from http.client import HTTPException
from unittest.mock import MagicMock, patch

import pytest

from evernote_mcp.client.thrift import (
    RETRY_DELAY,
    RETRY_MAX,
    Store,
    get_token_shard,
    retry_on_network_error,
)


class TestTokenParsing:
    def test_get_token_shard(self) -> None:
        token = "S=s592:U=ff1234:E=19f5a:C=18abc:P=1cd:A=en-devtoken:V=2:H=abc123"
        assert get_token_shard(token) == "s592"

    def test_get_token_shard_simple(self) -> None:
        token = "S=s1:U=ff:rest"
        assert get_token_shard(token) == "s1"


class TestRetry:
    @patch("evernote_mcp.client.thrift.time.sleep")
    def test_retries_on_http_exception(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry_on_network_error
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise HTTPException("connection reset")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch("evernote_mcp.client.thrift.time.sleep")
    def test_retries_on_connection_error(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @retry_on_network_error
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("refused")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 2

    @patch("evernote_mcp.client.thrift.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep: MagicMock) -> None:
        @retry_on_network_error
        def always_fails() -> str:
            raise HTTPException("permanent failure")

        with pytest.raises(HTTPException):
            always_fails()

        assert mock_sleep.call_count == RETRY_MAX

    @patch("evernote_mcp.client.thrift.time.sleep")
    def test_exponential_backoff(self, mock_sleep: MagicMock) -> None:
        @retry_on_network_error
        def always_fails() -> str:
            raise HTTPException("fail")

        with pytest.raises(HTTPException):
            always_fails()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays[0] == RETRY_DELAY
        assert delays[1] == RETRY_DELAY * 2
        assert delays[2] == RETRY_DELAY * 4

    def test_no_retry_on_other_exceptions(self) -> None:
        call_count = 0

        @retry_on_network_error
        def bad() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            bad()
        assert call_count == 1


class TestStoreProxy:
    def test_auto_injects_token(self) -> None:
        """Store should auto-inject authenticationToken into Thrift calls."""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        # Simulate a Thrift method that takes (self, authenticationToken, guid)
        mock_method = MagicMock(return_value="result")
        mock_method.__name__ = "getNote"
        import inspect

        # Create a fake argspec
        mock_spec = inspect.FullArgSpec(
            args=["self", "authenticationToken", "guid"],
            varargs=None,
            varkw=None,
            defaults=None,
            kwonlyargs=[],
            kwonlydefaults=None,
            annotations={},
        )

        mock_client_instance.getNote = mock_method

        with (
            patch.object(
                Store, "_get_thrift_client", return_value=mock_client_instance
            ),
            patch(
                "evernote_mcp.client.thrift.inspect.getfullargspec",
                return_value=mock_spec,
            ),
        ):
            store = Store(
                client_class=mock_client_class,
                store_url="https://example.com",
                token="test-token",
            )
            result = store.getNote("note-guid-123")

        assert result == "result"
        # Verify the token was injected
        mock_method.assert_called_once()
        call_kwargs = mock_method.call_args
        # The call should have authenticationToken=test-token
        assert call_kwargs[1]["authenticationToken"] == "test-token"
