from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _path_value(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


@dataclass(slots=True)
class IngestedJob:
    job_id: str
    status: str
    source_url: str
    content_type: str
    platform: str
    created_at: str | None = None
    job_dir: Path | None = None
    payload_path: Path | None = None
    metadata_path: Path | None = None
    ready_path: Path | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
            "source_url": self.source_url,
            "content_type": self.content_type,
            "platform": self.platform,
        }
        if self.created_at:
            data["created_at"] = self.created_at
        if self.job_dir:
            data["job_dir"] = _path_value(self.job_dir)
        if self.payload_path:
            data["payload_path"] = _path_value(self.payload_path)
        if self.metadata_path:
            data["metadata_path"] = _path_value(self.metadata_path)
        if self.ready_path:
            data["ready_path"] = _path_value(self.ready_path)
        return data


@dataclass(slots=True)
class JobRecord:
    job_id: str
    status: str
    source_url: str | None = None
    final_url: str | None = None
    platform: str | None = None
    content_type: str | None = None
    collection_mode: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    stage: str | None = None
    error: str | None = None
    job_dir: Path | None = None
    metadata_path: Path | None = None
    payload_path: Path | None = None
    result_dir: Path | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
        }
        optional_fields = {
            "source_url": self.source_url,
            "final_url": self.final_url,
            "platform": self.platform,
            "content_type": self.content_type,
            "collection_mode": self.collection_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stage": self.stage,
            "error": self.error,
            "job_dir": _path_value(self.job_dir),
            "metadata_path": _path_value(self.metadata_path),
            "payload_path": _path_value(self.payload_path),
            "result_dir": _path_value(self.result_dir),
        }
        for key, value in optional_fields.items():
            if value is not None:
                data[key] = value
        return data


@dataclass(slots=True)
class JobListResult:
    items: list[JobRecord] = field(default_factory=list)
    total: int = 0
    limit: int = 20
    statuses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "limit": self.limit,
            "statuses": list(self.statuses),
        }
