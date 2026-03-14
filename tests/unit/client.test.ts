import { describe, expect, test } from 'bun:test';
import { getTokenShard } from '../../src/client/thrift-helpers.js';

describe('getTokenShard', () => {
  test('extracts shard from token', () => {
    expect(getTokenShard('S=s1:U=1234:E=abcd')).toBe('s1');
  });

  test('extracts multi-digit shard', () => {
    expect(getTokenShard('S=s123:U=5678:E=efgh')).toBe('s123');
  });
});
