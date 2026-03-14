import { z } from 'zod/v4';

function tsToDate(ts: number | null | undefined): Date | null {
  if (ts == null) return null;
  return new Date(ts);
}

// --- Schemas ---

export const NotebookInfoSchema = z.object({
  guid: z.string(),
  name: z.string(),
  stack: z.string().nullable().optional(),
});

export const TagInfoSchema = z.object({
  guid: z.string(),
  name: z.string(),
});

export const NoteMetadataSchema = z.object({
  guid: z.string(),
  title: z.string(),
  notebookGuid: z.string().nullable().optional(),
  tagGuids: z.array(z.string()).default([]),
  tagNames: z.array(z.string()).default([]),
  created: z.date().nullable().optional(),
  updated: z.date().nullable().optional(),
  contentLength: z.number().nullable().optional(),
});

export const SearchResultSchema = z.object({
  notes: z.array(NoteMetadataSchema),
  total: z.number(),
  offset: z.number(),
  maxResults: z.number(),
});

export const NoteContentSchema = z.object({
  guid: z.string(),
  title: z.string(),
  content: z.string(),
});

export const CreatedNoteSchema = z.object({
  guid: z.string(),
  title: z.string(),
  notebookGuid: z.string().nullable().optional(),
});

// --- Types ---

export type NotebookInfo = z.infer<typeof NotebookInfoSchema>;
export type TagInfo = z.infer<typeof TagInfoSchema>;
export type NoteMetadata = z.infer<typeof NoteMetadataSchema>;
export type SearchResult = z.infer<typeof SearchResultSchema>;
export type NoteContent = z.infer<typeof NoteContentSchema>;
export type CreatedNote = z.infer<typeof CreatedNoteSchema>;

// --- Thrift conversion ---

interface ThriftNote {
  guid?: string | null;
  title?: string | null;
  notebookGuid?: string | null;
  tagGuids?: string[] | null;
  tagNames?: string[] | null;
  created?: number | null;
  updated?: number | null;
  contentLength?: number | null;
}

export function noteMetadataFromThrift(note: ThriftNote): NoteMetadata {
  if (!note.guid) {
    throw new Error('Note returned without GUID');
  }

  const tagNames: string[] = [];
  if (note.tagNames) {
    for (const n of note.tagNames) {
      if (n) tagNames.push(String(n));
    }
  }

  return {
    guid: note.guid,
    title: note.title ?? 'Untitled',
    notebookGuid: note.notebookGuid ?? null,
    tagGuids: [...(note.tagGuids ?? [])],
    tagNames,
    created: tsToDate(note.created),
    updated: tsToDate(note.updated),
    contentLength: note.contentLength ?? null,
  };
}
