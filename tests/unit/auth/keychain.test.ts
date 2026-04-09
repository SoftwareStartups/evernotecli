import { afterEach, beforeEach, describe, expect, spyOn, test } from 'bun:test';
import {
  deleteSecret,
  getSecret,
  sanitizeCredential,
  setSecret,
} from '../../../src/auth/keychain.js';

describe('sanitizeCredential', () => {
  test('trims whitespace', () => {
    expect(sanitizeCredential('  abc  ')).toBe('abc');
  });

  test('rejects empty string', () => {
    expect(() => sanitizeCredential('')).toThrow('Credential cannot be empty');
  });

  test('rejects whitespace-only', () => {
    expect(() => sanitizeCredential('   ')).toThrow(
      'Credential cannot be empty'
    );
  });

  test('rejects control characters', () => {
    expect(() => sanitizeCredential('abc\x00def')).toThrow(
      'invalid control characters'
    );
  });

  test('allows tabs and newlines in value', () => {
    expect(sanitizeCredential('abc\tdef')).toBe('abc\tdef');
  });

  test('rejects values over 4096 bytes', () => {
    expect(() => sanitizeCredential('a'.repeat(4097))).toThrow(
      'exceeds maximum length'
    );
  });

  test('accepts valid credential', () => {
    expect(sanitizeCredential('S123:abc123def456')).toBe('S123:abc123def456');
  });
});

describe('getSecret', () => {
  let getSpy: ReturnType<typeof spyOn>;

  beforeEach(() => {
    getSpy = spyOn(Bun.secrets, 'get');
  });

  afterEach(() => {
    getSpy.mockRestore();
  });

  test('returns value from keychain', async () => {
    getSpy.mockResolvedValue('S123:token');
    const result = await getSecret('EVERNOTE_TOKEN');
    expect(result).toBe('S123:token');
    expect(getSpy).toHaveBeenCalledWith({
      service: 'com.softwarestartups.evercli',
      name: 'EVERNOTE_TOKEN',
    });
  });

  test('returns null when not found', async () => {
    getSpy.mockResolvedValue(null);
    expect(await getSecret('EVERNOTE_TOKEN')).toBeNull();
  });

  test('returns null on keychain error', async () => {
    getSpy.mockRejectedValue(new Error('keychain unavailable'));
    expect(await getSecret('EVERNOTE_TOKEN')).toBeNull();
  });
});

describe('setSecret', () => {
  let setSpy: ReturnType<typeof spyOn>;

  beforeEach(() => {
    setSpy = spyOn(Bun.secrets, 'set');
  });

  afterEach(() => {
    setSpy.mockRestore();
  });

  test('stores value in keychain', async () => {
    setSpy.mockResolvedValue(undefined);
    await setSecret('EVERNOTE_TOKEN', 'S123:token');
    expect(setSpy).toHaveBeenCalledWith({
      service: 'com.softwarestartups.evercli',
      name: 'EVERNOTE_TOKEN',
      value: 'S123:token',
      allowUnrestrictedAccess: true,
    });
  });

  test('throws on keychain error', async () => {
    setSpy.mockRejectedValue(new Error('keychain unavailable'));
    expect(setSecret('EVERNOTE_TOKEN', 'val')).rejects.toThrow(
      'keychain unavailable'
    );
  });
});

describe('deleteSecret', () => {
  let deleteSpy: ReturnType<typeof spyOn>;

  beforeEach(() => {
    deleteSpy = spyOn(Bun.secrets, 'delete');
  });

  afterEach(() => {
    deleteSpy.mockRestore();
  });

  test('returns true when deleted', async () => {
    deleteSpy.mockResolvedValue(true);
    expect(await deleteSecret('EVERNOTE_TOKEN')).toBe(true);
  });

  test('returns false when not found', async () => {
    deleteSpy.mockResolvedValue(false);
    expect(await deleteSecret('EVERNOTE_TOKEN')).toBe(false);
  });

  test('returns false on keychain error', async () => {
    deleteSpy.mockRejectedValue(new Error('keychain unavailable'));
    expect(await deleteSecret('EVERNOTE_TOKEN')).toBe(false);
  });
});
