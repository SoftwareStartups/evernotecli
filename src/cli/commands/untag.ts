import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { handleWriteError } from '../error-handler.js';
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
      handleWriteError(err, 'untag_note', {
        guid: ctx.parameters.guid,
        tags: ctx.parameters.tags,
      });
    }
  }
);
