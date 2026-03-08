"""Markdown to ENML conversion."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import re
from collections.abc import Callable
from pathlib import Path

from evernote_client.enml.types import Attachment, EnmlResult, ResourceInfo

logger = logging.getLogger(__name__)

ENML_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
    "<en-note>"
)
ENML_FOOTER = "</en-note>"

# --- Compiled regex patterns ---

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_RE_HR = re.compile(r"^---+\s*$")
_RE_CHECKBOX = re.compile(r"^-\s+\[([ xX])\]\s+(.+)$")
_RE_UL_ITEM = re.compile(r"^[-*]\s+(.+)$")
_RE_UL_PREFIX = re.compile(r"^[-*]\s+")
_RE_OL_ITEM = re.compile(r"^\d+\.\s+(.+)$")
_RE_OL_PREFIX = re.compile(r"^\d+\.\s+")
_RE_CODE_FENCE_OPEN = re.compile(r"^```")
_RE_CODE_FENCE_CLOSE = re.compile(r"^```\s*$")
_RE_TABLE_ROW = re.compile(r"^\|.+\|")
_RE_TABLE_SEPARATOR = re.compile(r"^:?-+:?$")
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC = re.compile(r"\*(.+?)\*")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_INLINE_CODE = re.compile(r"`([^`]+)`")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_EVERNOTE_RESOURCE = re.compile(r"^evernote-resource:([0-9a-f]{32})$")


def markdown_to_enml(
    md: str,
    existing_resources: list[ResourceInfo] | None = None,
) -> EnmlResult:
    """Convert Markdown to valid ENML for note creation."""
    if not md:
        return EnmlResult(enml=f"{ENML_HEADER}{ENML_FOOTER}")

    existing_map: dict[str, ResourceInfo] = (
        {r.hash_hex: r for r in existing_resources} if existing_resources else {}
    )
    attachments: list[Attachment] = []
    seen_hashes: set[str] = set()

    lines = md.split("\n")
    enml_parts: list[str] = [ENML_HEADER]
    i = 0

    while i < len(lines):
        line = lines[i]

        for parser in _BLOCK_PARSERS:
            result, consumed = parser(lines, i, existing_map, attachments, seen_hashes)
            if result is not None:
                enml_parts.append(result)
                i += consumed
                break
        else:
            if line.strip():
                # Check if line is a standalone image
                img_result = _parse_image_line(
                    line, existing_map, attachments, seen_hashes
                )
                if img_result is not None:
                    enml_parts.append(img_result)
                else:
                    text = _escape_xml(line)
                    text = _inline_md_to_enml(
                        text, existing_map, attachments, seen_hashes
                    )
                    enml_parts.append(f"<div>{text}</div>")
            i += 1

    enml_parts.append(ENML_FOOTER)
    return EnmlResult(enml="".join(enml_parts), attachments=attachments)


# --- Image rendering ---


def _render_image(
    alt: str,
    url: str,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> str:
    """Render a Markdown image to ENML."""
    # evernote-resource:<hash> scheme
    m = _RE_EVERNOTE_RESOURCE.match(url)
    if m:
        hash_hex = m.group(1)
        info = existing_map.get(hash_hex)
        if info:
            return f'<en-media type="{info.mime_type}" hash="{hash_hex}"/>'
        # Unknown resource — fall back to link
        display = alt or hash_hex
        return f'<a href="evernote-resource:{hash_hex}">{_escape_xml(display)}</a>'

    # HTTP/HTTPS — render as link, not downloadable attachment
    if url.startswith("http://") or url.startswith("https://"):
        display = _escape_xml(alt or url)
        return f'<a href="{_escape_xml(url)}">{display}</a>'

    # Local file
    path = _resolve_local_path(url)
    if path is None or not path.exists():
        logger.warning("Image path not found: %s", url)
        display = _escape_xml(alt or url)
        return f'<a href="{_escape_xml(url)}">{display}</a>'

    try:
        data = path.read_bytes()
    except OSError as exc:
        logger.warning("Cannot read image file %s: %s", path, exc)
        display = _escape_xml(alt or url)
        return f'<a href="{_escape_xml(url)}">{display}</a>'

    hash_bytes = hashlib.md5(data).digest()
    hash_hex = hash_bytes.hex()
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"

    if hash_hex not in seen_hashes:
        seen_hashes.add(hash_hex)
        attachments.append(
            Attachment(
                hash_hex=hash_hex,
                hash_bytes=hash_bytes,
                mime_type=mime_type,
                data=data,
                filename=path.name,
                source_path=str(path),
            )
        )

    return f'<en-media type="{mime_type}" hash="{hash_hex}"/>'


def _resolve_local_path(url: str) -> Path | None:
    """Resolve a URL or path string to a Path, or return None."""
    if url.startswith("file://"):
        url = url[7:]
    try:
        return Path(url).expanduser()
    except Exception:
        return None


def _parse_image_line(
    line: str,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> str | None:
    """If the line is *only* a Markdown image, return ENML for it."""
    stripped = line.strip()
    m = _RE_IMAGE.fullmatch(stripped)
    if not m:
        return None
    alt, url = m.group(1), m.group(2)
    return _render_image(alt, url, existing_map, attachments, seen_hashes)


# --- Block parser infrastructure ---

_BlockParser = Callable[
    [list[str], int, dict[str, ResourceInfo], list[Attachment], set[str]],
    tuple[str | None, int],
]


def _single(
    fn: Callable[[str], str | None],
) -> _BlockParser:
    """Adapt a single-line parser (no resource state) to the full signature."""

    def wrapper(
        lines: list[str],
        i: int,
        existing_map: dict[str, ResourceInfo],
        attachments: list[Attachment],
        seen_hashes: set[str],
    ) -> tuple[str | None, int]:
        result = fn(lines[i])
        return (result, 1) if result is not None else (None, 0)

    return wrapper


def _single_inline(
    fn: Callable[
        [str, dict[str, ResourceInfo], list[Attachment], set[str]], str | None
    ],
) -> _BlockParser:
    """Adapt a single-line parser that receives resource state."""

    def wrapper(
        lines: list[str],
        i: int,
        existing_map: dict[str, ResourceInfo],
        attachments: list[Attachment],
        seen_hashes: set[str],
    ) -> tuple[str | None, int]:
        result = fn(lines[i], existing_map, attachments, seen_hashes)
        return (result, 1) if result is not None else (None, 0)

    return wrapper


# --- Block parsers ---


def _parse_heading(
    line: str,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> str | None:
    heading_match = _RE_HEADING.match(line)
    if not heading_match:
        return None
    level = len(heading_match.group(1))
    text = _escape_xml(heading_match.group(2))
    text = _inline_md_to_enml(text, existing_map, attachments, seen_hashes)
    return f"<h{level}>{text}</h{level}>"


def _parse_hr(line: str) -> str | None:
    if _RE_HR.match(line):
        return "<hr/>"
    return None


def _parse_checkbox(
    line: str,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> str | None:
    checkbox_match = _RE_CHECKBOX.match(line)
    if not checkbox_match:
        return None
    checked = checkbox_match.group(1).lower() == "x"
    text = _escape_xml(checkbox_match.group(2))
    text = _inline_md_to_enml(text, existing_map, attachments, seen_hashes)
    if checked:
        return f'<div><en-todo checked="true"/>{text}</div>'
    return f"<div><en-todo/>{text}</div>"


def _parse_list(
    tag: str,
    item_re: re.Pattern[str],
    prefix_re: re.Pattern[str],
    lines: list[str],
    i: int,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> tuple[str | None, int]:
    if not item_re.match(lines[i]):
        return None, 0
    items: list[str] = []
    start = i
    while i < len(lines) and prefix_re.match(lines[i]):
        m = item_re.match(lines[i])
        if m:
            items.append(_escape_xml(m.group(1)))
        i += 1
    parts = [f"<{tag}>"]
    for item in items:
        inner = _inline_md_to_enml(item, existing_map, attachments, seen_hashes)
        parts.append(f"<li>{inner}</li>")
    parts.append(f"</{tag}>")
    return "".join(parts), i - start


def _parse_ul(
    lines: list[str],
    i: int,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> tuple[str | None, int]:
    return _parse_list(
        "ul",
        _RE_UL_ITEM,
        _RE_UL_PREFIX,
        lines,
        i,
        existing_map,
        attachments,
        seen_hashes,
    )


def _parse_ol(
    lines: list[str],
    i: int,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> tuple[str | None, int]:
    return _parse_list(
        "ol",
        _RE_OL_ITEM,
        _RE_OL_PREFIX,
        lines,
        i,
        existing_map,
        attachments,
        seen_hashes,
    )


def _parse_code_block(
    lines: list[str],
    i: int,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> tuple[str | None, int]:
    if not _RE_CODE_FENCE_OPEN.match(lines[i]):
        return None, 0
    start = i
    i += 1
    content_lines: list[str] = []
    while i < len(lines):
        if _RE_CODE_FENCE_CLOSE.match(lines[i]):
            i += 1
            break
        content_lines.append(lines[i])
        i += 1
    content = _escape_xml("\n".join(content_lines))
    return f"<pre><code>{content}</code></pre>", i - start


def _parse_table(
    lines: list[str],
    i: int,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> tuple[str | None, int]:
    if not _RE_TABLE_ROW.match(lines[i]):
        return None, 0
    start = i
    rows: list[list[str]] = []
    while i < len(lines) and _RE_TABLE_ROW.match(lines[i]):
        line = lines[i].strip()
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Skip separator row
        if all(_RE_TABLE_SEPARATOR.match(c) for c in cells):
            i += 1
            continue
        rows.append(cells)
        i += 1
    if not rows:
        return None, 0
    parts = ["<table>"]
    for idx, row in enumerate(rows):
        tag = "th" if idx == 0 else "td"
        cell_parts: list[str] = []
        for c in row:
            inner = _inline_md_to_enml(
                _escape_xml(c), existing_map, attachments, seen_hashes
            )
            cell_parts.append(f"<{tag}>{inner}</{tag}>")
        cells_html = "".join(cell_parts)
        parts.append(f"<tr>{cells_html}</tr>")
    parts.append("</table>")
    return "".join(parts), i - start


_BLOCK_PARSERS: list[_BlockParser] = [
    _parse_code_block,
    _parse_table,
    _single_inline(_parse_heading),
    _single(_parse_hr),
    _single_inline(_parse_checkbox),
    _parse_ul,
    _parse_ol,
]


# --- Helpers ---


def _escape_xml(text: str) -> str:
    """Escape XML special characters.

    Note: this does not handle already-escaped entities — passing ``&amp;``
    will produce ``&amp;amp;``.  Callers are expected to provide raw text.
    """
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text.replace('"', "&quot;")


def _inline_md_to_enml(
    text: str,
    existing_map: dict[str, ResourceInfo],
    attachments: list[Attachment],
    seen_hashes: set[str],
) -> str:
    """Convert inline markdown formatting to ENML tags.

    Operates on already XML-escaped text, so we match escaped markers.
    Images (![alt](url)) are processed first.
    """

    # Images: ![alt](url) — must come before link processing
    def replace_image(m: re.Match[str]) -> str:
        alt = m.group(1)
        url = m.group(2)
        return _render_image(alt, url, existing_map, attachments, seen_hashes)

    text = _RE_IMAGE.sub(replace_image, text)
    # Bold: **text**
    text = _RE_BOLD.sub(r"<b>\1</b>", text)
    # Italic: *text*
    text = _RE_ITALIC.sub(r"<i>\1</i>", text)
    # Links: [text](url) — url is XML-escaped so ( and ) are literal
    text = _RE_LINK.sub(r'<a href="\2">\1</a>', text)
    # Inline code: `text`
    return _RE_INLINE_CODE.sub(r"<code>\1</code>", text)
