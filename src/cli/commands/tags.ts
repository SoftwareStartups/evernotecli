import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const tagsCommand = defineCommand(
  {
    name: 'tags',
    description: 'List all tags',
  },
  async () => {
    const result = await service.listTags();
    jsonOutput(result);
  }
);
