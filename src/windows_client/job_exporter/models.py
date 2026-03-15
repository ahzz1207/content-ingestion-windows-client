from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ExportRequest:
    source_url: str
    shared_root: Path | None = None
    content_type: str = "html"
    platform: str = "generic"
    video_download_mode: str | None = None
    collection_mode: str | None = None
    browser_channel: str | None = None
    profile_slug: str | None = None
    wait_until: str | None = None
    wait_for_selector: str | None = None
    wait_for_selector_state: str | None = None


@dataclass(slots=True)
class JobMetadata:
    job_id: str
    source_url: str
    final_url: str | None
    platform: str
    collector: str
    collected_at: datetime
    content_type: str
    video_download_mode: str | None = None
    collection_mode: str | None = None
    browser_channel: str | None = None
    profile_slug: str | None = None
    wait_until: str | None = None
    wait_for_selector: str | None = None
    wait_for_selector_state: str | None = None
    title_hint: str | None = None
    author_hint: str | None = None
    published_at_hint: str | None = None
    primary_payload_role: str | None = None
    content_shape: str | None = None
    capture_manifest_filename: str | None = None


@dataclass(slots=True)
class ExportResult:
    job_id: str
    job_dir: Path
    payload_path: Path
    metadata_path: Path
    ready_path: Path
    capture_manifest_path: Path | None = None
    attachments_dir: Path | None = None
