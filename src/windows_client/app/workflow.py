from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from windows_client.app.errors import WindowsClientError
from windows_client.app.service import WindowsClientService
from windows_client.app.view_models import (
    BrowserSessionSnapshot,
    OperationViewState,
    doctor_snapshot,
    error_state,
    job_export_snapshot,
)


class WindowsClientWorkflow:
    """GUI-facing adapter that converts service calls into stable view states."""

    def __init__(self, service: WindowsClientService) -> None:
        self.service = service

    def run_doctor(self) -> OperationViewState:
        try:
            lines = list(self.service.doctor())
            snapshot = doctor_snapshot(lines)
            summary = "Browser collector available." if snapshot.values.get("browser_collector_available") == "True" else (
                "Browser collector unavailable."
            )
            return OperationViewState(
                operation="doctor",
                status="success",
                summary=summary,
                doctor=snapshot,
            )
        except WindowsClientError as error:
            return self._failed("doctor", error)
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            return self._failed(
                "doctor",
                WindowsClientError(
                    "unexpected_error",
                    str(exc) or type(exc).__name__,
                    stage="workflow",
                    cause=exc,
                ),
            )

    def export_mock_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        content_type: str | None = None,
        platform: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> OperationViewState:
        return self._export(
            operation="export-mock-job",
            exporter=lambda: self.service.export_mock_job(
                url=url,
                shared_root=shared_root,
                content_type=content_type,
                platform=platform,
                on_progress=on_progress,
            ),
        )

    def export_url_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        content_type: str | None = None,
        platform: str | None = None,
        video_download_mode: str = "audio",
        on_progress: Callable[[str], None] | None = None,
    ) -> OperationViewState:
        return self._export(
            operation="export-url-job",
            exporter=lambda: self.service.export_url_job(
                url=url,
                shared_root=shared_root,
                content_type=content_type,
                platform=platform,
                video_download_mode=video_download_mode,
                on_progress=on_progress,
            ),
        )

    def export_browser_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        platform: str | None = None,
        video_download_mode: str = "audio",
        profile_dir: Path | None = None,
        browser_channel: str | None = None,
        headless: bool | None = None,
        wait_until: str | None = None,
        timeout_ms: int | None = None,
        settle_ms: int | None = None,
        wait_for_selector: str | None = None,
        wait_for_selector_state: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> OperationViewState:
        return self._export(
            operation="export-browser-job",
            exporter=lambda: self.service.export_browser_job(
                url=url,
                shared_root=shared_root,
                platform=platform,
                video_download_mode=video_download_mode,
                profile_dir=profile_dir,
                browser_channel=browser_channel,
                headless=headless,
                wait_until=wait_until,
                timeout_ms=timeout_ms,
                settle_ms=settle_ms,
                wait_for_selector=wait_for_selector,
                wait_for_selector_state=wait_for_selector_state,
                on_progress=on_progress,
            ),
        )

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
    ) -> OperationViewState:
        try:
            resolved_profile_dir = self.service.browser_login(
                start_url=start_url,
                profile_dir=profile_dir,
                browser_channel=browser_channel,
                wait_until=wait_until,
                timeout_ms=timeout_ms,
                completion_waiter=completion_waiter,
                on_progress=on_progress,
            )
            return OperationViewState(
                operation="browser-login",
                status="success",
                summary=f"Browser profile ready: {resolved_profile_dir}",
                browser_session=BrowserSessionSnapshot(profile_dir=resolved_profile_dir),
            )
        except WindowsClientError as error:
            return self._failed("browser-login", error)
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            return self._failed(
                "browser-login",
                WindowsClientError(
                    "unexpected_error",
                    str(exc) or type(exc).__name__,
                    stage="workflow",
                    cause=exc,
                ),
            )

    def _export(self, *, operation: str, exporter) -> OperationViewState:
        try:
            result = exporter()
            snapshot = job_export_snapshot(result)
            return OperationViewState(
                operation=operation,
                status="success",
                summary=f"Exported job {snapshot.job_id}",
                job=snapshot,
            )
        except WindowsClientError as error:
            return self._failed(operation, error)
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            return self._failed(
                operation,
                WindowsClientError(
                    "unexpected_error",
                    str(exc) or type(exc).__name__,
                    stage="workflow",
                    cause=exc,
                ),
            )

    def _failed(self, operation: str, error: WindowsClientError) -> OperationViewState:
        return OperationViewState(
            operation=operation,
            status="failed",
            summary=error.message,
            error=error_state(error),
        )
