"""Pydantic Settings for Evernote client configuration."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _data_dir() -> Path:
    """Default data directory, resilient to missing home."""
    try:
        return Path.home() / ".evernote-client"
    except (RuntimeError, KeyError):
        return Path("/tmp/evernote-client")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVERNOTE_",
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    consumer_key: SecretStr = SecretStr("")
    consumer_secret: SecretStr = SecretStr("")
    token: SecretStr = SecretStr("")
    token_path: Path = _data_dir() / "token.json"
    queue_path: Path = _data_dir() / "queue"


settings = Settings()
