import { EvernoteRateLimitError, PrivateNoteError } from '../errors.js';
import { enqueueWrite } from '../service.js';

export function handleWriteError(
  err: unknown,
  operation: string,
  params: Record<string, unknown>
): void {
  if (err instanceof PrivateNoteError) {
    console.error('Error: note is private.');
    process.exit(1);
  }
  if (err instanceof EvernoteRateLimitError) {
    enqueueWrite(operation, params);
    console.error(
      `Rate limited (retry after ${err.retryAfter}s) — queued. Run 'evercli drain' to process.`
    );
    return;
  }
  throw err;
}
