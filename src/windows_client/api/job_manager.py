from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from windows_client.app.service import WindowsClientService
from windows_client.api.models import IngestedJob, JobListResult, JobRecord

STATUS_TO_DIR = {
    "queued": "incoming",
    "processing": "processing",
    "completed": "processed",
    "failed": "failed",
}


class JobManager:
    def __init__(self, *, service: WindowsClientService, shared_inbox_root: Path) -> None:
        self.service = service
        self.shared_inbox_root = shared_inbox_root

    def submit_url(
        self,
        *,
        url: str,
        content_type: str | None = None,
        platform: str | None = None,
        video_download_mode: str | None = None,
    ) -> IngestedJob:
        result = self.service.export_url_job(
            url=url,
            shared_root=self.shared_inbox_root,
            content_type=content_type,
            platform=platform,
            video_download_mode=video_download_mode,
        )
        metadata = self._read_json(result.metadata_path)
        return IngestedJob(
            job_id=result.job_id,
            status="queued",
            source_url=str(metadata.get("source_url") or url),
            content_type=str(metadata.get("content_type") or content_type or "html"),
            platform=str(metadata.get("platform") or platform or "generic"),
            created_at=self._coerce_text(metadata.get("collected_at")),
            job_dir=result.job_dir,
            payload_path=result.payload_path,
            metadata_path=result.metadata_path,
            ready_path=result.ready_path,
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        for status in ("queued", "processing", "completed", "failed"):
            job_dir = self.shared_inbox_root / STATUS_TO_DIR[status] / job_id
            if job_dir.exists() and job_dir.is_dir():
                return self._load_job_record(job_dir=job_dir, status=status)
        return None

    def list_jobs(self, *, statuses: list[str] | None = None, limit: int = 20) -> JobListResult:
        resolved_statuses = statuses or ["queued", "processing", "completed", "failed"]
        records: list[JobRecord] = []
        for status in resolved_statuses:
            dirname = STATUS_TO_DIR.get(status)
            if not dirname:
                continue
            status_root = self.shared_inbox_root / dirname
            if not status_root.exists():
                continue
            for job_dir in status_root.iterdir():
                if job_dir.is_dir():
                    records.append(self._load_job_record(job_dir=job_dir, status=status))

        records.sort(key=lambda item: item.updated_at or "", reverse=True)
        return JobListResult(
            items=records[:limit],
            total=len(records),
            limit=limit,
            statuses=resolved_statuses,
        )

    def _load_job_record(self, *, job_dir: Path, status: str) -> JobRecord:
        metadata_path = job_dir / "metadata.json"
        metadata = self._read_json(metadata_path)
        payload_path = self._find_payload_path(job_dir)
        updated_at = self._timestamp_to_iso(job_dir.stat().st_mtime)
        created_at = self._coerce_text(metadata.get("collected_at")) or self._timestamp_to_iso(job_dir.stat().st_ctime)
        return JobRecord(
            job_id=job_dir.name,
            status=status,
            source_url=self._coerce_text(metadata.get("source_url")),
            final_url=self._coerce_text(metadata.get("final_url")),
            platform=self._coerce_text(metadata.get("platform")),
            content_type=self._coerce_text(metadata.get("content_type")),
            collection_mode=self._coerce_text(metadata.get("collection_mode")),
            created_at=created_at,
            updated_at=updated_at,
            stage=self._infer_stage(job_dir=job_dir, status=status),
            error=self._load_error(job_dir=job_dir, status=status),
            job_dir=job_dir,
            metadata_path=metadata_path if metadata_path.exists() else None,
            payload_path=payload_path,
            result_dir=job_dir if status in {"completed", "failed"} else None,
        )

    def _find_payload_path(self, job_dir: Path) -> Path | None:
        for suffix in ("html", "txt", "md"):
            path = job_dir / f"payload.{suffix}"
            if path.exists():
                return path
        return None

    def _infer_stage(self, *, job_dir: Path, status: str) -> str | None:
        if status == "queued":
            return "queued"
        if status == "processing":
            status_path = job_dir / "status.json"
            if status_path.exists():
                payload = self._read_json(status_path)
                stage = self._coerce_text(payload.get("stage"))
                if stage:
                    return stage
            return "processing"
        if status == "completed":
            return "completed"
        if status == "failed":
            return "failed"
        return None

    def _load_error(self, *, job_dir: Path, status: str) -> str | None:
        if status != "failed":
            return None
        error_path = job_dir / "error.json"
        if not error_path.exists():
            return None
        payload = self._read_json(error_path)
        for key in ("message", "error", "detail"):
            value = self._coerce_text(payload.get(key))
            if value:
                return value
        return None

    def _read_json(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _coerce_text(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _timestamp_to_iso(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()
