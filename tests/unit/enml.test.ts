import { describe, expect, test } from 'bun:test';
import { markdownToEnml } from '../../src/enml/to-enml.js';
import { enmlToMarkdown } from '../../src/enml/to-markdown.js';

describe('enmlToMarkdown', () => {
  test('empty input returns empty string', () => {
    expect(enmlToMarkdown('')).toBe('');
  });

  test('converts simple paragraph', () => {
    const enml = '<en-note><p>Hello world</p></en-note>';
    expect(enmlToMarkdown(enml)).toBe('Hello world');
  });

  test('converts headings', () => {
    const enml = '<en-note><h1>Title</h1><h2>Subtitle</h2></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('# Title');
    expect(md).toContain('## Subtitle');
  });

  test('converts bold and italic', () => {
    const enml = '<en-note><p><b>bold</b> and <i>italic</i></p></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('**bold**');
    expect(md).toContain('*italic*');
  });

  test('converts links', () => {
    const enml =
      '<en-note><p><a href="https://example.com">link</a></p></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('[link](https://example.com)');
  });

  test('converts unordered list', () => {
    const enml = '<en-note><ul><li>one</li><li>two</li></ul></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('- one');
    expect(md).toContain('- two');
  });

  test('converts ordered list', () => {
    const enml = '<en-note><ol><li>first</li><li>second</li></ol></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('1. first');
    expect(md).toContain('2. second');
  });

  test('converts checkboxes', () => {
    const enml =
      '<en-note><en-todo checked="true"/>Done<en-todo/>Not done</en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('- [x]');
    expect(md).toContain('- [ ]');
  });

  test('converts hr', () => {
    const enml = '<en-note><hr/></en-note>';
    expect(enmlToMarkdown(enml)).toContain('---');
  });

  test('converts code block', () => {
    const enml = '<en-note><pre><code>const x = 1;</code></pre></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('```');
    expect(md).toContain('const x = 1;');
  });

  test('converts en-media as image', () => {
    const enml =
      '<en-note><en-media type="image/png" hash="abcd1234abcd1234abcd1234abcd1234"/></en-note>';
    const md = enmlToMarkdown(enml, [
      {
        hashHex: 'abcd1234abcd1234abcd1234abcd1234',
        mimeType: 'image/png',
        filename: 'test.png',
      },
    ]);
    expect(md).toContain('![test.png]');
    expect(md).toContain('evernote-resource:');
  });

  test('converts en-media as link for non-image', () => {
    const enml =
      '<en-note><en-media type="application/pdf" hash="abcd1234abcd1234abcd1234abcd1234"/></en-note>';
    const md = enmlToMarkdown(enml, [
      {
        hashHex: 'abcd1234abcd1234abcd1234abcd1234',
        mimeType: 'application/pdf',
        filename: 'doc.pdf',
      },
    ]);
    expect(md).toContain('[doc.pdf]');
  });

  test('converts encrypted content', () => {
    const enml = '<en-note><en-crypt>secret</en-crypt></en-note>';
    expect(enmlToMarkdown(enml)).toContain('[Encrypted Content]');
  });

  test('strips XML declaration and DOCTYPE', () => {
    const enml =
      '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd"><en-note><p>text</p></en-note>';
    expect(enmlToMarkdown(enml)).toBe('text');
  });

  test('falls back to tag stripping on invalid XML', () => {
    const bad = '<not-valid>text<unclosed>';
    const result = enmlToMarkdown(bad);
    expect(result).toContain('text');
  });

  test('converts table', () => {
    const enml =
      '<en-note><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table></en-note>';
    const md = enmlToMarkdown(enml);
    expect(md).toContain('| A | B |');
    expect(md).toContain('| 1 | 2 |');
  });
});

describe('markdownToEnml', () => {
  test('empty input returns valid ENML', () => {
    const result = markdownToEnml('');
    expect(result.enml).toContain('<en-note>');
    expect(result.enml).toContain('</en-note>');
    expect(result.attachments).toHaveLength(0);
  });

  test('converts heading', () => {
    const result = markdownToEnml('# Title');
    expect(result.enml).toContain('<h1>Title</h1>');
  });

  test('converts bold', () => {
    const result = markdownToEnml('**bold**');
    expect(result.enml).toContain('<b>bold</b>');
  });

  test('converts italic', () => {
    const result = markdownToEnml('*italic*');
    expect(result.enml).toContain('<i>italic</i>');
  });

  test('converts link', () => {
    const result = markdownToEnml('[text](https://example.com)');
    expect(result.enml).toContain('<a href="https://example.com">text</a>');
  });

  test('converts inline code', () => {
    const result = markdownToEnml('`code`');
    expect(result.enml).toContain('<code>code</code>');
  });

  test('converts code block', () => {
    const result = markdownToEnml('```\nconst x = 1;\n```');
    expect(result.enml).toContain('<pre><code>');
    expect(result.enml).toContain('const x = 1;');
  });

  test('converts checkbox checked', () => {
    const result = markdownToEnml('- [x] Done');
    expect(result.enml).toContain('checked="true"');
    expect(result.enml).toContain('Done');
  });

  test('converts checkbox unchecked', () => {
    const result = markdownToEnml('- [ ] Not done');
    expect(result.enml).toContain('<en-todo/>');
    expect(result.enml).toContain('Not done');
  });

  test('converts hr', () => {
    const result = markdownToEnml('---');
    expect(result.enml).toContain('<hr/>');
  });

  test('converts unordered list', () => {
    const result = markdownToEnml('- one\n- two');
    expect(result.enml).toContain('<ul>');
    expect(result.enml).toContain('<li>one</li>');
    expect(result.enml).toContain('<li>two</li>');
  });

  test('converts ordered list', () => {
    const result = markdownToEnml('1. first\n2. second');
    expect(result.enml).toContain('<ol>');
    expect(result.enml).toContain('<li>first</li>');
    expect(result.enml).toContain('<li>second</li>');
  });

  test('converts table', () => {
    const md = '| A | B |\n| --- | --- |\n| 1 | 2 |';
    const result = markdownToEnml(md);
    expect(result.enml).toContain('<table>');
    expect(result.enml).toContain('<th>A</th>');
    expect(result.enml).toContain('<td>1</td>');
  });

  test('escapes XML entities', () => {
    const result = markdownToEnml('1 < 2 & 3 > 1');
    expect(result.enml).toContain('&lt;');
    expect(result.enml).toContain('&amp;');
    expect(result.enml).toContain('&gt;');
  });

  test('renders evernote-resource image', () => {
    const md = '![alt](evernote-resource:abcd1234abcd1234abcd1234abcd1234)';
    const result = markdownToEnml(md, [
      {
        hashHex: 'abcd1234abcd1234abcd1234abcd1234',
        mimeType: 'image/png',
        filename: 'test.png',
      },
    ]);
    expect(result.enml).toContain('en-media');
    expect(result.enml).toContain('image/png');
  });

  test('renders http image as link', () => {
    const md = '![alt](https://example.com/img.png)';
    const result = markdownToEnml(md);
    expect(result.enml).toContain('<a href=');
    expect(result.enml).toContain('example.com');
  });

  test('wraps standalone image in div', () => {
    const md = '![alt](evernote-resource:abcd1234abcd1234abcd1234abcd1234)';
    const result = markdownToEnml(md, [
      {
        hashHex: 'abcd1234abcd1234abcd1234abcd1234',
        mimeType: 'image/png',
        filename: 'test.png',
      },
    ]);
    expect(result.enml).toContain('<div><en-media');
  });

  test('creates attachment from evernote-resource when ResourceInfo has data', () => {
    const hash = 'abcd1234abcd1234abcd1234abcd1234';
    const data = new Uint8Array([1, 2, 3, 4]);
    const md = `![img.png](evernote-resource:${hash})`;
    const result = markdownToEnml(md, [
      { hashHex: hash, mimeType: 'image/png', filename: 'img.png', data },
    ]);
    expect(result.enml).toContain('<en-media');
    expect(result.attachments).toHaveLength(1);
    expect(result.attachments[0].data).toEqual(data);
  });

  test('separates consecutive unresolved evernote-resource images into divs', () => {
    const hash1 = 'aaaa1111aaaa1111aaaa1111aaaa1111';
    const hash2 = 'bbbb2222bbbb2222bbbb2222bbbb2222';
    const md = `![img1.png](evernote-resource:${hash1})\n![img2.png](evernote-resource:${hash2})`;
    const result = markdownToEnml(md);
    expect(result.enml).toContain('</div><div>');
    expect(result.enml).toContain('img1.png');
    expect(result.enml).toContain('img2.png');
  });
});
