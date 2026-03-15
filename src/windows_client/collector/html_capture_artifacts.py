import json
import re
from html import unescape
from urllib.parse import urljoin

from windows_client.collector.base import CollectedArtifact
from windows_client.collector.html_metadata import HtmlMetadataHints


def build_html_capture_artifacts(
    *,
    source_url: str,
    final_url: str,
    raw_html: str,
    primary_html: str,
    platform: str,
    content_shape: str,
    primary_payload_role: str,
    hints: HtmlMetadataHints,
) -> tuple[CollectedArtifact, ...]:
    raw_visible_text = _extract_visible_text(raw_html)
    primary_visible_text = _extract_visible_text(primary_html)
    media_manifest = _build_media_manifest(raw_html=raw_html, primary_html=primary_html, base_url=final_url)
    validation = _build_capture_validation(
        source_url=source_url,
        final_url=final_url,
        raw_html=raw_html,
        primary_html=primary_html,
        raw_visible_text=raw_visible_text,
        primary_visible_text=primary_visible_text,
        media_manifest=media_manifest,
        platform=platform,
        content_shape=content_shape,
        primary_payload_role=primary_payload_role,
        hints=hints,
    )

    artifacts: list[CollectedArtifact] = [
        CollectedArtifact(
            relative_path="attachments/derived/primary_visible_text.txt",
            media_type="text/plain",
            role="visible_text",
            content=primary_visible_text,
            description="Visible text extracted from the primary payload.",
        ),
        CollectedArtifact(
            relative_path="attachments/derived/media_manifest.json",
            media_type="application/json",
            role="media_manifest",
            content=json.dumps(media_manifest, ensure_ascii=False, indent=2),
            description="Media references extracted from raw and primary HTML.",
        ),
        CollectedArtifact(
            relative_path="attachments/derived/capture_validation.json",
            media_type="application/json",
            role="capture_validation",
            content=json.dumps(validation, ensure_ascii=False, indent=2),
            description="Automatic checks that describe capture completeness and focus correctness.",
        ),
    ]
    if primary_payload_role == "focused_capture":
        artifacts.append(
            CollectedArtifact(
                relative_path="attachments/derived/raw_visible_text.txt",
                media_type="text/plain",
                role="visible_text",
                content=raw_visible_text,
                description="Visible text extracted from the original raw HTML capture.",
            )
        )
    return tuple(artifacts)


def _build_capture_validation(
    *,
    source_url: str,
    final_url: str,
    raw_html: str,
    primary_html: str,
    raw_visible_text: str,
    primary_visible_text: str,
    media_manifest: dict[str, object],
    platform: str,
    content_shape: str,
    primary_payload_role: str,
    hints: HtmlMetadataHints,
) -> dict[str, object]:
    checks: list[dict[str, str | int]] = []
    raw_chars = len(raw_visible_text)
    primary_chars = len(primary_visible_text)

    checks.append(_metric_check("raw_visible_text_non_empty", raw_chars, warn_below=80))
    checks.append(_metric_check("primary_visible_text_non_empty", primary_chars, warn_below=40))
    checks.append(_optional_presence_check("title_hint_present", hints.title_hint))

    if hints.title_hint:
        checks.append(_content_match_check("title_hint_in_primary_text", primary_visible_text, hints.title_hint))
    if hints.author_hint:
        checks.append(_content_match_check("author_hint_in_primary_text", primary_visible_text, hints.author_hint))
    elif platform in {"wechat", "bilibili"}:
        checks.append(_warn_check("author_hint_missing", "expected author/uploader hint was not extracted"))
    if hints.published_at_hint:
        checks.append(_content_match_check("published_at_hint_in_primary_text", primary_visible_text, hints.published_at_hint))
    elif platform == "wechat":
        checks.append(_warn_check("published_at_hint_missing", "expected published-at hint was not extracted"))

    if primary_payload_role == "focused_capture":
        if primary_chars > raw_chars and raw_chars > 0:
            checks.append(
                {
                    "name": "focused_payload_reduces_noise",
                    "status": "warn",
                    "details": f"primary visible text is longer than raw visible text ({primary_chars} > {raw_chars})",
                }
            )
        else:
            checks.append(
                {
                    "name": "focused_payload_reduces_noise",
                    "status": "pass",
                    "details": f"primary visible text chars={primary_chars}, raw visible text chars={raw_chars}",
                }
            )

    if primary_payload_role == "focused_capture":
        has_url_reference = "http://" in primary_html or "https://" in primary_html
        checks.append(
            {
                "name": "focused_primary_contains_url_reference",
                "status": "pass" if has_url_reference else "warn",
                "details": "found URL reference in focused payload" if has_url_reference else "focused payload has no explicit URL reference",
            }
        )

    if platform == "bilibili":
        checks.append(_content_match_check("bilibili_primary_has_uploader_section", primary_html, "Uploader"))
        checks.append(_content_match_check("bilibili_primary_has_description_section", primary_html, "Description"))
        video_url_ok = "/video/BV" in final_url or "/video/BV" in raw_html
        checks.append(
            {
                "name": "bilibili_video_identity_present",
                "status": "pass" if video_url_ok else "fail",
                "details": final_url if video_url_ok else "missing BV video identity in final URL and raw HTML",
            }
        )
    if platform == "wechat":
        checks.append(_metric_check("wechat_raw_body_substantial", raw_chars, warn_below=200))

    summary = _summarize_checks(checks)
    return {
        "validator_version": 1,
        "platform": platform,
        "content_shape": content_shape,
        "primary_payload_role": primary_payload_role,
        "source_url": source_url,
        "final_url": final_url,
        "title_hint": hints.title_hint,
        "author_hint": hints.author_hint,
        "published_at_hint": hints.published_at_hint,
        "metrics": {
            "raw_visible_text_chars": raw_chars,
            "primary_visible_text_chars": primary_chars,
            "raw_media_count": len(media_manifest["raw_media_urls"]),
            "primary_media_count": len(media_manifest["primary_media_urls"]),
        },
        "checks": checks,
        "summary": summary,
    }


def _build_media_manifest(*, raw_html: str, primary_html: str, base_url: str) -> dict[str, object]:
    return {
        "raw_media_urls": _extract_media_urls(raw_html, base_url=base_url),
        "primary_media_urls": _extract_media_urls(primary_html, base_url=base_url),
    }


def _extract_media_urls(html: str, *, base_url: str) -> list[str]:
    candidates: list[str] = []
    for pattern in (
        r"<img[^>]+(?:src|data-src)=[\"'](?P<value>.*?)[\"']",
        r"<video[^>]+src=[\"'](?P<value>.*?)[\"']",
        r"<source[^>]+src=[\"'](?P<value>.*?)[\"']",
        r"<audio[^>]+src=[\"'](?P<value>.*?)[\"']",
        r"<iframe[^>]+src=[\"'](?P<value>.*?)[\"']",
    ):
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            value = _normalize_text(match.group("value"))
            if value:
                candidates.append(urljoin(base_url, value))
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def _extract_visible_text(html: str) -> str:
    normalized = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    normalized = re.sub(r"</p>", "\n\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<script.*?</script>", "", normalized, flags=re.IGNORECASE | re.DOTALL)
    normalized = re.sub(r"<style.*?</style>", "", normalized, flags=re.IGNORECASE | re.DOTALL)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = unescape(normalized)
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _metric_check(name: str, value: int, *, warn_below: int) -> dict[str, str | int]:
    if value <= 0:
        return {"name": name, "status": "fail", "details": "0 characters extracted"}
    if value < warn_below:
        return {"name": name, "status": "warn", "details": f"{value} characters extracted"}
    return {"name": name, "status": "pass", "details": f"{value} characters extracted"}


def _optional_presence_check(name: str, value: str | None) -> dict[str, str]:
    if value:
        return {"name": name, "status": "pass", "details": value}
    return {"name": name, "status": "warn", "details": "value was not extracted"}


def _content_match_check(name: str, haystack: str, needle: str) -> dict[str, str]:
    if _contains_normalized(haystack, needle):
        return {"name": name, "status": "pass", "details": needle}
    return {"name": name, "status": "fail", "details": needle}


def _warn_check(name: str, details: str) -> dict[str, str]:
    return {"name": name, "status": "warn", "details": details}


def _contains_normalized(haystack: str, needle: str) -> bool:
    normalized_haystack = _normalize_text(haystack).lower()
    normalized_needle = _normalize_text(needle).lower()
    if not normalized_needle:
        return False
    return normalized_needle in normalized_haystack


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _summarize_checks(checks: list[dict[str, str | int]]) -> dict[str, int | str]:
    passed = sum(1 for check in checks if check["status"] == "pass")
    warned = sum(1 for check in checks if check["status"] == "warn")
    failed = sum(1 for check in checks if check["status"] == "fail")
    if failed:
        status = "fail"
    elif warned:
        status = "warn"
    else:
        status = "pass"
    return {
        "status": status,
        "passed": passed,
        "warned": warned,
        "failed": failed,
    }
