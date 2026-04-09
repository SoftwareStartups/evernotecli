import { defineCommand } from 'clerc';
import { deleteSecret } from '../../auth/keychain.js';

export const logoutCommand = defineCommand(
  {
    name: 'logout',
    description: 'Remove stored credentials',
  },
  async () => {
    const deleted = await deleteSecret('EVERNOTE_TOKEN');

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
