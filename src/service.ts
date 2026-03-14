import { getToken } from './auth/oauth.js';
import {
  EvernoteClient,
  type ThriftNote,
} from './client/evernote-client.js';
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
  const safeTags =
    tags?.filter((t) => t.toLowerCase() !== 'private') ?? null;

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
  return notebooks
    .filter((nb) => nb.guid != null && nb.name != null)
    .map((nb) => ({
      guid: nb.guid!,
      name: nb.name!,
      stack: nb.stack ?? null,
    }));
}

export async function listTags(): Promise<TagInfo[]> {
  const client = await getClient();
  const tags = await client.listTags();
  return tags
    .filter(
      (t) =>
        t.guid != null &&
        t.name != null &&
        String(t.name).toLowerCase() !== 'private'
    )
    .map((t) => ({ guid: t.guid!, name: t.name! }));
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

const WRITE_DISPATCHER: WriteDispatcher = {
  create_note: (p) =>
    createNote(
      p.title as string,
      p.content as string,
      (p.notebook_name as string) ?? '',
      (p.tags as string[]) ?? null
    ),
  tag_note: (p) => tagNote(p.guid as string, p.tags as string[]),
  untag_note: (p) => untagNote(p.guid as string, p.tags as string[]),
  move_note: (p) => moveNote(p.guid as string, p.notebook_name as string),
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
