"""Write commands for the encl CLI."""

from __future__ import annotations

import sys

import click

from evernote_client import service
from evernote_client.auth import get_token
from evernote_client.client.thrift import EvernoteRateLimitError
from evernote_client.config import settings
from evernote_client.service import PrivateNoteError


@click.command()
@click.argument("title")
@click.option("-c", "--content", "body", default="", help="Note content (Markdown).")
@click.option("-n", "--notebook", default="", help="Target notebook name.")
@click.option("-t", "--tag", "tag_names", multiple=True, help="Tag names to apply.")
def create(title: str, body: str, notebook: str, tag_names: tuple[str, ...]) -> None:
    """Create a new note."""
    try:
        result = service.create_note(
            title=title,
            content=body,
            notebook_name=notebook,
            tags=list(tag_names) or None,
        )
        click.echo(result.model_dump_json(indent=2))
    except EvernoteRateLimitError as exc:
        service.enqueue_write(
            "create_note",
            title=title,
            content=body,
            notebook_name=notebook,
            tags=list(tag_names) or None,
        )
        click.echo(
            f"Rate limited (retry after {exc.retry_after}s) — queued."
            " Run 'encl drain' to process.",
            err=True,
        )


@click.command()
@click.argument("guid")
@click.argument("tag_names", nargs=-1, required=True)
def tag(guid: str, tag_names: tuple[str, ...]) -> None:
    """Add tags to a note."""
    try:
        result = service.tag_note(guid, list(tag_names))
        click.echo(result.model_dump_json(indent=2))
    except PrivateNoteError:
        click.echo("Error: note is private.", err=True)
        sys.exit(1)
    except EvernoteRateLimitError as exc:
        service.enqueue_write("tag_note", guid=guid, tags=list(tag_names))
        click.echo(
            f"Rate limited (retry after {exc.retry_after}s) — queued."
            " Run 'encl drain' to process.",
            err=True,
        )


@click.command()
@click.argument("guid")
@click.argument("tag_names", nargs=-1, required=True)
def untag(guid: str, tag_names: tuple[str, ...]) -> None:
    """Remove tags from a note."""
    try:
        result = service.untag_note(guid, list(tag_names))
        click.echo(result.model_dump_json(indent=2))
    except PrivateNoteError:
        click.echo("Error: note is private.", err=True)
        sys.exit(1)
    except EvernoteRateLimitError as exc:
        service.enqueue_write("untag_note", guid=guid, tags=list(tag_names))
        click.echo(
            f"Rate limited (retry after {exc.retry_after}s) — queued."
            " Run 'encl drain' to process.",
            err=True,
        )


@click.command()
@click.argument("guid")
@click.argument("notebook")
def move(guid: str, notebook: str) -> None:
    """Move a note to a different notebook."""
    try:
        result = service.move_note(guid, notebook)
        click.echo(result.model_dump_json(indent=2))
    except PrivateNoteError:
        click.echo("Error: note is private.", err=True)
        sys.exit(1)
    except EvernoteRateLimitError as exc:
        service.enqueue_write("move_note", guid=guid, notebook_name=notebook)
        click.echo(
            f"Rate limited (retry after {exc.retry_after}s) — queued."
            " Run 'encl drain' to process.",
            err=True,
        )


@click.command()
def drain() -> None:
    """Process all queued write operations."""
    pending = service.pending_write_count()
    if pending == 0:
        click.echo("No pending write operations.")
        return
    count = service.drain_pending_writes()
    remaining = service.pending_write_count()
    click.echo(f"Processed {count} operation(s). {remaining} remaining.")
    if remaining > 0:
        click.echo(
            "Some operations failed (rate limited?). Run 'encl drain' again later.",
            err=True,
        )


@click.command()
def login() -> None:
    """Authenticate with Evernote (always runs OAuth flow)."""
    # Clear any cached token so get_token is forced to run OAuth
    if settings.token_path.exists():
        settings.token_path.unlink()
    token = get_token(settings)
    click.echo(f"Authenticated (token: {token[:8]}...)")


@click.command()
def serve() -> None:
    """Start the MCP server."""
    from evernote_client.mcp import main

    main()
