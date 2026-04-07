import { defineCommand } from 'clerc';
import { getToken } from '../../auth/oauth.js';
import { deleteToken, saveToken } from '../../auth/token-store.js';
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
      token = ctx.flags.token.trim();
      if (!token) {
        console.error('Error: Token cannot be empty.');
        process.exit(1);
      }
    } else {
      // Clear cached token to force re-authentication
      deleteToken(settings.configPath);
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

    await saveToken(settings.configPath, token);
    console.log(`Credentials saved to ${settings.configPath}`);
  }
);
