import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { handleWriteError } from '../error-handler.js';
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
      handleWriteError(err, 'move_note', {
        guid: ctx.parameters.guid,
        notebook_name: ctx.parameters.notebook,
      });
    }
  }
);
