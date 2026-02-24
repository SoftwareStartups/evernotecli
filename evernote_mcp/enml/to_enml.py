"""Markdown to ENML conversion."""

from __future__ import annotations

import re

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

        result = _parse_heading(line)
        if result is not None:
            enml_parts.append(result)
            i += 1
            continue

        result = _parse_hr(line)
        if result is not None:
            enml_parts.append(result)
            i += 1
            continue

        result = _parse_checkbox(line)
        if result is not None:
            enml_parts.append(result)
            i += 1
            continue

        parsed, consumed = _parse_ul(lines, i)
        if parsed is not None:
            enml_parts.append(parsed)
            i += consumed
            continue

        parsed, consumed = _parse_ol(lines, i)
        if parsed is not None:
            enml_parts.append(parsed)
            i += consumed
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Regular paragraph
        text = _escape_xml(line)
        text = _inline_md_to_enml(text)
        enml_parts.append(f"<div>{text}</div>")
        i += 1

    enml_parts.append(ENML_FOOTER)
    return "".join(enml_parts)


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
