import { describe, expect, mock, test } from 'bun:test';
import { EvernoteClient } from '../../src/client/evernote-client.js';

const FAKE_TOKEN = 'S=s1:U=1:E=1:C=1:A=en_oauth:V=2:H=abc';

function makeClient(nsOverrides: Record<string, ReturnType<typeof mock>>) {
  const client = new EvernoteClient(FAKE_TOKEN);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (client as any)._noteStore = nsOverrides;
  return client;
}

describe('EvernoteClient.getNoteResources', () => {
  test('returns resource data from note', async () => {
    const hash = Buffer.alloc(16, 1);
    const hashHex = hash.toString('hex');
    const ns = {
      getNote: mock(() =>
        Promise.resolve({
          resources: [
            {
              data: { bodyHash: hash, body: Buffer.from([1, 2, 3]), size: 3 },
              mime: 'image/png',
              attributes: { fileName: 'shot.png' },
            },
          ],
        })
      ),
    };

    const client = makeClient(ns);
    const resources = await client.getNoteResources('note-guid');

    expect(resources).toHaveLength(1);
    expect(resources[0].hashHex).toBe(hashHex);
    expect(resources[0].mimeType).toBe('image/png');
    expect(resources[0].filename).toBe('shot.png');
    expect(resources[0].data).toBeDefined();
    expect(resources[0].data!.length).toBe(3);
  });

  test('skips resources without bodyHash', async () => {
    const ns = {
      getNote: mock(() =>
        Promise.resolve({
          resources: [
            { data: { bodyHash: null }, mime: 'image/png', attributes: {} },
          ],
        })
      ),
    };

    const client = makeClient(ns);
    const resources = await client.getNoteResources('note-guid');
    expect(resources).toHaveLength(0);
  });

  test('handles note with no resources', async () => {
    const ns = {
      getNote: mock(() => Promise.resolve({ resources: undefined })),
    };

    const client = makeClient(ns);
    const resources = await client.getNoteResources('note-guid');
    expect(resources).toHaveLength(0);
  });
});
