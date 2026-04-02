from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from windows_client.api.models import (
    IngestedJob,
    JobListResult,
    JobRecord,
    JobResultCard,
    JobResultCardListResult,
    JobResultDetail,
)
from windows_client.app.coverage_stats import CoverageStats
from windows_client.app.insight_brief import InsightBriefV2, ViewpointItem
from windows_client.app.result_workspace import ResultWorkspaceEntry, load_job_result
from windows_client.app.service import WindowsClientService

STATUS_TO_DIR = {
    "queued": "incoming",
    "processing": "processing",
    "completed": "processed",
    "failed": "failed",
    "archived": "archived",
}

_DEFAULT_LIST_STATUSES = ["queued", "processing", "completed", "failed"]

RESULT_STATE_TO_STATUS = {
    "pending": "queued",
    "processing": "processing",
    "processed": "completed",
    "failed": "failed",
    "archived": "archived",
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
        requested_mode: str = "auto",
    ) -> IngestedJob:
        resolved_video_download_mode = video_download_mode if video_download_mode is not None else "audio"
        result = self.service.export_url_job(
            url=url,
            shared_root=self.shared_inbox_root,
            content_type=content_type,
            platform=platform,
            requested_mode=requested_mode,
            video_download_mode=resolved_video_download_mode,
        )
        metadata = self._read_json(result.metadata_path)
        return IngestedJob(
            job_id=result.job_id,
            status="queued",
            source_url=str(metadata.get("source_url") or url),
            content_type=str(metadata.get("content_type") or content_type or "html"),
            platform=str(metadata.get("platform") or platform or "generic"),
            requested_mode=self._coerce_text(metadata.get("requested_mode")) or "auto",
            created_at=self._coerce_text(metadata.get("collected_at")),
            job_dir=result.job_dir,
            payload_path=result.payload_path,
            metadata_path=result.metadata_path,
            ready_path=result.ready_path,
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        for status in ("queued", "processing", "completed", "failed", "archived"):
            job_dir = self.shared_inbox_root / STATUS_TO_DIR[status] / job_id
            if job_dir.exists() and job_dir.is_dir():
                return self._load_job_record(job_dir=job_dir, status=status)
        return None

    def archive_job(self, job_id: str) -> JobRecord | None:
        record = self.get_job(job_id)
        if record is None or record.job_dir is None:
            return None
        if record.status == "archived":
            return record
        archive_root = self.shared_inbox_root / "archived"
        archive_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(record.job_dir), str(archive_root / job_id))
        return record

    def list_jobs(self, *, statuses: list[str] | None = None, limit: int = 20) -> JobListResult:
        resolved_statuses = statuses or _DEFAULT_LIST_STATUSES
        records = self._list_job_records(statuses=resolved_statuses)
        return JobListResult(
            items=records[:limit],
            total=len(records),
            limit=limit,
            statuses=resolved_statuses,
        )

    def list_result_cards(self, *, statuses: list[str] | None = None, limit: int = 20) -> JobResultCardListResult:
        resolved_statuses = statuses or _DEFAULT_LIST_STATUSES
        records = self._list_job_records(statuses=resolved_statuses)
        cards = [self._build_result_card(record) for record in records]
        return JobResultCardListResult(
            items=cards[:limit],
            total=len(cards),
            limit=limit,
            statuses=resolved_statuses,
        )

    def get_job_result(self, job_id: str) -> JobResultDetail | None:
        entry, incomplete_result = self._load_result_entry(job_id)
        if entry is None:
            if incomplete_result:
                record = self.get_job(job_id)
                if record is None:
                    return None
                return JobResultDetail(
                    job_id=record.job_id,
                    status="processing",
                    analysis_state="processing",
                    updated_at=record.updated_at,
                    source_url=record.source_url,
                    canonical_url=record.final_url,
                    title=record.title,
                    author=record.author,
                    published_at=record.published_at,
                    platform=record.platform,
                    source_metadata={"status": "processing"},
                )
            return None
        return self._build_job_result_detail(entry)

    def _list_job_records(self, *, statuses: list[str]) -> list[JobRecord]:
        records: list[JobRecord] = []
        for status in statuses:
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
        return records

    def _load_job_record(self, *, job_dir: Path, status: str) -> JobRecord:
        metadata_path = job_dir / "metadata.json"
        metadata = self._read_json(metadata_path)
        payload_path = self._find_payload_path(job_dir)
        updated_at = self._timestamp_to_iso(job_dir.stat().st_mtime)
        created_at = self._coerce_text(metadata.get("collected_at")) or self._timestamp_to_iso(job_dir.stat().st_ctime)
        title = self._coerce_text(metadata.get("title")) or self._coerce_text(metadata.get("title_hint"))
        author = self._coerce_text(metadata.get("author")) or self._coerce_text(metadata.get("author_hint"))
        published_at = self._coerce_text(metadata.get("published_at")) or self._coerce_text(metadata.get("published_at_hint"))
        return JobRecord(
            job_id=job_dir.name,
            status=status,
            source_url=self._coerce_text(metadata.get("source_url")),
            final_url=self._coerce_text(metadata.get("final_url")),
            title=title,
            author=author,
            published_at=published_at,
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
            result_dir=job_dir if status in {"completed", "failed", "archived"} else None,
        )

    def _build_result_card(self, record: JobRecord) -> JobResultCard:
        entry, incomplete_result = self._load_result_entry(record.job_id)
        status = "processing" if incomplete_result and record.status == "completed" else record.status
        analysis_state = entry.analysis_state if entry is not None else self._default_analysis_state(status)
        title = self._pick_text(entry.title if entry else None, record.title, record.job_id)
        author = self._pick_text(entry.author if entry else None, record.author)
        published_at = self._pick_text(entry.published_at if entry else None, record.published_at)
        platform = self._pick_text(entry.platform if entry else None, record.platform)
        source_url = self._pick_text(entry.source_url if entry else None, record.source_url)
        canonical_url = self._pick_text(entry.canonical_url if entry else None, record.final_url, source_url)

        result_card: dict[str, Any] | None = None
        failure_card: dict[str, Any] | None = None
        if status == "completed" and entry is not None:
            result_card = self._build_completed_result_card(entry)
        elif status == "archived" and entry is not None:
            if entry.details.get("structured_result"):
                result_card = self._build_completed_result_card(entry)
            else:
                detailed_error = self._entry_error_text(entry)
                summary = detailed_error or entry.summary or record.error or "Archived."
                failure_card = {"summary": summary, "error": detailed_error or record.error or summary}
        elif status == "failed":
            detailed_error = self._entry_error_text(entry)
            summary = detailed_error or (entry.summary if entry is not None else None) or record.error or "Processing failed."
            failure_card = {
                "summary": summary,
                "error": detailed_error or record.error or summary,
            }

        return JobResultCard(
            job_id=record.job_id,
            status=status,
            updated_at=record.updated_at,
            analysis_state=analysis_state,
            title=title,
            author=author,
            published_at=published_at,
            platform=platform,
            source_url=source_url,
            canonical_url=canonical_url,
            result_card=result_card,
            failure_card=failure_card,
        )

    def _load_result_entry(self, job_id: str) -> tuple[ResultWorkspaceEntry | None, bool]:
        try:
            return load_job_result(self.shared_inbox_root, job_id), False
        except FileNotFoundError:
            return None, True

    def _build_job_result_detail(self, entry: ResultWorkspaceEntry) -> JobResultDetail:
        status = RESULT_STATE_TO_STATUS.get(entry.state, entry.state)
        metadata = self._source_metadata(entry)
        normalized_markdown = self._read_text(entry.normalized_md_path)
        structured_result = self._coerce_dict(entry.details.get("structured_result"))
        warnings = self._collect_warnings(entry)

        return JobResultDetail(
            job_id=entry.job_id,
            status=status,
            analysis_state=entry.analysis_state,
            updated_at=self._timestamp_to_iso(entry.updated_at),
            source_url=entry.source_url,
            canonical_url=entry.canonical_url,
            title=entry.title,
            author=entry.author,
            published_at=entry.published_at,
            platform=entry.platform,
            source_metadata=metadata,
            normalized_markdown=normalized_markdown,
            structured_result=structured_result,
            insight_brief=self._serialize_insight_brief(entry.details.get("insight_brief")),
            coverage=self._serialize_coverage(entry.coverage),
            warnings=warnings,
            available_artifacts=self._available_artifacts(entry),
            error=self._entry_error_text(entry) if entry.state in {"failed", "archived"} else None,
        )

    def _build_completed_result_card(self, entry: ResultWorkspaceEntry) -> dict[str, Any]:
        brief = entry.details.get("insight_brief")
        structured_result = self._coerce_dict(entry.details.get("structured_result"))
        summary_payload = self._coerce_dict(structured_result.get("summary"))
        quick_takeaways = self._quick_takeaways(brief, structured_result)
        headline = self._pick_text(
            self._brief_attr(brief, "hero", "title"),
            self._coerce_text(summary_payload.get("headline")),
            entry.title,
            entry.job_id,
        )
        one_sentence_take = self._pick_text(
            self._brief_attr(brief, "hero", "one_sentence_take"),
            self._coerce_text(summary_payload.get("short_text")),
            entry.summary,
        )
        conclusion = self._pick_text(
            self._coerce_text(getattr(brief, "synthesis_conclusion", None)) if brief is not None else None,
            entry.summary,
        )
        warnings = self._collect_warnings(entry)
        return {
            "headline": headline,
            "one_sentence_take": one_sentence_take,
            "quick_takeaways": quick_takeaways,
            "conclusion": conclusion,
            "verification_signal": self._derive_verification_signal(structured_result),
            "warning_count": len(warnings),
            "coverage_warning": self._coverage_warning(entry),
        }

    def _source_metadata(self, entry: ResultWorkspaceEntry) -> dict[str, Any]:
        details_metadata = self._coerce_dict(entry.details.get("metadata"))
        normalized = self._coerce_dict(entry.details.get("normalized"))
        normalized_metadata = self._coerce_dict(normalized.get("metadata"))
        asset = self._coerce_dict(normalized.get("asset"))
        handoff = self._coerce_dict(normalized_metadata.get("handoff"))

        metadata = {
            "content_type": self._pick_text(
                self._coerce_text(normalized.get("content_type")),
                self._coerce_text(details_metadata.get("content_type")),
            ),
            "collection_mode": self._pick_text(
                self._coerce_text(details_metadata.get("collection_mode")),
                self._coerce_text(handoff.get("collection_mode")),
            ),
            "content_shape": self._pick_text(
                self._coerce_text(asset.get("content_shape")),
                self._coerce_text(details_metadata.get("content_shape")),
                self._coerce_text(handoff.get("content_shape")),
            ),
            "captured_at": self._pick_text(
                self._coerce_text(details_metadata.get("collected_at")),
                self._coerce_text(handoff.get("collected_at")),
            ),
            "final_url": self._pick_text(
                self._coerce_text(details_metadata.get("final_url")),
                entry.canonical_url,
            ),
            "status": RESULT_STATE_TO_STATUS.get(entry.state, entry.state),
        }
        return {key: value for key, value in metadata.items() if value is not None}

    def _available_artifacts(self, entry: ResultWorkspaceEntry) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        for kind, path, description in (
            ("metadata", entry.metadata_path, "Job metadata"),
            ("normalized_markdown", entry.normalized_md_path, "Normalized markdown"),
            ("normalized_json", entry.normalized_json_path, "Normalized structured output"),
            ("analysis_json", entry.analysis_json_path, "Analysis JSON output"),
            ("insight_card", self._coerce_path(entry.details.get("insight_card_path")), "Rendered visual summary card"),
            ("status", entry.status_path, "Processor status"),
            ("error", entry.error_path, "Failure details"),
        ):
            if path is None or not path.exists():
                continue
            self._append_artifact(
                artifacts,
                seen_paths,
                {
                    "kind": kind,
                    "path": str(path),
                    "description": description,
                },
            )

        normalized = self._coerce_dict(entry.details.get("normalized"))
        normalized_metadata = self._coerce_dict(normalized.get("metadata"))
        capture = self._coerce_dict(normalized_metadata.get("capture"))
        capture_manifest_path = entry.job_dir / "capture_manifest.json" if entry.job_dir is not None else None
        capture_manifest = self._read_json(capture_manifest_path) if capture_manifest_path is not None else {}
        if capture_manifest_path is not None and capture_manifest_path.exists():
            self._append_artifact(
                artifacts,
                seen_paths,
                {
                    "kind": "capture_manifest",
                    "path": str(capture_manifest_path),
                    "description": "Capture manifest",
                },
            )
        raw_artifacts = capture.get("artifacts")
        if not isinstance(raw_artifacts, list):
            raw_artifacts = capture_manifest.get("artifacts")
        self._extend_capture_artifacts(artifacts, seen_paths, entry.job_dir, raw_artifacts)
        return artifacts

    def _extend_capture_artifacts(
        self,
        artifacts: list[dict[str, Any]],
        seen_paths: set[str],
        job_dir: Path | None,
        raw_artifacts: object,
    ) -> None:
        if not isinstance(raw_artifacts, list) or job_dir is None:
            return
        for artifact in raw_artifacts:
            if not isinstance(artifact, dict):
                continue
            relative_path = self._coerce_text(artifact.get("path"))
            if not relative_path:
                continue
            candidate = job_dir / relative_path
            self._append_artifact(
                artifacts,
                seen_paths,
                {
                    "kind": self._coerce_text(artifact.get("role")) or "capture_artifact",
                    "path": str(candidate),
                    "description": self._coerce_text(artifact.get("description")),
                    "media_type": self._coerce_text(artifact.get("media_type")),
                },
            )

    def _append_artifact(
        self,
        artifacts: list[dict[str, Any]],
        seen_paths: set[str],
        artifact: dict[str, Any],
    ) -> None:
        path = self._coerce_text(artifact.get("path"))
        if not path or path in seen_paths:
            return
        seen_paths.add(path)
        artifacts.append(artifact)

    def _collect_warnings(self, entry: ResultWorkspaceEntry) -> list[Any]:
        warnings: list[Any] = []
        structured_result = self._coerce_dict(entry.details.get("structured_result"))
        structured_warnings = structured_result.get("warnings")
        if isinstance(structured_warnings, list):
            warnings.extend(structured_warnings)

        llm_processing = self._coerce_dict(entry.details.get("llm_processing"))
        llm_warnings = llm_processing.get("warnings")
        if isinstance(llm_warnings, list):
            warnings.extend(llm_warnings)

        normalized = self._coerce_dict(entry.details.get("normalized"))
        normalized_metadata = self._coerce_dict(normalized.get("metadata"))
        media_processing = self._coerce_dict(normalized_metadata.get("media_processing"))
        media_warnings = media_processing.get("warnings")
        if isinstance(media_warnings, list):
            warnings.extend(media_warnings)
        return warnings

    def _entry_error_text(self, entry: ResultWorkspaceEntry | None) -> str | None:
        if entry is None or entry.state not in {"failed", "archived"}:
            return None
        error_payload = self._coerce_dict(entry.details.get("error"))
        for key in ("message", "error", "detail", "error_message"):
            value = self._coerce_text(error_payload.get(key))
            if value:
                return value
        return self._coerce_text(entry.summary)

    def _quick_takeaways(self, brief: object, structured_result: dict[str, Any]) -> list[str]:
        if isinstance(brief, InsightBriefV2):
            return [item for item in brief.quick_takeaways[:3] if item]
        key_points = structured_result.get("key_points")
        takeaways: list[str] = []
        if isinstance(key_points, list):
            for item in key_points:
                if not isinstance(item, dict):
                    continue
                title = self._coerce_text(item.get("title"))
                if title:
                    takeaways.append(title)
                if len(takeaways) >= 3:
                    break
        return takeaways

    def _derive_verification_signal(self, structured_result: dict[str, Any]) -> str:
        verification_items = structured_result.get("verification_items")
        if not isinstance(verification_items, list) or not verification_items:
            return "unavailable"
        statuses: list[str] = []
        for item in verification_items:
            if not isinstance(item, dict):
                continue
            status = (self._coerce_text(item.get("status")) or "").strip().lower()
            if status:
                statuses.append(status)
        if not statuses:
            return "unavailable"
        unique = set(statuses)
        if unique == {"supported"}:
            return "supported"
        if "supported" in unique and len(unique) > 1:
            return "mixed"
        if unique & {"unsupported", "failed"}:
            return "warning"
        if unique == {"unclear"}:
            return "unclear"
        return "mixed"

    def _coverage_warning(self, entry: ResultWorkspaceEntry) -> str | None:
        coverage = entry.coverage
        if coverage is None or not coverage.input_truncated:
            return None
        pct = int(round(coverage.coverage_ratio * 100))
        return f"Only {pct}% of source segments were analysed."

    def _serialize_insight_brief(self, brief: object) -> dict[str, Any]:
        if not isinstance(brief, InsightBriefV2):
            return {}
        return {
            "hero": {
                "title": brief.hero.title,
                "one_sentence_take": brief.hero.one_sentence_take,
                "content_kind": brief.hero.content_kind,
                "author_stance": brief.hero.author_stance,
            },
            "quick_takeaways": list(brief.quick_takeaways),
            "viewpoints": [self._serialize_viewpoint(item) for item in brief.viewpoints],
            "coverage": self._serialize_coverage(brief.coverage),
            "gaps": list(brief.gaps),
            "synthesis_conclusion": brief.synthesis_conclusion,
        }

    def _serialize_viewpoint(self, item: ViewpointItem) -> dict[str, Any]:
        return {
            "statement": item.statement,
            "kind": item.kind,
            "why_it_matters": item.why_it_matters,
            "support_level": item.support_level,
            "evidence_refs": [
                {
                    "segment_id": evidence.segment_id,
                    "text": evidence.text,
                    "start_ms": evidence.start_ms,
                    "end_ms": evidence.end_ms,
                    "kind": evidence.kind,
                }
                for evidence in item.evidence_refs
            ],
        }

    def _serialize_coverage(self, coverage: CoverageStats | None) -> dict[str, Any] | None:
        if coverage is None:
            return None
        return {
            "total_segments": coverage.total_segments,
            "used_segments": coverage.used_segments,
            "total_duration_ms": coverage.total_duration_ms,
            "used_duration_ms": coverage.used_duration_ms,
            "coverage_ratio": coverage.coverage_ratio,
            "input_truncated": coverage.input_truncated,
        }

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
        for key in ("message", "error", "detail", "error_message"):
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

    def _read_text(self, path: Path | None) -> str | None:
        if path is None or not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _coerce_path(self, value: object) -> Path | None:
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value.strip():
            return Path(value)
        return None

    def _coerce_dict(self, value: object) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    def _coerce_text(self, value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _pick_text(self, *values: str | None) -> str | None:
        for value in values:
            if value is not None and str(value).strip():
                return str(value)
        return None

    def _brief_attr(self, brief: object, *path: str) -> str | None:
        current = brief
        for name in path:
            current = getattr(current, name, None)
            if current is None:
                return None
        return self._coerce_text(current)

    def _default_analysis_state(self, status: str) -> str:
        return {
            "queued": "pending",
            "processing": "processing",
            "completed": "ready",
            "failed": "failed",
        }.get(status, "pending")

    def _timestamp_to_iso(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()
