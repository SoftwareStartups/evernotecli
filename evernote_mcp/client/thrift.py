"""Thrift client infrastructure: Store proxy, hotfixes, retry decorator.

Ported from:
- ragevernote: Store proxy with __getattr__ auto-token-injection
- evernote-backup: TBinaryProtocol/THttpClient hotfixes, retry with backoff
"""

from __future__ import annotations

import functools
import inspect
from http.client import HTTPException
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.THttpClient import THttpClient

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
    """Raise on HTTP errors instead of letting the Thrift binary parser
    try to decode HTML error pages from the Evernote API.

    The upstream THttpClient stores status/message but never raises on
    non-200 responses.
    """

    def flush(self) -> None:
        super().flush()
        if self.code != 200:  # type: ignore[attr-defined]
            body = self._THttpClient__http_response.read()  # type: ignore[attr-defined]
            msg = f"Evernote HTTP {self.code}: {body[:500]!r}"  # type: ignore[attr-defined]
            raise HTTPException(msg)


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

        @retry(
            retry=retry_if_exception_type((HTTPException, ConnectionError)),
            stop=stop_after_attempt(4),  # 1 initial + 3 retries
            wait=wait_exponential(multiplier=0.25, exp_base=2),  # 0.5, 1.0, 2.0
            reraise=True,
        )
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
