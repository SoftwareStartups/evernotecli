import { defineCommand } from 'clerc';
import pkg from '../../../package.json' with { type: 'json' };

export const serveCommand = defineCommand(
  {
    name: 'serve',
    description: 'Start the MCP server',
  },
  async () => {
    const { startServer } = await import('../../server/index.js');
    await startServer(pkg.version);
  }
);
