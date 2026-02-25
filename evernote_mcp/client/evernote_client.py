"""High-level Evernote API client."""

from __future__ import annotations

from typing import Any

from evernote.edam.notestore import NoteStore
from evernote.edam.notestore.ttypes import (
    NoteFilter,
    NotesMetadataResultSpec,
)
from evernote.edam.type.ttypes import Note, Tag
from evernote.edam.userstore import UserStore

from evernote_mcp.client.thrift import Store, get_token_shard
from evernote_mcp.enml.to_enml import markdown_to_enml
from evernote_mcp.enml.to_markdown import enml_to_markdown


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

        return self.note_store.findNotesMetadata(filter_, offset, max_results, spec)

    def get_note(self, guid: str) -> Any:
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
    ) -> Any:
        note = Note()
        note.title = title
        note.content = markdown_to_enml(markdown)
        if notebook_guid:
            note.notebookGuid = notebook_guid
        if tag_names:
            note.tagNames = tag_names
        return self.note_store.createNote(note)

    def _get_note_tag_guids(self, guid: str) -> list[str]:
        """Get tag GUIDs for a note.

        getNote doesn't populate tagGuids, so we use getNoteTagNames
        and map back to GUIDs via listTags.
        """
        tag_names = self.note_store.getNoteTagNames(guid)
        if not tag_names:
            return []
        all_tags = {t.name: t.guid for t in self.list_tags()}
        return [all_tags[n] for n in tag_names if n in all_tags]

    def _resolve_tag_guids(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to GUIDs, creating missing tags."""
        all_tags = {t.name: t.guid for t in self.list_tags()}
        guids: list[str] = []
        for name in tag_names:
            if name in all_tags:
                guids.append(all_tags[name])
            else:
                tag = Tag()
                tag.name = name
                created = self.note_store.createTag(tag)
                guids.append(created.guid)
        return guids

    def _update_note(self, **fields: Any) -> Any:
        """Update a note with the given fields.

        Evernote's updateNote requires title to be set. We fetch the
        existing note to preserve required fields the caller didn't supply.
        """
        guid = fields.get("guid")
        if guid and "title" not in fields:
            existing = self.note_store.getNote(guid, False, False, False, False)
            fields.setdefault("title", existing.title)
        update = Note()
        for key, value in fields.items():
            setattr(update, key, value)
        return self.note_store.updateNote(update)

    def tag_note(self, guid: str, tag_names: list[str]) -> Any:
        existing_guids = self._get_note_tag_guids(guid)
        new_guids = self._resolve_tag_guids(tag_names)
        merged = list(set(existing_guids + new_guids))
        note = self.note_store.getNote(guid, False, False, False, False)
        self._update_note(guid=guid, title=note.title, tagGuids=merged)
        result = self.note_store.getNote(guid, False, False, False, False)
        result.tagGuids = merged
        return result

    def untag_note(self, guid: str, tag_names: list[str]) -> Any:
        existing_guids = set(self._get_note_tag_guids(guid))
        all_tags = {t.name: t.guid for t in self.list_tags()}
        remove_guids = {all_tags[n] for n in tag_names if n in all_tags}
        remaining = list(existing_guids - remove_guids)
        note = self.note_store.getNote(guid, False, False, False, False)
        self._update_note(guid=guid, title=note.title, tagGuids=remaining)
        result = self.note_store.getNote(guid, False, False, False, False)
        result.tagGuids = remaining
        return result

    def move_note(self, guid: str, notebook_guid: str) -> Any:
        self._update_note(guid=guid, notebookGuid=notebook_guid)
        return self.get_note(guid)
