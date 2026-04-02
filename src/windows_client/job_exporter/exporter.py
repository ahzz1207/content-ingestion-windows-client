import json
import os
import secrets
import shutil
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from windows_client.app.errors import WindowsClientError
from windows_client.collector.base import CollectedArtifact, CollectedPayload
from windows_client.config.settings import Settings
from windows_client.job_exporter.models import ExportRequest, ExportResult, JobMetadata

SUPPORTED_CONTENT_TYPES = {"html", "txt", "md"}
CAPTURE_MANIFEST_FILENAME = "capture_manifest.json"
ATTACHMENTS_DIRNAME = "attachments"
CONTENT_TYPE_MEDIA_TYPES = {
    "html": "text/html",
    "txt": "text/plain",
    "md": "text/markdown",
}


class JobExporter:
    """Owns job id generation, metadata assembly, and file write ordering."""

    def __init__(self, *, settings: Settings) -> None:
        self.settings = settings

    def build_metadata(self, request: ExportRequest, payload: CollectedPayload, *, job_id: str) -> JobMetadata:
        return JobMetadata(
            job_id=job_id,
            source_url=request.source_url,
            final_url=payload.final_url,
            platform=payload.platform,
            collector="windows-client",
            collected_at=datetime.now().astimezone(),
            content_type=payload.content_type,
            requested_mode=request.requested_mode,
            video_download_mode=request.video_download_mode,
            collection_mode=request.collection_mode,
            browser_channel=request.browser_channel,
            profile_slug=request.profile_slug,
            wait_until=request.wait_until,
            wait_for_selector=request.wait_for_selector,
            wait_for_selector_state=request.wait_for_selector_state,
            title_hint=payload.title_hint,
            author_hint=payload.author_hint,
            published_at_hint=payload.published_at_hint,
            primary_payload_role=payload.primary_payload_role,
            content_shape=payload.content_shape,
            capture_manifest_filename=CAPTURE_MANIFEST_FILENAME,
        )

    def generate_job_id(self, shared_root: Path | None = None) -> str:
        resolved_root = shared_root or self.settings.effective_shared_inbox_root
        incoming_dir = resolved_root / "incoming"
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        while True:
            job_id = f"{timestamp}_{secrets.token_hex(3)}"
            if not (incoming_dir / job_id).exists():
                return job_id

    def export(self, request: ExportRequest, payload: CollectedPayload) -> ExportResult:
        self._validate_request(request, payload)

        shared_root = request.shared_root or self.settings.effective_shared_inbox_root
        incoming_dir = shared_root / "incoming"
        try:
            incoming_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise WindowsClientError(
                "job_export_failed",
                f"failed to prepare incoming job directory: {incoming_dir}",
                stage="job_export",
                details={"incoming_dir": str(incoming_dir)},
                cause=exc,
            ) from exc

        job_id = self.generate_job_id(shared_root)
        job_dir = incoming_dir / job_id
        try:
            job_dir.mkdir()
        except OSError as exc:
            raise WindowsClientError(
                "job_export_failed",
                f"failed to create job directory: {job_dir}",
                stage="job_export",
                details={"job_dir": str(job_dir), "job_id": job_id},
                cause=exc,
            ) from exc

        payload_path = job_dir / self._payload_filename(payload.content_type)
        capture_manifest_path = job_dir / CAPTURE_MANIFEST_FILENAME
        metadata = self.build_metadata(request, payload, job_id=job_id)
        metadata_path = job_dir / "metadata.json"
        ready_path = job_dir / "READY"

        try:
            self._write_text_file(payload_path, payload.payload_text)
            written_artifacts = self._write_artifacts(job_dir, payload.artifacts)
            self._write_text_file(
                capture_manifest_path,
                json.dumps(
                    self._build_capture_manifest(
                        metadata=metadata,
                        payload=payload,
                        payload_path=payload_path,
                        artifacts=written_artifacts,
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            self._write_text_file(
                metadata_path,
                json.dumps(self._metadata_to_dict(metadata), ensure_ascii=False, indent=2),
            )
            self._write_text_file(ready_path, "")
        except OSError as exc:
            raise WindowsClientError(
                "job_export_failed",
                f"failed to write exported job files: {job_dir}",
                stage="job_export",
                details={"job_dir": str(job_dir), "job_id": job_id},
                cause=exc,
            ) from exc

        attachments_dir = job_dir / ATTACHMENTS_DIRNAME
        return ExportResult(
            job_id=job_id,
            job_dir=job_dir,
            payload_path=payload_path,
            metadata_path=metadata_path,
            ready_path=ready_path,
            capture_manifest_path=capture_manifest_path,
            attachments_dir=attachments_dir if attachments_dir.exists() else None,
        )

    def _validate_request(self, request: ExportRequest, payload: CollectedPayload) -> None:
        parsed = urlparse(request.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WindowsClientError(
                "invalid_source_url",
                f"unsupported source_url: {request.source_url}",
                stage="job_export",
                details={"source_url": request.source_url},
            )
        if request.content_type not in SUPPORTED_CONTENT_TYPES:
            raise WindowsClientError(
                "unsupported_content_type",
                f"unsupported content_type: {request.content_type}",
                stage="job_export",
                details={"content_type": request.content_type},
            )
        if payload.content_type != request.content_type:
            raise WindowsClientError(
                "payload_content_type_mismatch",
                f"payload content_type does not match export request: {payload.content_type} != {request.content_type}",
                stage="job_export",
                details={
                    "request_content_type": request.content_type,
                    "payload_content_type": payload.content_type,
                },
            )
        if payload.source_url != request.source_url:
            raise WindowsClientError(
                "payload_source_url_mismatch",
                f"payload source_url does not match export request: {payload.source_url} != {request.source_url}",
                stage="job_export",
                details={
                    "request_source_url": request.source_url,
                    "payload_source_url": payload.source_url,
                },
            )

    def _payload_filename(self, content_type: str) -> str:
        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise WindowsClientError(
                "unsupported_content_type",
                f"unsupported content_type: {content_type}",
                stage="job_export",
                details={"content_type": content_type},
            )
        return f"payload.{content_type}"

    def _metadata_to_dict(self, metadata: JobMetadata) -> dict[str, object]:
        data: dict[str, object] = {
            "job_id": metadata.job_id,
            "source_url": metadata.source_url,
            "platform": metadata.platform,
            "collector": metadata.collector,
            "collected_at": metadata.collected_at.isoformat(),
            "content_type": metadata.content_type,
        }
        if metadata.final_url:
            data["final_url"] = metadata.final_url
        if metadata.collection_mode:
            data["collection_mode"] = metadata.collection_mode
        data["requested_mode"] = metadata.requested_mode
        if metadata.video_download_mode:
            data["video_download_mode"] = metadata.video_download_mode
        if metadata.browser_channel:
            data["browser_channel"] = metadata.browser_channel
        if metadata.profile_slug:
            data["profile_slug"] = metadata.profile_slug
        if metadata.wait_until:
            data["wait_until"] = metadata.wait_until
        if metadata.wait_for_selector:
            data["wait_for_selector"] = metadata.wait_for_selector
        if metadata.wait_for_selector_state:
            data["wait_for_selector_state"] = metadata.wait_for_selector_state
        if metadata.title_hint:
            data["title_hint"] = metadata.title_hint
        if metadata.author_hint:
            data["author_hint"] = metadata.author_hint
        if metadata.published_at_hint:
            data["published_at_hint"] = metadata.published_at_hint
        if metadata.primary_payload_role:
            data["primary_payload_role"] = metadata.primary_payload_role
        if metadata.content_shape:
            data["content_shape"] = metadata.content_shape
        if metadata.capture_manifest_filename:
            data["capture_manifest_filename"] = metadata.capture_manifest_filename
        return data

    def _build_capture_manifest(
        self,
        *,
        metadata: JobMetadata,
        payload: CollectedPayload,
        payload_path: Path,
        artifacts: list[dict[str, object]],
    ) -> dict[str, object]:
        primary_entry = {
            "path": payload_path.name,
            "role": payload.primary_payload_role,
            "media_type": CONTENT_TYPE_MEDIA_TYPES[payload.content_type],
            "content_type": payload.content_type,
            "size_bytes": len(payload.payload_text.encode("utf-8")),
            "is_primary": True,
        }
        return {
            "manifest_version": 1,
            "job_id": metadata.job_id,
            "source_url": metadata.source_url,
            "final_url": metadata.final_url,
            "platform": metadata.platform,
            "collection_mode": metadata.collection_mode,
            "video_download_mode": metadata.video_download_mode,
            "content_shape": payload.content_shape,
            "primary_payload": primary_entry,
            "artifacts": [primary_entry, *artifacts],
        }

    def _write_artifacts(self, job_dir: Path, artifacts: tuple[CollectedArtifact, ...]) -> list[dict[str, object]]:
        written: list[dict[str, object]] = []
        seen_paths: set[str] = set()
        for artifact in artifacts:
            artifact_path = self._resolve_artifact_path(job_dir, artifact.relative_path)
            relative_path = artifact_path.relative_to(job_dir).as_posix()
            if relative_path in seen_paths:
                raise WindowsClientError(
                    "duplicate_artifact_path",
                    f"duplicate artifact path: {relative_path}",
                    stage="job_export",
                    details={"relative_path": relative_path},
                )
            seen_paths.add(relative_path)
            if artifact.source_path is not None:
                shutil.copyfile(artifact.source_path, artifact_path)
                size_bytes = artifact.source_path.stat().st_size
            elif isinstance(artifact.content, bytes):
                self._write_binary_file(artifact_path, artifact.content)
                size_bytes = len(artifact.content)
            elif isinstance(artifact.content, str):
                self._write_text_file(artifact_path, artifact.content)
                size_bytes = len(artifact.content.encode("utf-8"))
            else:
                raise WindowsClientError(
                    "invalid_artifact_content",
                    f"artifact must provide content or source_path: {relative_path}",
                    stage="job_export",
                    details={"relative_path": relative_path},
                )
            entry = {
                "path": relative_path,
                "role": artifact.role,
                "media_type": artifact.media_type,
                "size_bytes": size_bytes,
                "is_primary": False,
            }
            if artifact.description:
                entry["description"] = artifact.description
            written.append(entry)
        return written

    def _resolve_artifact_path(self, job_dir: Path, relative_path: str) -> Path:
        normalized = PurePosixPath(relative_path)
        if normalized.is_absolute() or ".." in normalized.parts or not normalized.parts:
            raise WindowsClientError(
                "invalid_artifact_path",
                f"invalid artifact path: {relative_path}",
                stage="job_export",
                details={"relative_path": relative_path},
            )
        artifact_path = job_dir.joinpath(*normalized.parts)
        if artifact_path.name in {"READY", "metadata.json", CAPTURE_MANIFEST_FILENAME} or artifact_path == job_dir / self._payload_filename("html") or artifact_path == job_dir / self._payload_filename("txt") or artifact_path == job_dir / self._payload_filename("md"):
            raise WindowsClientError(
                "reserved_artifact_path",
                f"artifact path collides with reserved export files: {relative_path}",
                stage="job_export",
                details={"relative_path": relative_path},
            )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        return artifact_path

    def _write_text_file(self, path: Path, content: str) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass

    def _write_binary_file(self, path: Path, content: bytes) -> None:
        with path.open("wb") as handle:
            handle.write(content)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
