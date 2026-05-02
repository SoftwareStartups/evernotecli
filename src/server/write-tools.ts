import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod/v4';
import * as service from '../service.js';
import { jsonResult } from './response.js';

export function registerWriteTools(server: McpServer): void {
  server.tool(
    'create_note',
    'Create a new note with Markdown content',
    {
      title: z.string().describe('Note title'),
      content: z
        .string()
        .optional()
        .describe('Note content in Markdown format'),
      notebook_name: z
        .string()
        .optional()
        .describe('Target notebook name (uses default if empty)'),
      tags: z
        .array(z.string())
        .optional()
        .describe('List of tag names to apply'),
    },
    async (args) =>
      jsonResult(
        await service.createNote(
          args.title,
          args.content ?? '',
          args.notebook_name ?? '',
          args.tags ?? null
        )
      )
  );

  server.tool(
    'tag_note',
    'Add tags to an existing note',
    {
      guid: z.string().describe('Note GUID'),
      tags: z.array(z.string()).describe('Tag names to add'),
    },
    async (args) => jsonResult(await service.tagNote(args.guid, args.tags))
  );

  server.tool(
    'untag_note',
    'Remove tags from an existing note',
    {
      guid: z.string().describe('Note GUID'),
      tags: z.array(z.string()).describe('Tag names to remove'),
    },
    async (args) => jsonResult(await service.untagNote(args.guid, args.tags))
  );

  server.tool(
    'move_note',
    'Move a note to a different notebook',
    {
      guid: z.string().describe('Note GUID'),
      notebook_name: z.string().describe('Target notebook name'),
    },
    async (args) =>
      jsonResult(await service.moveNote(args.guid, args.notebook_name))
  );
}
