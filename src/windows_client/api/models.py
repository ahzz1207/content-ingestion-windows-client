from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


def _path_value(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {key: _serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


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
    title: str | None = None
    author: str | None = None
    published_at: str | None = None
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
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
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


@dataclass(slots=True)
class JobResultCard:
    job_id: str
    status: str
    updated_at: str | None = None
    analysis_state: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: str | None = None
    platform: str | None = None
    source_url: str | None = None
    canonical_url: str | None = None
    result_card: dict[str, Any] | None = None
    failure_card: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
        }
        optional_fields = {
            "updated_at": self.updated_at,
            "analysis_state": self.analysis_state,
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "platform": self.platform,
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "result_card": self.result_card,
            "failure_card": self.failure_card,
        }
        for key, value in optional_fields.items():
            if value is not None:
                data[key] = _serialize_value(value)
        return data


@dataclass(slots=True)
class JobResultCardListResult:
    items: list[JobResultCard] = field(default_factory=list)
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


@dataclass(slots=True)
class JobResultDetail:
    job_id: str
    status: str
    analysis_state: str | None = None
    updated_at: str | None = None
    source_url: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: str | None = None
    platform: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)
    normalized_markdown: str | None = None
    structured_result: dict[str, Any] = field(default_factory=dict)
    insight_brief: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] | None = None
    warnings: list[Any] = field(default_factory=list)
    available_artifacts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
        }
        optional_fields = {
            "analysis_state": self.analysis_state,
            "updated_at": self.updated_at,
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "author": self.author,
            "published_at": self.published_at,
            "platform": self.platform,
            "source_metadata": self.source_metadata,
            "normalized_markdown": self.normalized_markdown,
            "structured_result": self.structured_result,
            "insight_brief": self.insight_brief,
            "coverage": self.coverage,
            "warnings": self.warnings,
            "available_artifacts": self.available_artifacts,
            "error": self.error,
        }
        for key, value in optional_fields.items():
            if value is None:
                continue
            if key in {"structured_result", "insight_brief", "source_metadata", "warnings", "available_artifacts"}:
                data[key] = _serialize_value(value)
                continue
            data[key] = _serialize_value(value)
        return data
