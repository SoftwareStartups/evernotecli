import { logger } from '../logger.js';
import {
  EvernoteAuthError,
  EvernoteError,
  EvernoteNotFoundError,
  EvernotePermissionError,
  EvernoteRateLimitError,
} from '../errors.js';

// @ts-expect-error — generated CommonJS module
import ErrorTypes from '../edam/Errors_types.js';

const EDAMErrorCode = ErrorTypes.EDAMErrorCode;

const MAX_RETRIES = 3;
const BACKOFF_MULTIPLIER = 250; // ms

function isRetriable(err: unknown): boolean {
  if (err instanceof Error) {
    if (
      err.message?.includes('ECONNRESET') ||
      err.message?.includes('ECONNREFUSED') ||
      err.message?.includes('ETIMEDOUT') ||
      err.message?.includes('socket hang up')
    ) {
      return true;
    }
  }
  // SHARD_UNAVAILABLE is retriable
  if (isEDAMSystemException(err) && err.errorCode === EDAMErrorCode.SHARD_UNAVAILABLE) {
    return true;
  }
  return false;
}

function isEDAMUserException(err: unknown): err is { errorCode: number; parameter?: string } {
  return (
    err !== null &&
    typeof err === 'object' &&
    'errorCode' in err &&
    err.constructor?.name === 'EDAMUserException'
  );
}

function isEDAMSystemException(
  err: unknown
): err is { errorCode: number; message?: string; rateLimitDuration?: number } {
  return (
    err !== null &&
    typeof err === 'object' &&
    'errorCode' in err &&
    err.constructor?.name === 'EDAMSystemException'
  );
}

function isEDAMNotFoundException(
  err: unknown
): err is { identifier?: string; key?: string } {
  return (
    err !== null &&
    typeof err === 'object' &&
    err.constructor?.name === 'EDAMNotFoundException'
  );
}

function convertEdamError(err: unknown): EvernoteError {
  if (isEDAMNotFoundException(err)) {
    return new EvernoteNotFoundError(
      `Not found: identifier=${err.identifier ?? '?'}, key=${err.key ?? '?'}`
    );
  }

  if (isEDAMSystemException(err)) {
    if (err.errorCode === EDAMErrorCode.RATE_LIMIT_REACHED) {
      const retryAfter =
        typeof err.rateLimitDuration === 'number'
          ? err.rateLimitDuration
          : 60;
      logger.warn(
        `Evernote rate limit reached (rateLimitDuration=${err.rateLimitDuration}s) — not retrying`
      );
      return new EvernoteRateLimitError(retryAfter);
    }
    return new EvernoteError(`Evernote system error: ${err.errorCode}`);
  }

  if (isEDAMUserException(err)) {
    if (
      err.errorCode === EDAMErrorCode.AUTH_EXPIRED ||
      err.errorCode === EDAMErrorCode.INVALID_AUTH
    ) {
      return new EvernoteAuthError(
        `Evernote auth error: ${err.errorCode} (parameter=${err.parameter ?? '?'}). ` +
          "Run 'evercli login' to re-authenticate."
      );
    }
    if (err.errorCode === EDAMErrorCode.PERMISSION_DENIED) {
      return new EvernotePermissionError(
        `Permission denied (parameter=${err.parameter ?? '?'})`
      );
    }
    return new EvernoteError(
      `Evernote API error: ${err.errorCode} (parameter=${err.parameter ?? '?'})`
    );
  }

  if (err instanceof Error) {
    return new EvernoteError(err.message);
  }
  return new EvernoteError(String(err));
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Store proxy that auto-injects authenticationToken into Thrift calls
 * and provides retry with exponential backoff.
 */
export class Store {
  private token: string;
  private client: Record<string, (...args: unknown[]) => unknown>;

  constructor(
    client: Record<string, (...args: unknown[]) => unknown>,
    token: string
  ) {
    this.client = client;
    this.token = token;

    // Return a proxy that intercepts method calls
    return new Proxy(this, {
      get(target, prop: string) {
        if (prop in target) {
          return (target as Record<string, unknown>)[prop];
        }

        const method = target.client[prop];
        if (typeof method !== 'function') {
          return method;
        }

        return (...args: unknown[]) => {
          return target.callWithRetry(prop, method.bind(target.client), args);
        };
      },
    });
  }

  private async callWithRetry(
    methodName: string,
    method: (...args: unknown[]) => unknown,
    args: unknown[]
  ): Promise<unknown> {
    // Prepend auth token as first argument (Evernote Thrift convention)
    const fullArgs = [this.token, ...args];

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        const result = await this.callThrift(method, fullArgs);
        return result;
      } catch (err) {
        // Convert EDAM exceptions immediately — don't retry rate limits
        if (
          isEDAMUserException(err) ||
          isEDAMNotFoundException(err) ||
          isEDAMSystemException(err)
        ) {
          throw convertEdamError(err);
        }

        if (attempt < MAX_RETRIES && isRetriable(err)) {
          const delay = BACKOFF_MULTIPLIER * 2 ** attempt;
          logger.warn(
            `Retrying ${methodName} (attempt ${attempt + 1}/${MAX_RETRIES}) after ${delay}ms`
          );
          await sleep(delay);
          continue;
        }

        throw convertEdamError(err);
      }
    }

    throw new EvernoteError(`${methodName} failed after ${MAX_RETRIES} retries`);
  }

  private callThrift(
    method: (...args: unknown[]) => unknown,
    args: unknown[]
  ): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const callback = (err: unknown, result: unknown) => {
        if (err) reject(err);
        else resolve(result);
      };
      method(...args, callback);
    });
  }
}
