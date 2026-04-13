"""Package a local file / pasted text / pasted image into a shared-inbox job."""
from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from windows_client.app.input_router import FilePayload, ImagePayload, TextPayload


def submit_local(
    payload: FilePayload | ImagePayload | TextPayload,
    shared_root: Path,
    requested_mode: str = "auto",
) -> str:
    """Write payload + metadata into shared_root/incoming/<job_id>/ and touch READY."""
    job_id = _generate_job_id()
    job_dir = shared_root / "incoming" / job_id
    job_dir.mkdir(parents=True)
    source_url, content_type, content_shape = _write_payload(job_dir, payload, job_id)
    _write_metadata(job_dir, job_id, source_url, content_type, content_shape, requested_mode)
    (job_dir / "READY").touch()
    return job_id


def _generate_job_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(3)


def _write_payload(
    job_dir: Path,
    payload: FilePayload | ImagePayload | TextPayload,
    job_id: str,
) -> tuple[str, str, str]:
    """Copy/write payload file. Returns (source_url, content_type, content_shape)."""
    if isinstance(payload, FilePayload):
        suffix = payload.path.suffix.lower()
        dest = job_dir / f"payload{suffix}"
        shutil.copy2(payload.path, dest)
        source_url = payload.path.as_uri()
        content_shape = "image" if payload.content_type == "image" else "document"
        return source_url, payload.content_type, content_shape

    if isinstance(payload, ImagePayload):
        dest = job_dir / f"payload{payload.suffix}"
        dest.write_bytes(payload.data)
        return f"local://image/{job_id}", "image", "image"

    dest = job_dir / "payload.txt"
    dest.write_text(payload.text, encoding="utf-8")
    return f"local://text/{job_id}", "text", "document"


def _write_metadata(
    job_dir: Path,
    job_id: str,
    source_url: str,
    content_type: str,
    content_shape: str,
    requested_mode: str,
) -> None:
    metadata = {
        "job_id": job_id,
        "source_url": source_url,
        "platform": "local",
        "collector": "windows-client-local",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "content_type": content_type,
        "content_shape": content_shape,
        "requested_mode": requested_mode,
    }
    (job_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
