"""Tests for Evernote client — Store proxy, token parsing, EvernoteClient."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from evernote_client.client.evernote_client import EvernoteClient
from evernote_client.client.thrift import (
    Store,
    TBinaryProtocolHotfix,
    get_token_shard,
)


class TestTokenParsing:
    def test_get_token_shard(self) -> None:
        token = "S=s592:U=ff1234:E=19f5a:C=18abc:P=1cd:A=en-devtoken:V=2:H=abc123"
        assert get_token_shard(token) == "s592"

    def test_get_token_shard_simple(self) -> None:
        token = "S=s1:U=ff:rest"
        assert get_token_shard(token) == "s1"


class _FakeThriftClient:
    """Mimics a Thrift-generated client with bound methods and real signatures."""

    def __init__(self) -> None:
        self.call_log: list[dict[str, object]] = []

    def getNote(self, authenticationToken: str, guid: str) -> str:
        self.call_log.append({"authenticationToken": authenticationToken, "guid": guid})
        return "result"

    def checkVersion(self, clientName: str, edamVersionMajor: int) -> bool:
        self.call_log.append(
            {"clientName": clientName, "edamVersionMajor": edamVersionMajor}
        )
        return True


class TestStoreProxy:
    def test_auto_injects_token(self) -> None:
        """Store should auto-inject authenticationToken into Thrift calls."""
        fake_client = _FakeThriftClient()

        with patch.object(Store, "_get_thrift_client", return_value=fake_client):
            store = Store(
                client_class=MagicMock(),
                store_url="https://example.com",
                token="test-token",
            )
            result = store.getNote("note-guid-123")

        assert result == "result"
        assert len(fake_client.call_log) == 1
        assert fake_client.call_log[0]["authenticationToken"] == "test-token"
        assert fake_client.call_log[0]["guid"] == "note-guid-123"

    def test_skips_token_when_not_in_signature(self) -> None:
        """Skip token injection when method lacks authenticationToken."""
        fake_client = _FakeThriftClient()

        with patch.object(Store, "_get_thrift_client", return_value=fake_client):
            store = Store(
                client_class=MagicMock(),
                store_url="https://example.com",
                token="test-token",
            )
            result = store.checkVersion("evernote-mcp", 2)

        assert result is True
        assert len(fake_client.call_log) == 1
        assert fake_client.call_log[0]["clientName"] == "evernote-mcp"


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
    """Patch note_store cached_property to return mock_store."""
    return patch.object(
        type(client),
        "note_store",
        new_callable=lambda: property(lambda self: mock_store),
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

    def test_uses_provided_tag_map(self) -> None:
        client, mock_store = _make_client()
        with _patch_store(client, mock_store):
            guids = client._resolve_tag_guids(["python"], tag_map={"python": "tag-1"})
        assert guids == ["tag-1"]
        mock_store.listTags.assert_not_called()


class TestTagNote:
    def test_merges_guids(self) -> None:
        client, mock_store = _make_client()
        tags = [_make_tag("existing", "tag-1"), _make_tag("newtag", "tag-2")]
        mock_store.listTags.return_value = tags
        mock_store.getNoteTagNames.return_value = ["existing"]
        note = _make_note()
        mock_store.getNote.return_value = note
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.tag_note("note-1", ["newtag"])

        update_call = mock_store.updateNote.call_args[0][0]
        assert set(update_call.tagGuids) == {"tag-1", "tag-2"}
        assert result.tagGuids is not None
        assert set(result.tagGuids) == {"tag-1", "tag-2"}

    def test_api_call_count(self) -> None:
        """tag_note should call getNote once and listTags once."""
        client, mock_store = _make_client()
        mock_store.listTags.return_value = [_make_tag("t", "tag-1")]
        mock_store.getNoteTagNames.return_value = []
        note = _make_note()
        mock_store.getNote.return_value = note
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.tag_note("note-1", ["t"])

        assert mock_store.getNote.call_count == 1
        assert mock_store.listTags.call_count == 1
        assert result.tagGuids == ["tag-1"]

    def test_listTags_called_once(self) -> None:
        """listTags should be called exactly once even with existing + new tags."""
        client, mock_store = _make_client()
        tags = [_make_tag("old", "tag-1"), _make_tag("new", "tag-2")]
        mock_store.listTags.return_value = tags
        mock_store.getNoteTagNames.return_value = ["old"]
        mock_store.getNote.return_value = _make_note()
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            client.tag_note("note-1", ["new"])

        mock_store.listTags.assert_called_once()


class TestUntagNote:
    def test_removes_guids(self) -> None:
        client, mock_store = _make_client()
        tags = [_make_tag("keep", "tag-1"), _make_tag("remove", "tag-2")]
        mock_store.listTags.return_value = tags
        mock_store.getNoteTagNames.return_value = ["keep", "remove"]
        note = _make_note()
        mock_store.getNote.return_value = note
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            result = client.untag_note("note-1", ["remove"])

        update_call = mock_store.updateNote.call_args[0][0]
        assert update_call.tagGuids == ["tag-1"]
        assert result.tagGuids == ["tag-1"]

    def test_listTags_called_once(self) -> None:
        """listTags should be called exactly once in untag_note."""
        client, mock_store = _make_client()
        tags = [_make_tag("keep", "tag-1"), _make_tag("remove", "tag-2")]
        mock_store.listTags.return_value = tags
        mock_store.getNoteTagNames.return_value = ["keep", "remove"]
        mock_store.getNote.return_value = _make_note()
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            client.untag_note("note-1", ["remove"])

        mock_store.listTags.assert_called_once()
        assert mock_store.getNote.call_count == 1


class TestUpdateNote:
    def test_preserves_title(self) -> None:
        """_update_note fetches existing title when not provided (for move_note)."""
        client, mock_store = _make_client()
        existing = _make_note(title="Original Title")
        mock_store.getNote.return_value = existing
        mock_store.updateNote.return_value = existing

        with _patch_store(client, mock_store):
            client._update_note(guid="note-1", notebook_guid="nb-2")

        update_call = mock_store.updateNote.call_args[0][0]
        assert update_call.title == "Original Title"
        assert update_call.notebookGuid == "nb-2"

    def test_explicit_kwargs(self) -> None:
        """_update_note accepts explicit keyword arguments."""
        client, mock_store = _make_client()
        mock_store.updateNote.return_value = _make_note()

        with _patch_store(client, mock_store):
            client._update_note(
                guid="note-1",
                title="My Title",
                tag_guids=["tag-1"],
                notebook_guid="nb-2",
            )

        update_call = mock_store.updateNote.call_args[0][0]
        assert update_call.guid == "note-1"
        assert update_call.title == "My Title"
        assert update_call.tagGuids == ["tag-1"]
        assert update_call.notebookGuid == "nb-2"
