"""Persistent write-operation queue backed by SQLite."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import persistqueue


class OperationQueue:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._q: persistqueue.SQLiteQueue = persistqueue.SQLiteQueue(
            str(path), auto_commit=True
        )

    def put(self, operation: str, **params: Any) -> None:
        self._q.put({"operation": operation, "params": params})

    def process_all(
        self, dispatcher: dict[str, Callable[..., Any]]
    ) -> list[Any]:
        results = []
        while not self._q.empty():
            item = self._q.get(block=False)
            fn = dispatcher[item["operation"]]
            results.append(fn(**item["params"]))
            self._q.task_done()
        return results

    def size(self) -> int:
        return self._q.size

    def is_empty(self) -> bool:
        return self._q.empty()
