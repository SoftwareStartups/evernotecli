import { describe, expect, test } from 'bun:test';
import { $ } from 'bun';

const hasToken = !!process.env.EVERNOTE_TOKEN;

describe.skipIf(!hasToken)('e2e CLI', () => {
  test('notebooks returns JSON array', async () => {
    const result = await $`bun run src/index.ts notebooks`.text();
    const data = JSON.parse(result);
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
    expect(data[0]).toHaveProperty('guid');
    expect(data[0]).toHaveProperty('name');
  });

  test('tags returns JSON array', async () => {
    const result = await $`bun run src/index.ts tags`.text();
    const data = JSON.parse(result);
    expect(Array.isArray(data)).toBe(true);
  });

  test('search returns SearchResult', async () => {
    const result = await $`bun run src/index.ts search test`.text();
    const data = JSON.parse(result);
    expect(data).toHaveProperty('notes');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('offset');
    expect(Array.isArray(data.notes)).toBe(true);
  });

  test('note returns metadata', async () => {
    // First search to get a GUID
    const searchResult = await $`bun run src/index.ts search --max 1`.text();
    const searchData = JSON.parse(searchResult);
    if (searchData.notes.length === 0) return;

    const guid = searchData.notes[0].guid;
    const result = await $`bun run src/index.ts note ${guid}`.text();
    const data = JSON.parse(result);
    expect(data).toHaveProperty('guid');
    expect(data.guid).toBe(guid);
  });

  test('content returns markdown', async () => {
    // First search to get a GUID
    const searchResult = await $`bun run src/index.ts search --max 1`.text();
    const searchData = JSON.parse(searchResult);
    if (searchData.notes.length === 0) return;

    const guid = searchData.notes[0].guid;
    const result = await $`bun run src/index.ts content ${guid}`.text();
    expect(typeof result).toBe('string');
  });
});
