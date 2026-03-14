import { XMLParser } from 'fast-xml-parser';
import { logger } from '../logger.js';
import type { ResourceInfo } from './types.js';

export function enmlToMarkdown(
  enml: string,
  resources?: ResourceInfo[]
): string {
  if (!enml) return '';

  const resourceMap = new Map<string, ResourceInfo>();
  if (resources) {
    for (const r of resources) resourceMap.set(r.hashHex, r);
  }

  // Strip XML declaration and DOCTYPE
  enml = enml.replace(/<\?xml[^>]*\?>/, '');
  enml = enml.replace(/<!DOCTYPE[^>]*>/, '');
  enml = enml.trim();

  // Pre-process en-todo before XML parsing
  enml = enml.replace(
    /<en-todo\s+checked="true"\s*\/?>/g,
    '<en-todo-checked/>'
  );
  enml = enml.replace(/<en-todo\s*\/?>/g, '<en-todo-unchecked/>');

  try {
    const parser = new XMLParser({
      ignoreAttributes: false,
      preserveOrder: true,
      trimValues: false,
      processEntities: true,
      htmlEntities: true,
    });
    const parsed = parser.parse(enml);
    const lines: string[] = [];
    walkNodes(parsed, lines, resourceMap);
    let result = lines.join('\n');
    result = result.replace(/\n{3,}/g, '\n\n');
    return result.trim();
  } catch {
    logger.warn('Failed to parse ENML as XML, falling back to tag stripping');
    return stripTags(enml);
  }
}

// --- Node walking ---

function walkNodes(
  nodes: ParsedNode[],
  lines: string[],
  resourceMap: Map<string, ResourceInfo>
): void {
  for (const node of nodes) {
    if (typeof node === 'string' || node['#text'] !== undefined) {
      const text = String(node['#text'] ?? node);
      if (text.trim()) lines.push(text.trim());
      continue;
    }
    walkNode(node, lines, resourceMap);
  }
}

function walkNode(
  node: ParsedNode,
  lines: string[],
  resourceMap: Map<string, ResourceInfo>
): void {
  const tagName = getTagName(node);
  if (!tagName) {
    // Text node
    const text = node['#text'];
    if (text !== undefined && String(text).trim()) {
      lines.push(String(text).trim());
    }
    return;
  }

  const attrs = node[':@'] ?? {};
  const children = node[tagName] ?? [];

  switch (tagName) {
    case 'en-note':
      walkNodes(children, lines, resourceMap);
      break;

    case 'h1':
    case 'h2':
    case 'h3':
    case 'h4':
    case 'h5':
    case 'h6': {
      const level = parseInt(tagName[1], 10);
      const inner = inlineText(children);
      lines.push(`${'#'.repeat(level)} ${inner}`);
      lines.push('');
      break;
    }

    case 'p':
    case 'div': {
      const inner = inlineText(children);
      if (inner.trim()) {
        lines.push(inner);
        lines.push('');
      }
      break;
    }

    case 'br':
      lines.push('');
      break;

    case 'hr':
      lines.push('---');
      lines.push('');
      break;

    case 'ul':
    case 'ol':
      handleList(tagName, children, lines);
      break;

    case 'table':
      handleTable(children, lines);
      break;

    case 'en-todo-checked':
      lines.push('- [x] ');
      break;

    case 'en-todo-unchecked':
      lines.push('- [ ] ');
      break;

    case 'en-media':
      handleMedia(attrs, lines, resourceMap);
      break;

    case 'en-crypt':
      lines.push('[Encrypted Content]');
      break;

    case 'pre':
      handlePre(children, lines);
      break;

    case 'a': {
      const href = getAttr(attrs, 'href');
      const text = getAllText(children);
      lines.push(`[${text}](${href})`);
      break;
    }

    default:
      // Unknown block — recurse
      walkNodes(children, lines, resourceMap);
      break;
  }
}

// --- Handlers ---

function handleList(
  tag: string,
  children: ParsedNode[],
  lines: string[]
): void {
  let index = 0;
  for (const child of children) {
    const childTag = getTagName(child);
    if (childTag === 'li') {
      index++;
      const prefix = tag === 'ol' ? `${index}. ` : '- ';
      const inner = inlineText(child[childTag] ?? []);
      lines.push(`${prefix}${inner}`);
    }
  }
  lines.push('');
}

function handleTable(children: ParsedNode[], lines: string[]): void {
  const rows: string[][] = [];
  collectTableRows(children, rows);

  if (rows.length === 0) return;

  lines.push(`| ${rows[0].join(' | ')} |`);
  lines.push(`| ${rows[0].map(() => '---').join(' | ')} |`);
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    while (row.length < rows[0].length) row.push('');
    lines.push(`| ${row.join(' | ')} |`);
  }
  lines.push('');
}

function collectTableRows(nodes: ParsedNode[], rows: string[][]): void {
  for (const node of nodes) {
    const tag = getTagName(node);
    if (tag === 'tr') {
      const cells: string[] = [];
      for (const cell of node[tag] ?? []) {
        const cellTag = getTagName(cell);
        if (cellTag === 'td' || cellTag === 'th') {
          cells.push(getAllText(cell[cellTag] ?? []).trim());
        }
      }
      if (cells.length > 0) rows.push(cells);
    } else if (tag) {
      collectTableRows(node[tag] ?? [], rows);
    }
  }
}

function handleMedia(
  attrs: Record<string, unknown>,
  lines: string[],
  resourceMap: Map<string, ResourceInfo>
): void {
  const hashHex = getAttr(attrs, 'hash');
  let mime = getAttr(attrs, 'type');
  const info = resourceMap.get(hashHex);
  let display: string;

  if (info) {
    display = info.filename || hashHex.substring(0, 8);
    mime = info.mimeType || mime;
  } else {
    display = hashHex ? hashHex.substring(0, 8) : 'attachment';
  }

  if (mime.startsWith('image/')) {
    lines.push(`![${display}](evernote-resource:${hashHex})`);
  } else {
    lines.push(`[${display}](evernote-resource:${hashHex})`);
  }
}

function handlePre(children: ParsedNode[], lines: string[]): void {
  // Look for a <code> child
  let content = '';
  for (const child of children) {
    if (getTagName(child) === 'code') {
      content = getAllText(child.code ?? []);
      break;
    }
  }
  if (!content) content = getAllText(children);

  lines.push('```');
  lines.push(content);
  lines.push('```');
  lines.push('');
}

// --- Inline text ---

function inlineText(nodes: ParsedNode[]): string {
  const parts: string[] = [];
  for (const node of nodes) {
    const tag = getTagName(node);
    if (!tag) {
      if (node['#text'] !== undefined) parts.push(String(node['#text']));
      continue;
    }

    const children = node[tag] ?? [];
    switch (tag) {
      case 'b':
      case 'strong':
        parts.push(`**${getAllText(children)}**`);
        break;
      case 'i':
      case 'em':
        parts.push(`*${getAllText(children)}*`);
        break;
      case 'a': {
        const href = getAttr(node[':@'] ?? {}, 'href');
        parts.push(`[${getAllText(children)}](${href})`);
        break;
      }
      case 'br':
        parts.push('\n');
        break;
      case 'en-todo-checked':
        parts.push('- [x] ');
        break;
      case 'en-todo-unchecked':
        parts.push('- [ ] ');
        break;
      case 'code':
        parts.push(`\`${getAllText(children)}\``);
        break;
      default:
        parts.push(getAllText(children));
        break;
    }
  }
  return parts.join('');
}

// --- Helpers ---

// biome-ignore lint/suspicious/noExplicitAny: fast-xml-parser produces dynamic node shapes
type ParsedNode = any;

function getTagName(node: ParsedNode): string | null {
  if (!node || typeof node !== 'object') return null;
  for (const key of Object.keys(node)) {
    if (key !== '#text' && key !== ':@') return key;
  }
  return null;
}

function getAttr(attrs: Record<string, unknown>, name: string): string {
  // fast-xml-parser prefixes attributes with @_
  const val = attrs[`@_${name}`];
  return val != null ? String(val) : '';
}

function getAllText(nodes: ParsedNode[]): string {
  if (!Array.isArray(nodes)) return '';
  const parts: string[] = [];
  for (const node of nodes) {
    if (node['#text'] !== undefined) {
      parts.push(String(node['#text']));
    }
    const tag = getTagName(node);
    if (tag) {
      parts.push(getAllText(node[tag] ?? []));
    }
  }
  return parts.join('');
}

function stripTags(html: string): string {
  let text = html.replace(/<[^>]+>/g, '');
  text = text.replace(/&nbsp;/g, ' ');
  text = text.replace(/&amp;/g, '&');
  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&quot;/g, '"');
  return text.trim();
}
