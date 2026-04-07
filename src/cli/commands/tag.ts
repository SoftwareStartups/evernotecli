import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { handleWriteError } from '../error-handler.js';
import { jsonOutput } from '../format.js';

export const tagCommand = defineCommand(
  {
    name: 'tag',
    description: 'Add tags to a note',
    parameters: ['<guid>', '<tags...>'],
  },
  async (ctx) => {
    try {
      const result = await service.tagNote(
        ctx.parameters.guid,
        ctx.parameters.tags
      );
      jsonOutput(result);
    } catch (err) {
      handleWriteError(err, 'tag_note', {
        guid: ctx.parameters.guid,
        tags: ctx.parameters.tags,
      });
    }
  }
);
