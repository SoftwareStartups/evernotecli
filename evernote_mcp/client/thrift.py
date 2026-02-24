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
from typing import Any, cast

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
    """Prevent crash on bad UTF-8 data from server."""

    def readString(self) -> str:
        return cast(str, self.readBinary().decode("utf-8", errors="replace"))  # type: ignore[attr-defined]


class THttpClientHotfix(THttpClient):
    """Fix deprecated key_file/cert_file args in newer Python ssl."""

    def open(self) -> None:  # type: ignore[override]
        if self.scheme == "http":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=self._THttpClient__timeout,  # type: ignore[attr-defined]
            )
        elif self.scheme == "https":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPSConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=self._THttpClient__timeout,  # type: ignore[attr-defined]
                context=self.context,  # type: ignore[attr-defined]
            )
        if self.using_proxy():  # type: ignore[attr-defined]
            self._THttpClient__http.set_tunnel(  # type: ignore[attr-defined]
                self.realhost,  # type: ignore[attr-defined]
                self.realport,  # type: ignore[attr-defined]
                {"Proxy-Authorization": self.proxy_auth},  # type: ignore[attr-defined]
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
