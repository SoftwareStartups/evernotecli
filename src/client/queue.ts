import { mkdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { chmod } from 'node:fs/promises';
import { join } from 'node:path';
import { logger } from '../logger.js';

interface QueueItem {
  operation: string;
  params: Record<string, unknown>;
  retries: number;
}

type Dispatcher = Record<
  string,
  (params: Record<string, unknown>) => Promise<unknown>
>;

const MAX_RETRIES = 5;

/**
 * Persistent write-operation queue backed by a JSON file.
 * Simple file-based queue for durability without requiring SQLite.
 */
export class OperationQueue {
  private filePath: string;

  constructor(queuePath: string) {
    mkdirSync(queuePath, { recursive: true });
    chmod(queuePath, 0o700).catch((err) =>
      logger.warn(`Could not set queue dir permissions: ${err}`)
    );
    this.filePath = join(queuePath, 'queue.json');
  }

  private load(): QueueItem[] {
    if (!existsSync(this.filePath)) return [];
    try {
      return JSON.parse(readFileSync(this.filePath, 'utf-8'));
    } catch {
      return [];
    }
  }

  private save(items: QueueItem[]): void {
    writeFileSync(this.filePath, JSON.stringify(items, null, 2));
  }

  put(operation: string, params: Record<string, unknown>): void {
    const items = this.load();
    items.push({ operation, params, retries: 0 });
    this.save(items);
  }

  async processAll(dispatcher: Dispatcher): Promise<unknown[]> {
    const items = this.load();
    if (items.length === 0) return [];

    const results: unknown[] = [];
    const failed: QueueItem[] = [];

    for (const item of items) {
      const fn = dispatcher[item.operation];
      if (!fn) {
        logger.error(`Unknown queued operation '${item.operation}' — dropping`);
        continue;
      }
      try {
        results.push(await fn(item.params));
      } catch (err) {
        logger.warn({ err }, `Queued operation '${item.operation}' error`);
        const retries = (item.retries ?? 0) + 1;
        if (retries >= MAX_RETRIES) {
          logger.error(
            `Queued operation '${item.operation}' failed ${retries} times — dropping`
          );
        } else {
          logger.warn(
            `Queued operation '${item.operation}' failed — will re-enqueue (attempt ${retries}/${MAX_RETRIES})`
          );
          failed.push({ ...item, retries });
        }
      }
    }

    this.save(failed);
    return results;
  }

  size(): number {
    return this.load().length;
  }

  isEmpty(): boolean {
    return this.size() === 0;
  }
}
