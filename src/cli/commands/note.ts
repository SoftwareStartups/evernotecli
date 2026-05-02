import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { handleReadError } from '../error-handler.js';
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
      handleReadError(err);
    }
  }
);
