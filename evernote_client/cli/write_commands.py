"""Write commands for the encl CLI."""

from __future__ import annotations

import click

from evernote_client import service
from evernote_client.auth import get_token
from evernote_client.config import settings


@click.command()
@click.argument("title")
@click.option("-c", "--content", "body", default="", help="Note content (Markdown).")
@click.option("-n", "--notebook", default="", help="Target notebook name.")
@click.option("-t", "--tag", "tag_names", multiple=True, help="Tag names to apply.")
def create(title: str, body: str, notebook: str, tag_names: tuple[str, ...]) -> None:
    """Create a new note."""
    result = service.create_note(
        title=title,
        content=body,
        notebook_name=notebook,
        tags=list(tag_names) or None,
    )
    click.echo(result.model_dump_json(indent=2))


@click.command()
@click.argument("guid")
@click.argument("tag_names", nargs=-1, required=True)
def tag(guid: str, tag_names: tuple[str, ...]) -> None:
    """Add tags to a note."""
    result = service.tag_note(guid, list(tag_names))
    click.echo(result.model_dump_json(indent=2))


@click.command()
@click.argument("guid")
@click.argument("tag_names", nargs=-1, required=True)
def untag(guid: str, tag_names: tuple[str, ...]) -> None:
    """Remove tags from a note."""
    result = service.untag_note(guid, list(tag_names))
    click.echo(result.model_dump_json(indent=2))


@click.command()
@click.argument("guid")
@click.argument("notebook")
def move(guid: str, notebook: str) -> None:
    """Move a note to a different notebook."""
    result = service.move_note(guid, notebook)
    click.echo(result.model_dump_json(indent=2))


@click.command()
def login() -> None:
    """Authenticate with Evernote."""
    token = get_token(settings)
    click.echo(f"Authenticated (token: {token[:8]}...)")


@click.command()
def serve() -> None:
    """Start the MCP server."""
    from evernote_client.mcp import main

    main()
