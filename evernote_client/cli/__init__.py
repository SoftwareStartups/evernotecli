"""CLI entry point for encl."""

from __future__ import annotations

import click

from evernote_client.cli.read_commands import content, note, notebooks, search, tags
from evernote_client.cli.write_commands import create, login, move, serve, tag, untag


@click.group()
def main() -> None:
    """Evernote CLI client."""


main.add_command(search)
main.add_command(note)
main.add_command(content)
main.add_command(notebooks)
main.add_command(tags)
main.add_command(create)
main.add_command(tag)
main.add_command(untag)
main.add_command(move)
main.add_command(login)
main.add_command(serve)
