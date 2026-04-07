import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { handleWriteError } from '../error-handler.js';
import { jsonOutput } from '../format.js';

export const createCommand = defineCommand(
  {
    name: 'create',
    description: 'Create a new note',
    parameters: ['<title>'],
    flags: {
      content: {
        type: String,
        alias: 'c',
        description: 'Note content (Markdown)',
      },
      notebook: {
        type: String,
        alias: 'n',
        description: 'Target notebook name',
      },
      tag: {
        type: [String],
        alias: 't',
        description: 'Tag names to apply',
      },
      'source-note': {
        type: String,
        description:
          'GUID of source note to copy resources from (for re-creating edited notes)',
      },
    },
  },
  async (ctx) => {
    try {
      const result = await service.createNote(
        ctx.parameters.title,
        ctx.flags.content ?? '',
        ctx.flags.notebook ?? '',
        ctx.flags.tag?.length ? ctx.flags.tag : null,
        ctx.flags['source-note']
      );
      jsonOutput(result);
    } catch (err) {
      handleWriteError(err, 'create_note', {
        title: ctx.parameters.title,
        content: ctx.flags.content ?? '',
        notebook_name: ctx.flags.notebook ?? '',
        tags: ctx.flags.tag?.length ? ctx.flags.tag : null,
        source_note_guid: ctx.flags['source-note'],
      });
    }
  }
);
