"""Read commands for the encl CLI."""

from __future__ import annotations

import json
import sys

import click

from evernote_client import service
from evernote_client.service import PrivateNoteError


@click.command()
@click.argument("query", default="")
@click.option("-n", "--notebook", default="", help="Filter by notebook name.")
@click.option("-t", "--tag", "tag_names", multiple=True, help="Filter by tag name.")
@click.option("--max", "max_results", default=20, help="Max results (default 20).")
@click.option("--offset", default=0, help="Pagination offset.")
def search(
    query: str,
    notebook: str,
    tag_names: tuple[str, ...],
    max_results: int,
    offset: int,
) -> None:
    """Search notes."""
    result = service.search_notes(
        query=query,
        notebook_name=notebook,
        tags=list(tag_names) or None,
        max_results=max_results,
        offset=offset,
    )
    click.echo(result.model_dump_json(indent=2))


@click.command()
@click.argument("guid")
def note(guid: str) -> None:
    """Show note metadata."""
    try:
        result = service.get_note(guid)
        click.echo(result.model_dump_json(indent=2))
    except PrivateNoteError:
        click.echo("Error: note is private.", err=True)
        sys.exit(1)


@click.command()
@click.argument("guid")
def content(guid: str) -> None:
    """Show note content as Markdown."""
    try:
        result = service.get_note_content(guid)
        click.echo(result.content)
    except PrivateNoteError:
        click.echo("Error: note is private.", err=True)
        sys.exit(1)


@click.command()
def notebooks() -> None:
    """List all notebooks."""
    result = service.list_notebooks()
    click.echo(json.dumps([nb.model_dump() for nb in result], indent=2, default=str))


@click.command()
def tags() -> None:
    """List all tags."""
    result = service.list_tags()
    click.echo(json.dumps([t.model_dump() for t in result], indent=2, default=str))
