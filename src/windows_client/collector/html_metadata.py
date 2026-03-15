import html
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

_HEAD_SCAN_LIMIT = 200_000
_ELEMENT_SCAN_LIMIT = 4_000


@dataclass(slots=True)
class HtmlMetadataHints:
    platform: str = "generic"
    title_hint: str | None = None
    author_hint: str | None = None
    published_at_hint: str | None = None


def detect_platform(url: str, payload_text: str = "") -> str:
    host = urlparse(url).netloc.lower()
    if "mp.weixin.qq.com" in host:
        return "wechat"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    lowered = payload_text[:_HEAD_SCAN_LIMIT].lower()
    if "wechat-enable-text-zoom-em" in lowered or ('id="activity-name"' in payload_text and 'id="js_name"' in payload_text):
        return "wechat"
    if "window.__initial_state__" in lowered or "哔哩哔哩" in payload_text[:_HEAD_SCAN_LIMIT]:
        return "bilibili"
    if "ytinitialdata" in lowered or "ytinitialplayerresponse" in lowered:
        return "youtube"
    return "generic"


def extract_html_metadata(url: str, payload_text: str) -> HtmlMetadataHints:
    platform = detect_platform(url, payload_text)
    title_hint = _first_non_empty(
        _extract_element_text(payload_text, "activity-name"),
        _extract_meta_content(payload_text, "og:title"),
        _extract_meta_content(payload_text, "twitter:title"),
        _extract_meta_content(payload_text, "title"),
        _extract_title(payload_text),
    )
    author_hint = _first_non_empty(
        _extract_element_text(payload_text, "js_name"),
        _extract_meta_content(payload_text, "author"),
        _extract_meta_content(payload_text, "og:article:author"),
        _extract_meta_content(payload_text, "og:video:actor"),
        _extract_meta_content(payload_text, "channelid"),
    )
    published_at_hint = _first_non_empty(
        _extract_element_text(payload_text, "publish_time"),
        _extract_meta_content(payload_text, "article:published_time"),
        _extract_meta_content(payload_text, "og:article:published_time"),
        _extract_meta_content(payload_text, "datepublished"),
    )
    return HtmlMetadataHints(
        platform=platform,
        title_hint=title_hint,
        author_hint=author_hint,
        published_at_hint=published_at_hint,
    )


def focus_platform_payload(url: str, payload_text: str, hints: HtmlMetadataHints) -> str:
    if hints.platform == "bilibili":
        return _build_bilibili_video_payload(url, payload_text, hints)
    return payload_text


def build_video_summary_payload(
    *,
    url: str,
    platform: str,
    title: str,
    author: str,
    description: str,
    published_at: str | None = None,
) -> str:
    canonical_url = url
    embed_url = _bilibili_embed_url(canonical_url) if platform == "bilibili" else None
    author_heading = "Uploader" if platform == "bilibili" else "Author"

    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{html.escape(title)}</title>",
        "</head>",
        "<body>",
        f'  <article data-platform="{html.escape(platform)}" data-scope="video-summary">',
        f"    <h1>{html.escape(title)}</h1>",
    ]
    if embed_url is not None:
        parts.extend(
            [
                '    <section>',
                "      <h2>Video</h2>",
                f'      <iframe src="{html.escape(embed_url)}" title="{html.escape(title)}" loading="lazy"></iframe>',
                "    </section>",
            ]
        )
    parts.extend(
        [
            '    <section>',
            "      <h2>Source</h2>",
            f'      <p><a href="{html.escape(canonical_url)}">{html.escape(canonical_url)}</a></p>',
            "    </section>",
            '    <section>',
            f"      <h2>{author_heading}</h2>",
            f"      <p>{html.escape(author)}</p>",
            "    </section>",
        ]
    )
    if published_at:
        parts.extend(
            [
                '    <section>',
                "      <h2>Published At</h2>",
                f"      <p>{html.escape(published_at)}</p>",
                "    </section>",
            ]
        )
    parts.extend(
        [
            '    <section>',
            "      <h2>Description</h2>",
            f"      <p>{html.escape(description)}</p>",
            "    </section>",
        ]
    )
    parts.extend(["  </article>", "</body>", "</html>"])
    return "\n".join(parts)


def _build_bilibili_video_payload(url: str, payload_text: str, hints: HtmlMetadataHints) -> str:
    canonical_url = _first_non_empty(
        _extract_link_href(payload_text, "canonical"),
        _extract_meta_content(payload_text, "og:url"),
        _extract_meta_content(payload_text, "twitter:url"),
        _extract_meta_content(payload_text, "url"),
        url,
    ) or url
    title = hints.title_hint or _extract_title(payload_text) or "Bilibili video"
    uploader = hints.author_hint or "Unknown uploader"
    description = _extract_bilibili_description(payload_text) or "No concise description was found on the page."
    return build_video_summary_payload(
        url=canonical_url,
        platform="bilibili",
        title=title,
        author=uploader,
        description=description,
        published_at=hints.published_at_hint,
    )


def _extract_title(payload_text: str) -> str | None:
    head = payload_text[:_HEAD_SCAN_LIMIT]
    match = re.search(r"<title[^>]*>(.*?)</title>", head, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _clean_text(match.group(1))


def _extract_element_text(payload_text: str, element_id: str) -> str | None:
    markers = (f'id="{element_id}"', f"id='{element_id}'")
    index = -1
    for marker in markers:
        index = payload_text.find(marker)
        if index != -1:
            break
    if index == -1:
        return None

    start = payload_text.rfind("<", max(0, index - 200), index)
    if start == -1:
        return None
    snippet = payload_text[start : start + _ELEMENT_SCAN_LIMIT]
    match = re.search(
        rf'<[^>]+id=["\']{re.escape(element_id)}["\'][^>]*>(.*?)</[^>]+>',
        snippet,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return _clean_text(match.group(1))


def _extract_meta_content(payload_text: str, name: str) -> str | None:
    head = payload_text[:_HEAD_SCAN_LIMIT]
    index = 0
    lowered_name = name.lower()
    while True:
        meta_start = head.find("<meta", index)
        if meta_start == -1:
            return None
        meta_end = head.find(">", meta_start)
        if meta_end == -1:
            return None
        tag = head[meta_start : meta_end + 1]
        tag_lower = tag.lower()
        if lowered_name in tag_lower:
            attr_name = _extract_attr(tag, "name")
            attr_property = _extract_attr(tag, "property")
            attr_itemprop = _extract_attr(tag, "itemprop")
            if (
                (attr_name and attr_name.lower() == lowered_name)
                or (attr_property and attr_property.lower() == lowered_name)
                or (attr_itemprop and attr_itemprop.lower() == lowered_name)
            ):
                content = _extract_attr(tag, "content")
                cleaned = _clean_text(content or "")
                if cleaned:
                    return cleaned
        index = meta_end + 1


def _extract_link_href(payload_text: str, rel: str) -> str | None:
    head = payload_text[:_HEAD_SCAN_LIMIT]
    index = 0
    lowered_rel = rel.lower()
    while True:
        link_start = head.find("<link", index)
        if link_start == -1:
            return None
        link_end = head.find(">", link_start)
        if link_end == -1:
            return None
        tag = head[link_start : link_end + 1]
        rel_value = _extract_attr(tag, "rel")
        if rel_value and rel_value.lower() == lowered_rel:
            href = _extract_attr(tag, "href")
            cleaned = _clean_text(href or "")
            if cleaned:
                return cleaned
        index = link_end + 1


def _extract_attr(tag: str, attr_name: str) -> str | None:
    match = re.search(rf'{re.escape(attr_name)}\s*=\s*["\'](.*?)["\']', tag, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(1)


def _extract_bilibili_description(payload_text: str) -> str | None:
    description = _extract_meta_content(payload_text, "description")
    if not description:
        return None
    for marker in ("视频播放量", "作者简介", "相关推荐"):
        position = description.find(marker)
        if position != -1:
            description = description[:position]
            break
    cleaned = _clean_text(description)
    if cleaned is None:
        return None
    return cleaned.rstrip(" ")


def _bilibili_embed_url(url: str) -> str | None:
    match = re.search(r"/video/(BV[0-9A-Za-z]+)", url)
    if not match:
        return None
    return f"https://player.bilibili.com/player.html?bvid={match.group(1)}&page=1"


def _clean_text(value: str) -> str | None:
    cleaned = re.sub(r"<[^>]+>", "", value)
    cleaned = unescape(cleaned)
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n+", " ", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None
