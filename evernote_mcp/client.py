"""Thrift client for Evernote API with Store proxy, retry, and hotfixes.

Ported from:
- ragevernote: Store proxy with __getattr__ auto-token-injection
- evernote-backup: TBinaryProtocol/THttpClient hotfixes, retry with backoff
"""

from __future__ import annotations

import functools
import inspect
import time
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from typing import Any, cast

from evernote.edam.notestore import NoteStore
from evernote.edam.notestore.ttypes import (
    NoteFilter,
    NotesMetadataResultSpec,
)
from evernote.edam.type.ttypes import Note
from evernote.edam.userstore import UserStore
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.THttpClient import THttpClient

from evernote_mcp.enml import enml_to_markdown, markdown_to_enml

# --- Retry defaults ---

RETRY_MAX = 3
RETRY_DELAY = 0.5
RETRY_BACKOFF = 2.0
RETRY_EXCEPTIONS = (HTTPException, ConnectionError)

# --- Token parsing ---


def get_token_shard(token: str) -> str:
    """Extract shard ID from token string S=s1:U=..."""
    return token[2 : token.index(":")]


# --- Thrift hotfixes ---


class TBinaryProtocolHotfix(TBinaryProtocol):
    """Prevent crash on bad UTF-8 data from server."""

    def readString(self) -> str:
        return cast(str, self.readBinary().decode("utf-8", errors="replace"))  # type: ignore[attr-defined]


class THttpClientHotfix(THttpClient):
    """Fix deprecated key_file/cert_file args in newer Python ssl."""

    def open(self) -> None:  # type: ignore[override]
        if self.scheme == "http":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=self._THttpClient__timeout,  # type: ignore[attr-defined]
            )
        elif self.scheme == "https":  # type: ignore[attr-defined]
            self._THttpClient__http = HTTPSConnection(  # type: ignore[attr-defined]
                self.host,  # type: ignore[arg-type]
                self.port,
                timeout=self._THttpClient__timeout,  # type: ignore[attr-defined]
                context=self.context,  # type: ignore[attr-defined]
            )
        if self.using_proxy():  # type: ignore[attr-defined]
            self._THttpClient__http.set_tunnel(  # type: ignore[attr-defined]
                self.realhost,  # type: ignore[attr-defined]
                self.realport,  # type: ignore[attr-defined]
                {"Proxy-Authorization": self.proxy_auth},  # type: ignore[attr-defined]
            )


# --- Retry decorator ---


def retry_on_network_error(func: Any) -> Any:
    """Exponential backoff retry on HTTPException/ConnectionError."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delay = RETRY_DELAY
        last_exception: Exception | None = None
        for attempt in range(RETRY_MAX + 1):
            try:
                return func(*args, **kwargs)
            except RETRY_EXCEPTIONS as e:
                last_exception = e
                if attempt < RETRY_MAX:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF
        raise last_exception  # type: ignore[misc]

    return wrapper


# --- Store proxy ---


class Store:
    """Proxy that auto-injects authenticationToken into Thrift calls.

    Ported from ragevernote's Store class.
    """

    def __init__(
        self,
        client_class: type,
        store_url: str,
        token: str | None = None,
    ) -> None:
        self.token = token
        self._client = self._get_thrift_client(client_class, store_url)

    def __getattr__(self, name: str) -> Any:
        target_method = getattr(self._client, name)

        if not callable(target_method):
            return target_method

        @retry_on_network_error
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            org_args = inspect.getfullargspec(target_method).args
            if len(org_args) == len(args) + 1:
                return target_method(*args, **kwargs)
            if self.token and "authenticationToken" in org_args:
                skip_args = ["self", "authenticationToken"]
                arg_names = [i for i in org_args if i not in skip_args]
                return functools.partial(
                    target_method,
                    authenticationToken=self.token,
                )(**dict(zip(arg_names, args, strict=False)), **kwargs)
            return target_method(*args, **kwargs)

        return wrapper

    @staticmethod
    def _get_thrift_client(client_class: type, url: str) -> Any:
        http_client = THttpClientHotfix(url)
        http_client.setCustomHeaders(
            {
                "User-Agent": "evernote-mcp/0.1.0",
                "x-feature-version": "3",
                "accept": "application/x-thrift",
                "cache-control": "no-cache",
            }
        )
        protocol = TBinaryProtocolHotfix(http_client)
        return client_class(protocol)


# --- EvernoteClient ---


class EvernoteClient:
    """High-level Evernote API client."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.shard = get_token_shard(token)

    @property
    def note_store(self) -> Store:
        url = f"https://www.evernote.com/edam/note/{self.shard}"
        return Store(NoteStore.Client, url, token=self.token)

    @property
    def user_store(self) -> Store:
        url = "https://www.evernote.com/edam/user"
        return Store(UserStore.Client, url, token=self.token)

    # --- Read operations ---

    def list_notebooks(self) -> list[Any]:
        return self.note_store.listNotebooks()

    def list_tags(self) -> list[Any]:
        return self.note_store.listTags()

    def search_notes(
        self,
        query: str = "",
        notebook_guid: str | None = None,
        tag_names: list[str] | None = None,
        max_results: int = 20,
        offset: int = 0,
    ) -> Any:
        filter_ = NoteFilter()
        filter_.words = query or None
        filter_.inactive = False
        if notebook_guid:
            filter_.notebookGuid = notebook_guid
        if tag_names:
            # Tag names are embedded in the search query with Evernote grammar
            tag_query = " ".join(f'tag:"{t}"' for t in tag_names)
            if filter_.words:
                filter_.words += " " + tag_query
            else:
                filter_.words = tag_query

        spec = NotesMetadataResultSpec()
        spec.includeTitle = True
        spec.includeContentLength = True
        spec.includeCreated = True
        spec.includeUpdated = True
        spec.includeNotebookGuid = True
        spec.includeTagGuids = True

        return self.note_store.findNotesMetadata(
            filter_, offset, max_results, spec
        )

    def get_note(self, guid: str) -> Any:
        return self.note_store.getNote(guid, False, False, False, False)

    def get_note_content(self, guid: str) -> str:
        enml = self.note_store.getNoteContent(guid)
        return enml_to_markdown(enml)

    # --- Write operations ---

    def create_note(
        self,
        title: str,
        markdown: str,
        notebook_guid: str | None = None,
        tag_names: list[str] | None = None,
    ) -> Any:
        note = Note()
        note.title = title
        note.content = markdown_to_enml(markdown)
        if notebook_guid:
            note.notebookGuid = notebook_guid
        if tag_names:
            note.tagNames = tag_names
        return self.note_store.createNote(note)

    def tag_note(self, guid: str, tag_names: list[str]) -> Any:
        note = self.note_store.getNote(guid, False, False, False, False)
        existing_guids = note.tagGuids or []

        # Resolve tag names to guids
        all_tags = {t.name: t.guid for t in self.list_tags()}
        new_guids = [all_tags[name] for name in tag_names if name in all_tags]

        # Create tags that don't exist yet
        for name in tag_names:
            if name not in all_tags:
                from evernote.edam.type.ttypes import Tag

                tag = Tag()
                tag.name = name
                created = self.note_store.createTag(tag)
                new_guids.append(created.guid)

        merged = list(set(existing_guids + new_guids))

        update = Note()
        update.guid = guid
        update.tagGuids = merged
        return self.note_store.updateNote(update)

    def untag_note(self, guid: str, tag_names: list[str]) -> Any:
        note = self.note_store.getNote(guid, False, False, False, False)
        existing_guids = set(note.tagGuids or [])

        all_tags = {t.name: t.guid for t in self.list_tags()}
        remove_guids = {all_tags[name] for name in tag_names if name in all_tags}

        update = Note()
        update.guid = guid
        update.tagGuids = list(existing_guids - remove_guids)
        return self.note_store.updateNote(update)

    def move_note(self, guid: str, notebook_guid: str) -> Any:
        update = Note()
        update.guid = guid
        update.notebookGuid = notebook_guid
        return self.note_store.updateNote(update)
