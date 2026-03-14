import { defineCommand } from 'clerc';

export const serveCommand = defineCommand(
  {
    name: 'serve',
    description: 'Start the MCP server',
  },
  async () => {
    const { startServer } = await import('../../server/index.js');
    await startServer();
  }
);
