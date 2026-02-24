"""Pydantic Settings for Evernote MCP server configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVERNOTE_")

    consumer_key: str = ""
    consumer_secret: str = ""
    token: str = ""
    token_path: Path = Path.home() / ".evernote-mcp" / "token.json"


settings = Settings()
