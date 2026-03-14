import thrift from 'thrift';
// @ts-expect-error — generated CommonJS module
import NoteStore from '../edam/NoteStore.js';
// @ts-expect-error — generated CommonJS module
import UserStore from '../edam/UserStore.js';

const HTTP_TIMEOUT_MS = 30_000;
const USER_AGENT = 'evercli/0.1.0';

const CUSTOM_HEADERS = {
  'User-Agent': USER_AGENT,
  'x-feature-version': '3',
  accept: 'application/x-thrift',
  'cache-control': 'no-cache',
};

export function createNoteStoreClient(
  shard: string,
  token: string
): { client: NoteStoreClient; connection: thrift.HttpConnection } {
  const url = `https://www.evernote.com/edam/note/${shard}`;
  return createThriftClient(NoteStore, url, token);
}

export function createUserStoreClient(
  token: string
): { client: UserStoreClient; connection: thrift.HttpConnection } {
  const url = 'https://www.evernote.com/edam/user';
  return createThriftClient(UserStore, url, token);
}

function createThriftClient<T>(
  serviceModule: { Client: new (output: thrift.TTransport) => T },
  url: string,
  _token: string
): { client: T; connection: thrift.HttpConnection } {
  const parsed = new URL(url);
  const connection = thrift.createHttpConnection(parsed.hostname, 443, {
    transport: thrift.TBufferedTransport,
    protocol: thrift.TBinaryProtocol,
    path: parsed.pathname,
    headers: CUSTOM_HEADERS,
    https: true,
    timeout: HTTP_TIMEOUT_MS,
  });

  const client = thrift.createHttpClient<T>(serviceModule, connection);
  return { client, connection };
}

export function getTokenShard(token: string): string {
  return token.substring(2, token.indexOf(':'));
}

// Re-export the client types for convenience
export type NoteStoreClient = InstanceType<typeof NoteStore.Client>;
export type UserStoreClient = InstanceType<typeof UserStore.Client>;
