import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { chmod } from 'node:fs/promises';
import { dirname } from 'node:path';
import { logger } from '../logger.js';

export function loadToken(tokenPath: string): string | null {
  if (!existsSync(tokenPath)) return null;
  try {
    const data = JSON.parse(readFileSync(tokenPath, 'utf-8'));
    return data.token ?? null;
  } catch {
    return null;
  }
}

export async function saveToken(
  tokenPath: string,
  token: string
): Promise<void> {
  const dir = dirname(tokenPath);
  mkdirSync(dir, { recursive: true });
  writeFileSync(tokenPath, JSON.stringify({ token }));
  try {
    await chmod(dir, 0o700);
    await chmod(tokenPath, 0o600);
  } catch (err) {
    logger.warn(`Could not set file permissions on ${tokenPath}: ${err}`);
  }
}
