import path from 'node:path';

/**
 * Joins a user-supplied filename onto a trusted base directory and verifies
 * the result stays within the base. Rejects path-traversal patterns (`..`,
 * absolute paths, mixed-separator escapes). Returns an absolute path safe
 * for filesystem writes.
 *
 * @throws Error('Invalid file path') if the resolved target escapes base.
 */
export function safeJoin(baseDir: string, untrustedName: string): string {
  const base = path.resolve(baseDir);
  const target = path.resolve(base, untrustedName);
  const relative = path.relative(base, target);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error('Invalid file path');
  }
  return target;
}
