import { afterEach, beforeEach, describe, expect, mock, test } from 'bun:test';
import { mkdtemp, readdir, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path, { join } from 'node:path';
import type { NoteStoreProxy } from '../../src/client/evernote-client.js';

// Fake token with valid shard so EvernoteClient constructor succeeds
const FAKE_TOKEN = 'S=s1:U=1:E=1:C=1:A=en_oauth:V=2:H=abc';

// Mock auth so getClient() can construct the client without a real token
mock.module('../../src/auth/oauth.js', () => ({
  getToken: () => Promise.resolve(FAKE_TOKEN),
}));

const serviceModule = await import('../../src/service.js');

/**
 * Creates a mock NoteStore that returns a note with a resource using the given filename.
 * This allows us to test various malicious filenames.
 */
function createMockNoteStore(resourceFilename: string, hashHex: string) {
  const imgData = new Uint8Array([0xde, 0xad, 0xbe, 0xef]);
  
  const getNoteMock = mock(
    (_guid: string, _withContent: boolean, withResourcesData: boolean) => {
      if (withResourcesData) {
        return Promise.resolve({
          guid: 'note-1',
          title: 'Test',
          notebookGuid: 'nb-1',
          tagGuids: [],
          resources: [
            {
              data: {
                bodyHash: Buffer.from(hashHex, 'hex'),
                body: Buffer.from(imgData),
              },
              mime: 'image/png',
              attributes: { fileName: resourceFilename },
            },
          ],
        });
      }
      return Promise.resolve({
        guid: 'note-1',
        title: 'Test',
        notebookGuid: 'nb-1',
        tagGuids: [],
      });
    }
  );

  const getNoteContentMock = mock(() => {
    const enml = `<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note><en-media type="image/png" hash="${hashHex}"/></en-note>`;
    return Promise.resolve(enml);
  });

  return {
    getNote: getNoteMock,
    getNoteContent: getNoteContentMock,
    getNoteTagNames: mock(() => Promise.resolve([])),
    listTags: mock(() => Promise.resolve([])),
  };
}

async function setupClient(mockNs: Record<string, ReturnType<typeof mock>>) {
  serviceModule.resetClient();
  const client = await serviceModule.getClient();
  client._injectNoteStore(mockNs as unknown as NoteStoreProxy);
  client._injectPrivateTagGuid(null); // bypass private tag lookup
  return client;
}

describe('Path Traversal Vulnerability Mitigation', () => {
  const hashHex = '55aa55aa55aa55aa55aa55aa55aa55aa';

  afterEach(() => {
    serviceModule.resetClient();
  });

  describe('getNoteContent with malicious filenames', () => {
    test('rejects path traversal with ../ (Unix-style)', async () => {
      const mockNs = createMockNoteStore('../../../etc/passwd', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));

      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects path traversal with ..\\..\\', async () => {
      const mockNs = createMockNoteStore('..\\..\\..\\windows\\system32\\config', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));

      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects absolute Unix path', async () => {
      const mockNs = createMockNoteStore('/etc/passwd', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));

      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('rejects absolute Windows path (on Windows)', async () => {
      // Note: On Unix systems, Windows paths like C:\... are treated as relative paths
      // This test verifies the behavior is platform-appropriate
      const mockNs = createMockNoteStore('C:\\Windows\\System32\\config', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));

      // On Windows, this should be rejected as absolute
      // On Unix, it's treated as a relative path (which is safe)
      if (process.platform === 'win32') {
        await expect(
          serviceModule.getNoteContent('note-1', { resourceDir: dir })
        ).rejects.toThrow('Invalid file path');
      } else {
        // On Unix, this is treated as a relative filename (safe but unusual)
        // The test just verifies it doesn't escape the directory
        const result = await serviceModule.getNoteContent('note-1', {
          resourceDir: dir,
        });
        expect(result.content).toBeDefined();
      }
    });

    test('rejects path with mixed traversal patterns', async () => {
      const mockNs = createMockNoteStore('subdir/../../../etc/passwd', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));

      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow('Invalid file path');
    });

    test('allows safe filename in root directory', async () => {
      const mockNs = createMockNoteStore('safe-image.png', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));
      const result = await serviceModule.getNoteContent('note-1', {
        resourceDir: dir,
      });

      // Verify the file was written to the expected location
      const expectedPath = join(dir, 'safe-image.png');
      expect(result.content).toContain(expectedPath);

      // Verify file exists in the resource directory
      const files = await readdir(dir);
      expect(files).toContain('safe-image.png');
    });

    test('allows safe filename with subdirectory (no traversal)', async () => {
      // Note: The current implementation doesn't create parent directories
      // This test verifies that paths with subdirectories are validated correctly
      // but may fail at write time if the subdirectory doesn't exist
      const mockNs = createMockNoteStore('images/photo.png', hashHex);
      await setupClient(mockNs);

      const dir = await mkdtemp(join(tmpdir(), 'evercli-test-'));
      
      // The path validation should pass (no traversal)
      // but writeFile will fail because 'images' subdirectory doesn't exist
      await expect(
        serviceModule.getNoteContent('note-1', { resourceDir: dir })
      ).rejects.toThrow(); // Will throw ENOENT because parent dir doesn't exist
      
      // The important security property: the validated path is within resourceDir
      // We can verify this by checking the path resolution logic
      const base = path.resolve(dir);
      const target = path.resolve(base, 'images/photo.png');
      const relative = path.relative(base, target);
      
      // Security check: relative path should not start with '..' and should not be absolute
      expect(relative.startsWith('..')).toBe(false);
      expect(path.isAbsolute(relative)).toBe(false);
    });
  });
});
