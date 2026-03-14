import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const copyCommand = defineCommand(
  {
    name: 'copy',
    description: 'Copy a note (including all attachments)',
    parameters: ['<source-guid>', '<title>'],
    flags: {
      notebook: {
        type: String,
        description: 'Target notebook name (default: same as source)',
        alias: 'n',
        default: '',
      },
    },
  },
  async (ctx) => {
    const result = await service.copyNote(
      ctx.parameters['source-guid'],
      ctx.parameters.title,
      ctx.flags.notebook
    );
    jsonOutput(result);
  }
);
