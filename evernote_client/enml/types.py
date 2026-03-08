"""Shared types for ENML <-> Markdown conversion."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResourceInfo:
    """Resource metadata passed into conversion (existing Evernote resources)."""

    hash_hex: str  # lowercase hex MD5
    mime_type: str = ""
    filename: str = ""


@dataclass
class Attachment:
    """New file attachment produced by markdown_to_enml."""

    hash_hex: str
    hash_bytes: bytes
    mime_type: str
    data: bytes
    filename: str = ""
    source_path: str = ""


@dataclass
class EnmlResult:
    """Return value of markdown_to_enml."""

    enml: str
    attachments: list[Attachment] = field(default_factory=list)
