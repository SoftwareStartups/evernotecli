"""Thrift client infrastructure: Store proxy, hotfixes, retry decorator.

Ported from:
- ragevernote: Store proxy with __getattr__ auto-token-injection
- evernote-backup: TBinaryProtocol/THttpClient hotfixes, retry with backoff
"""

from __future__ import annotations

import functools
import inspect
import time
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from typing import Any

from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.THttpClient import THttpClient

# --- Retry defaults ---

RETRY_MAX = 3
RETRY_DELAY = 0.5
RETRY_BACKOFF = 2.0
RETRY_EXCEPTIONS = (HTTPException, ConnectionError)

# --- Token parsing ---


def get_token_shard(token: str) -> str:
    """Extract shard ID from token string S=s1:U=..."""
    return token[2 : token.index(":")]


# --- Thrift hotfixes ---


class TBinaryProtocolHotfix(TBinaryProtocol):
    """Sanitize bad UTF-8 from server while returning bytes.

    The generated Thrift code expects readString() to return bytes — it calls
    .decode('utf-8') on the result to produce str fields on Thrift objects.
    We sanitize by round-tripping through decode/encode with replacement so
    malformed sequences become U+FFFD rather than crashing the decode step.
    """

    def readString(self) -> bytes:  # type: ignore[override]
        raw = super().readString()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace").encode("utf-8")
        return raw.encode("utf-8")


class THttpClientHotfix(THttpClient):
    """Fix bugs in the evernote3-bundled THttpClient.

    1. flush() — check HTTP status and raise on server errors instead of
       letting the Thrift protocol try to parse HTML error pages as binary.

    2. readAll() — the base class delegates to a single read(sz) call, but
       HTTPResponse.read(sz) may return fewer than sz bytes for large
       responses. We loop until all requested bytes are collected.

    3. open() — the base class ignores setTimeout(); it only sets the global
       default socket timeout during flush(). We pass the timeout directly
       to HTTPConnection/HTTPSConnection.
    """

    def flush(self) -> None:
        super().flush()
        status = self.response.status  # type: ignore[attr-defined]
        if status != 200:
            body = self.response.read()  # type: ignore[attr-defined]
            msg = f"Evernote HTTP {status}: {body[:500]!r}"
            raise HTTPException(msg)

    def readAll(self, sz: int) -> bytes:  # type: ignore[override]
        buff = b""
        while len(buff) < sz:
            chunk = self.read(sz - len(buff))
            if not chunk:
                raise EOFError()
            buff += chunk
        return buff

    def open(self) -> None:  # type: ignore[override]
        timeout = self._THttpClient__timeout  # type: ignore[attr-defined]
        if self.scheme == "http":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=timeout,
            )
        elif self.scheme == "https":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPSConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=timeout,
            )


# --- Retry decorator ---


def retry_on_network_error(func: Any) -> Any:
    """Exponential backoff retry on HTTPException/ConnectionError."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delay = RETRY_DELAY
        last_exception: Exception | None = None
        for attempt in range(RETRY_MAX + 1):
            try:
                return func(*args, **kwargs)
            except RETRY_EXCEPTIONS as e:
                last_exception = e
                if attempt < RETRY_MAX:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF
        raise last_exception  # type: ignore[misc]

    return wrapper


# --- Store proxy ---


class Store:
    """Proxy that auto-injects authenticationToken into Thrift calls.

    Ported from ragevernote's Store class.
    """

    def __init__(
        self,
        client_class: type,
        store_url: str,
        token: str | None = None,
    ) -> None:
        self.token = token
        self._client = self._get_thrift_client(client_class, store_url)

    def __getattr__(self, name: str) -> Any:
        target_method = getattr(self._client, name)

        if not callable(target_method):
            return target_method

        @retry_on_network_error
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            org_args = inspect.getfullargspec(target_method).args
            if len(org_args) == len(args) + 1:
                return target_method(*args, **kwargs)
            if self.token and "authenticationToken" in org_args:
                skip_args = ["self", "authenticationToken"]
                arg_names = [i for i in org_args if i not in skip_args]
                return functools.partial(
                    target_method,
                    authenticationToken=self.token,
                )(**dict(zip(arg_names, args, strict=False)), **kwargs)
            return target_method(*args, **kwargs)

        return wrapper

    @staticmethod
    def _get_thrift_client(client_class: type, url: str) -> Any:
        http_client = THttpClientHotfix(url)
        http_client.setCustomHeaders(
            {
                "User-Agent": "evernote-mcp/0.1.0",
                "x-feature-version": "3",
                "accept": "application/x-thrift",
                "cache-control": "no-cache",
            }
        )
        protocol = TBinaryProtocolHotfix(http_client)
        return client_class(protocol)
