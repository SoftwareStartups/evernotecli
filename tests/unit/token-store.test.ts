import { afterEach, describe, expect, test } from 'bun:test';
import { existsSync, mkdirSync, rmSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { loadToken, saveToken } from '../../src/auth/token-store.js';

const TEST_DIR = join(tmpdir(), 'evercli-test-tokens');
const TOKEN_PATH = join(TEST_DIR, 'token.json');

afterEach(() => {
  if (existsSync(TEST_DIR)) {
    rmSync(TEST_DIR, { recursive: true });
  }
});

describe('loadToken', () => {
  test('returns null when file does not exist', () => {
    expect(loadToken('/nonexistent/path/token.json')).toBeNull();
  });

  test('returns null on invalid JSON', () => {
    mkdirSync(TEST_DIR, { recursive: true });
    Bun.write(TOKEN_PATH, 'not json');
    expect(loadToken(TOKEN_PATH)).toBeNull();
  });

  test('returns token from valid file', () => {
    mkdirSync(TEST_DIR, { recursive: true });
    Bun.write(TOKEN_PATH, JSON.stringify({ token: 'test-token' }));
    expect(loadToken(TOKEN_PATH)).toBe('test-token');
  });

  test('returns null when token key is missing', () => {
    mkdirSync(TEST_DIR, { recursive: true });
    Bun.write(TOKEN_PATH, JSON.stringify({ other: 'value' }));
    expect(loadToken(TOKEN_PATH)).toBeNull();
  });
});

describe('saveToken', () => {
  test('creates directory and writes token', async () => {
    await saveToken(TOKEN_PATH, 'my-secret');
    expect(existsSync(TOKEN_PATH)).toBe(true);
    expect(loadToken(TOKEN_PATH)).toBe('my-secret');
  });

  test('sets restrictive permissions', async () => {
    await saveToken(TOKEN_PATH, 'my-secret');
    const dirStat = statSync(TEST_DIR);
    const fileStat = statSync(TOKEN_PATH);
    // Check permissions (owner-only)
    expect(dirStat.mode & 0o777).toBe(0o700);
    expect(fileStat.mode & 0o777).toBe(0o600);
  });
});
