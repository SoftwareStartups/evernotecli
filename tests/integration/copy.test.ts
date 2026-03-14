import { describe, expect, mock, test } from 'bun:test';
import {
  EvernoteClient,
  type NoteStoreProxy,
} from '../../src/client/evernote-client.js';

const FAKE_TOKEN = 'S=s1:U=1:E=1:C=1:A=en_oauth:V=2:H=abc';

function makeClient(nsOverrides: Record<string, ReturnType<typeof mock>>) {
  const client = new EvernoteClient(FAKE_TOKEN);
  client._injectNoteStore(nsOverrides as unknown as NoteStoreProxy);
  return client;
}

describe('EvernoteClient.copyNote', () => {
  test('calls Thrift copyNote and returns result with updated title', async () => {
    const updateNote = mock(() =>
      Promise.resolve({
        guid: 'new-guid',
        title: 'My Copy',
        notebookGuid: 'nb-1',
      })
    );
    const ns = {
      copyNote: mock(() =>
        Promise.resolve({
          guid: 'new-guid',
          title: 'Original',
          notebookGuid: 'nb-1',
        })
      ),
      updateNote,
    };

    const client = makeClient(ns);
    const result = await client.copyNote('src-guid', 'My Copy', 'nb-1');

    expect(ns.copyNote).toHaveBeenCalledTimes(1);
    expect(ns.copyNote.mock.calls[0][0]).toBe('src-guid');
    expect(ns.copyNote.mock.calls[0][1]).toBe('nb-1');
    // Title differs from original, so updateNote should be called
    expect(updateNote).toHaveBeenCalledTimes(1);
    expect(result.guid).toBe('new-guid');
    expect(result.title).toBe('My Copy');
  });

  test('skips updateNote when title matches original', async () => {
    const updateNote = mock(() => Promise.resolve({}));
    const ns = {
      copyNote: mock(() =>
        Promise.resolve({
          guid: 'new-guid',
          title: 'Same Title',
          notebookGuid: 'nb-1',
        })
      ),
      updateNote,
    };

    const client = makeClient(ns);
    const result = await client.copyNote('src-guid', 'Same Title', 'nb-1');

    expect(ns.copyNote).toHaveBeenCalledTimes(1);
    expect(updateNote).not.toHaveBeenCalled();
    expect(result.guid).toBe('new-guid');
  });
});
