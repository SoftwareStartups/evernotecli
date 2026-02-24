"""ENML <-> Markdown conversion.

ENML (Evernote Markup Language) is a subset of XHTML with custom tags:
- <en-note> wrapper
- <en-todo> checkboxes
- <en-media> attachments
- <en-crypt> encrypted content
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET


def enml_to_markdown(enml: str) -> str:
    """Convert ENML to Markdown."""
    if not enml:
        return ""

    # Strip XML declaration and DOCTYPE
    enml = re.sub(r"<\?xml[^>]*\?>", "", enml)
    enml = re.sub(r"<!DOCTYPE[^>]*>", "", enml)
    enml = enml.strip()

    # Handle en-todo before XML parsing (self-closing tags with no namespace)
    enml = re.sub(
        r'<en-todo\s+checked="true"\s*/?>',
        '<en-todo-checked/>',
        enml,
    )
    enml = re.sub(
        r"<en-todo\s*/?>",
        "<en-todo-unchecked/>",
        enml,
    )

    try:
        root = ET.fromstring(enml)
    except ET.ParseError:
        # Fallback: strip all tags
        return _strip_tags(enml)

    lines: list[str] = []
    _walk(root, lines, context={})
    result = "\n".join(lines)
    # Clean up excessive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _walk(
    el: ET.Element,
    lines: list[str],
    context: dict[str, bool],
) -> None:
    """Recursively walk ENML element tree and build markdown lines."""
    tag = _local_tag(el.tag)
    text = el.text or ""
    tail = el.tail or ""

    # Headings
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        inner = _inline_text(el)
        lines.append(f"{'#' * level} {inner}")
        lines.append("")

    # Paragraphs / divs
    elif tag in ("p", "div"):
        inner = _inline_text(el)
        if inner.strip():
            lines.append(inner)
            lines.append("")

    # Line break
    elif tag == "br":
        lines.append("")

    # Horizontal rule
    elif tag == "hr":
        lines.append("---")
        lines.append("")

    # Lists
    elif tag in ("ul", "ol"):
        for i, child in enumerate(el):
            if _local_tag(child.tag) == "li":
                prefix = f"{i + 1}. " if tag == "ol" else "- "
                inner = _inline_text(child)
                lines.append(f"{prefix}{inner}")
        lines.append("")

    # Table
    elif tag == "table":
        _convert_table(el, lines)

    # en-todo (already transformed to en-todo-checked / en-todo-unchecked)
    elif tag == "en-todo-checked":
        lines.append("- [x] ")
    elif tag == "en-todo-unchecked":
        lines.append("- [ ] ")

    # en-media (attachments)
    elif tag == "en-media":
        hash_val = el.get("hash", "")
        mime = el.get("type", "")
        lines.append(f"![attachment:{mime}]({hash_val})")

    # en-crypt (encrypted content)
    elif tag == "en-crypt":
        lines.append("[Encrypted Content]")

    # en-note wrapper — just process children
    elif tag == "en-note":
        for child in el:
            _walk(child, lines, context)
        if text.strip():
            lines.append(text.strip())

    # Anchors at block level
    elif tag == "a":
        href = el.get("href", "")
        link_text = _get_all_text(el)
        lines.append(f"[{link_text}]({href})")

    # Unknown block element — recurse
    else:
        if text.strip():
            lines.append(text.strip())
        for child in el:
            _walk(child, lines, context)

    # Append tail text
    if tail.strip():
        lines.append(tail.strip())


def _inline_text(el: ET.Element) -> str:
    """Convert an element and its children to inline markdown."""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)

    for child in el:
        tag = _local_tag(child.tag)
        child_text = _get_all_text(child)
        tail = child.tail or ""

        if tag in ("b", "strong"):
            parts.append(f"**{child_text}**")
        elif tag in ("i", "em"):
            parts.append(f"*{child_text}*")
        elif tag == "a":
            href = child.get("href", "")
            parts.append(f"[{child_text}]({href})")
        elif tag == "br":
            parts.append("\n")
        elif tag == "en-todo-checked":
            parts.append("- [x] ")
        elif tag == "en-todo-unchecked":
            parts.append("- [ ] ")
        elif tag in ("code", "pre"):
            parts.append(f"`{child_text}`")
        else:
            parts.append(child_text)

        if tail:
            parts.append(tail)

    return "".join(parts)


def _get_all_text(el: ET.Element) -> str:
    """Get all text content from an element, stripping tags."""
    return "".join(el.itertext())


def _local_tag(tag: str) -> str:
    """Strip namespace from tag name."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _convert_table(table: ET.Element, lines: list[str]) -> None:
    """Convert an HTML table to markdown table."""
    rows: list[list[str]] = []
    for tr in table.iter():
        if _local_tag(tr.tag) == "tr":
            cells = []
            for td in tr:
                if _local_tag(td.tag) in ("td", "th"):
                    cells.append(_get_all_text(td).strip())
            if cells:
                rows.append(cells)

    if not rows:
        return

    # Header row
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for row in rows[1:]:
        # Pad row to match header length
        while len(row) < len(rows[0]):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")


def _strip_tags(html: str) -> str:
    """Fallback: strip all HTML/XML tags."""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    return text.strip()


# --- Markdown to ENML ---

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

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = _escape_xml(heading_match.group(2))
            text = _inline_md_to_enml(text)
            enml_parts.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line):
            enml_parts.append("<hr/>")
            i += 1
            continue

        # Checkbox list items
        checkbox_match = re.match(r"^-\s+\[([ xX])\]\s+(.+)$", line)
        if checkbox_match:
            checked = checkbox_match.group(1).lower() == "x"
            text = _escape_xml(checkbox_match.group(2))
            text = _inline_md_to_enml(text)
            if checked:
                enml_parts.append(
                    f'<div><en-todo checked="true"/>{text}</div>'
                )
            else:
                enml_parts.append(f"<div><en-todo/>{text}</div>")
            i += 1
            continue

        # Unordered list items
        ul_match = re.match(r"^[-*]\s+(.+)$", line)
        if ul_match:
            items: list[str] = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                m = re.match(r"^[-*]\s+(.+)$", lines[i])
                if m:
                    items.append(_escape_xml(m.group(1)))
                i += 1
            enml_parts.append("<ul>")
            for item in items:
                enml_parts.append(f"<li>{_inline_md_to_enml(item)}</li>")
            enml_parts.append("</ul>")
            continue

        # Ordered list items
        ol_match = re.match(r"^\d+\.\s+(.+)$", line)
        if ol_match:
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                m = re.match(r"^\d+\.\s+(.+)$", lines[i])
                if m:
                    items.append(_escape_xml(m.group(1)))
                i += 1
            enml_parts.append("<ol>")
            for item in items:
                enml_parts.append(f"<li>{_inline_md_to_enml(item)}</li>")
            enml_parts.append("</ol>")
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
