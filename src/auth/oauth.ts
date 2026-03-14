import { OAuth } from 'oauth';
import { OAuthError } from '../errors.js';
import type { Config } from '../config.js';
import { loadToken, saveToken } from './token-store.js';
import {
  CALLBACK_HOST,
  OAUTH_PORT,
  SERVICE_HOST,
  waitForCallback,
} from './callback-server.js';

const CALLBACK_URL = `http://${CALLBACK_HOST}:${OAUTH_PORT}/oauth_callback`;

function createOAuthClient(consumerKey: string, consumerSecret: string): OAuth {
  return new OAuth(
    `https://${SERVICE_HOST}/oauth`,
    `https://${SERVICE_HOST}/oauth`,
    consumerKey,
    consumerSecret,
    '1.0',
    CALLBACK_URL,
    'HMAC-SHA1'
  );
}

async function runOAuthFlow(
  consumerKey: string,
  consumerSecret: string
): Promise<string> {
  const client = createOAuthClient(consumerKey, consumerSecret);

  // Step 1: Get request token
  const { requestToken, requestTokenSecret } = await new Promise<{
    requestToken: string;
    requestTokenSecret: string;
  }>((resolve, reject) => {
    client.getOAuthRequestToken(
      (err: unknown, token: string, tokenSecret: string) => {
        if (err) reject(new OAuthError(`Failed to get request token: ${err}`));
        else resolve({ requestToken: token, requestTokenSecret: tokenSecret });
      }
    );
  });

  // Step 2: Open browser for authorization
  const authUrl = `https://${SERVICE_HOST}/OAuth.action?oauth_token=${requestToken}`;
  console.log(`Opening browser for Evernote authorization:\n${authUrl}`);

  const cmd =
    process.platform === 'darwin'
      ? 'open'
      : process.platform === 'win32'
        ? 'cmd'
        : 'xdg-open';
  const args =
    process.platform === 'win32' ? ['/c', 'start', authUrl] : [authUrl];
  try {
    Bun.spawn([cmd, ...args]);
  } catch {
    // Browser launch failed — URL is already printed above
  }

  // Step 3: Wait for callback
  const callbackResult = await waitForCallback();
  const callbackUrl = new URL(callbackResult.fullUrl);
  const oauthVerifier = callbackUrl.searchParams.get('oauth_verifier');

  if (!oauthVerifier) {
    throw new OAuthError('OAuth declined by user');
  }

  // Step 4: Exchange for access token
  const accessToken = await new Promise<string>((resolve, reject) => {
    client.getOAuthAccessToken(
      requestToken,
      requestTokenSecret,
      oauthVerifier,
      (err: unknown, token: string) => {
        if (err) reject(new OAuthError(`OAuth token request denied: ${err}`));
        else resolve(token);
      }
    );
  });

  return accessToken;
}

async function promptForDeveloperToken(): Promise<string> {
  console.log(
    'No OAuth credentials configured.\n' +
      'You can get a developer token at: https://dev.evernote.com/get-token/\n'
  );
  const token = prompt('Paste your developer token:');
  if (!token?.trim()) {
    throw new OAuthError('No token provided.');
  }
  return token.trim();
}

export async function getToken(config: Config): Promise<string> {
  // 1. Direct token from env
  if (config.token) {
    return config.token;
  }

  // 2. Cached token file
  const cached = loadToken(config.tokenPath);
  if (cached) {
    return cached;
  }

  // 3a. Run OAuth flow if credentials are configured
  if (config.consumerKey && config.consumerSecret) {
    const token = await runOAuthFlow(config.consumerKey, config.consumerSecret);
    await saveToken(config.tokenPath, token);
    return token;
  }

  // 3b. Prompt for developer token if running interactively
  if (process.stdin.isTTY) {
    const token = await promptForDeveloperToken();
    await saveToken(config.tokenPath, token);
    return token;
  }

  // 3c. Non-interactive context (e.g. MCP server) — no way to authenticate
  throw new OAuthError(
    'No EVERNOTE_TOKEN set and no OAuth credentials configured. ' +
      'Set EVERNOTE_TOKEN or both EVERNOTE_CONSUMER_KEY and EVERNOTE_CONSUMER_SECRET.'
  );
}
