"""Thrift client infrastructure: Store proxy, hotfixes.

Ported from:
- ragevernote: Store proxy with __getattr__ auto-token-injection
- evernote-backup: TBinaryProtocol/THttpClient hotfixes, retry with backoff
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from http.client import HTTPException
from typing import Any

from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.THttpClient import THttpClient

from evernote_client.edam.error.ttypes import (
    EDAMErrorCode,
    EDAMNotFoundException,
    EDAMSystemException,
    EDAMUserException,
)

# --- Native exception types ---


class EvernoteError(Exception):
    """Base class for Evernote API errors."""


class EvernoteAuthError(EvernoteError):
    """Authentication/authorisation failure (AUTH_EXPIRED, INVALID_AUTH, …)."""


class EvernoteNotFoundError(EvernoteError):
    """Requested resource not found."""


class EvernotePermissionError(EvernoteError):
    """Permission denied."""


class EvernoteRateLimitError(EvernoteError):
    """Server-side rate limit reached. Retry after ``retry_after`` seconds."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Evernote rate limit reached — retry after {retry_after}s "
            f"({retry_after // 60}m {retry_after % 60}s)"
        )


def _convert_edam(
    exc: EDAMUserException | EDAMNotFoundException | EDAMSystemException,
) -> EvernoteError:
    """Convert an immutable Thrift exception to a Python-native one."""
    if isinstance(exc, EDAMNotFoundException):
        identifier = getattr(exc, "identifier", None)
        key = getattr(exc, "key", None)
        return EvernoteNotFoundError(
            f"Not found: identifier={identifier!r}, key={key!r}"
        )
    if isinstance(exc, EDAMSystemException):
        error_code = getattr(exc, "errorCode", None)
        if error_code == EDAMErrorCode.RATE_LIMIT_REACHED:
            raw = getattr(exc, "rateLimitDuration", None)
            retry_after = int(raw) if raw else 60
            logger.warning(
                "Evernote rate limit reached (rateLimitDuration=%s s) — not retrying",
                raw,
            )
            return EvernoteRateLimitError(retry_after)
        return EvernoteError(f"Evernote system error: {error_code}")
    # EDAMUserException
    error_code = getattr(exc, "errorCode", None)
    parameter = getattr(exc, "parameter", None)
    if error_code in (EDAMErrorCode.AUTH_EXPIRED, EDAMErrorCode.INVALID_AUTH):
        code_name = error_code.name if error_code is not None else str(error_code)
        return EvernoteAuthError(
            f"Evernote auth error: {code_name} (parameter={parameter!r}). "
            "Run 'encl login' to re-authenticate."
        )
    if error_code == EDAMErrorCode.PERMISSION_DENIED:
        return EvernotePermissionError(f"Permission denied (parameter={parameter!r})")
    return EvernoteError(f"Evernote API error: {error_code} (parameter={parameter!r})")


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


HTTP_TIMEOUT_MS: int = 30_000  # 30-second socket timeout

logger = logging.getLogger(__name__)


def _is_retriable(exc: BaseException) -> bool:
    # Transient network errors only.
    # RATE_LIMIT_REACHED is NOT retried — it is immediately converted to
    # EvernoteRateLimitError by safe_wrapper so the caller sees a clear message.
    # TimeoutError is NOT retried — a 30 s timeout already waited long enough.
    if isinstance(exc, (HTTPException, ConnectionError)):
        return True
    if isinstance(exc, EDAMSystemException):
        return exc.errorCode == EDAMErrorCode.SHARD_UNAVAILABLE  # type: ignore[attr-defined]
    return False


def _edam_wait(retry_state: RetryCallState) -> float:
    return wait_exponential(multiplier=0.25, exp_base=2)(retry_state)


def _execute_api_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Executor shared across all Store instances.

    Client-side rate limiting is intentionally omitted: the Evernote server
    returns EDAMSystemException(RATE_LIMIT_REACHED) with rateLimitDuration
    when throttled, which the tenacity retry in Store.__getattr__ handles
    correctly.  A ratelimit.sleep_and_retry decorator with a 3600-second
    period would sleep for up to one hour, causing process hangs.
    """
    return fn(*args, **kwargs)


# --- Store proxy ---


class Store:
    """Proxy that auto-injects authenticationToken into Thrift calls."""

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
            retry=retry_if_exception(_is_retriable),
            stop=stop_after_attempt(4),  # 1 initial + 3 retries
            wait=_edam_wait,
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            org_args = inspect.getfullargspec(target_method).args
            if len(org_args) == len(args) + 1:
                return _execute_api_call(target_method, *args, **kwargs)
            if self.token and "authenticationToken" in org_args:
                skip_args = ["self", "authenticationToken"]
                arg_names = [i for i in org_args if i not in skip_args]
                fn = functools.partial(
                    target_method,
                    authenticationToken=self.token,
                )
                return _execute_api_call(
                    fn, **dict(zip(arg_names, args, strict=False)), **kwargs
                )
            return _execute_api_call(target_method, *args, **kwargs)

        def safe_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return wrapper(*args, **kwargs)
            except (
                EDAMUserException,
                EDAMNotFoundException,
                EDAMSystemException,
            ) as exc:
                raise _convert_edam(exc) from None

        return safe_wrapper

    @staticmethod
    def _get_thrift_client(client_class: type, url: str) -> Any:
        http_client = THttpClientHotfix(url)
        http_client.setTimeout(HTTP_TIMEOUT_MS)
        http_client.setCustomHeaders(
            {
                "User-Agent": "evernote-client/0.1.0",
                "x-feature-version": "3",
                "accept": "application/x-thrift",
                "cache-control": "no-cache",
            }
        )
        protocol = TBinaryProtocolHotfix(http_client)
        return client_class(protocol)
