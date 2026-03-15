from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class CollectedArtifact:
    relative_path: str
    media_type: str
    role: str
    content: str | bytes | None = None
    description: str | None = None
    source_path: Path | None = None


@dataclass(slots=True)
class CollectedPayload:
    source_url: str
    content_type: str
    payload_text: str
    final_url: str | None = None
    platform: str = "generic"
    title_hint: str | None = None
    author_hint: str | None = None
    published_at_hint: str | None = None
    primary_payload_role: str = "raw_capture"
    content_shape: str = "document"
    artifacts: tuple[CollectedArtifact, ...] = field(default_factory=tuple)


def infer_content_shape(*, content_type: str, platform: str) -> str:
    if platform in {"bilibili", "youtube"}:
        return "video"
    if platform == "wechat":
        return "article"
    if content_type == "html":
        return "webpage"
    if content_type == "md":
        return "markdown"
    return "plaintext"


class Collector(Protocol):
    def collect(self, url: str, *, content_type: str, platform: str) -> CollectedPayload:
        """Collect raw content for export."""
