import pino from 'pino';
import { settings } from './config.js';

// Use stderr transport — stdout is reserved for MCP JSON-RPC
export const logger = pino({
  level: settings.logLevel,
  transport: {
    target: 'pino/file',
    options: { destination: 2 }, // stderr
  },
});
