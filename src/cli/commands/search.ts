import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const searchCommand = defineCommand(
  {
    name: 'search',
    description: 'Search notes',
    parameters: ['[query]'],
    flags: {
      notebook: {
        type: String,
        alias: 'n',
        description: 'Filter by notebook name',
      },
      tag: {
        type: [String],
        alias: 't',
        description: 'Filter by tag name',
      },
      max: {
        type: Number,
        description: 'Max results (default 20)',
      },
      offset: {
        type: Number,
        description: 'Pagination offset',
      },
    },
  },
  async (ctx) => {
    const result = await service.searchNotes(
      ctx.parameters.query ?? '',
      ctx.flags.notebook ?? '',
      ctx.flags.tag?.length ? ctx.flags.tag : null,
      ctx.flags.max ?? 20,
      ctx.flags.offset ?? 0
    );
    jsonOutput(result);
  }
);
