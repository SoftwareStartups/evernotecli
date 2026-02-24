"""Pydantic Settings for Evernote MCP server configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVERNOTE_",
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    consumer_key: str = ""
    consumer_secret: str = ""
    token: str = ""
    token_path: Path = Path.home() / ".evernote-mcp" / "token.json"


settings = Settings()
