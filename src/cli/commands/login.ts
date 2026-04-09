import { defineCommand } from 'clerc';
import {
  deleteSecret,
  sanitizeCredential,
  setSecret,
} from '../../auth/keychain.js';
import { getToken } from '../../auth/oauth.js';
import { EvernoteClient } from '../../client/evernote-client.js';
import { settings } from '../../config.js';

async function validateToken(token: string): Promise<boolean> {
  try {
    const client = new EvernoteClient(token);
    await client.listNotebooks();
    return true;
  } catch {
    return false;
  }
}

export const loginCommand = defineCommand(
  {
    name: 'login',
    description: 'Authenticate with Evernote',
    flags: {
      token: {
        type: String,
        description: 'Provide token directly (non-interactive)',
      },
      'skip-validation': {
        type: Boolean,
        description: 'Skip credential validation',
      },
    },
  },
  async (ctx) => {
    let token: string;

    if (ctx.flags.token) {
      try {
        token = sanitizeCredential(ctx.flags.token);
      } catch (err: unknown) {
        console.error(
          `Error: ${err instanceof Error ? err.message : 'Invalid credential.'}`
        );
        process.exit(1);
      }
    } else {
      // Clear cached keychain entry to force re-authentication
      await deleteSecret('EVERNOTE_TOKEN');
      // Temporarily clear env token so auth flow runs
      const origToken = settings.token;
      settings.token = '';
      try {
        token = await getToken(settings);
      } finally {
        settings.token = origToken;
      }
    }

    if (!ctx.flags['skip-validation']) {
      const valid = await validateToken(token);
      if (!valid) {
        console.error(
          'Warning: Could not validate credentials. The token may be invalid or the API may be unreachable.'
        );
        console.error('Storing the token anyway.');
      }
    }

    try {
      await setSecret('EVERNOTE_TOKEN', token);
    } catch {
      console.error(
        'Error: OS keychain not available. Set EVERNOTE_TOKEN environment variable instead.'
      );
      process.exit(1);
    }

    console.log('Credentials saved to OS keychain.');
  }
);
