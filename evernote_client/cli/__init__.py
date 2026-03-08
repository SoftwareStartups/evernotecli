"""CLI entry point for encl."""

from __future__ import annotations

from typing import Any

import click

from evernote_client.cli.read_commands import content, note, notebooks, search, tags
from evernote_client.cli.write_commands import (
    create,
    drain,
    login,
    move,
    serve,
    tag,
    untag,
)
from evernote_client.client.thrift import EvernoteError


class _EvernoteGroup(click.Group):
    """Click group that converts EvernoteError subclasses to ClickException."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except EvernoteError as exc:
            raise click.ClickException(str(exc)) from exc


@click.group(cls=_EvernoteGroup)
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
main.add_command(drain)
