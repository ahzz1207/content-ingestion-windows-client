import json
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from windows_client.app.errors import WindowsClientError
from windows_client.app.result_workspace import ResultWorkspaceEntry, load_job_result
from windows_client import __version__
from windows_client.collector.base import CollectedArtifact, Collector
from windows_client.collector.browser import BrowserCollectOptions, BrowserLoginOptions
from windows_client.collector.html_capture_artifacts import build_html_capture_artifacts
from windows_client.collector.html_metadata import HtmlMetadataHints, build_video_summary_payload, detect_platform
from windows_client.collector.wechat_assets import build_wechat_article_artifacts
from windows_client.config.settings import Settings
from windows_client.job_exporter.exporter import JobExporter
from windows_client.job_exporter.models import ExportRequest, ExportResult
from windows_client.video_downloader import YtDlpVideoDownloader


@dataclass(slots=True)
class ReinterpretRequest:
    job_id: str
    reading_goal: str
    domain_template: str


class WindowsClientService:
    """Thin application service for CLI and future GUI wrappers."""

    def __init__(
        self,
        *,
        settings: Settings,
        mock_collector: Collector,
        url_collector: Collector,
        browser_collector,
        exporter: JobExporter,
        video_downloader: YtDlpVideoDownloader | None = None,
    ) -> None:
        self.settings = settings
        self.mock_collector = mock_collector
        self.url_collector = url_collector
        self.browser_collector = browser_collector
        self.exporter = exporter
        self.video_downloader = video_downloader

    def doctor(self) -> Iterable[str]:
        shared_root = self.settings.effective_shared_inbox_root
        yield f"project_root={self.settings.project_root}"
        yield f"python_executable={sys.executable}"
        yield f"windows_client_version={__version__}"
        yield f"shared_inbox_root={shared_root}"
        yield f"shared_inbox_exists={shared_root.exists()}"
        yield f"default_content_type={self.settings.default_content_type}"
        yield f"default_platform={self.settings.default_platform}"
        yield f"browser_profiles_dir={self.settings.browser_profiles_dir}"
        yield f"browser_default_headless={self.settings.browser_headless}"
        yield f"browser_default_wait_until={self.settings.browser_wait_until}"
        yield f"browser_default_timeout_ms={self.settings.browser_timeout_ms}"
        yield f"browser_default_settle_ms={self.settings.browser_settle_ms}"
        yield f"browser_collector_available={self.browser_collector.is_available()}"
        yield f"browser_collector_reason={self.browser_collector.availability_reason()}"
        yield f"video_downloader_available={self.video_downloader.is_available() if self.video_downloader else False}"
        yield f"video_downloader_reason={self.video_downloader.availability_reason() if self.video_downloader else 'not_configured'}"
        yield f"ffmpeg_available={self.video_downloader.ffmpeg_available() if self.video_downloader else False}"
        yield f"video_js_runtime={(self.video_downloader.js_runtime() if self.video_downloader else None) or 'none'}"
        yield f"wsl_llm_credentials_available={self.settings.llm_credentials_available}"
        yield f"wsl_llm_provider_hint={self.settings.llm_provider_hint}"
        yield f"wsl_analysis_model_override={self.settings.analysis_model_override or 'default'}"
        yield f"wsl_multimodal_model_override={self.settings.multimodal_model_override or 'default'}"
        yield f"wsl_whisper_model_override={self.settings.whisper_model_override or 'default'}"

    def export_mock_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        content_type: str | None = None,
        platform: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ExportResult:
        resolved_content_type = content_type or self.settings.default_content_type
        resolved_platform = platform or self.settings.default_platform
        resolved_shared_root = shared_root or self.settings.effective_shared_inbox_root

        self._emit_progress(on_progress, "collecting")
        payload = self.mock_collector.collect(url, content_type=resolved_content_type, platform=resolved_platform)
        request = ExportRequest(
            source_url=url,
            shared_root=resolved_shared_root,
            content_type=resolved_content_type,
            platform=resolved_platform,
            collection_mode="mock",
        )
        self._emit_progress(on_progress, "exporting")
        return self.exporter.export(request, payload)

    def export_url_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        content_type: str | None = None,
        platform: str | None = None,
        requested_mode: str = "auto",
        video_download_mode: str | None = "audio",
        on_progress: Callable[[str], None] | None = None,
    ) -> ExportResult:
        resolved_platform = platform or self.settings.default_platform
        resolved_shared_root = shared_root or self.settings.effective_shared_inbox_root

        self._emit_progress(on_progress, "collecting")
        payload = self.url_collector.collect(url, content_type=content_type, platform=resolved_platform)
        payload = self._attach_wechat_images(payload, url=url)
        payload, cleanup_dir = self._attach_video_download(
            payload,
            url=url,
            on_progress=on_progress,
            profile_dir=None,
            video_download_mode=video_download_mode,
        )
        request = ExportRequest(
            source_url=url,
            shared_root=resolved_shared_root,
            content_type=payload.content_type,
            platform=resolved_platform,
            requested_mode=requested_mode,
            video_download_mode=video_download_mode if payload.content_shape == "video" else None,
            collection_mode="http",
        )
        try:
            self._emit_progress(on_progress, "exporting")
            return self.exporter.export(request, payload)
        finally:
            self._cleanup_video_download(cleanup_dir)

    def export_browser_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        platform: str | None = None,
        requested_mode: str = "auto",
        video_download_mode: str | None = "audio",
        profile_dir: Path | None = None,
        browser_channel: str | None = None,
        headless: bool | None = None,
        wait_until: str | None = None,
        timeout_ms: int | None = None,
        settle_ms: int | None = None,
        wait_for_selector: str | None = None,
        wait_for_selector_state: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ExportResult:
        resolved_platform = platform or self.settings.default_platform
        resolved_shared_root = shared_root or self.settings.effective_shared_inbox_root
        resolved_profile_dir = profile_dir or self._default_browser_profile_dir(url, platform=resolved_platform)
        options = BrowserCollectOptions(
            headless=self.settings.browser_headless if headless is None else headless,
            wait_until=wait_until or self.settings.browser_wait_until,
            timeout_ms=timeout_ms or self.settings.browser_timeout_ms,
            settle_ms=self.settings.browser_settle_ms if settle_ms is None else settle_ms,
            profile_dir=resolved_profile_dir,
            browser_channel=browser_channel,
            wait_for_selector=wait_for_selector,
            wait_for_selector_state=wait_for_selector_state or "visible",
        )

        self._emit_progress(on_progress, "checking_runtime")
        self._emit_progress(on_progress, "collecting")
        payload = self.browser_collector.collect(
            url,
            content_type="html",
            platform=resolved_platform,
            options=options,
        )
        payload = self._attach_wechat_images(payload, url=url)
        payload, cleanup_dir = self._attach_video_download(
            payload,
            url=url,
            on_progress=on_progress,
            profile_dir=resolved_profile_dir,
            video_download_mode=video_download_mode,
        )
        request = ExportRequest(
            source_url=url,
            shared_root=resolved_shared_root,
            content_type=payload.content_type,
            platform=resolved_platform,
            requested_mode=requested_mode,
            video_download_mode=video_download_mode if payload.content_shape == "video" else None,
            collection_mode="browser",
            browser_channel=browser_channel,
            profile_slug=self._profile_slug(resolved_profile_dir),
            wait_until=options.wait_until,
            wait_for_selector=options.wait_for_selector,
            wait_for_selector_state=options.wait_for_selector_state if options.wait_for_selector else None,
        )
        try:
            self._emit_progress(on_progress, "exporting")
            return self.exporter.export(request, payload)
        finally:
            self._cleanup_video_download(cleanup_dir)

    def browser_login(
        self,
        *,
        start_url: str | None = None,
        profile_dir: Path | None = None,
        browser_channel: str | None = None,
        wait_until: str | None = None,
        timeout_ms: int | None = None,
        completion_waiter: Callable[[], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> Path:
        resolved_start_url = start_url or "https://mp.weixin.qq.com/"
        resolved_profile_dir = profile_dir or (
            self.settings.browser_profiles_dir / self.browser_collector.default_profile_slug(resolved_start_url)
        )
        options = BrowserLoginOptions(
            profile_dir=resolved_profile_dir,
            start_url=resolved_start_url,
            wait_until=wait_until or "domcontentloaded",
            timeout_ms=timeout_ms or self.settings.browser_timeout_ms,
            browser_channel=browser_channel,
        )
        self._emit_progress(on_progress, "opening_browser")
        self._emit_progress(on_progress, "waiting_for_login")
        return self.browser_collector.open_profile_session(options, completion_waiter=completion_waiter)

    def reinterpret_result(
        self,
        request: ReinterpretRequest,
        *,
        shared_root: Path | None = None,
    ) -> ResultWorkspaceEntry:
        resolved_shared_root = shared_root or self.settings.effective_shared_inbox_root
        processed_root = resolved_shared_root / "processed"
        base_job_id = self._reinterpretation_base_job_id(request.job_id)
        base_dir = processed_root / base_job_id
        if not base_dir.exists():
            raise WindowsClientError(
                "reinterpretation_source_missing",
                f"processed result not found: {base_job_id}",
                stage="reinterpretation",
                details={"job_id": request.job_id, "base_job_id": base_job_id},
            )

        source_dir = self._reinterpretation_source_dir(processed_root, request.job_id)
        target_job_id = self._next_reinterpret_job_id(processed_root, base_job_id)
        target_dir = processed_root / target_job_id
        reinterpretation_metadata = {
            "status": "local_clone",
            "source_job_id": base_job_id,
            "source_version_job_id": source_dir.name,
            "requested_reading_goal": request.reading_goal,
            "requested_domain_template": request.domain_template,
        }

        try:
            shutil.copytree(source_dir, target_dir)
            copied_active_version = target_dir / "active_version.json"
            if copied_active_version.exists():
                copied_active_version.unlink()
            self._rewrite_reinterpreted_payloads(
                target_dir,
                target_job_id=target_job_id,
                reinterpretation_metadata=reinterpretation_metadata,
            )
            self._write_active_version(
                base_dir,
                processed_root=processed_root,
                active_job_id=target_job_id,
            )
        except OSError as exc:
            raise WindowsClientError(
                "reinterpretation_failed",
                f"failed to create reinterpretation for {base_job_id}",
                stage="reinterpretation",
                details={"job_id": request.job_id, "target_job_id": target_job_id},
                cause=exc,
            ) from exc

        entry = load_job_result(resolved_shared_root, target_job_id)
        if entry is None:
            raise WindowsClientError(
                "reinterpretation_failed",
                f"reinterpretation result could not be loaded: {target_job_id}",
                stage="reinterpretation",
                details={"job_id": request.job_id, "target_job_id": target_job_id},
            )
        return entry

    def _default_browser_profile_dir(self, url: str, *, platform: str) -> Path | None:
        detected_platform = detect_platform(url)
        if detected_platform != "generic":
            slug = self.browser_collector.default_profile_slug(url)
            return self.settings.browser_profiles_dir / slug
        if platform != "generic":
            slug = re.sub(r"[^a-z0-9]+", "-", platform.lower()).strip("-") or "default"
            return self.settings.browser_profiles_dir / slug
        return None

    def _profile_slug(self, profile_dir: Path | None) -> str | None:
        if profile_dir is None:
            return None
        return profile_dir.name

    def _reinterpretation_base_job_id(self, job_id: str) -> str:
        marker = "--reinterpret-"
        if marker in job_id:
            return job_id.split(marker, 1)[0]
        return job_id

    def _active_processed_source_dir(self, processed_root: Path, base_job_id: str) -> Path:
        base_dir = processed_root / base_job_id
        active_version_path = base_dir / "active_version.json"
        if not active_version_path.exists():
            return base_dir
        try:
            active_job_id = str(json.loads(active_version_path.read_text(encoding="utf-8")).get("active_job_id") or "").strip()
        except Exception:
            return base_dir
        if not active_job_id:
            return base_dir
        active_dir = processed_root / active_job_id
        if active_dir.exists():
            return active_dir
        return base_dir

    def _reinterpretation_source_dir(self, processed_root: Path, requested_job_id: str) -> Path:
        requested_dir = processed_root / requested_job_id
        if requested_dir.exists():
            return requested_dir
        base_job_id = self._reinterpretation_base_job_id(requested_job_id)
        return self._active_processed_source_dir(processed_root, base_job_id)

    def _next_reinterpret_job_id(self, processed_root: Path, base_job_id: str) -> str:
        counter = 1
        while True:
            candidate = f"{base_job_id}--reinterpret-{counter:02d}"
            if not (processed_root / candidate).exists():
                return candidate
            counter += 1

    def _rewrite_reinterpreted_payloads(
        self,
        target_dir: Path,
        *,
        target_job_id: str,
        reinterpretation_metadata: dict[str, str],
    ) -> None:
        normalized_path = target_dir / "normalized.json"
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        normalized["job_id"] = target_job_id
        metadata = normalized.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            normalized["metadata"] = metadata
        self._apply_reinterpretation_metadata(metadata, reinterpretation_metadata)

        asset = normalized.get("asset")
        if isinstance(asset, dict):
            asset_metadata = asset.get("metadata")
            if not isinstance(asset_metadata, dict):
                asset_metadata = {}
                asset["metadata"] = asset_metadata
            self._apply_reinterpretation_metadata(asset_metadata, reinterpretation_metadata)
        normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

        metadata_path = target_dir / "metadata.json"
        if metadata_path.exists():
            metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata_payload["job_id"] = target_job_id
            metadata_payload["requested_mode"] = reinterpretation_metadata["requested_reading_goal"]
            metadata_payload["domain_template"] = reinterpretation_metadata["requested_domain_template"]
            metadata_payload["reinterpretation"] = dict(reinterpretation_metadata)
            metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        capture_manifest_path = target_dir / "capture_manifest.json"
        if capture_manifest_path.exists():
            capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))
            if isinstance(capture_manifest, dict):
                capture_manifest["job_id"] = target_job_id
                capture_manifest_path.write_text(json.dumps(capture_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def _apply_reinterpretation_metadata(
        self,
        metadata: dict[str, object],
        reinterpretation_metadata: dict[str, str],
    ) -> None:
        metadata["reinterpretation"] = dict(reinterpretation_metadata)

    def _write_active_version(
        self,
        base_dir: Path,
        *,
        processed_root: Path,
        active_job_id: str,
    ) -> None:
        active_version_path = base_dir / "active_version.json"
        version_ids = [base_dir.name]
        if active_version_path.exists():
            try:
                existing = json.loads(active_version_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            raw_version_ids = existing.get("version_ids")
            if isinstance(raw_version_ids, list):
                version_ids = [str(version_id) for version_id in raw_version_ids if str(version_id).strip()]
                if base_dir.name not in version_ids:
                    version_ids.insert(0, base_dir.name)
        if active_job_id not in version_ids:
            version_ids.append(active_job_id)
        version_ids = [version_id for version_id in version_ids if (processed_root / version_id).exists()]
        active_version_path.write_text(
            json.dumps(
                {
                    "active_job_id": active_job_id,
                    "version_ids": version_ids,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _emit_progress(self, callback: Callable[[str], None] | None, stage: str) -> None:
        if callback is not None:
            callback(stage)

    def _attach_video_download(
        self,
        payload,
        *,
        url: str,
        on_progress: Callable[[str], None] | None,
        profile_dir: Path | None,
        video_download_mode: str | None,
    ):
        if self.video_downloader is None:
            return payload, None
        if not video_download_mode or video_download_mode == "none":
            return payload, None
        resolved_platform = payload.platform if payload.platform != "generic" else detect_platform(url, payload.payload_text)
        if payload.content_shape != "video" and not self.video_downloader.supports(url=url, platform=resolved_platform):
            return payload, None
        self._emit_progress(on_progress, "downloading_video")
        download_result = self.video_downloader.download(
            payload.final_url or url,
            platform=resolved_platform,
            download_mode=video_download_mode,
            profile_dir=profile_dir,
        )
        payload.platform = resolved_platform
        payload.content_shape = "video"
        payload.artifacts = tuple(payload.artifacts) + tuple(download_result.artifacts)
        if download_result.title_hint:
            payload.title_hint = download_result.title_hint
        if download_result.author_hint:
            payload.author_hint = download_result.author_hint
        if download_result.published_at_hint:
            payload.published_at_hint = download_result.published_at_hint
        if download_result.final_url:
            payload.final_url = download_result.final_url
        self._refresh_video_payload(payload, url=url, description_hint=download_result.description_hint)
        return payload, download_result.cleanup_dir

    def _cleanup_video_download(self, cleanup_dir: Path | None) -> None:
        if cleanup_dir is None:
            return
        shutil.rmtree(cleanup_dir, ignore_errors=True)

    def _attach_wechat_images(self, payload, *, url: str):
        if payload.platform != "wechat" or payload.content_type != "html":
            return payload
        annotated_html, artifacts = build_wechat_article_artifacts(
            payload.payload_text,
            base_url=payload.final_url or url,
        )
        if not artifacts:
            return payload
        payload.payload_text = annotated_html
        payload.artifacts = tuple(payload.artifacts) + tuple(artifacts)
        return payload

    def _refresh_video_payload(self, payload, *, url: str, description_hint: str | None) -> None:
        if payload.content_type != "html":
            return
        if payload.platform not in {"bilibili", "youtube"}:
            return
        if not payload.title_hint or not payload.author_hint:
            return

        raw_html = payload.payload_text
        refreshed_artifacts = []
        has_raw_capture = False
        for artifact in payload.artifacts:
            if artifact.role in {"visible_text", "media_manifest", "capture_validation"}:
                continue
            if artifact.role == "raw_capture" and isinstance(artifact.content, str):
                raw_html = artifact.content
                has_raw_capture = True
            refreshed_artifacts.append(artifact)

        if not has_raw_capture:
            refreshed_artifacts.insert(
                0,
                CollectedArtifact(
                    relative_path="attachments/source/raw.html",
                    media_type="text/html",
                    role="raw_capture",
                    content=raw_html,
                    description="Original HTML before video metadata enrichment.",
                ),
            )

        description = description_hint or "No concise description was found on the page."
        payload.payload_text = build_video_summary_payload(
            url=payload.final_url or url,
            platform=payload.platform,
            title=payload.title_hint,
            author=payload.author_hint,
            description=description,
            published_at=payload.published_at_hint,
        )
        payload.primary_payload_role = "focused_capture"
        refreshed_artifacts.extend(
            build_html_capture_artifacts(
                source_url=url,
                final_url=payload.final_url or url,
                raw_html=raw_html,
                primary_html=payload.payload_text,
                platform=payload.platform,
                content_shape=payload.content_shape,
                primary_payload_role=payload.primary_payload_role,
                hints=HtmlMetadataHints(
                    platform=payload.platform,
                    title_hint=payload.title_hint,
                    author_hint=payload.author_hint,
                    published_at_hint=payload.published_at_hint,
                ),
            )
        )
        payload.artifacts = tuple(refreshed_artifacts)
