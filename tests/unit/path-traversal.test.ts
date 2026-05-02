import { afterEach, describe, expect, test } from 'bun:test';
import { mkdtemp, readdir } from 'node:fs/promises';
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

async function setupWithFilename(filename: string) {
  const noteStore = makeNoteStoreMock({
    resource: { filename, hashHex, body: imgData },
  });
  await setupTestClient(noteStore);
  return mkdtemp(join(tmpdir(), 'evercli-test-'));
}

describe('Path Traversal Vulnerability Mitigation', () => {
  afterEach(() => {
    serviceModule.resetClient();
  });

  describe('getNoteContent rejects malicious filenames', () => {
    test('rejects ../ traversal', async () => {
      const dir = await setupWithFilename('../../../etc/passwd');
      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects ..\\..\\ traversal', async () => {
      const dir = await setupWithFilename(
        '..\\..\\..\\windows\\system32\\config'
      );
      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects absolute Unix path', async () => {
      const dir = await setupWithFilename('/etc/passwd');
      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects mixed traversal patterns', async () => {
      const dir = await setupWithFilename('subdir/../../../etc/passwd');
      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('allows safe filename in root directory', async () => {
      const dir = await setupWithFilename('safe-image.png');
      const result = await serviceModule.getNoteContent('note-1', {
        resourceDir: dir,
      });
      const expectedPath = join(dir, 'safe-image.png');
      expect(result.content).toContain(expectedPath);
      const files = await readdir(dir);
      expect(files).toContain('safe-image.png');
    });
  });
});
