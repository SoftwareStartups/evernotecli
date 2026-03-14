import { describe, expect, test } from 'bun:test';
import { noteMetadataFromThrift } from '../../src/models.js';
import { makeNote, makeNotebook, makeTag } from '../helpers/test-data.js';

describe('NoteMetadata fromThrift', () => {
  test('converts basic note', () => {
    const note = makeNote();
    const result = noteMetadataFromThrift(note);
    expect(result.guid).toBe('note-1');
    expect(result.title).toBe('Test Note');
    expect(result.notebookGuid).toBe('nb-1');
    expect(result.tagGuids).toEqual([]);
    expect(result.created).toBeInstanceOf(Date);
    expect(result.updated).toBeInstanceOf(Date);
  });

  test('converts note with tag names', () => {
    const note = makeNote({ tagNames: ['work', 'important'] });
    const result = noteMetadataFromThrift(note);
    expect(result.tagNames).toEqual(['work', 'important']);
  });

  test('throws on missing GUID', () => {
    expect(() => noteMetadataFromThrift({ guid: null })).toThrow(
      'Note returned without GUID'
    );
  });

  test('defaults title to Untitled', () => {
    const note = makeNote({ title: null });
    const result = noteMetadataFromThrift(note);
    expect(result.title).toBe('Untitled');
  });

  test('handles null timestamps', () => {
    const note = makeNote({ created: null, updated: null });
    const result = noteMetadataFromThrift(note);
    expect(result.created).toBeNull();
    expect(result.updated).toBeNull();
  });
});

describe('model types', () => {
  test('NotebookInfo from thrift', () => {
    const nb = makeNotebook({ stack: 'Work' });
    expect(nb.guid).toBe('nb-1');
    expect(nb.name).toBe('My Notebook');
    expect(nb.stack).toBe('Work');
  });

  test('TagInfo from thrift', () => {
    const tag = makeTag({ guid: 'tag-2', name: 'project' });
    expect(tag.guid).toBe('tag-2');
    expect(tag.name).toBe('project');
  });
});
