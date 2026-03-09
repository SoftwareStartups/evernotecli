"""Persistent write-operation queue backed by SQLite."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import persistqueue

logger = logging.getLogger(__name__)


class OperationQueue:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._q: persistqueue.SQLiteQueue = persistqueue.SQLiteQueue(
            str(path), auto_commit=True
        )

    MAX_RETRIES = 5

    def put(self, operation: str, **params: Any) -> None:
        self._q.put({"operation": operation, "params": params, "retries": 0})

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
                retries = item.get("retries", 0) + 1
                if retries >= self.MAX_RETRIES:
                    logger.error(
                        "Queued operation %r failed %d times — dropping",
                        operation,
                        retries,
                    )
                else:
                    logger.warning(
                        "Queued operation %r failed — will re-enqueue (attempt %d/%d)",
                        operation,
                        retries,
                        self.MAX_RETRIES,
                    )
                    logger.debug(
                        "Queued operation %r failure details",
                        operation,
                        exc_info=True,
                    )
                    failed.append({**item, "retries": retries})
                self._q.task_done()
        for item in failed:
            self._q.put(item)
        return results

    def size(self) -> int:
        return self._q.size

    def is_empty(self) -> bool:
        return self._q.empty()
