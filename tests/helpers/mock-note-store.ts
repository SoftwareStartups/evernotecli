import { mock } from 'bun:test';
import type { NoteStoreProxy } from '../../src/client/evernote-client.js';
import * as service from '../../src/service.js';

// Valid-looking token so EvernoteClient constructor (token shard parser) succeeds.
export const FAKE_TOKEN = 'S=s1:U=1:E=1:C=1:A=en_oauth:V=2:H=abc';

/**
 * Mocks src/auth/oauth.ts so getClient() can construct a client without real credentials.
 * Call once at module top-level before importing service.
 */
export function mockOAuth(): void {
  mock.module('../../src/auth/oauth.js', () => ({
    getToken: () => Promise.resolve(FAKE_TOKEN),
  }));
}

export interface ResourceFixture {
  filename: string;
  hashHex: string;
  body?: Uint8Array;
}

/**
 * Builds a NoteStore mock returning a single-resource note. The third arg of
 * getNote (withResourcesData) selects between the metadata-only and binary-data
 * shapes — matching the pattern in EvernoteClient.getNote/getNoteResources.
 */
export function makeNoteStoreMock(opts: { resource?: ResourceFixture } = {}) {
  const { resource } = opts;

  const getNote = mock(
    (_guid: string, _withContent: boolean, withResourcesData: boolean) => {
      const baseNote = {
        guid: 'note-1',
        title: 'Test',
        notebookGuid: 'nb-1',
        tagGuids: [],
      };
      if (!resource) return Promise.resolve(baseNote);
      const resourceWith = (data: { bodyHash: Buffer; body?: Buffer }) => ({
        ...baseNote,
        resources: [
          {
            data,
            mime: 'image/png',
            attributes: { fileName: resource.filename },
          },
        ],
      });
      const bodyHash = Buffer.from(resource.hashHex, 'hex');
      if (withResourcesData) {
        return Promise.resolve(
          resourceWith({
            bodyHash,
            body: Buffer.from(resource.body ?? new Uint8Array()),
          })
        );
      }
      return Promise.resolve(resourceWith({ bodyHash }));
    }
  );

  const getNoteContent = mock(() => {
    if (!resource) return Promise.resolve('');
    const enml = `<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note><en-media type="image/png" hash="${resource.hashHex}"/></en-note>`;
    return Promise.resolve(enml);
  });

  return {
    getNote,
    getNoteContent,
    getNoteTagNames: mock(() => Promise.resolve([])),
    listTags: mock(() => Promise.resolve([])),
    createNote: mock(() =>
      Promise.resolve({ guid: 'new', title: 'New', notebookGuid: 'nb-1' })
    ),
  };
}

export type NoteStoreMock = ReturnType<typeof makeNoteStoreMock>;

/**
 * Resets the service singleton, constructs a fresh client, and injects the mock
 * NoteStore. Bypasses the private-tag lookup by injecting null.
 */
export async function setupTestClient(noteStore: NoteStoreMock): Promise<void> {
  service.resetClient();
  const client = await service.getClient();
  client._injectNoteStore(noteStore as unknown as NoteStoreProxy);
  client._injectPrivateTagGuid(null);
}
