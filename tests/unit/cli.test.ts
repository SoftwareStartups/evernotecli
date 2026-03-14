import { describe, expect, test } from 'bun:test';
import {
  EvernoteError,
  EvernoteAuthError,
  EvernoteNotFoundError,
  EvernotePermissionError,
  EvernoteRateLimitError,
  PrivateNoteError,
  OAuthError,
} from '../../src/errors.js';

describe('error types', () => {
  test('EvernoteError is an Error', () => {
    const err = new EvernoteError('test');
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('EvernoteError');
  });

  test('EvernoteAuthError extends EvernoteError', () => {
    const err = new EvernoteAuthError('auth failed');
    expect(err).toBeInstanceOf(EvernoteError);
    expect(err.name).toBe('EvernoteAuthError');
  });

  test('EvernoteNotFoundError extends EvernoteError', () => {
    const err = new EvernoteNotFoundError('not found');
    expect(err).toBeInstanceOf(EvernoteError);
    expect(err.name).toBe('EvernoteNotFoundError');
  });

  test('EvernotePermissionError extends EvernoteError', () => {
    const err = new EvernotePermissionError('denied');
    expect(err).toBeInstanceOf(EvernoteError);
  });

  test('EvernoteRateLimitError has retryAfter', () => {
    const err = new EvernoteRateLimitError(30);
    expect(err).toBeInstanceOf(EvernoteError);
    expect(err.retryAfter).toBe(30);
  });

  test('PrivateNoteError extends EvernoteError', () => {
    const err = new PrivateNoteError('note-1');
    expect(err).toBeInstanceOf(EvernoteError);
    expect(err.name).toBe('PrivateNoteError');
  });

  test('OAuthError extends EvernoteError', () => {
    const err = new OAuthError('oauth failed');
    expect(err).toBeInstanceOf(EvernoteError);
    expect(err.name).toBe('OAuthError');
  });
});

describe('config', () => {
  test('settings has expected shape', async () => {
    const { settings } = await import('../../src/config.js');
    expect(settings).toHaveProperty('token');
    expect(settings).toHaveProperty('consumerKey');
    expect(settings).toHaveProperty('consumerSecret');
    expect(settings).toHaveProperty('tokenPath');
    expect(settings).toHaveProperty('queuePath');
    expect(settings).toHaveProperty('logLevel');
    expect(settings.tokenPath).toContain('.evercli');
    expect(settings.queuePath).toContain('.evercli');
  });
});
