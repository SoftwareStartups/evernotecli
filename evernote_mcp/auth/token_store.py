"""Token cache persistence (load/save)."""

from __future__ import annotations

import json

from evernote_mcp.config import Settings


def load_cached_token(settings: Settings) -> str | None:
    """Load token from cache file if it exists."""
    if not settings.token_path.exists():
        return None
    try:
        data = json.loads(settings.token_path.read_text())
        return data.get("token")
    except (json.JSONDecodeError, KeyError):
        return None


def save_token(settings: Settings, token: str) -> None:
    """Save token to cache file with restricted permissions."""
    settings.token_path.parent.mkdir(parents=True, exist_ok=True)
    settings.token_path.write_text(json.dumps({"token": token}))
    settings.token_path.chmod(0o600)
