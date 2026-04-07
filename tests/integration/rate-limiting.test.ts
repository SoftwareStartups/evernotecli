import { afterEach, describe, expect, test } from 'bun:test';
import { existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { OperationQueue } from '../../src/client/queue.js';
import { EvernoteRateLimitError } from '../../src/errors.js';

const QUEUE_DIR = join(tmpdir(), 'evercli-test-queue');

afterEach(() => {
  if (existsSync(QUEUE_DIR)) {
    rmSync(QUEUE_DIR, { recursive: true });
  }
});

describe('OperationQueue', () => {
  test('starts empty', () => {
    const queue = new OperationQueue(QUEUE_DIR);
    expect(queue.size()).toBe(0);
    expect(queue.isEmpty()).toBe(true);
  });

  test('put increments size', () => {
    const queue = new OperationQueue(QUEUE_DIR);
    queue.put('create_note', { title: 'Test' });
    expect(queue.size()).toBe(1);
    expect(queue.isEmpty()).toBe(false);
  });

  test('processAll runs operations', async () => {
    const queue = new OperationQueue(QUEUE_DIR);
    queue.put('create_note', { title: 'Test' });
    queue.put('create_note', { title: 'Test 2' });

    const results = await queue.processAll({
      create_note: async (params) => params.title,
    });

    expect(results).toHaveLength(2);
    expect(queue.size()).toBe(0);
  });

  test('processAll re-enqueues failed operations', async () => {
    const queue = new OperationQueue(QUEUE_DIR);
    queue.put('create_note', { title: 'Test' });

    const results = await queue.processAll({
      create_note: async () => {
        throw new Error('fail');
      },
    });

    expect(results).toHaveLength(0);
    // Failed operation should be re-enqueued
    expect(queue.size()).toBe(1);
  });

  test('drops operations after max retries', async () => {
    const queue = new OperationQueue(QUEUE_DIR);
    queue.put('create_note', { title: 'Test' });

    // Process 5 times (max retries)
    for (let i = 0; i < 5; i++) {
      await queue.processAll({
        create_note: async () => {
          throw new Error('fail');
        },
      });
    }

    expect(queue.size()).toBe(0);
  });

  test('unknown operations are dropped', async () => {
    const queue = new OperationQueue(QUEUE_DIR);
    queue.put('unknown_op', { title: 'Test' });

    const results = await queue.processAll({
      create_note: async (params) => params.title,
    });

    expect(results).toHaveLength(0);
    expect(queue.size()).toBe(0);
  });
});

describe('EvernoteRateLimitError', () => {
  test('has retryAfter property', () => {
    const err = new EvernoteRateLimitError(60);
    expect(err.retryAfter).toBe(60);
    expect(err.message).toContain('60s');
  });

  test('formats minutes and seconds', () => {
    const err = new EvernoteRateLimitError(125);
    expect(err.message).toContain('2m 5s');
  });
});
