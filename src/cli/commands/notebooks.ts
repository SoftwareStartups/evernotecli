import { defineCommand } from 'clerc';
import * as service from '../../service.js';
import { jsonOutput } from '../format.js';

export const notebooksCommand = defineCommand(
  {
    name: 'notebooks',
    description: 'List all notebooks',
  },
  async () => {
    const result = await service.listNotebooks();
    jsonOutput(result);
  }
);
