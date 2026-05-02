import { describe, expect, test } from 'bun:test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { safeJoin } from '../../src/path-utils.js';

const base = mkdtempSync(join(tmpdir(), 'evercli-safejoin-'));

describe('safeJoin', () => {
  test('rejects parent-directory traversal', () => {
    expect(() => safeJoin(base, '../../../etc/passwd')).toThrow(
      'Invalid file path'
    );
  });

  test('rejects backslash traversal', () => {
    expect(() =>
      safeJoin(base, '..\\..\\..\\windows\\system32\\config')
    ).toThrow('Invalid file path');
  });

  test('rejects absolute Unix paths', () => {
    expect(() => safeJoin(base, '/etc/passwd')).toThrow('Invalid file path');
  });

  test('rejects mixed traversal patterns', () => {
    expect(() => safeJoin(base, 'subdir/../../../etc/passwd')).toThrow(
      'Invalid file path'
    );
  });

  test('returns absolute target for safe relative filename', () => {
    expect(safeJoin(base, 'photo.png')).toBe(join(base, 'photo.png'));
  });

  test('allows safe nested path within base', () => {
    expect(safeJoin(base, 'images/photo.png')).toBe(
      join(base, 'images/photo.png')
    );
  });
});
