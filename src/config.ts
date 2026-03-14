import { config } from 'dotenv';
import { homedir } from 'node:os';
import { join } from 'node:path';

config();

function dataDir(): string {
  try {
    return join(homedir(), '.evercli');
  } catch {
    return '/tmp/evercli';
  }
}

export interface Config {
  token: string;
  consumerKey: string;
  consumerSecret: string;
  tokenPath: string;
  queuePath: string;
  logLevel: string;
}

export const settings: Config = {
  token: process.env.EVERNOTE_TOKEN ?? '',
  consumerKey: process.env.EVERNOTE_CONSUMER_KEY ?? '',
  consumerSecret: process.env.EVERNOTE_CONSUMER_SECRET ?? '',
  tokenPath: process.env.EVERNOTE_TOKEN_PATH ?? join(dataDir(), 'token.json'),
  queuePath: process.env.EVERNOTE_QUEUE_PATH ?? join(dataDir(), 'queue'),
  logLevel: process.env.LOG_LEVEL ?? 'info',
};
