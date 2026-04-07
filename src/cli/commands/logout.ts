import { defineCommand } from 'clerc';
import { deleteToken } from '../../auth/token-store.js';
import { settings } from '../../config.js';

export const logoutCommand = defineCommand(
  {
    name: 'logout',
    description: 'Remove stored credentials',
  },
  () => {
    const deleted = deleteToken(settings.configPath);

    if (!deleted) {
      console.log('No stored credentials found. Already logged out.');
      return;
    }

    console.log('Credentials removed.');

    if (process.env.EVERNOTE_TOKEN) {
      console.log('Note: EVERNOTE_TOKEN environment variable is still set.');
    }
  }
);
