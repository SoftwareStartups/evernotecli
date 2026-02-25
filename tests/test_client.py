"""Tests for Evernote client — Store proxy, token parsing, retry, EvernoteClient."""

from __future__ import annotations

from http.client import HTTPException
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from evernote_mcp.client.evernote_client import EvernoteClient
from evernote_mcp.client.thrift import (
    RETRY_DELAY,
    RETRY_MAX,
    Store,
    TBinaryProtocolHotfix,
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


class TestTBinaryProtocolHotfix:
    def test_readstring_returns_bytes(self) -> None:
        """readString must return bytes so generated Thrift code can .decode()."""
        proto = TBinaryProtocolHotfix.__new__(TBinaryProtocolHotfix)
        with patch.object(
            TBinaryProtocolHotfix.__bases__[0], "readString", return_value=b"hello"
        ):
            result = proto.readString()
        assert isinstance(result, bytes)
        assert result == b"hello"

    def test_readstring_sanitizes_bad_utf8(self) -> None:
        """Malformed UTF-8 bytes should be replaced with U+FFFD."""
        proto = TBinaryProtocolHotfix.__new__(TBinaryProtocolHotfix)
        bad_bytes = b"hello\x80world"
        with patch.object(
            TBinaryProtocolHotfix.__bases__[0], "readString", return_value=bad_bytes
        ):
            result = proto.readString()
        assert isinstance(result, bytes)
        decoded = result.decode("utf-8")
        assert "\ufffd" in decoded
        assert "hello" in decoded
        assert "world" in decoded

    def test_readstring_handles_str_input(self) -> None:
        """If super().readString() returns str, encode it to bytes."""
        proto = TBinaryProtocolHotfix.__new__(TBinaryProtocolHotfix)
        with patch.object(
            TBinaryProtocolHotfix.__bases__[0], "readString", return_value="text"
        ):
            result = proto.readString()
        assert isinstance(result, bytes)
        assert result == b"text"


def _make_client() -> tuple[EvernoteClient, MagicMock]:
    """Create an EvernoteClient with a mocked note_store."""
    client = EvernoteClient.__new__(EvernoteClient)
    client.token = "S=s1:U=ff:rest"
    client.shard = "s1"
    mock_store = MagicMock()
    return client, mock_store


def _patch_store(client: EvernoteClient, mock_store: MagicMock):  # type: ignore[type-arg]
    """Patch note_store property to return mock_store."""
    return patch.object(
        type(client),
        "note_store",
        new_callable=lambda: property(
            lambda self: mock_store
        ),
    )


def _make_tag(name: str, guid: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, guid=guid)


def _make_note(
    guid: str = "note-1",
    title: str = "Test",
    tag_guids: list[str] | None = None,
    notebook_guid: str = "nb-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        guid=guid,
        title=title,
        tagGuids=tag_guids,
        notebookGuid=notebook_guid,
    )


class TestResolveTagGuids:
    def test_finds_existing_tags(self) -> None:
        client, mock_store = _make_client()
        mock_store.listTags.return_value = [
            _make_tag("python", "tag-1"),
            _make_tag("coding", "tag-2"),
        ]
        with _patch_store(client, mock_store):
            guids = client._resolve_tag_guids(["python"])
        assert guids == ["tag-1"]
        mock_store.createTag.assert_not_called()

    def test_creates_missing_tags(self) -> None:
        client, mock_store = _make_client()
        mock_store.listTags.return_value = [_make_tag("python", "tag-1")]
        mock_store.createTag.return_value = SimpleNamespace(guid="tag-new")
        with _patch_store(client, mock_store):
            guids = client._resolve_tag_guids(["newtagname"])
        assert guids == ["tag-new"]
        mock_store.createTag.assert_called_once()


class TestTagNote:
    def test_merges_guids(self) -> None:
        client, mock_store = _make_client()
        tags = [_make_tag("existing", "tag-1"), _make_tag("newtag", "tag-2")]
        mock_store.listTags.return_value = tags
        # getNoteTagNames returns existing tag names
        mock_store.getNoteTagNames.return_value = ["existing"]
        note = _make_note()
        refetched = _make_note()
        mock_store.getNote.side_effect = [note, refetched]
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.tag_note("note-1", ["newtag"])

        update_call = mock_store.updateNote.call_args[0][0]
        assert set(update_call.tagGuids) == {"tag-1", "tag-2"}
        assert set(result.tagGuids) == {"tag-1", "tag-2"}

    def test_refetches_after_update(self) -> None:
        client, mock_store = _make_client()
        mock_store.listTags.return_value = [_make_tag("t", "tag-1")]
        mock_store.getNoteTagNames.return_value = []
        note = _make_note()
        refetched = _make_note()
        mock_store.getNote.side_effect = [note, refetched]
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.tag_note("note-1", ["t"])

        # getNote called twice: once for title, once for re-fetch
        assert mock_store.getNote.call_count == 2
        assert result.tagGuids == ["tag-1"]


class TestUntagNote:
    def test_removes_guids(self) -> None:
        client, mock_store = _make_client()
        tags = [_make_tag("keep", "tag-1"), _make_tag("remove", "tag-2")]
        mock_store.listTags.return_value = tags
        mock_store.getNoteTagNames.return_value = ["keep", "remove"]
        note = _make_note()
        refetched = _make_note()
        mock_store.getNote.side_effect = [note, refetched]
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.untag_note("note-1", ["remove"])

        update_call = mock_store.updateNote.call_args[0][0]
        assert update_call.tagGuids == ["tag-1"]
        assert result.tagGuids == ["tag-1"]


class TestUpdateNote:
    def test_preserves_title(self) -> None:
        """_update_note fetches existing title when not provided (for move_note)."""
        client, mock_store = _make_client()
        existing = _make_note(title="Original Title")
        mock_store.getNote.return_value = existing
        mock_store.updateNote.return_value = existing

        with _patch_store(client, mock_store):
            client._update_note(guid="note-1", notebookGuid="nb-2")

        update_call = mock_store.updateNote.call_args[0][0]
        assert update_call.title == "Original Title"
        assert update_call.notebookGuid == "nb-2"
