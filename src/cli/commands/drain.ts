import { defineCommand } from 'clerc';
import * as service from '../../service.js';

export const drainCommand = defineCommand(
  {
    name: 'drain',
    description: 'Process all queued write operations',
  },
  async () => {
    const pending = service.pendingWriteCount();
    if (pending === 0) {
      console.log('No pending write operations.');
      return;
    }
    const count = await service.drainPendingWrites();
    const remaining = service.pendingWriteCount();
    console.log(`Processed ${count} operation(s). ${remaining} remaining.`);
    if (remaining > 0) {
      console.error(
        "Some operations failed (rate limited?). Run 'evercli drain' again later."
      );
    }
  }
);
