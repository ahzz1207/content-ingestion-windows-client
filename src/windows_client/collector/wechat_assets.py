from __future__ import annotations

import html
import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from windows_client.collector.base import CollectedArtifact

_IMG_TAG_PATTERN = re.compile(r"<img\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
_ATTR_PATTERN_TEMPLATE = r"""{attr}\s*=\s*["'](?P<value>.*?)["']"""
_IMAGE_ATTRS = ("data-src", "data-original", "src")
_MAX_DOWNLOADED_IMAGES = 12
_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_REQUEST_TIMEOUT_SECONDS = 15.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)


@dataclass(slots=True)
class _ImageRef:
    index: int
    url: str
    alt: str | None
    start: int
    end: int


def build_wechat_article_artifacts(
    html_text: str,
    *,
    base_url: str,
) -> tuple[str, tuple[CollectedArtifact, ...]]:
    refs = _extract_image_refs(html_text, base_url=base_url)
    if not refs:
        return html_text, ()

    annotated_html = _annotate_html(html_text, refs)
    manifest_entries: list[dict[str, object]] = []
    artifacts: list[CollectedArtifact] = []

    for ref in refs:
        entry: dict[str, object] = {
            "index": ref.index,
            "source_url": ref.url,
        }
        if ref.alt:
            entry["alt"] = ref.alt

        if ref.index > _MAX_DOWNLOADED_IMAGES:
            entry["status"] = "skipped_limit"
            manifest_entries.append(entry)
            continue

        downloaded = _download_image(ref.url, referer=base_url)
        entry.update(downloaded["manifest"])
        if downloaded["artifact"] is not None:
            artifacts.append(downloaded["artifact"])
        manifest_entries.append(entry)

    artifacts.append(
        CollectedArtifact(
            relative_path="attachments/derived/wechat_image_manifest.json",
            media_type="application/json",
            role="image_manifest",
            content=json.dumps(
                {
                    "manifest_version": 1,
                    "platform": "wechat",
                    "base_url": base_url,
                    "image_count": len(refs),
                    "downloaded_image_count": sum(
                        1 for entry in manifest_entries if entry.get("status") == "downloaded"
                    ),
                    "images": manifest_entries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            description="Downloaded WeChat article images and positional markers.",
        )
    )
    return annotated_html, tuple(artifacts)


def _extract_image_refs(html_text: str, *, base_url: str) -> list[_ImageRef]:
    refs: list[_ImageRef] = []
    seen_urls: set[str] = set()
    next_index = 1
    for match in _IMG_TAG_PATTERN.finditer(html_text):
        attrs = match.group("attrs") or ""
        raw_url = _first_attr(attrs, *_IMAGE_ATTRS)
        if raw_url is None:
            continue
        url = _normalize_url(raw_url, base_url=base_url)
        if url is None or url in seen_urls:
            continue
        seen_urls.add(url)
        refs.append(
            _ImageRef(
                index=next_index,
                url=url,
                alt=_first_attr(attrs, "alt"),
                start=match.start(),
                end=match.end(),
            )
        )
        next_index += 1
    return refs


def _first_attr(attrs: str, *names: str) -> str | None:
    for name in names:
        pattern = _ATTR_PATTERN_TEMPLATE.format(attr=re.escape(name))
        match = re.search(pattern, attrs, re.IGNORECASE | re.DOTALL)
        if match:
            value = html.unescape(match.group("value")).strip()
            if value:
                return value
    return None


def _normalize_url(value: str, *, base_url: str) -> str | None:
    if value.startswith("data:"):
        return None
    normalized = urljoin(base_url, value)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


def _annotate_html(html_text: str, refs: list[_ImageRef]) -> str:
    chunks: list[str] = []
    cursor = 0
    for ref in refs:
        chunks.append(html_text[cursor:ref.end])
        chunks.append(_marker_html(ref))
        cursor = ref.end
    chunks.append(html_text[cursor:])
    return "".join(chunks)


def _marker_html(ref: _ImageRef) -> str:
    marker = f"[WeChat image {ref.index}] {ref.url}"
    if ref.alt:
        marker += f" alt={ref.alt}"
    return f'<p data-wechat-image-ref="image-{ref.index:03d}">{html.escape(marker)}</p>'


def _download_image(url: str, *, referer: str) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "image/*,*/*;q=0.8",
            "Referer": referer,
        },
    )
    try:
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            media_type = response.info().get_content_type()
            if not media_type.startswith("image/"):
                return {
                    "artifact": None,
                    "manifest": {
                        "status": "skipped_non_image",
                        "media_type": media_type,
                    },
                }
            content = response.read(_MAX_IMAGE_BYTES + 1)
            if len(content) > _MAX_IMAGE_BYTES:
                return {
                    "artifact": None,
                    "manifest": {
                        "status": "skipped_too_large",
                        "media_type": media_type,
                    },
                }
    except (OSError, URLError):
        return {
            "artifact": None,
            "manifest": {
                "status": "download_failed",
            },
        }

    extension = _extension_for(media_type, url)
    relative_path = f"attachments/source/wechat-images/image-{_stable_slug(url)}{extension}"
    return {
        "artifact": CollectedArtifact(
            relative_path=relative_path,
            media_type=media_type,
            role="image_attachment",
            content=content,
            description="Downloaded WeChat article image.",
        ),
        "manifest": {
            "status": "downloaded",
            "media_type": media_type,
            "path": relative_path,
            "size_bytes": len(content),
        },
    }


def _extension_for(media_type: str, url: str) -> str:
    guessed = mimetypes.guess_extension(media_type, strict=False)
    if guessed:
        return guessed
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix:
        return suffix
    return ".bin"


def _stable_slug(url: str) -> str:
    parsed = urlparse(url)
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    candidate = Path(parsed.path).stem or "asset"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", candidate).strip("-")
    prefix = cleaned[:36] if cleaned else "asset"
    return f"{prefix}-{digest}"
