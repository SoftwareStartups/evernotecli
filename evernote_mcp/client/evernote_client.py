"""High-level Evernote API client."""

from __future__ import annotations

import functools
from typing import cast

from evernote_mcp.client.thrift import Store, get_token_shard
from evernote_mcp.edam.notestore import NoteStore
from evernote_mcp.edam.notestore.ttypes import (
    NoteFilter,
    NotesMetadataList,
    NotesMetadataResultSpec,
)
from evernote_mcp.edam.type.ttypes import Note, Notebook, Tag
from evernote_mcp.edam.userstore import UserStore
from evernote_mcp.enml.to_enml import markdown_to_enml
from evernote_mcp.enml.to_markdown import enml_to_markdown


class EvernoteClient:
    """High-level Evernote API client."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.shard = get_token_shard(token)

    @functools.cached_property
    def note_store(self) -> Store:
        url = f"https://www.evernote.com/edam/note/{self.shard}"
        return Store(NoteStore.Client, url, token=self.token)

    @functools.cached_property
    def user_store(self) -> Store:
        url = "https://www.evernote.com/edam/user"
        return Store(UserStore.Client, url, token=self.token)

    # --- Read operations ---

    def list_notebooks(self) -> list[Notebook]:
        return self.note_store.listNotebooks()

    def list_tags(self) -> list[Tag]:
        return self.note_store.listTags()

    def search_notes(
        self,
        query: str = "",
        notebook_guid: str | None = None,
        tag_names: list[str] | None = None,
        max_results: int = 20,
        offset: int = 0,
    ) -> NotesMetadataList:
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

        return self.note_store.findNotesMetadata(filter_, offset, max_results, spec)

    def get_note(self, guid: str) -> Note:
        note = self.note_store.getNote(guid, False, False, False, False)
        note.tagGuids = self._get_note_tag_guids(guid)
        return note

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
    ) -> Note:
        note = Note()
        note.title = title
        note.content = markdown_to_enml(markdown)
        if notebook_guid:
            note.notebookGuid = notebook_guid
        if tag_names:
            note.tagNames = tag_names
        return self.note_store.createNote(note)

    def _build_tag_map(self) -> dict[str, str]:
        """Build a name→guid map from all tags."""
        return {
            cast(str, t.name): cast(str, t.guid)
            for t in self.list_tags()
            if t.name and t.guid
        }

    def _get_note_tag_guids(
        self, guid: str, tag_map: dict[str, str] | None = None
    ) -> list[str]:
        """Get tag GUIDs for a note.

        getNote doesn't populate tagGuids, so we use getNoteTagNames
        and map back to GUIDs via listTags.
        """
        tag_names = self.note_store.getNoteTagNames(guid)
        if not tag_names:
            return []
        if tag_map is None:
            tag_map = self._build_tag_map()
        return [tag_map[n] for n in tag_names if n in tag_map]

    def _resolve_tag_guids(
        self, tag_names: list[str], tag_map: dict[str, str] | None = None
    ) -> list[str]:
        """Resolve tag names to GUIDs, creating missing tags."""
        if tag_map is None:
            tag_map = self._build_tag_map()
        guids: list[str] = []
        for name in tag_names:
            if name in tag_map:
                guids.append(tag_map[name])
            else:
                tag = Tag()
                tag.name = name
                created = self.note_store.createTag(tag)
                guids.append(created.guid)
        return guids

    def _update_note(
        self,
        guid: str,
        title: str | None = None,
        tag_guids: list[str] | None = None,
        notebook_guid: str | None = None,
    ) -> Note:
        """Update a note with the given fields.

        Evernote's updateNote requires title to be set. We fetch the
        existing note to preserve required fields the caller didn't supply.
        """
        if title is None:
            existing = self.note_store.getNote(guid, False, False, False, False)
            title = existing.title
        update = Note()
        update.guid = guid
        update.title = title
        if tag_guids is not None:
            update.tagGuids = tag_guids
        if notebook_guid is not None:
            update.notebookGuid = notebook_guid
        return self.note_store.updateNote(update)

    def tag_note(self, guid: str, tag_names: list[str]) -> Note:
        all_tags = self._build_tag_map()
        existing_guids = self._get_note_tag_guids(guid, tag_map=all_tags)
        new_guids = self._resolve_tag_guids(tag_names, tag_map=all_tags)
        merged = list(set(existing_guids + new_guids))
        note = self.note_store.getNote(guid, False, False, False, False)
        result = self._update_note(guid=guid, title=note.title, tag_guids=merged)
        result.tagGuids = merged
        return result

    def untag_note(self, guid: str, tag_names: list[str]) -> Note:
        all_tags = self._build_tag_map()
        existing_guids = set(self._get_note_tag_guids(guid, tag_map=all_tags))
        remove_guids = {all_tags[n] for n in tag_names if n in all_tags}
        remaining = list(existing_guids - remove_guids)
        note = self.note_store.getNote(guid, False, False, False, False)
        result = self._update_note(guid=guid, title=note.title, tag_guids=remaining)
        result.tagGuids = remaining
        return result

    def move_note(self, guid: str, notebook_guid: str) -> Note:
        self._update_note(guid=guid, notebook_guid=notebook_guid)
        return self.get_note(guid)
