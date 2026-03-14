import { defineCommand } from 'clerc';
import { EvernoteRateLimitError, PrivateNoteError } from '../../errors.js';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const untagCommand = defineCommand(
  {
    name: 'untag',
    description: 'Remove tags from a note',
    parameters: ['<guid>', '<tags...>'],
  },
  async (ctx) => {
    try {
      const result = await service.untagNote(
        ctx.parameters.guid,
        ctx.parameters.tags
      );
      jsonOutput(result);
    } catch (err) {
      if (err instanceof PrivateNoteError) {
        console.error('Error: note is private.');
        process.exit(1);
      }
      if (err instanceof EvernoteRateLimitError) {
        service.enqueueWrite('untag_note', {
          guid: ctx.parameters.guid,
          tags: ctx.parameters.tags,
        });
        console.error(
          `Rate limited (retry after ${err.retryAfter}s) — queued. Run 'evercli drain' to process.`
        );
        return;
      }
      throw err;
    }
  }
);
