"""Tests for rate-limit retry logic and persistent write queue."""

from __future__ import annotations

from http.client import HTTPException
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from evernote_client.client.queue import OperationQueue
from evernote_client.client.thrift import (
    EvernoteRateLimitError,
    Store,
    _edam_wait,
    _is_retriable,
)
from evernote_client.edam.error.ttypes import EDAMErrorCode, EDAMSystemException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(client: object, token: str | None = None) -> Store:
    """Build a Store without triggering network I/O."""
    store = Store.__new__(Store)
    store.token = token
    store._client = client  # type: ignore[attr-defined]
    return store


def _make_retry_state(exc: BaseException, attempt: int = 1) -> MagicMock:
    """Build a RetryCallState-like mock with the given outcome exception."""
    state = MagicMock()
    state.outcome.exception.return_value = exc
    state.attempt_number = attempt
    return state


# ---------------------------------------------------------------------------
# TestStoreRateLimitHandling
# ---------------------------------------------------------------------------


class TestStoreRateLimitHandling:
    def test_rate_limit_raises_immediately(self) -> None:
        """RATE_LIMIT_REACHED must raise EvernoteRateLimitError on the first attempt."""

        class FakeClient:
            def __init__(self) -> None:
                self.call_count = 0

            def echo(self, value: str) -> str:
                self.call_count += 1
                raise EDAMSystemException(
                    errorCode=EDAMErrorCode.RATE_LIMIT_REACHED,
                    rateLimitDuration=300,
                )

        client = FakeClient()
        store = _make_store(client)

        with (
            patch(
                "evernote_client.client.thrift._execute_api_call",
                side_effect=lambda fn, *a, **kw: fn(*a, **kw),
            ),
            pytest.raises(EvernoteRateLimitError) as exc_info,
        ):
            store.echo("hello")

        assert client.call_count == 1  # no retries
        assert exc_info.value.retry_after == 300

    def test_does_not_retry_on_quota_reached(self) -> None:
        """QUOTA_REACHED must be converted to EvernoteError without retrying."""

        from evernote_client.client.thrift import EvernoteError

        class FakeClient:
            def __init__(self) -> None:
                self.call_count = 0

            def quota_method(self) -> None:
                self.call_count += 1
                raise EDAMSystemException(errorCode=EDAMErrorCode.QUOTA_REACHED)

        client = FakeClient()
        store = _make_store(client)

        with (
            patch(
                "evernote_client.client.thrift._execute_api_call",
                side_effect=lambda fn, *a, **kw: fn(*a, **kw),
            ),
            pytest.raises(EvernoteError),
        ):
            store.quota_method()

        assert client.call_count == 1

    def test_does_not_retry_on_shard_unavailable_beyond_limit(self) -> None:
        """SHARD_UNAVAILABLE is retried up to max attempts then raises EvernoteError."""

        from evernote_client.client.thrift import EvernoteError

        class FakeClient:
            def __init__(self) -> None:
                self.call_count = 0

            def shard_method(self, value: str) -> str:
                self.call_count += 1
                raise EDAMSystemException(errorCode=EDAMErrorCode.SHARD_UNAVAILABLE)

        client = FakeClient()
        store = _make_store(client)

        with (
            patch(
                "evernote_client.client.thrift._execute_api_call",
                side_effect=lambda fn, *a, **kw: fn(*a, **kw),
            ),
            patch("time.sleep"),
            pytest.raises(EvernoteError),
        ):
            store.shard_method("test")

        assert client.call_count == 4  # stop_after_attempt(4)


# ---------------------------------------------------------------------------
# TestEDamWait
# ---------------------------------------------------------------------------


class TestEDamWait:
    def test_uses_exponential_for_rate_limit(self) -> None:
        """RATE_LIMIT_REACHED is no longer retriable so _edam_wait never sees it,
        but if it did it would fall through to exponential backoff."""
        exc = EDAMSystemException(
            errorCode=EDAMErrorCode.RATE_LIMIT_REACHED,
            rateLimitDuration=42,
        )
        state = _make_retry_state(exc, attempt=1)
        wait = _edam_wait(state)
        assert isinstance(wait, float)
        assert wait > 0

    def test_falls_back_to_exponential_for_http(self) -> None:
        exc = HTTPException("connection failed")
        state = _make_retry_state(exc, attempt=1)
        wait = _edam_wait(state)
        assert isinstance(wait, float)
        assert wait > 0


# ---------------------------------------------------------------------------
# TestIsRetriable
# ---------------------------------------------------------------------------


class TestIsRetriable:
    def test_http_exception_is_retriable(self) -> None:
        assert _is_retriable(HTTPException("oops")) is True

    def test_connection_error_is_retriable(self) -> None:
        assert _is_retriable(ConnectionError("reset")) is True

    def test_rate_limit_is_not_retriable(self) -> None:
        """RATE_LIMIT_REACHED is handled by safe_wrapper, not tenacity retry."""
        exc = EDAMSystemException(errorCode=EDAMErrorCode.RATE_LIMIT_REACHED)
        assert _is_retriable(exc) is False

    def test_shard_unavailable_is_retriable(self) -> None:
        exc = EDAMSystemException(errorCode=EDAMErrorCode.SHARD_UNAVAILABLE)
        assert _is_retriable(exc) is True

    def test_quota_reached_is_not_retriable(self) -> None:
        exc = EDAMSystemException(errorCode=EDAMErrorCode.QUOTA_REACHED)
        assert _is_retriable(exc) is False

    def test_generic_exception_is_not_retriable(self) -> None:
        assert _is_retriable(ValueError("bad")) is False


# ---------------------------------------------------------------------------
# TestOperationQueue
# ---------------------------------------------------------------------------


class TestOperationQueue:
    def test_enqueue_and_process(self, tmp_path: Path) -> None:
        q = OperationQueue(tmp_path / "queue")
        calls: list[tuple[str, dict]] = []

        def fake_create(**params: object) -> str:
            calls.append(("create_note", params))  # type: ignore[arg-type]
            return "note_guid"

        dispatcher = {"create_note": fake_create}
        q.put("create_note", title="Test", content="Hello")
        results = q.process_all(dispatcher)

        assert results == ["note_guid"]
        assert calls == [("create_note", {"title": "Test", "content": "Hello"})]

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        queue_path = tmp_path / "queue"
        q1 = OperationQueue(queue_path)
        q1.put("create_note", title="Test", content="Hello")

        q2 = OperationQueue(queue_path)
        assert not q2.is_empty()

        results = q2.process_all({"create_note": lambda **p: "ok"})
        assert results == ["ok"]
        assert q2.is_empty()

    def test_size_and_is_empty(self, tmp_path: Path) -> None:
        q = OperationQueue(tmp_path / "queue")
        assert q.is_empty()
        assert q.size() == 0

        q.put("tag_note", guid="abc", tags=["tag1"])
        assert not q.is_empty()
        assert q.size() == 1

        q.process_all({"tag_note": lambda **p: None})
        assert q.is_empty()

    def test_multiple_operations(self, tmp_path: Path) -> None:
        q = OperationQueue(tmp_path / "queue")
        calls: list[tuple[str, dict]] = []

        def fake_create(**p: object) -> str:
            calls.append(("create_note", p))  # type: ignore[arg-type]
            return "note1"

        def fake_tag(**p: object) -> str:
            calls.append(("tag_note", p))  # type: ignore[arg-type]
            return "note2"

        q.put("create_note", title="T", content="C")
        q.put("tag_note", guid="g", tags=["t"])

        dispatcher = {"create_note": fake_create, "tag_note": fake_tag}
        results = q.process_all(dispatcher)

        assert len(results) == 2
        assert calls[0] == ("create_note", {"title": "T", "content": "C"})
        assert calls[1] == ("tag_note", {"guid": "g", "tags": ["t"]})


# ---------------------------------------------------------------------------
# TestDrainPendingWrites
# ---------------------------------------------------------------------------


class TestDrainPendingWrites:
    def test_drain_returns_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import evernote_client.service as svc

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")

        mock_create = MagicMock(return_value="result1")
        mock_tag = MagicMock(return_value="result2")
        monkeypatch.setitem(svc._WRITE_DISPATCHER, "create_note", mock_create)
        monkeypatch.setitem(svc._WRITE_DISPATCHER, "tag_note", mock_tag)

        svc.enqueue_write("create_note", title="T1", content="C1")
        svc.enqueue_write("tag_note", guid="g1", tags=["t1"])

        count = svc.drain_pending_writes()

        assert count == 2
        mock_create.assert_called_once_with(title="T1", content="C1")
        mock_tag.assert_called_once_with(guid="g1", tags=["t1"])

    def test_drain_empty_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import evernote_client.service as svc

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")

        count = svc.drain_pending_writes()
        assert count == 0


# ---------------------------------------------------------------------------
# TestCLIWriteCommands
# ---------------------------------------------------------------------------


class TestCLIWriteCommands:
    def test_create_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create command prints JSON on success."""
        import evernote_client.service as svc
        from evernote_client.cli import main
        from evernote_client.models import CreatedNote

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        mock_result = CreatedNote(guid="abc123", title="Test", notebook_guid=None)
        monkeypatch.setattr(svc, "create_note", MagicMock(return_value=mock_result))

        runner = CliRunner()
        result = runner.invoke(main, ["create", "Test", "-c", "body"])

        assert result.exit_code == 0
        assert "abc123" in result.output

    def test_create_rate_limited_enqueues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create command enqueues and exits 0 on rate limit."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        monkeypatch.setattr(
            svc,
            "create_note",
            MagicMock(side_effect=EvernoteRateLimitError(retry_after=60)),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["create", "Test", "-c", "body"])

        assert result.exit_code == 0
        assert "queued" in result.output
        assert "60s" in result.output
        assert svc.pending_write_count() == 1

    def test_tag_rate_limited_enqueues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """tag command enqueues on rate limit."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        monkeypatch.setattr(
            svc,
            "tag_note",
            MagicMock(side_effect=EvernoteRateLimitError(retry_after=30)),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["tag", "guid123", "mytag"])

        assert result.exit_code == 0
        assert "queued" in result.output
        assert svc.pending_write_count() == 1

    def test_untag_rate_limited_enqueues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """untag command enqueues on rate limit."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        monkeypatch.setattr(
            svc,
            "untag_note",
            MagicMock(side_effect=EvernoteRateLimitError(retry_after=30)),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["untag", "guid123", "mytag"])

        assert result.exit_code == 0
        assert "queued" in result.output
        assert svc.pending_write_count() == 1

    def test_move_rate_limited_enqueues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """move command enqueues on rate limit."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        monkeypatch.setattr(
            svc,
            "move_note",
            MagicMock(side_effect=EvernoteRateLimitError(retry_after=45)),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["move", "guid123", "MyNotebook"])

        assert result.exit_code == 0
        assert "queued" in result.output
        assert svc.pending_write_count() == 1


# ---------------------------------------------------------------------------
# TestDrainCommand
# ---------------------------------------------------------------------------


class TestDrainCommand:
    def test_drain_empty_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """drain reports no pending operations when queue is empty."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")

        runner = CliRunner()
        result = runner.invoke(main, ["drain"])

        assert result.exit_code == 0
        assert "No pending write operations." in result.output

    def test_drain_processes_queued_items(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """drain processes queued items and reports count."""
        import evernote_client.service as svc
        from evernote_client.cli import main
        from evernote_client.models import CreatedNote

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        mock_result = CreatedNote(guid="abc", title="T", notebook_guid=None)
        monkeypatch.setitem(
            svc._WRITE_DISPATCHER,
            "create_note",
            MagicMock(return_value=mock_result),
        )

        svc.enqueue_write("create_note", title="T", content="C")

        runner = CliRunner()
        result = runner.invoke(main, ["drain"])

        assert result.exit_code == 0
        assert "Processed 1 operation(s). 0 remaining." in result.output

    def test_drain_still_rate_limited(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """drain reports remaining count when operations fail due to rate limit."""
        import evernote_client.service as svc
        from evernote_client.cli import main

        monkeypatch.setattr(svc.settings, "queue_path", tmp_path / "queue")
        monkeypatch.setitem(
            svc._WRITE_DISPATCHER,
            "create_note",
            MagicMock(side_effect=EvernoteRateLimitError(retry_after=60)),
        )

        svc.enqueue_write("create_note", title="T", content="C")

        runner = CliRunner()
        result = runner.invoke(main, ["drain"])

        assert result.exit_code == 0
        assert "again later" in result.output
