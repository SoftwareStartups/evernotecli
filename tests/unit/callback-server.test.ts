import { describe, expect, test } from 'bun:test';
import {
  CALLBACK_HOST,
  CALLBACK_TIMEOUT,
  OAUTH_PORT,
  SERVICE_HOST,
} from '../../src/auth/callback-server.js';

describe('callback server constants', () => {
  test('SERVICE_HOST is evernote.com', () => {
    expect(SERVICE_HOST).toBe('www.evernote.com');
  });

  test('OAUTH_PORT is 10500', () => {
    expect(OAUTH_PORT).toBe(10500);
  });

  test('CALLBACK_HOST is localhost', () => {
    expect(CALLBACK_HOST).toBe('localhost');
  });

  test('CALLBACK_TIMEOUT is 5 minutes', () => {
    expect(CALLBACK_TIMEOUT).toBe(300_000);
  });
});
