import { z } from 'zod';
import { getToken } from './auth/oauth.js';
import { EvernoteClient } from './client/evernote-client.js';
import { OperationQueue } from './client/queue.js';
import { settings } from './config.js';
import { PrivateNoteError } from './errors.js';
import {
  noteMetadataFromThrift,
  type CreatedNote,
  type NotebookInfo,
  type NoteContent,
  type NoteMetadata,
  type SearchResult,
  type TagInfo,
} from './models.js';

let _client: EvernoteClient | null = null;

export async function getClient(): Promise<EvernoteClient> {
  if (!_client) {
    const token = await getToken(settings);
    _client = new EvernoteClient(token);
  }
  return _client;
}

export function resetClient(): void {
  _client = null;
}

async function isPrivate(tagGuids: string[]): Promise<boolean> {
  const client = await getClient();
  const guid = await client.getPrivateTagGuid();
  return guid !== null && tagGuids.includes(guid);
}

async function resolveNotebookGuid(
  client: EvernoteClient,
  name: string
): Promise<string> {
  const notebooks = await client.listNotebooks();
  for (const nb of notebooks) {
    if (nb.name === name && nb.guid) {
      return nb.guid;
    }
  }
  throw new Error(`Notebook not found: ${name}`);
}

// --- Read operations ---

export async function searchNotes(
  query = '',
  notebookName = '',
  tags?: string[] | null,
  maxResults = 20,
  offset = 0
): Promise<SearchResult> {
  const client = await getClient();
  maxResults = Math.min(maxResults, 100);

  let notebookGuid: string | null = null;
  if (notebookName) {
    notebookGuid = await resolveNotebookGuid(client, notebookName);
  }

  // Strip "private" from tag filters
  const safeTags = tags?.filter((t) => t.toLowerCase() !== 'private') ?? null;

  const result = await client.searchNotes(
    query,
    notebookGuid,
    safeTags && safeTags.length > 0 ? safeTags : null,
    maxResults,
    offset
  );

  const allNotes = (result.notes ?? []).map(noteMetadataFromThrift);
  const notes: NoteMetadata[] = [];
  for (const n of allNotes) {
    if (!(await isPrivate(n.tagGuids))) {
      notes.push(n);
    }
  }
  const filtered = allNotes.length - notes.length;

  // NOTE: The total is approximate — we only know how many private notes were
  // on *this* page. Other pages may contain different counts of private notes.
  return {
    notes,
    total: Math.max(0, (result.totalNotes ?? 0) - filtered),
    offset,
    maxResults,
  };
}

export async function getNote(guid: string): Promise<NoteMetadata> {
  const client = await getClient();
  const note = await client.getNote(guid);
  if (await isPrivate(note.tagGuids ?? [])) {
    throw new PrivateNoteError(guid);
  }
  return noteMetadataFromThrift(note);
}

export async function getNoteContent(guid: string): Promise<NoteContent> {
  const client = await getClient();
  const note = await client.getNote(guid);
  if (await isPrivate(note.tagGuids ?? [])) {
    throw new PrivateNoteError(guid);
  }
  const content = await client.getNoteContent(guid);
  if (!note.guid) throw new Error('Note returned without GUID');
  return {
    guid: note.guid,
    title: note.title ?? 'Untitled',
    content,
  };
}

export async function listNotebooks(): Promise<NotebookInfo[]> {
  const client = await getClient();
  const notebooks = await client.listNotebooks();
  return notebooks.flatMap((nb) =>
    nb.guid != null && nb.name != null
      ? [{ guid: nb.guid, name: nb.name, stack: nb.stack ?? null }]
      : []
  );
}

export async function listTags(): Promise<TagInfo[]> {
  const client = await getClient();
  const tags = await client.listTags();
  return tags.flatMap((t) =>
    t.guid != null &&
    t.name != null &&
    String(t.name).toLowerCase() !== 'private'
      ? [{ guid: t.guid, name: t.name }]
      : []
  );
}

// --- Write operations ---

export async function createNote(
  title: string,
  content: string,
  notebookName = '',
  tags?: string[] | null
): Promise<CreatedNote> {
  const client = await getClient();

  let notebookGuid: string | null = null;
  if (notebookName) {
    notebookGuid = await resolveNotebookGuid(client, notebookName);
  }

  const note = await client.createNote(
    title,
    content,
    notebookGuid,
    tags && tags.length > 0 ? tags : null
  );

  if (!note.guid || !note.title) {
    throw new Error('Created note missing GUID or title');
  }

  return {
    guid: note.guid,
    title: note.title,
    notebookGuid: note.notebookGuid ?? null,
  };
}

export async function copyNote(
  sourceGuid: string,
  newTitle: string,
  notebookName = ''
): Promise<CreatedNote> {
  const client = await getClient();

  let toNotebookGuid: string;
  if (notebookName) {
    toNotebookGuid = await resolveNotebookGuid(client, notebookName);
  } else {
    const src = await client.getNote(sourceGuid);
    if (!src.notebookGuid) throw new Error('Source note has no notebook GUID');
    toNotebookGuid = src.notebookGuid;
  }

  const note = await client.copyNote(sourceGuid, newTitle, toNotebookGuid);
  if (!note.guid || !note.title) throw new Error('Copied note missing GUID or title');
  return { guid: note.guid, title: note.title, notebookGuid: note.notebookGuid ?? null };
}

export async function tagNote(
  guid: string,
  tags: string[]
): Promise<NoteMetadata> {
  if (tags.some((t) => t.toLowerCase() === 'private')) {
    throw new PrivateNoteError("Cannot add 'private' tag");
  }
  const client = await getClient();
  const existing = await client.getNote(guid);
  if (await isPrivate(existing.tagGuids ?? [])) {
    throw new PrivateNoteError(guid);
  }
  const note = await client.tagNote(guid, tags);
  return noteMetadataFromThrift(note);
}

export async function untagNote(
  guid: string,
  tags: string[]
): Promise<NoteMetadata> {
  if (tags.some((t) => t.toLowerCase() === 'private')) {
    throw new PrivateNoteError("Cannot remove 'private' tag");
  }
  const client = await getClient();
  const existing = await client.getNote(guid);
  if (await isPrivate(existing.tagGuids ?? [])) {
    throw new PrivateNoteError(guid);
  }
  const note = await client.untagNote(guid, tags);
  return noteMetadataFromThrift(note);
}

export async function moveNote(
  guid: string,
  notebookName: string
): Promise<NoteMetadata> {
  const client = await getClient();
  const notebookGuid = await resolveNotebookGuid(client, notebookName);
  const existing = await client.getNote(guid);
  if (await isPrivate(existing.tagGuids ?? [])) {
    throw new PrivateNoteError(guid);
  }
  const note = await client.moveNote(guid, notebookGuid);
  return noteMetadataFromThrift(note);
}

// --- Write queue ---

type WriteDispatcher = Record<
  string,
  (params: Record<string, unknown>) => Promise<unknown>
>;

const CreateNoteParams = z.object({
  title: z.string(),
  content: z.string(),
  notebook_name: z.string().optional().default(''),
  tags: z.array(z.string()).nullable().optional().default(null),
});

const GuidTagsParams = z.object({
  guid: z.string(),
  tags: z.array(z.string()),
});

const MoveNoteParams = z.object({
  guid: z.string(),
  notebook_name: z.string(),
});

const WRITE_DISPATCHER: WriteDispatcher = {
  create_note: (p) => {
    const v = CreateNoteParams.parse(p);
    return createNote(v.title, v.content, v.notebook_name, v.tags);
  },
  tag_note: (p) => {
    const v = GuidTagsParams.parse(p);
    return tagNote(v.guid, v.tags);
  },
  untag_note: (p) => {
    const v = GuidTagsParams.parse(p);
    return untagNote(v.guid, v.tags);
  },
  move_note: (p) => {
    const v = MoveNoteParams.parse(p);
    return moveNote(v.guid, v.notebook_name);
  },
};

export function enqueueWrite(
  operation: string,
  params: Record<string, unknown>
): void {
  new OperationQueue(settings.queuePath).put(operation, params);
}

export function pendingWriteCount(): number {
  return new OperationQueue(settings.queuePath).size();
}

export async function drainPendingWrites(): Promise<number> {
  const queue = new OperationQueue(settings.queuePath);
  if (queue.isEmpty()) return 0;
  const results = await queue.processAll(WRITE_DISPATCHER);
  return results.length;
}
