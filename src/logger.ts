import pino from 'pino';
import { settings } from './config.js';

// Use stderr transport — stdout is reserved for MCP JSON-RPC
export const logger = pino({ level: settings.logLevel }, pino.destination(2));
