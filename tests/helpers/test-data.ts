import type {
  ThriftNote,
  ThriftNotebook,
  ThriftNotesMetadataList,
  ThriftTag,
} from '../../src/client/evernote-client.js';

export function makeNote(overrides?: Partial<ThriftNote>): ThriftNote {
  return {
    guid: 'note-1',
    title: 'Test Note',
    notebookGuid: 'nb-1',
    tagGuids: [],
    tagNames: [],
    created: 1700000000000,
    updated: 1700000001000,
    contentLength: 42,
    ...overrides,
  };
}

export function makeTag(overrides?: Partial<ThriftTag>): ThriftTag {
  return {
    guid: 'tag-1',
    name: 'TestTag',
    ...overrides,
  };
}

export function makeNotebook(
  overrides?: Partial<ThriftNotebook>
): ThriftNotebook {
  return {
    guid: 'nb-1',
    name: 'My Notebook',
    stack: null,
    ...overrides,
  };
}

export function makeSearchResult(
  notes?: ThriftNote[],
  total?: number
): ThriftNotesMetadataList {
  const noteList = notes ?? [makeNote()];
  return {
    notes: noteList,
    totalNotes: total ?? noteList.length,
  };
}
