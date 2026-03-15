import gzip
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from windows_client.app.errors import WindowsClientError
from windows_client.collector.base import CollectedArtifact, CollectedPayload, infer_content_shape
from windows_client.collector.html_capture_artifacts import build_html_capture_artifacts
from windows_client.collector.html_metadata import detect_platform, extract_html_metadata, focus_platform_payload


class HttpCollector:
    """Fetches simple web pages using the Python standard library."""

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def collect(self, url: str, *, content_type: str | None, platform: str) -> CollectedPayload:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WindowsClientError(
                "invalid_source_url",
                f"unsupported source_url: {url}",
                stage="http_collect",
                details={"source_url": url},
            )

        request = Request(
            url,
            headers={
                "User-Agent": "content-ingestion-windows-client/0.1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
                content_encoding = (response.headers.get("Content-Encoding") or "").lower().strip()
                final_url = response.geturl()
                header_content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
        except HTTPError as exc:
            raise WindowsClientError(
                "http_status_error",
                f"http request failed with status {exc.code}: {url}",
                stage="http_collect",
                details={"source_url": url, "status_code": exc.code},
                cause=exc,
            ) from exc
        except URLError as exc:
            raise WindowsClientError(
                "http_request_failed",
                f"http request failed: {url}",
                stage="http_collect",
                details={"source_url": url, "reason": str(exc.reason)},
                cause=exc,
            ) from exc

        raw_bytes = self._decode_response_bytes(raw_bytes, content_encoding=content_encoding)
        raw_payload_text = raw_bytes.decode(charset, errors="replace")
        payload_text = raw_payload_text
        resolved_content_type = content_type or self._infer_content_type(url, header_content_type)

        title_hint = None
        author_hint = None
        published_at_hint = None
        primary_payload_role = "raw_capture"
        artifacts: list[CollectedArtifact] = []
        resolved_platform = platform
        if resolved_content_type == "html":
            hints = extract_html_metadata(url, raw_payload_text)
            title_hint = hints.title_hint
            author_hint = hints.author_hint
            published_at_hint = hints.published_at_hint
            if platform == "generic":
                resolved_platform = hints.platform
            focused_payload_text = focus_platform_payload(final_url or url, raw_payload_text, hints)
            if focused_payload_text != raw_payload_text:
                artifacts.append(
                    CollectedArtifact(
                        relative_path="attachments/source/raw.html",
                        media_type="text/html",
                        role="raw_capture",
                        content=raw_payload_text,
                        description="Original HTML before platform-specific focusing.",
                    )
                )
                payload_text = focused_payload_text
                primary_payload_role = "focused_capture"
            content_shape = infer_content_shape(content_type=resolved_content_type, platform=resolved_platform)
            artifacts.extend(
                build_html_capture_artifacts(
                    source_url=url,
                    final_url=final_url or url,
                    raw_html=raw_payload_text,
                    primary_html=payload_text,
                    platform=resolved_platform,
                    content_shape=content_shape,
                    primary_payload_role=primary_payload_role,
                    hints=hints,
                )
            )
        elif platform == "generic":
            resolved_platform = detect_platform(url, payload_text)
        content_shape = infer_content_shape(content_type=resolved_content_type, platform=resolved_platform)

        return CollectedPayload(
            source_url=url,
            content_type=resolved_content_type,
            payload_text=payload_text,
            final_url=final_url,
            platform=resolved_platform,
            title_hint=title_hint,
            author_hint=author_hint,
            published_at_hint=published_at_hint,
            primary_payload_role=primary_payload_role,
            content_shape=content_shape,
            artifacts=tuple(artifacts),
        )

    def _infer_content_type(self, url: str, header_content_type: str) -> str:
        if header_content_type in {"text/html", "application/xhtml+xml"}:
            return "html"
        if header_content_type in {"text/plain"}:
            return "txt"
        if header_content_type in {"text/markdown", "text/x-markdown"}:
            return "md"
        if url.lower().endswith(".md"):
            return "md"
        return "html"

    def _decode_response_bytes(self, raw_bytes: bytes, *, content_encoding: str) -> bytes:
        if not raw_bytes:
            return raw_bytes
        if content_encoding in {"gzip", "x-gzip"} or raw_bytes.startswith(b"\x1f\x8b"):
            return gzip.decompress(raw_bytes)
        if content_encoding == "deflate":
            try:
                return zlib.decompress(raw_bytes)
            except zlib.error:
                return zlib.decompress(raw_bytes, -zlib.MAX_WBITS)
        return raw_bytes
