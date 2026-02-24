"""OAuth 1.0a authentication for Evernote.

Ported from ragevernote's EvernoteOAuthClient + EvernoteOAuthCallbackHandler.
"""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenMissing, TokenRequestDenied

from evernote_mcp.config import Settings

SERVICE_HOST = "www.evernote.com"
OAUTH_PORT = 10500
CALLBACK_HOST = "localhost"


class OAuthError(Exception):
    """Raised when OAuth flow fails or is declined."""


# --- Callback server ---


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackServer  # type: ignore[assignment]

    def do_GET(self) -> None:
        if not self.path.startswith("/oauth_callback?"):
            self.send_response(404)
            self.end_headers()
            return
        self.server.callback_response = self.path
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"<html><body>Authentication complete."
            b" You can close this tab.</body></html>"
        )

    def log_message(self, *args: Any, **kwargs: Any) -> None:
        pass  # silence server log


class _CallbackServer(HTTPServer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.callback_response: str = ""


# --- OAuth flow ---


def _run_oauth_flow(consumer_key: str, consumer_secret: str) -> str:
    """Run full OAuth 1.0a flow with local callback server. Returns access token."""
    session = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        callback_uri=f"http://{CALLBACK_HOST}:{OAUTH_PORT}/oauth_callback",
    )

    # Step 1: Request token
    session.fetch_request_token(f"https://{SERVICE_HOST}/oauth")

    # Step 2: Authorize
    auth_url = session.authorization_url(f"https://{SERVICE_HOST}/OAuth.action")
    print(f"Opening browser for Evernote authorization:\n{auth_url}")
    webbrowser.open(auth_url)

    # Step 3: Wait for callback
    server = _CallbackServer((CALLBACK_HOST, OAUTH_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    try:
        while not server.callback_response:
            time.sleep(0.1)
    finally:
        server.shutdown()
        thread.join()

    # Step 4: Exchange for access token
    try:
        session.parse_authorization_response(server.callback_response)
    except TokenMissing as e:
        raise OAuthError("OAuth declined by user") from e

    try:
        access = session.fetch_access_token(f"https://{SERVICE_HOST}/oauth")
    except TokenRequestDenied as e:
        raise OAuthError("OAuth token request denied") from e

    return access["oauth_token"]


def _load_cached_token(settings: Settings) -> str | None:
    """Load token from cache file if it exists."""
    if not settings.token_path.exists():
        return None
    try:
        data = json.loads(settings.token_path.read_text())
        return data.get("token")
    except (json.JSONDecodeError, KeyError):
        return None


def _save_token(settings: Settings, token: str) -> None:
    """Save token to cache file."""
    settings.token_path.parent.mkdir(parents=True, exist_ok=True)
    settings.token_path.write_text(json.dumps({"token": token}))


def get_token(settings: Settings) -> str:
    """Get Evernote auth token: env var -> cached file -> OAuth flow."""
    # 1. Direct token from env
    if settings.token:
        return settings.token

    # 2. Cached token file
    cached = _load_cached_token(settings)
    if cached:
        return cached

    # 3. Run OAuth flow
    if not settings.consumer_key or not settings.consumer_secret:
        msg = (
            "No EVERNOTE_TOKEN set and no OAuth credentials configured. "
            "Set EVERNOTE_TOKEN or both "
            "EVERNOTE_CONSUMER_KEY and EVERNOTE_CONSUMER_SECRET."
        )
        raise OAuthError(msg)

    token = _run_oauth_flow(settings.consumer_key, settings.consumer_secret)
    _save_token(settings, token)
    return token
