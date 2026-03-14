import { Store } from './store.js';
import {
  createNoteStoreClient,
  createUserStoreClient,
  getTokenShard,
} from './thrift-helpers.js';
import { enmlToMarkdown } from '../enml/to-markdown.js';
import { markdownToEnml } from '../enml/to-enml.js';
import type { ResourceInfo } from '../enml/types.js';
import { logger } from '../logger.js';

// @ts-expect-error — generated CommonJS module
import NoteStoreTypes from '../edam/NoteStore_types.js';
// @ts-expect-error — generated CommonJS module
import TypesTypes from '../edam/Types_types.js';

const PRIVATE_TAG_NAME = 'private';

/** Typed façade for the Thrift NoteStore proxy methods we use. */
interface NoteStoreProxy {
  listNotebooks(): Promise<ThriftNotebook[]>;
  listTags(): Promise<ThriftTag[]>;
  findNotesMetadata(
    filter: unknown,
    offset: number,
    maxResults: number,
    spec: unknown
  ): Promise<ThriftNotesMetadataList>;
  getNote(
    guid: string,
    withContent: boolean,
    withResourcesData: boolean,
    withResourcesRecognition: boolean,
    withResourcesAlternateData: boolean
  ): Promise<ThriftNote>;
  getNoteContent(guid: string): Promise<string>;
  getNoteTagNames(guid: string): Promise<string[] | null>;
  createNote(note: unknown): Promise<ThriftNote>;
  createTag(tag: unknown): Promise<ThriftTag>;
  updateNote(note: unknown): Promise<ThriftNote>;
  copyNote(noteGuid: string, toNotebookGuid: string): Promise<ThriftNote>;
}

function s(value: string | Buffer | null | undefined): string {
  if (Buffer.isBuffer(value)) {
    return value.toString('utf-8');
  }
  return value ?? '';
}

export class EvernoteClient {
  private token: string;
  private shard: string;
  private _noteStore: Store | null = null;
  private _userStore: Store | null = null;
  private _privateTagGuid: string | null | undefined = undefined;
  private _tagMap: Map<string, string> | null = null;

  constructor(token: string) {
    this.token = token;
    this.shard = getTokenShard(token);
  }

  private get ns(): NoteStoreProxy {
    if (!this._noteStore) {
      const { client } = createNoteStoreClient(this.shard, this.token);
      this._noteStore = new Store(
        client as unknown as Record<string, (...args: unknown[]) => unknown>,
        this.token
      );
    }
    return this._noteStore as unknown as NoteStoreProxy;
  }

  get userStore(): Store {
    if (!this._userStore) {
      const { client } = createUserStoreClient(this.token);
      this._userStore = new Store(
        client as unknown as Record<string, (...args: unknown[]) => unknown>,
        this.token
      );
    }
    return this._userStore;
  }

  async getPrivateTagGuid(): Promise<string | null> {
    if (this._privateTagGuid !== undefined) return this._privateTagGuid;

    const tags = await this.listTags();
    for (const t of tags) {
      const name = s(t.name);
      if (name.toLowerCase() === PRIVATE_TAG_NAME && t.guid) {
        this._privateTagGuid = s(t.guid);
        return this._privateTagGuid;
      }
    }
    this._privateTagGuid = null;
    return null;
  }

  // --- Read operations ---

  async listNotebooks(): Promise<ThriftNotebook[]> {
    return this.ns.listNotebooks();
  }

  async listTags(): Promise<ThriftTag[]> {
    return this.ns.listTags();
  }

  async searchNotes(
    query = '',
    notebookGuid?: string | null,
    tagNames?: string[] | null,
    maxResults = 20,
    offset = 0
  ): Promise<ThriftNotesMetadataList> {
    const filter = new NoteStoreTypes.NoteFilter();
    filter.words = query || null;
    filter.inactive = false;
    if (notebookGuid) filter.notebookGuid = notebookGuid;

    if (tagNames && tagNames.length > 0) {
      const tagQuery = tagNames.map((t) => `tag:"${t}"`).join(' ');
      filter.words = filter.words ? `${filter.words} ${tagQuery}` : tagQuery;
    }

    const spec = new NoteStoreTypes.NotesMetadataResultSpec();
    spec.includeTitle = true;
    spec.includeContentLength = true;
    spec.includeCreated = true;
    spec.includeUpdated = true;
    spec.includeNotebookGuid = true;
    spec.includeTagGuids = true;

    return this.ns.findNotesMetadata(filter, offset, maxResults, spec);
  }

  async getNote(guid: string): Promise<ThriftNote> {
    const note = await this.ns.getNote(guid, false, false, false, false);

    const rawNames: string[] = (await this.ns.getNoteTagNames(guid)) ?? [];
    const names = rawNames.map((n) => s(n));
    const tagMap = names.length > 0 ? await this.buildTagMap() : new Map();

    note.tagNames = names;
    note.tagGuids = names
      .map((n) => tagMap.get(n))
      .filter((g): g is string => g !== undefined);

    return note;
  }

  async getNoteResources(guid: string): Promise<ResourceInfo[]> {
    const note = await this.ns.getNote(guid, false, true, false, false);
    const resources: ResourceInfo[] = [];
    for (const r of note.resources ?? []) {
      if (!r.data?.bodyHash) continue;
      const hashHex = Buffer.isBuffer(r.data.bodyHash)
        ? r.data.bodyHash.toString('hex')
        : String(r.data.bodyHash);
      const body = r.data.body;
      resources.push({
        hashHex,
        mimeType: s(r.mime),
        filename: r.attributes?.fileName ? s(r.attributes.fileName) : '',
        data: body
          ? new Uint8Array(Buffer.isBuffer(body) ? body : Buffer.from(body))
          : undefined,
      });
    }
    return resources;
  }

  async getNoteContent(guid: string): Promise<string> {
    const note = await this.ns.getNote(guid, false, false, false, true);

    let enml = await this.ns.getNoteContent(s(note.guid) || guid);

    if (Buffer.isBuffer(enml)) {
      enml = (enml as unknown as Buffer).toString('utf-8');
    }

    const resources: ResourceInfo[] = [];
    for (const r of note.resources ?? []) {
      if (r.data?.bodyHash) {
        const hashHex = Buffer.isBuffer(r.data.bodyHash)
          ? r.data.bodyHash.toString('hex')
          : String(r.data.bodyHash);
        const mime = s(r.mime);
        const filename = r.attributes?.fileName ? s(r.attributes.fileName) : '';
        resources.push({ hashHex, mimeType: mime, filename });
      }
    }

    return enmlToMarkdown(enml, resources.length > 0 ? resources : undefined);
  }

  // --- Write operations ---

  async createNote(
    title: string,
    markdown: string,
    notebookGuid?: string | null,
    tagNames?: string[] | null,
    existingResources?: ResourceInfo[]
  ): Promise<ThriftNote> {
    const note = new TypesTypes.Note();
    note.title = title;

    const result = markdownToEnml(markdown, existingResources);
    note.content = result.enml;

    if (result.attachments.length > 0) {
      note.resources = [];
      for (const att of result.attachments) {
        const d = new TypesTypes.Data();
        d.body = att.data;
        d.bodyHash = att.hashBytes;
        d.size = att.data.length;
        const r = new TypesTypes.Resource();
        r.data = d;
        r.mime = att.mimeType;
        if (att.filename) {
          const ra = new TypesTypes.ResourceAttributes();
          ra.fileName = att.filename;
          r.attributes = ra;
        }
        note.resources.push(r);
      }
    }

    if (notebookGuid) note.notebookGuid = notebookGuid;
    if (tagNames && tagNames.length > 0) note.tagNames = tagNames;

    return this.ns.createNote(note);
  }

  async copyNote(
    sourceGuid: string,
    newTitle: string,
    toNotebookGuid: string
  ): Promise<ThriftNote> {
    const copied = await this.ns.copyNote(sourceGuid, toNotebookGuid);
    if (copied.title !== newTitle) {
      const update = new TypesTypes.Note();
      update.guid = copied.guid;
      update.title = newTitle;
      return this.ns.updateNote(update);
    }
    return copied;
  }

  async tagNote(guid: string, tagNames: string[]): Promise<ThriftNote> {
    const allTags = await this.buildTagMap();
    const existingGuids = await this.getNoteTagGuids(guid, allTags);
    const newGuids = await this.resolveTagGuids(tagNames, allTags);
    const merged = [...new Set([...existingGuids, ...newGuids])];

    const note = await this.ns.getNote(guid, false, false, false, false);
    const updated = await this.updateNote(guid, s(note.title), merged);
    updated.tagGuids = merged;
    return updated;
  }

  async untagNote(guid: string, tagNames: string[]): Promise<ThriftNote> {
    const allTags = await this.buildTagMap();
    const existingGuids = new Set(await this.getNoteTagGuids(guid, allTags));
    const removeGuids = new Set(
      tagNames
        .map((n) => allTags.get(n))
        .filter((g): g is string => g !== undefined)
    );
    const remaining = [...existingGuids].filter((g) => !removeGuids.has(g));

    const note = await this.ns.getNote(guid, false, false, false, false);
    const updated = await this.updateNote(guid, s(note.title), remaining);
    updated.tagGuids = remaining;
    return updated;
  }

  async moveNote(guid: string, notebookGuid: string): Promise<ThriftNote> {
    await this.updateNote(guid, undefined, undefined, notebookGuid);
    return this.getNote(guid);
  }

  // --- Helpers ---

  async buildTagMap(): Promise<Map<string, string>> {
    if (this._tagMap) return this._tagMap;
    const tags = await this.listTags();
    const map = new Map<string, string>();
    for (const t of tags) {
      if (t.name && t.guid) {
        map.set(s(t.name), s(t.guid));
      }
    }
    this._tagMap = map;
    return map;
  }

  private async getNoteTagGuids(
    guid: string,
    tagMap?: Map<string, string>
  ): Promise<string[]> {
    const names: string[] = (await this.ns.getNoteTagNames(guid)) ?? [];
    if (names.length === 0) return [];
    const map = tagMap ?? (await this.buildTagMap());
    return names
      .map((n) => s(n))
      .reduce<string[]>((acc, n) => {
        const guid = map.get(n);
        if (guid !== undefined) {
          acc.push(guid);
        } else {
          logger.warn(`Tag name not found in tag map: ${n}`);
        }
        return acc;
      }, []);
  }

  private async resolveTagGuids(
    tagNames: string[],
    tagMap?: Map<string, string>
  ): Promise<string[]> {
    const map = tagMap ?? (await this.buildTagMap());
    const guids: string[] = [];
    for (const name of tagNames) {
      const existing = map.get(name);
      if (existing !== undefined) {
        guids.push(existing);
      } else {
        const tag = new TypesTypes.Tag();
        tag.name = name;
        const created = await this.ns.createTag(tag);
        const newGuid = s(created.guid);
        guids.push(newGuid);
        map.set(name, newGuid);
      }
    }
    return guids;
  }

  private async updateNote(
    guid: string,
    title?: string,
    tagGuids?: string[],
    notebookGuid?: string
  ): Promise<ThriftNote> {
    if (title === undefined) {
      const existing = await this.ns.getNote(guid, false, false, false, false);
      title = s(existing.title);
    }
    const update = new TypesTypes.Note();
    update.guid = guid;
    update.title = title;
    if (tagGuids !== undefined) update.tagGuids = tagGuids;
    if (notebookGuid !== undefined) update.notebookGuid = notebookGuid;
    return this.ns.updateNote(update);
  }
}

// --- Thrift type interfaces ---

export interface ThriftNote {
  guid?: string | null;
  title?: string | null;
  notebookGuid?: string | null;
  tagGuids?: string[] | null;
  tagNames?: string[] | null;
  created?: number | null;
  updated?: number | null;
  contentLength?: number | null;
  content?: string | null;
  resources?: ThriftResource[] | null;
}

interface ThriftResource {
  data?: {
    bodyHash?: Buffer | string | null;
    body?: Buffer | Uint8Array | null;
    size?: number | null;
  } | null;
  mime?: string | null;
  attributes?: { fileName?: string | null } | null;
}

export interface ThriftNotebook {
  guid?: string | null;
  name?: string | null;
  stack?: string | null;
}

export interface ThriftTag {
  guid?: string | null;
  name?: string | null;
}

export interface ThriftNotesMetadataList {
  notes?: ThriftNote[] | null;
  totalNotes?: number | null;
}
