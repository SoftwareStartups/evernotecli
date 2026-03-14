import { Cli } from 'clerc';
import { EvernoteError } from '../errors.js';
import { searchCommand } from './commands/search.js';
import { noteCommand } from './commands/note.js';
import { contentCommand } from './commands/content.js';
import { notebooksCommand } from './commands/notebooks.js';
import { tagsCommand } from './commands/tags.js';
import { createCommand } from './commands/create.js';
import { tagCommand } from './commands/tag.js';
import { untagCommand } from './commands/untag.js';
import { moveCommand } from './commands/move.js';
import { loginCommand } from './commands/login.js';
import { serveCommand } from './commands/serve.js';
import { drainCommand } from './commands/drain.js';

export async function run(argv: string[]): Promise<void> {
  const cli = Cli({
    name: 'evercli',
    description: 'Evernote CLI client',
    version: '0.1.0',
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
    .command(serveCommand)
    .command(drainCommand)
    .errorHandler((err) => {
      if (err instanceof EvernoteError) {
        console.error(`Error: ${err.message}`);
        process.exit(1);
      }
      throw err;
    });

  await cli.parse(argv);
}
