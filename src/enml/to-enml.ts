import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { basename } from 'node:path';
import { logger } from '../logger.js';
import type { Attachment, EnmlResult, ResourceInfo } from './types.js';

const ENML_HEADER =
  '<?xml version="1.0" encoding="UTF-8"?>' +
  '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">' +
  '<en-note>';
const ENML_FOOTER = '</en-note>';

// --- Regex patterns ---
const RE_HEADING = /^(#{1,6})\s+(.+)$/;
const RE_HR = /^---+\s*$/;
const RE_CHECKBOX = /^-\s+\[([ xX])\]\s+(.+)$/;
const RE_UL_ITEM = /^[-*]\s+(.+)$/;
const RE_UL_PREFIX = /^[-*]\s+/;
const RE_OL_ITEM = /^\d+\.\s+(.+)$/;
const RE_OL_PREFIX = /^\d+\.\s+/;
const RE_CODE_FENCE_OPEN = /^```/;
const RE_CODE_FENCE_CLOSE = /^```\s*$/;
const RE_TABLE_ROW = /^\|.+\|/;
const RE_TABLE_SEPARATOR = /^:?-+:?$/;
// Bold must be applied before italic so `**bold**` isn't consumed as italic.
// Limitation: nested patterns like `*italic **bold** more italic*` will
// produce incorrect nesting — a full markdown parser would be needed to fix.
const RE_BOLD = /\*\*(.+?)\*\*/g;
const RE_ITALIC = /\*(.+?)\*/g;
const RE_LINK = /\[([^\]]+)\]\(([^)]+)\)/g;
const RE_INLINE_CODE = /`([^`]+)`/g;
const RE_IMAGE = /!\[([^\]]*)\]\(([^)]+)\)/g;
const RE_IMAGE_FULL = /^!\[([^\]]*)\]\(([^)]+)\)$/;
const RE_EVERNOTE_RESOURCE = /^evernote-resource:([0-9a-f]{32})$/;

export function markdownToEnml(
  md: string,
  existingResources?: ResourceInfo[]
): EnmlResult {
  if (!md) return { enml: `${ENML_HEADER}${ENML_FOOTER}`, attachments: [] };

  const existingMap = new Map<string, ResourceInfo>();
  if (existingResources) {
    for (const r of existingResources) existingMap.set(r.hashHex, r);
  }

  const attachments: Attachment[] = [];
  const seenHashes = new Set<string>();
  const lines = md.split('\n');
  const enmlParts: string[] = [ENML_HEADER];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Try block parsers in order
    let consumed = 0;
    let result: string | null = null;

    // Code block
    ({ result, consumed } = parseCodeBlock(lines, i));
    if (result !== null) {
      enmlParts.push(result);
      i += consumed;
      continue;
    }

    // Table
    ({ result, consumed } = parseTable(
      lines,
      i,
      existingMap,
      attachments,
      seenHashes
    ));
    if (result !== null) {
      enmlParts.push(result);
      i += consumed;
      continue;
    }

    // Heading
    result = parseHeading(line, existingMap, attachments, seenHashes);
    if (result !== null) {
      enmlParts.push(result);
      i++;
      continue;
    }

    // HR
    if (RE_HR.test(line)) {
      enmlParts.push('<hr/>');
      i++;
      continue;
    }

    // Checkbox
    result = parseCheckbox(line, existingMap, attachments, seenHashes);
    if (result !== null) {
      enmlParts.push(result);
      i++;
      continue;
    }

    // Unordered list
    ({ result, consumed } = parseList(
      'ul',
      RE_UL_ITEM,
      RE_UL_PREFIX,
      lines,
      i,
      existingMap,
      attachments,
      seenHashes
    ));
    if (result !== null) {
      enmlParts.push(result);
      i += consumed;
      continue;
    }

    // Ordered list
    ({ result, consumed } = parseList(
      'ol',
      RE_OL_ITEM,
      RE_OL_PREFIX,
      lines,
      i,
      existingMap,
      attachments,
      seenHashes
    ));
    if (result !== null) {
      enmlParts.push(result);
      i += consumed;
      continue;
    }

    // Regular line
    if (line.trim()) {
      // Check for standalone image
      const imgResult = parseImageLine(
        line,
        existingMap,
        attachments,
        seenHashes
      );
      if (imgResult !== null) {
        enmlParts.push(imgResult);
      } else {
        let text = escapeXml(line);
        text = inlineMdToEnml(text, existingMap, attachments, seenHashes);
        enmlParts.push(`<div>${text}</div>`);
      }
    }
    i++;
  }

  enmlParts.push(ENML_FOOTER);
  return { enml: enmlParts.join(''), attachments };
}

// --- Image rendering ---

function renderImage(
  alt: string,
  url: string,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): string {
  // evernote-resource:<hash> scheme
  const m = RE_EVERNOTE_RESOURCE.exec(url);
  if (m) {
    const hashHex = m[1];
    const info = existingMap.get(hashHex);
    if (info) {
      if (info.data && !seenHashes.has(hashHex)) {
        seenHashes.add(hashHex);
        attachments.push({
          hashHex,
          hashBytes: new Uint8Array(Buffer.from(hashHex, 'hex')),
          mimeType: info.mimeType,
          data: info.data,
          filename: info.filename,
          sourcePath: '',
        });
      }
      return `<en-media type="${info.mimeType}" hash="${hashHex}"/>`;
    }
    // Resource not available — text placeholder
    const display = alt || hashHex;
    return `[image: ${escapeXml(display)}]`;
  }

  // HTTP/HTTPS — render as link
  if (url.startsWith('http://') || url.startsWith('https://')) {
    const display = escapeXml(alt || url);
    return `<a href="${escapeXml(url)}">${display}</a>`;
  }

  // Local file
  const path = resolveLocalPath(url);
  if (!path || !existsSync(path)) {
    logger.warn(`Image path not found: ${url}`);
    const display = escapeXml(alt || url);
    return `<a href="${escapeXml(url)}">${display}</a>`;
  }

  let data: Uint8Array;
  try {
    data = readFileSync(path);
  } catch (err) {
    logger.warn(`Cannot read image file ${path}: ${err}`);
    const display = escapeXml(alt || url);
    return `<a href="${escapeXml(url)}">${display}</a>`;
  }

  const hashBytes = createHash('md5').update(data).digest();
  const hashHex = hashBytes.toString('hex');

  // Guess mime type
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  const mimeMap: Record<string, string> = {
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    gif: 'image/gif',
    webp: 'image/webp',
    svg: 'image/svg+xml',
    pdf: 'application/pdf',
  };
  const mimeType = mimeMap[ext] ?? 'application/octet-stream';

  if (!seenHashes.has(hashHex)) {
    seenHashes.add(hashHex);
    attachments.push({
      hashHex,
      hashBytes: new Uint8Array(hashBytes),
      mimeType,
      data: new Uint8Array(data),
      filename: basename(path),
      sourcePath: path,
    });
  }

  return `<en-media type="${mimeType}" hash="${hashHex}"/>`;
}

function resolveLocalPath(url: string): string | null {
  if (url.startsWith('file://')) url = url.substring(7);
  try {
    return resolve(
      url.startsWith('~') ? url.replace('~', process.env.HOME ?? '') : url
    );
  } catch {
    return null;
  }
}

function parseImageLine(
  line: string,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): string | null {
  const m = RE_IMAGE_FULL.exec(line.trim());
  if (!m) return null;
  const rendered = renderImage(
    m[1],
    m[2],
    existingMap,
    attachments,
    seenHashes
  );
  return `<div>${rendered}</div>`;
}

// --- Block parsers ---

function parseHeading(
  line: string,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): string | null {
  const m = RE_HEADING.exec(line);
  if (!m) return null;
  const level = m[1].length;
  let text = escapeXml(m[2]);
  text = inlineMdToEnml(text, existingMap, attachments, seenHashes);
  return `<h${level}>${text}</h${level}>`;
}

function parseCheckbox(
  line: string,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): string | null {
  const m = RE_CHECKBOX.exec(line);
  if (!m) return null;
  const checked = m[1].toLowerCase() === 'x';
  let text = escapeXml(m[2]);
  text = inlineMdToEnml(text, existingMap, attachments, seenHashes);
  return checked
    ? `<div><en-todo checked="true"/>${text}</div>`
    : `<div><en-todo/>${text}</div>`;
}

function parseList(
  tag: string,
  itemRe: RegExp,
  prefixRe: RegExp,
  lines: string[],
  i: number,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): { result: string | null; consumed: number } {
  if (!itemRe.test(lines[i])) return { result: null, consumed: 0 };
  const items: string[] = [];
  const start = i;
  while (i < lines.length && prefixRe.test(lines[i])) {
    const m = itemRe.exec(lines[i]);
    if (m) items.push(escapeXml(m[1]));
    i++;
  }
  const parts = [`<${tag}>`];
  for (const item of items) {
    const inner = inlineMdToEnml(item, existingMap, attachments, seenHashes);
    parts.push(`<li>${inner}</li>`);
  }
  parts.push(`</${tag}>`);
  return { result: parts.join(''), consumed: i - start };
}

function parseCodeBlock(
  lines: string[],
  i: number
): { result: string | null; consumed: number } {
  if (!RE_CODE_FENCE_OPEN.test(lines[i])) return { result: null, consumed: 0 };
  const start = i;
  i++;
  const contentLines: string[] = [];
  while (i < lines.length) {
    if (RE_CODE_FENCE_CLOSE.test(lines[i])) {
      i++;
      break;
    }
    contentLines.push(lines[i]);
    i++;
  }
  const content = escapeXml(contentLines.join('\n'));
  return {
    result: `<pre><code>${content}</code></pre>`,
    consumed: i - start,
  };
}

function parseTable(
  lines: string[],
  i: number,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): { result: string | null; consumed: number } {
  if (!RE_TABLE_ROW.test(lines[i])) return { result: null, consumed: 0 };
  const start = i;
  const rows: string[][] = [];
  while (i < lines.length && RE_TABLE_ROW.test(lines[i])) {
    const line = lines[i].trim();
    const cells = line
      .replace(/^\||\|$/g, '')
      .split('|')
      .map((c) => c.trim());
    if (cells.every((c) => RE_TABLE_SEPARATOR.test(c))) {
      i++;
      continue;
    }
    rows.push(cells);
    i++;
  }
  if (rows.length === 0) return { result: null, consumed: 0 };

  const parts = ['<table>'];
  for (let idx = 0; idx < rows.length; idx++) {
    const tag = idx === 0 ? 'th' : 'td';
    const cellParts: string[] = [];
    for (const c of rows[idx]) {
      const inner = inlineMdToEnml(
        escapeXml(c),
        existingMap,
        attachments,
        seenHashes
      );
      cellParts.push(`<${tag}>${inner}</${tag}>`);
    }
    parts.push(`<tr>${cellParts.join('')}</tr>`);
  }
  parts.push('</table>');
  return { result: parts.join(''), consumed: i - start };
}

// --- Helpers ---

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function inlineMdToEnml(
  text: string,
  existingMap: Map<string, ResourceInfo>,
  attachments: Attachment[],
  seenHashes: Set<string>
): string {
  // Images first
  text = text.replace(RE_IMAGE, (_match, alt: string, url: string) =>
    renderImage(alt, url, existingMap, attachments, seenHashes)
  );
  // Bold
  text = text.replace(RE_BOLD, '<b>$1</b>');
  // Italic
  text = text.replace(RE_ITALIC, '<i>$1</i>');
  // Links
  text = text.replace(RE_LINK, '<a href="$2">$1</a>');
  // Inline code
  text = text.replace(RE_INLINE_CODE, '<code>$1</code>');
  return text;
}
