import { defineCommand } from 'clerc';
import { PrivateNoteError } from '../../errors.js';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const noteCommand = defineCommand(
  {
    name: 'note',
    description: 'Show note metadata',
    parameters: ['<guid>'],
  },
  async (ctx) => {
    try {
      const result = await service.getNote(ctx.parameters.guid);
      jsonOutput(result);
    } catch (err) {
      if (err instanceof PrivateNoteError) {
        console.error('Error: note is private.');
        process.exit(1);
      }
      throw err;
    }
  }
);
