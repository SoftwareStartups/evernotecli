"""Persistent write-operation queue backed by SQLite."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import persistqueue

logger = logging.getLogger(__name__)


class OperationQueue:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._q: persistqueue.SQLiteQueue = persistqueue.SQLiteQueue(
            str(path), auto_commit=True
        )

    def put(self, operation: str, **params: Any) -> None:
        self._q.put({"operation": operation, "params": params})

    def process_all(self, dispatcher: dict[str, Callable[..., Any]]) -> list[Any]:
        """Process all queued operations.

        Failed operations are logged and re-enqueued so they are not lost.
        Returns results of successful operations.
        """
        results = []
        failed: list[dict[str, Any]] = []
        while not self._q.empty():
            item = self._q.get(block=False)
            operation = item["operation"]
            fn = dispatcher.get(operation)
            if fn is None:
                logger.error("Unknown queued operation %r — dropping", operation)
                self._q.task_done()
                continue
            try:
                results.append(fn(**item["params"]))
                self._q.task_done()
            except Exception:
                logger.exception(
                    "Queued operation %r failed — will re-enqueue", operation
                )
                self._q.task_done()
                failed.append(item)
        for item in failed:
            self._q.put(item)
        return results

    def size(self) -> int:
        return self._q.size

    def is_empty(self) -> bool:
        return self._q.empty()
