import { mkdir, writeFile } from 'node:fs/promises';
import { z } from 'zod';
import { getToken } from './auth/oauth.js';
import { EvernoteClient, PRIVATE_TAG_NAME } from './client/evernote-client.js';
import { OperationQueue } from './client/queue.js';
import { settings } from './config.js';
import type { ResourceInfo } from './enml/types.js';
import { PrivateNoteError } from './errors.js';
import { logger } from './logger.js';
import { safeJoin } from './path-utils.js';
import {
  type CreatedNote,
  type NotebookInfo,
  type NoteContent,
  type NoteMetadata,
  noteMetadataFromThrift,
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

async function assertNotPrivate(
  noteGuid: string,
  tagGuids: string[]
): Promise<void> {
  if (await isPrivate(tagGuids)) {
    throw new PrivateNoteError(noteGuid);
  }
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

async function resolveNotebookGuidIfProvided(
  client: EvernoteClient,
  name: string
): Promise<string | null> {
  return name ? resolveNotebookGuid(client, name) : null;
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

  const notebookGuid = await resolveNotebookGuidIfProvided(
    client,
    notebookName
  );

  const safeTags = tags?.filter((t) => t.toLowerCase() !== PRIVATE_TAG_NAME);
  const tagFilter = safeTags?.length ? safeTags : null;

  const result = await client.searchNotes(
    query,
    notebookGuid,
    tagFilter,
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
  await assertNotPrivate(guid, note.tagGuids ?? []);
  return noteMetadataFromThrift(note);
}

export async function getNoteContent(
  guid: string,
  options: { resourceDir?: string } = {}
): Promise<NoteContent> {
  const client = await getClient();
  const note = await client.getNote(guid);
  await assertNotPrivate(guid, note.tagGuids ?? []);
  if (!note.guid) throw new Error('Note returned without GUID');

  let content = await client.getNoteContent(guid);

  if (options.resourceDir) {
    const resources = await client.getNoteResources(guid);
    await mkdir(options.resourceDir, { recursive: true });
    for (const r of resources) {
      if (!r.data || !r.filename) continue;
      const target = safeJoin(options.resourceDir, r.filename);
      await writeFile(target, r.data);
      content = content.replaceAll(`evernote-resource:${r.hashHex}`, target);
    }
  }

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
    String(t.name).toLowerCase() !== PRIVATE_TAG_NAME
      ? [{ guid: t.guid, name: t.name }]
      : []
  );
}

// --- Write operations ---

export async function createNote(
  title: string,
  content: string,
  notebookName = '',
  tags?: string[] | null,
  sourceNoteGuid?: string
): Promise<CreatedNote> {
  const client = await getClient();

  const notebookGuid = await resolveNotebookGuidIfProvided(
    client,
    notebookName
  );

  let existingResources: ResourceInfo[] | undefined;
  if (sourceNoteGuid) {
    try {
      existingResources = await client.getNoteResources(sourceNoteGuid);
    } catch (err) {
      logger.warn(
        { err, sourceNoteGuid },
        'Could not fetch source note resources — images will be skipped'
      );
    }
  }

  const note = await client.createNote(
    title,
    content,
    notebookGuid,
    tags && tags.length > 0 ? tags : null,
    existingResources
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
  if (!note.guid || !note.title)
    throw new Error('Copied note missing GUID or title');
  return {
    guid: note.guid,
    title: note.title,
    notebookGuid: note.notebookGuid ?? null,
  };
}

async function modifyNoteTags(
  guid: string,
  tags: string[],
  op: 'add' | 'remove'
): Promise<NoteMetadata> {
  if (tags.some((t) => t.toLowerCase() === PRIVATE_TAG_NAME)) {
    const verb = op === 'add' ? 'add' : 'remove';
    throw new PrivateNoteError(`Cannot ${verb} '${PRIVATE_TAG_NAME}' tag`);
  }
  const client = await getClient();
  const existing = await client.getNote(guid);
  await assertNotPrivate(guid, existing.tagGuids ?? []);
  const note =
    op === 'add'
      ? await client.tagNote(guid, tags)
      : await client.untagNote(guid, tags);
  return noteMetadataFromThrift(note);
}

export function tagNote(guid: string, tags: string[]): Promise<NoteMetadata> {
  return modifyNoteTags(guid, tags, 'add');
}

export function untagNote(guid: string, tags: string[]): Promise<NoteMetadata> {
  return modifyNoteTags(guid, tags, 'remove');
}

export async function moveNote(
  guid: string,
  notebookName: string
): Promise<NoteMetadata> {
  const client = await getClient();
  const notebookGuid = await resolveNotebookGuid(client, notebookName);
  const existing = await client.getNote(guid);
  await assertNotPrivate(guid, existing.tagGuids ?? []);
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
  source_note_guid: z.string().optional(),
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
    return createNote(
      v.title,
      v.content,
      v.notebook_name,
      v.tags,
      v.source_note_guid
    );
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
