import { unlinkSync, existsSync } from 'node:fs';
import { defineCommand } from 'clerc';
import { getToken } from '../../auth/oauth.js';
import { settings } from '../../config.js';

export const loginCommand = defineCommand(
  {
    name: 'login',
    description: 'Authenticate with Evernote (always runs OAuth flow)',
  },
  async () => {
    // Clear cached token to force OAuth
    if (existsSync(settings.tokenPath)) {
      unlinkSync(settings.tokenPath);
    }
    // Temporarily clear env token so OAuth flow runs
    const origToken = settings.token;
    settings.token = '';
    try {
      await getToken(settings);
      console.log('Authenticated successfully.');
    } finally {
      settings.token = origToken;
    }
  }
);
