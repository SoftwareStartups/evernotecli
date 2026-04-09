import { homedir } from 'node:os';
import { join } from 'node:path';

function configDir(): string {
  try {
    return join(homedir(), '.config', 'evercli');
  } catch {
    return '/tmp/evercli';
  }
}

export interface Config {
  token: string;
  consumerKey: string;
  consumerSecret: string;
  queuePath: string;
  logLevel: string;
}

export const settings: Config = {
  token: process.env.EVERNOTE_TOKEN ?? '',
  consumerKey: process.env.EVERNOTE_CONSUMER_KEY ?? '',
  consumerSecret: process.env.EVERNOTE_CONSUMER_SECRET ?? '',
  queuePath: process.env.EVERNOTE_QUEUE_PATH ?? join(configDir(), 'queue'),
  logLevel: process.env.LOG_LEVEL ?? 'info',
};
