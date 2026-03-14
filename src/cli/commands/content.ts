import { defineCommand } from 'clerc';
import { PrivateNoteError } from '../../errors.js';
import * as service from '../../service.js';

export const contentCommand = defineCommand(
  {
    name: 'content',
    description: 'Show note content as Markdown',
    parameters: ['<guid>'],
    flags: {
      'save-resources': {
        type: String,
        description:
          'Directory to save resource files; rewrites image refs to local paths',
      },
    },
  },
  async (ctx) => {
    try {
      const result = await service.getNoteContent(ctx.parameters.guid, {
        resourceDir: ctx.flags['save-resources'],
      });
      console.log(result.content);
    } catch (err) {
      if (err instanceof PrivateNoteError) {
        console.error('Error: note is private.');
        process.exit(1);
      }
      throw err;
    }
  }
);
