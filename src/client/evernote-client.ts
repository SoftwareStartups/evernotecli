import { Store } from './store.js';
import {
  createNoteStoreClient,
  createUserStoreClient,
  getTokenShard,
} from './thrift-helpers.js';
import { enmlToMarkdown } from '../enml/to-markdown.js';
import { markdownToEnml } from '../enml/to-enml.js';
import type { ResourceInfo } from '../enml/types.js';

// @ts-expect-error — generated CommonJS module
import NoteStoreTypes from '../edam/NoteStore_types.js';
// @ts-expect-error — generated CommonJS module
import TypesTypes from '../edam/Types_types.js';

const PRIVATE_TAG_NAME = 'private';

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

  get noteStore(): Store {
    if (!this._noteStore) {
      const { client } = createNoteStoreClient(this.shard, this.token);
      this._noteStore = new Store(
        client as unknown as Record<string, (...args: unknown[]) => unknown>,
        this.token
      );
    }
    return this._noteStore;
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
    return (await (this.noteStore as any).listNotebooks()) as ThriftNotebook[];
  }

  async listTags(): Promise<ThriftTag[]> {
    return (await (this.noteStore as any).listTags()) as ThriftTag[];
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
      filter.words = filter.words
        ? `${filter.words} ${tagQuery}`
        : tagQuery;
    }

    const spec = new NoteStoreTypes.NotesMetadataResultSpec();
    spec.includeTitle = true;
    spec.includeContentLength = true;
    spec.includeCreated = true;
    spec.includeUpdated = true;
    spec.includeNotebookGuid = true;
    spec.includeTagGuids = true;

    return (await (this.noteStore as any).findNotesMetadata(
      filter,
      offset,
      maxResults,
      spec
    )) as ThriftNotesMetadataList;
  }

  async getNote(guid: string): Promise<ThriftNote> {
    const note = (await (this.noteStore as any).getNote(
      guid,
      false,
      false,
      false,
      false
    )) as ThriftNote;

    const rawNames: string[] =
      ((await (this.noteStore as any).getNoteTagNames(guid)) as
        | string[]
        | null) ?? [];
    const names = rawNames.map((n) => s(n));
    const tagMap = names.length > 0 ? await this.buildTagMap() : new Map();

    note.tagNames = names;
    note.tagGuids = names
      .filter((n) => tagMap.has(n))
      .map((n) => tagMap.get(n)!);

    return note;
  }

  async getNoteContent(guid: string): Promise<string> {
    const note = (await (this.noteStore as any).getNote(
      guid,
      false,
      false,
      false,
      true
    )) as ThriftNote;

    let enml: string = (await (this.noteStore as any).getNoteContent(
      s(note.guid) || guid
    )) as string;

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
        const filename =
          r.attributes?.fileName ? s(r.attributes.fileName) : '';
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
    tagNames?: string[] | null
  ): Promise<ThriftNote> {
    const note = new TypesTypes.Note();
    note.title = title;

    const result = markdownToEnml(markdown);
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

    return (await (this.noteStore as any).createNote(note)) as ThriftNote;
  }

  async tagNote(guid: string, tagNames: string[]): Promise<ThriftNote> {
    const allTags = await this.buildTagMap();
    const existingGuids = await this.getNoteTagGuids(guid, allTags);
    const newGuids = await this.resolveTagGuids(tagNames, allTags);
    const merged = [...new Set([...existingGuids, ...newGuids])];

    const note = (await (this.noteStore as any).getNote(
      guid,
      false,
      false,
      false,
      false
    )) as ThriftNote;
    const updated = await this.updateNote(guid, s(note.title), merged);
    updated.tagGuids = merged;
    return updated;
  }

  async untagNote(guid: string, tagNames: string[]): Promise<ThriftNote> {
    const allTags = await this.buildTagMap();
    const existingGuids = new Set(await this.getNoteTagGuids(guid, allTags));
    const removeGuids = new Set(
      tagNames.filter((n) => allTags.has(n)).map((n) => allTags.get(n)!)
    );
    const remaining = [...existingGuids].filter((g) => !removeGuids.has(g));

    const note = (await (this.noteStore as any).getNote(
      guid,
      false,
      false,
      false,
      false
    )) as ThriftNote;
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
    const names: string[] =
      ((await (this.noteStore as any).getNoteTagNames(guid)) as
        | string[]
        | null) ?? [];
    if (names.length === 0) return [];
    const map = tagMap ?? (await this.buildTagMap());
    return names.map((n) => s(n)).filter((n) => map.has(n)).map((n) => map.get(n)!);
  }

  private async resolveTagGuids(
    tagNames: string[],
    tagMap?: Map<string, string>
  ): Promise<string[]> {
    const map = tagMap ?? (await this.buildTagMap());
    const guids: string[] = [];
    for (const name of tagNames) {
      if (map.has(name)) {
        guids.push(map.get(name)!);
      } else {
        const tag = new TypesTypes.Tag();
        tag.name = name;
        const created = (await (this.noteStore as any).createTag(
          tag
        )) as ThriftTag;
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
      const existing = (await (this.noteStore as any).getNote(
        guid,
        false,
        false,
        false,
        false
      )) as ThriftNote;
      title = s(existing.title);
    }
    const update = new TypesTypes.Note();
    update.guid = guid;
    update.title = title;
    if (tagGuids !== undefined) update.tagGuids = tagGuids;
    if (notebookGuid !== undefined) update.notebookGuid = notebookGuid;
    return (await (this.noteStore as any).updateNote(update)) as ThriftNote;
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
  data?: { bodyHash?: Buffer | string | null } | null;
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
