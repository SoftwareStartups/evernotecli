import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  makeNoteStoreMock,
  mockOAuth,
  setupTestClient,
} from '../helpers/mock-note-store.js';

mockOAuth();

const serviceModule = await import('../../src/service.js');

const hashHex = '55aa55aa55aa55aa55aa55aa55aa55aa';
const imgData = new Uint8Array([0xde, 0xad, 0xbe, 0xef]);

let noteStore: ReturnType<typeof makeNoteStoreMock>;

beforeEach(async () => {
  noteStore = makeNoteStoreMock({
    resource: { filename: 'img.png', hashHex, body: imgData },
  });
  await setupTestClient(noteStore);
});

afterEach(() => {
  serviceModule.resetClient();
});

describe('service.getNoteContent with resourceDir', () => {
  test('writes resource files and rewrites markdown refs to local paths', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));
    const result = await serviceModule.getNoteContent('note-1', {
      resourceDir: dir,
    });

    const expectedPath = join(dir, 'img.png');
    expect(result.content).toContain(expectedPath);
    expect(result.content).not.toContain('evernote-resource:');

    const written = await readFile(expectedPath);
    expect(Buffer.from(written)).toEqual(Buffer.from(imgData));
  });

  test('returns normal markdown when no resourceDir provided', async () => {
    const result = await serviceModule.getNoteContent('note-1');
    expect(result.content).toContain('evernote-resource:');
    // getNote with withResourcesData=true (binary fetch) should NOT be called
    const resourceDataCalls = noteStore.getNote.mock.calls.filter(
      (c) => c[2] === true
    );
    expect(resourceDataCalls).toHaveLength(0);
  });
});

describe('service.createNote with sourceNoteGuid', () => {
  test('fetches resources from source note and re-attaches matching resource', async () => {
    const md = `![img.png](evernote-resource:${hashHex})`;
    const result = await serviceModule.createNote(
      'New',
      md,
      '',
      null,
      'src-guid'
    );

    const resourceCalls = noteStore.getNote.mock.calls.filter(
      (c) => c[2] === true
    );
    expect(resourceCalls.length).toBeGreaterThan(0);
    expect(resourceCalls[0][0]).toBe('src-guid');

    expect(noteStore.createNote).toHaveBeenCalledTimes(1);
    const created = noteStore.createNote.mock.calls[0][0] as {
      resources: { mime: string }[];
    };
    expect(created.resources).toHaveLength(1);
    expect(created.resources[0].mime).toBe('image/png');
    expect(result.guid).toBe('new');
  });

  test('warns and continues when source note fetch fails', async () => {
    noteStore.getNote.mockRejectedValueOnce(new Error('Not found'));

    const result = await serviceModule.createNote(
      'New',
      'some content',
      '',
      null,
      'bad-guid'
    );
    expect(result.guid).toBe('new');
    expect(noteStore.createNote).toHaveBeenCalledTimes(1);
  });
});
