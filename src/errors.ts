export class EvernoteError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvernoteError';
  }
}

export class EvernoteAuthError extends EvernoteError {
  constructor(message: string) {
    super(message);
    this.name = 'EvernoteAuthError';
  }
}

export class EvernoteNotFoundError extends EvernoteError {
  constructor(message: string) {
    super(message);
    this.name = 'EvernoteNotFoundError';
  }
}

export class EvernotePermissionError extends EvernoteError {
  constructor(message: string) {
    super(message);
    this.name = 'EvernotePermissionError';
  }
}

export class EvernoteRateLimitError extends EvernoteError {
  public retryAfter: number;

  constructor(retryAfter: number) {
    const mins = Math.floor(retryAfter / 60);
    const secs = retryAfter % 60;
    super(
      `Evernote rate limit reached — retry after ${retryAfter}s (${mins}m ${secs}s)`
    );
    this.name = 'EvernoteRateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class PrivateNoteError extends EvernoteError {
  constructor(message: string) {
    super(message);
    this.name = 'PrivateNoteError';
  }
}

export class OAuthError extends EvernoteError {
  constructor(message: string) {
    super(message);
    this.name = 'OAuthError';
  }
}
