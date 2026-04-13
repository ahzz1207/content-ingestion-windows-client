"""Detect and classify user input: URL, local file, pasted image, or plain text."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_SUPPORTED_PDF = frozenset({".pdf"})
_SUPPORTED_IMAGE = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
_SUPPORTED_TEXT = frozenset({".txt", ".md"})
_SUPPORTED_FILE = _SUPPORTED_PDF | _SUPPORTED_IMAGE | _SUPPORTED_TEXT

MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TEXT_BYTES = 10 * 1024 * 1024
MIN_TEXT_CHARS = 50


class LocalInputError(Exception):
    pass


@dataclass(slots=True)
class UrlPayload:
    url: str


@dataclass(slots=True)
class FilePayload:
    path: Path
    content_type: str


@dataclass(slots=True)
class ImagePayload:
    data: bytes
    suffix: str


@dataclass(slots=True)
class TextPayload:
    text: str


def route_text(text: str) -> UrlPayload | FilePayload | TextPayload:
    """Route a string (URL input / pasted text / file path) to the correct payload type."""
    stripped = text.strip()
    if _URL_RE.match(stripped):
        return UrlPayload(url=stripped)
    candidate = Path(stripped)
    if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in _SUPPORTED_FILE:
        return route_file(candidate)
    if len(stripped) < MIN_TEXT_CHARS:
        raise LocalInputError(f"Text too short (minimum {MIN_TEXT_CHARS} characters). Paste a URL or longer text.")
    return TextPayload(text=stripped)


def route_file(path: Path) -> FilePayload:
    """Validate and classify a file path."""
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_FILE:
        raise LocalInputError(
            f"Unsupported file type: {suffix}. Supported: PDF, images (.png .jpg .jpeg .webp .gif), .txt, .md"
        )
    if not path.exists():
        raise LocalInputError(f"File not found: {path}")
    if not path.is_file():
        raise LocalInputError(f"Not a file: {path}")
    size = path.stat().st_size
    if suffix in _SUPPORTED_PDF and size > MAX_PDF_BYTES:
        raise LocalInputError("PDF too large (max 50 MB)")
    if suffix in _SUPPORTED_IMAGE and size > MAX_IMAGE_BYTES:
        raise LocalInputError("Image too large (max 20 MB)")
    if suffix in _SUPPORTED_TEXT and size > MAX_TEXT_BYTES:
        raise LocalInputError("Text file too large (max 10 MB)")
    if suffix in _SUPPORTED_PDF:
        content_type = "pdf"
    elif suffix in _SUPPORTED_IMAGE:
        content_type = "image"
    else:
        content_type = "text"
    return FilePayload(path=path, content_type=content_type)


def route_clipboard_image(data: bytes) -> ImagePayload:
    """Wrap raw clipboard image bytes."""
    if len(data) > MAX_IMAGE_BYTES:
        raise LocalInputError("Pasted image too large (max 20 MB)")
    return ImagePayload(data=data, suffix=".png")
