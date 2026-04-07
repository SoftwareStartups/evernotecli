import { Cli } from 'clerc';
import pkg from '../../package.json' with { type: 'json' };
import { EvernoteError } from '../errors.js';
import { contentCommand } from './commands/content.js';
import { copyCommand } from './commands/copy.js';
import { createCommand } from './commands/create.js';
import { drainCommand } from './commands/drain.js';
import { loginCommand } from './commands/login.js';
import { logoutCommand } from './commands/logout.js';
import { moveCommand } from './commands/move.js';
import { noteCommand } from './commands/note.js';
import { notebooksCommand } from './commands/notebooks.js';
import { searchCommand } from './commands/search.js';
import { serveCommand } from './commands/serve.js';
import { tagCommand } from './commands/tag.js';
import { tagsCommand } from './commands/tags.js';
import { untagCommand } from './commands/untag.js';

export async function run(argv: string[]): Promise<void> {
  const cli = Cli({
    name: 'evercli',
    scriptName: 'evercli',
    description: 'Evernote CLI client',
    version: pkg.version,
  })
    .command(searchCommand)
    .command(noteCommand)
    .command(contentCommand)
    .command(notebooksCommand)
    .command(tagsCommand)
    .command(createCommand)
    .command(tagCommand)
    .command(untagCommand)
    .command(moveCommand)
    .command(loginCommand)
    .command(logoutCommand)
    .command(serveCommand)
    .command(drainCommand)
    .command(copyCommand)
    .errorHandler((err) => {
      if (err instanceof EvernoteError) {
        console.error(`Error: ${err.message}`);
        process.exit(1);
      }
      throw err;
    });

  await cli.parse({ argv: argv.slice(2) });
}
