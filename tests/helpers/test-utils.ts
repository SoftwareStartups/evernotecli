import { mock } from 'bun:test';
import * as service from '../../src/service.js';

/**
 * Create a mock EvernoteClient with all methods mocked.
 * Patches service.getClient to return it.
 */
export function createMockClient() {
  const client = {
    getPrivateTagGuid: mock(() => Promise.resolve(null)),
    listNotebooks: mock(() => Promise.resolve([])),
    listTags: mock(() => Promise.resolve([])),
    searchNotes: mock(() =>
      Promise.resolve({ notes: [], totalNotes: 0 })
    ),
    getNote: mock(() => Promise.resolve({})),
    getNoteContent: mock(() => Promise.resolve('')),
    createNote: mock(() => Promise.resolve({})),
    tagNote: mock(() => Promise.resolve({})),
    untagNote: mock(() => Promise.resolve({})),
    moveNote: mock(() => Promise.resolve({})),
    buildTagMap: mock(() => Promise.resolve(new Map())),
    noteStore: {},
    userStore: {},
  };

  // Patch getClient to return our mock
  const originalModule = require('../../src/service.js');
  // We'll use mock.module in test files instead

  return client;
}

export function resetServiceClient(): void {
  service.resetClient();
}
