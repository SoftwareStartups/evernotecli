import { defineCommand } from 'clerc';
import { EvernoteRateLimitError, PrivateNoteError } from '../../errors.js';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const moveCommand = defineCommand(
  {
    name: 'move',
    description: 'Move a note to a different notebook',
    parameters: ['<guid>', '<notebook>'],
  },
  async (ctx) => {
    try {
      const result = await service.moveNote(
        ctx.parameters.guid,
        ctx.parameters.notebook
      );
      jsonOutput(result);
    } catch (err) {
      if (err instanceof PrivateNoteError) {
        console.error('Error: note is private.');
        process.exit(1);
      }
      if (err instanceof EvernoteRateLimitError) {
        service.enqueueWrite('move_note', {
          guid: ctx.parameters.guid,
          notebook_name: ctx.parameters.notebook,
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
