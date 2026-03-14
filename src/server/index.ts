import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { registerReadTools } from './read-tools.js';
import { registerWriteTools } from './write-tools.js';

export async function startServer(): Promise<void> {
  const server = new McpServer({
    name: 'evercli',
    version: '0.1.0',
  });

  registerReadTools(server);
  registerWriteTools(server);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.on('SIGINT', async () => {
    await server.close();
    process.exit(0);
  });
}
