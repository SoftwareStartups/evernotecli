"""ENML to Markdown conversion.

ENML (Evernote Markup Language) is a subset of XHTML with custom tags:
- <en-note> wrapper
- <en-todo> checkboxes
- <en-media> attachments
- <en-crypt> encrypted content
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable

_WalkContext = dict[str, bool]
_BlockHandler = Callable[[ET.Element, list[str], _WalkContext], None]
_InlineHandler = Callable[[ET.Element], str]


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
        "<en-todo-checked/>",
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


# --- Block handlers ---


def _handle_heading(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    level = int(_local_tag(el.tag)[1])
    inner = _inline_text(el)
    lines.append(f"{'#' * level} {inner}")
    lines.append("")


def _handle_paragraph(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    inner = _inline_text(el)
    if inner.strip():
        lines.append(inner)
        lines.append("")


def _handle_br(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    lines.append("")


def _handle_hr(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    lines.append("---")
    lines.append("")


def _handle_list(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    tag = _local_tag(el.tag)
    for i, child in enumerate(el):
        if _local_tag(child.tag) == "li":
            prefix = f"{i + 1}. " if tag == "ol" else "- "
            inner = _inline_text(child)
            lines.append(f"{prefix}{inner}")
    lines.append("")


def _handle_table(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    _convert_table(el, lines)


def _handle_todo_checked(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    lines.append("- [x] ")


def _handle_todo_unchecked(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    lines.append("- [ ] ")


def _handle_media(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    hash_val = el.get("hash", "")
    mime = el.get("type", "")
    lines.append(f"![attachment:{mime}]({hash_val})")


def _handle_crypt(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    lines.append("[Encrypted Content]")


def _handle_en_note(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    for child in el:
        _walk(child, lines, ctx)
    text = el.text or ""
    if text.strip():
        lines.append(text.strip())


def _handle_pre(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    code_el = el.find("code")
    content = _get_all_text(code_el) if code_el is not None else _get_all_text(el)
    lines.append("```")
    lines.append(content)
    lines.append("```")
    lines.append("")


def _handle_anchor(el: ET.Element, lines: list[str], ctx: _WalkContext) -> None:
    href = el.get("href", "")
    link_text = _get_all_text(el)
    lines.append(f"[{link_text}]({href})")


_BLOCK_HANDLERS: dict[str, _BlockHandler] = {
    "h1": _handle_heading,
    "h2": _handle_heading,
    "h3": _handle_heading,
    "h4": _handle_heading,
    "h5": _handle_heading,
    "h6": _handle_heading,
    "p": _handle_paragraph,
    "div": _handle_paragraph,
    "br": _handle_br,
    "hr": _handle_hr,
    "ul": _handle_list,
    "ol": _handle_list,
    "table": _handle_table,
    "en-todo-checked": _handle_todo_checked,
    "en-todo-unchecked": _handle_todo_unchecked,
    "en-media": _handle_media,
    "en-crypt": _handle_crypt,
    "en-note": _handle_en_note,
    "pre": _handle_pre,
    "a": _handle_anchor,
}


# --- Inline handlers ---


def _inline_bold(child: ET.Element) -> str:
    return f"**{_get_all_text(child)}**"


def _inline_italic(child: ET.Element) -> str:
    return f"*{_get_all_text(child)}*"


def _inline_anchor(child: ET.Element) -> str:
    href = child.get("href", "")
    return f"[{_get_all_text(child)}]({href})"


def _inline_br(child: ET.Element) -> str:
    return "\n"


def _inline_todo_checked(child: ET.Element) -> str:
    return "- [x] "


def _inline_todo_unchecked(child: ET.Element) -> str:
    return "- [ ] "


def _inline_code(child: ET.Element) -> str:
    return f"`{_get_all_text(child)}`"


_INLINE_HANDLERS: dict[str, _InlineHandler] = {
    "b": _inline_bold,
    "strong": _inline_bold,
    "i": _inline_italic,
    "em": _inline_italic,
    "a": _inline_anchor,
    "br": _inline_br,
    "en-todo-checked": _inline_todo_checked,
    "en-todo-unchecked": _inline_todo_unchecked,
    "code": _inline_code,
}


# --- Core functions ---


def _walk(
    el: ET.Element,
    lines: list[str],
    context: _WalkContext,
) -> None:
    """Recursively walk ENML element tree and build markdown lines."""
    tag = _local_tag(el.tag)
    tail = el.tail or ""

    handler = _BLOCK_HANDLERS.get(tag)
    if handler:
        handler(el, lines, context)
    else:
        # Unknown block element — recurse
        text = el.text or ""
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
        tail = child.tail or ""

        handler = _INLINE_HANDLERS.get(tag)
        if handler:
            parts.append(handler(child))
        else:
            parts.append(_get_all_text(child))

        if tail:
            parts.append(tail)

    return "".join(parts)


# --- Helpers ---


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
