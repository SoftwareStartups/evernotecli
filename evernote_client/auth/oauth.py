"""OAuth 1.0a flow + token resolution for Evernote."""

from __future__ import annotations

import webbrowser

from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenMissing, TokenRequestDenied

from evernote_client.auth.callback_server import (
    CALLBACK_HOST,
    OAUTH_PORT,
    SERVICE_HOST,
    wait_for_callback,
)
from evernote_client.auth.token_store import load_cached_token, save_token
from evernote_client.config import Settings


class OAuthError(Exception):
    """Raised when OAuth flow fails or is declined."""


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
    callback_response = wait_for_callback()

    # Step 4: Exchange for access token
    try:
        session.parse_authorization_response(callback_response)
    except TokenMissing as e:
        raise OAuthError("OAuth declined by user") from e

    try:
        access = session.fetch_access_token(f"https://{SERVICE_HOST}/oauth")
    except TokenRequestDenied as e:
        raise OAuthError("OAuth token request denied") from e

    return access["oauth_token"]


def get_token(settings: Settings) -> str:
    """Get Evernote auth token: env var -> cached file -> OAuth flow."""
    # 1. Direct token from env
    if settings.token:
        return settings.token

    # 2. Cached token file
    cached = load_cached_token(settings)
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
    save_token(settings, token)
    return token
