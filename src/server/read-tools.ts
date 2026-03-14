import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod/v4';
import * as service from '../service.js';

export function registerReadTools(server: McpServer): void {
  server.tool(
    'search_notes',
    'Search notes using Evernote search grammar',
    {
      query: z.string().optional().describe('Search query (Evernote search grammar)'),
      notebook_name: z.string().optional().describe('Filter by notebook name'),
      tags: z.array(z.string()).optional().describe('Filter by tag names'),
      max_results: z.number().optional().describe('Maximum number of results (default 20, max 100)'),
      offset: z.number().optional().describe('Offset for pagination'),
    },
    async (args) => {
      const result = await service.searchNotes(
        args.query ?? '',
        args.notebook_name ?? '',
        args.tags ?? null,
        args.max_results ?? 20,
        args.offset ?? 0
      );
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'get_note',
    'Get note metadata (title, tags, notebook, dates)',
    {
      guid: z.string().describe('Note GUID'),
    },
    async (args) => {
      const result = await service.getNote(args.guid);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'get_note_content',
    'Get full note content as Markdown',
    {
      guid: z.string().describe('Note GUID'),
    },
    async (args) => {
      const result = await service.getNoteContent(args.guid);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'list_notebooks',
    'List all notebooks with guid, name, and stack',
    {},
    async () => {
      const result = await service.listNotebooks();
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'list_tags',
    'List all tags with guid and name',
    {},
    async () => {
      const result = await service.listTags();
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
