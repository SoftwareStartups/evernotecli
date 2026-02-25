"""Markdown to ENML conversion."""

from __future__ import annotations

import re
from collections.abc import Callable

ENML_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
    "<en-note>"
)
ENML_FOOTER = "</en-note>"


def markdown_to_enml(md: str) -> str:
    """Convert Markdown to valid ENML for note creation."""
    if not md:
        return f"{ENML_HEADER}{ENML_FOOTER}"

    lines = md.split("\n")
    enml_parts: list[str] = [ENML_HEADER]
    i = 0

    while i < len(lines):
        line = lines[i]

        for parser in _BLOCK_PARSERS:
            result, consumed = parser(lines, i)
            if result is not None:
                enml_parts.append(result)
                i += consumed
                break
        else:
            if line.strip():
                text = _escape_xml(line)
                text = _inline_md_to_enml(text)
                enml_parts.append(f"<div>{text}</div>")
            i += 1

    enml_parts.append(ENML_FOOTER)
    return "".join(enml_parts)


# --- Block parser infrastructure ---


def _single(
    fn: Callable[[str], str | None],
) -> Callable[[list[str], int], tuple[str | None, int]]:
    """Adapt a single-line parser to the multi-line ``(lines, i)`` signature."""

    def wrapper(lines: list[str], i: int) -> tuple[str | None, int]:
        result = fn(lines[i])
        return (result, 1) if result is not None else (None, 0)

    return wrapper


# --- Block parsers ---


def _parse_heading(line: str) -> str | None:
    heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if not heading_match:
        return None
    level = len(heading_match.group(1))
    text = _escape_xml(heading_match.group(2))
    text = _inline_md_to_enml(text)
    return f"<h{level}>{text}</h{level}>"


def _parse_hr(line: str) -> str | None:
    if re.match(r"^---+\s*$", line):
        return "<hr/>"
    return None


def _parse_checkbox(line: str) -> str | None:
    checkbox_match = re.match(r"^-\s+\[([ xX])\]\s+(.+)$", line)
    if not checkbox_match:
        return None
    checked = checkbox_match.group(1).lower() == "x"
    text = _escape_xml(checkbox_match.group(2))
    text = _inline_md_to_enml(text)
    if checked:
        return f'<div><en-todo checked="true"/>{text}</div>'
    return f"<div><en-todo/>{text}</div>"


def _parse_ul(lines: list[str], i: int) -> tuple[str | None, int]:
    if not re.match(r"^[-*]\s+(.+)$", lines[i]):
        return None, 0
    items: list[str] = []
    start = i
    while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
        m = re.match(r"^[-*]\s+(.+)$", lines[i])
        if m:
            items.append(_escape_xml(m.group(1)))
        i += 1
    parts = ["<ul>"]
    for item in items:
        parts.append(f"<li>{_inline_md_to_enml(item)}</li>")
    parts.append("</ul>")
    return "".join(parts), i - start


def _parse_ol(lines: list[str], i: int) -> tuple[str | None, int]:
    if not re.match(r"^\d+\.\s+(.+)$", lines[i]):
        return None, 0
    items: list[str] = []
    start = i
    while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
        m = re.match(r"^\d+\.\s+(.+)$", lines[i])
        if m:
            items.append(_escape_xml(m.group(1)))
        i += 1
    parts = ["<ol>"]
    for item in items:
        parts.append(f"<li>{_inline_md_to_enml(item)}</li>")
    parts.append("</ol>")
    return "".join(parts), i - start


def _parse_code_block(lines: list[str], i: int) -> tuple[str | None, int]:
    if not re.match(r"^```", lines[i]):
        return None, 0
    start = i
    i += 1
    content_lines: list[str] = []
    while i < len(lines):
        if re.match(r"^```\s*$", lines[i]):
            i += 1
            break
        content_lines.append(lines[i])
        i += 1
    content = _escape_xml("\n".join(content_lines))
    return f"<pre><code>{content}</code></pre>", i - start


def _parse_table(lines: list[str], i: int) -> tuple[str | None, int]:
    if not re.match(r"^\|.+\|", lines[i]):
        return None, 0
    start = i
    rows: list[list[str]] = []
    while i < len(lines) and re.match(r"^\|.+\|", lines[i]):
        line = lines[i].strip()
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Skip separator row
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            i += 1
            continue
        rows.append(cells)
        i += 1
    if not rows:
        return None, 0
    parts = ["<table>"]
    for idx, row in enumerate(rows):
        tag = "th" if idx == 0 else "td"
        cells_html = "".join(
            f"<{tag}>{_inline_md_to_enml(_escape_xml(c))}</{tag}>" for c in row
        )
        parts.append(f"<tr>{cells_html}</tr>")
    parts.append("</table>")
    return "".join(parts), i - start


_BLOCK_PARSERS: list[Callable[[list[str], int], tuple[str | None, int]]] = [
    _parse_code_block,
    _parse_table,
    _single(_parse_heading),
    _single(_parse_hr),
    _single(_parse_checkbox),
    _parse_ul,
    _parse_ol,
]


# --- Helpers ---


def _escape_xml(text: str) -> str:
    """Escape XML special characters (but not already-escaped ones)."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text.replace('"', "&quot;")


def _inline_md_to_enml(text: str) -> str:
    """Convert inline markdown formatting to ENML tags.

    Operates on already XML-escaped text, so we match escaped markers.
    """
    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic: *text*
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Links: [text](url) — url is XML-escaped so ( and ) are literal
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # Inline code: `text`
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
