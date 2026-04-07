import {
  existsSync,
  mkdirSync,
  readFileSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { chmod } from 'node:fs/promises';
import { dirname } from 'node:path';
import { logger } from '../logger.js';

export function loadToken(configPath: string): string | null {
  if (!existsSync(configPath)) return null;
  try {
    const data = JSON.parse(readFileSync(configPath, 'utf-8'));
    return data.token ?? null;
  } catch {
    return null;
  }
}

export async function saveToken(
  configPath: string,
  token: string
): Promise<void> {
  const dir = dirname(configPath);
  mkdirSync(dir, { recursive: true });
  writeFileSync(configPath, JSON.stringify({ token }));
  try {
    await chmod(dir, 0o700);
    await chmod(configPath, 0o600);
  } catch (err) {
    logger.warn(`Could not set file permissions on ${configPath}: ${err}`);
  }
}

export function deleteToken(configPath: string): boolean {
  try {
    if (!existsSync(configPath)) return false;
    unlinkSync(configPath);
    return true;
  } catch {
    return false;
  }
}
