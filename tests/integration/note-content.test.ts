import { afterEach, beforeEach, describe, expect, mock, test } from 'bun:test';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

// Fake token with valid shard so EvernoteClient constructor succeeds
const FAKE_TOKEN = 'S=s1:U=1:E=1:C=1:A=en_oauth:V=2:H=abc';
const hashHex = '55aa55aa55aa55aa55aa55aa55aa55aa';
const imgData = new Uint8Array([0xde, 0xad, 0xbe, 0xef]);

// Mock auth so getClient() can construct the client without a real token
mock.module('../../src/auth/oauth.js', () => ({
  getToken: () => Promise.resolve(FAKE_TOKEN),
}));

const serviceModule = await import('../../src/service.js');

// NoteStore mock (Promise-based — injected as _noteStore to bypass Store proxy)
// Differentiates by withResourcesData (3rd arg) to serve different data per call type
const getNoteMock = mock(
  (_guid: string, _withContent: boolean, withResourcesData: boolean) => {
    if (withResourcesData) {
      return Promise.resolve({
        guid: 'note-1',
        title: 'Test',
        notebookGuid: 'nb-1',
        resources: [
          {
            data: {
              bodyHash: Buffer.from(hashHex, 'hex'),
              body: Buffer.from(imgData),
            },
            mime: 'image/png',
            attributes: { fileName: 'img.png' },
          },
        ],
      });
    }
    return Promise.resolve({
      guid: 'note-1',
      title: 'Test',
      notebookGuid: 'nb-1',
      tagGuids: [],
      resources: [
        {
          data: { bodyHash: Buffer.from(hashHex, 'hex') },
          mime: 'image/png',
          attributes: { fileName: 'img.png' },
        },
      ],
    });
  }
);
const getNoteContentMock = mock(() => {
  const enml = `<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note><en-media type="image/png" hash="${hashHex}"/></en-note>`;
  return Promise.resolve(enml);
});
const getNoteTagNamesMock = mock(() => Promise.resolve([]));
const listTagsMock = mock(() => Promise.resolve([]));
const createNoteMock = mock(() =>
  Promise.resolve({ guid: 'new', title: 'New', notebookGuid: 'nb-1' })
);

// getNoteResources mock: returns resource with binary data
const getNoteResourcesMock = mock(() =>
  Promise.resolve({
    resources: [
      {
        data: {
          bodyHash: Buffer.from(hashHex, 'hex'),
          body: Buffer.from(imgData),
        },
        mime: 'image/png',
        attributes: { fileName: 'img.png' },
      },
    ],
  })
);

const mockNs = {
  getNote: getNoteMock,
  getNoteContent: getNoteContentMock,
  getNoteTagNames: getNoteTagNamesMock,
  listTags: listTagsMock,
  createNote: createNoteMock,
};

async function setupClient() {
  serviceModule.resetClient();
  const client = await serviceModule.getClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (client as any)._noteStore = mockNs;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (client as any)._privateTagGuid = null; // bypass private tag lookup
  return client;
}

beforeEach(async () => {
  await setupClient();
  getNoteMock.mockClear();
  getNoteContentMock.mockClear();
  getNoteTagNamesMock.mockClear();
  getNoteResourcesMock.mockClear();
  createNoteMock.mockClear();
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
    // getNote for resources (withResourcesData=true) should NOT be called
    const resourceDataCalls = getNoteMock.mock.calls.filter(
      (c: unknown[]) => c[2] === true
    );
    expect(resourceDataCalls).toHaveLength(0);
  });
});

describe('service.createNote with sourceNoteGuid', () => {
  test('fetches resources from source note and re-attaches matching resource', async () => {
    // Use hashHex so the resource fetched from getNoteResources matches the markdown ref
    const md = `![img.png](evernote-resource:${hashHex})`;
    const result = await serviceModule.createNote(
      'New',
      md,
      '',
      null,
      'src-guid'
    );

    // Verify getNoteResources was called for the source note
    const resourceCalls = getNoteMock.mock.calls.filter(
      (c: unknown[]) => c[2] === true
    );
    expect(resourceCalls.length).toBeGreaterThan(0);
    expect(resourceCalls[0][0]).toBe('src-guid');

    expect(createNoteMock).toHaveBeenCalledOnce();
    const created = createNoteMock.mock.calls[0][0];
    // Resource should be attached because hash matches
    expect(created.resources).toHaveLength(1);
    expect(created.resources[0].mime).toBe('image/png');
    expect(result.guid).toBe('new');
  });

  test('warns and continues when source note fetch fails', async () => {
    getNoteMock.mockRejectedValueOnce(new Error('Not found'));

    const result = await serviceModule.createNote(
      'New',
      'some content',
      '',
      null,
      'bad-guid'
    );
    expect(result.guid).toBe('new');
    expect(createNoteMock).toHaveBeenCalledOnce();
  });
});
