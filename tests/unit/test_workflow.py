import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.app.service import WindowsClientService
from windows_client.app.workflow import WindowsClientWorkflow
from windows_client.collector.http import HttpCollector
from windows_client.collector.mock import MockCollector
from windows_client.config.settings import Settings
from windows_client.job_exporter.exporter import JobExporter


class WindowsClientWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name) / "project-root"
        settings = Settings(project_root=self.project_root)
        browser_collector = MagicMock()
        browser_collector.is_available.return_value = False
        browser_collector.availability_reason.return_value = "playwright_not_installed"
        self.service = WindowsClientService(
            settings=settings,
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=browser_collector,
            exporter=JobExporter(settings=settings),
        )
        self.workflow = WindowsClientWorkflow(self.service)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_doctor_builds_keyed_snapshot(self) -> None:
        state = self.workflow.run_doctor()

        self.assertEqual(state.operation, "doctor")
        self.assertEqual(state.status, "success")
        self.assertIsNotNone(state.doctor)
        self.assertEqual(state.doctor.values["browser_collector_available"], "False")
        self.assertIn("Browser collector unavailable.", state.summary)

    def test_export_mock_job_returns_gui_snapshot(self) -> None:
        state = self.workflow.export_mock_job(url="https://example.com/article")

        self.assertEqual(state.operation, "export-mock-job")
        self.assertEqual(state.status, "success")
        self.assertIsNotNone(state.job)
        self.assertTrue(state.job.job_dir.exists())
        self.assertEqual(state.job.payload_path.name, "payload.html")
        self.assertIn(state.job.job_id, state.summary)

    def test_export_mock_job_forwards_progress_callback(self) -> None:
        stages: list[str] = []

        state = self.workflow.export_mock_job(
            url="https://example.com/article",
            on_progress=stages.append,
        )

        self.assertEqual(state.status, "success")
        self.assertEqual(stages, ["collecting", "exporting"])

    def test_export_url_job_forwards_video_download_mode(self) -> None:
        self.service.export_url_job = MagicMock(return_value=self.service.export_mock_job(url="https://example.com/article"))

        state = self.workflow.export_url_job(
            url="https://www.bilibili.com/video/BV1demo/",
            video_download_mode="video",
        )

        self.assertEqual(state.status, "success")
        self.service.export_url_job.assert_called_once()
        self.assertEqual(self.service.export_url_job.call_args.kwargs["video_download_mode"], "video")

    def test_export_url_job_defaults_requested_mode_to_auto(self) -> None:
        self.service.export_url_job = MagicMock(return_value=self.service.export_mock_job(url="https://example.com/article"))

        state = self.workflow.export_url_job(url="https://example.com/article")

        self.assertEqual(state.status, "success")
        self.assertEqual(self.service.export_url_job.call_args.kwargs["requested_mode"], "auto")

    def test_browser_login_returns_profile_snapshot(self) -> None:
        profile_dir = self.project_root / "data" / "browser-profiles" / "wechat"
        self.service.browser_collector.open_profile_session.return_value = profile_dir
        self.service.browser_collector.default_profile_slug.return_value = "wechat"

        state = self.workflow.browser_login(start_url="https://mp.weixin.qq.com/")

        self.assertEqual(state.operation, "browser-login")
        self.assertEqual(state.status, "success")
        self.assertIsNotNone(state.browser_session)
        self.assertEqual(state.browser_session.profile_dir, profile_dir)

    def test_export_browser_job_returns_failure_state_for_structured_errors(self) -> None:
        self.service.browser_collector.collect.side_effect = WindowsClientError(
            "browser_runtime_unavailable",
            "browser collector unavailable: playwright_not_installed",
            stage="browser_collect",
            details={"reason": "playwright_not_installed"},
        )

        state = self.workflow.export_browser_job(url="https://example.com/article")

        self.assertEqual(state.operation, "export-browser-job")
        self.assertEqual(state.status, "failed")
        self.assertIsNotNone(state.error)
        self.assertEqual(state.error.code, "browser_runtime_unavailable")
        self.assertEqual(state.error.stage, "browser_collect")
        self.assertEqual(state.error.details["reason"], "playwright_not_installed")

    def test_export_browser_job_wraps_unexpected_errors(self) -> None:
        self.service.browser_collector.collect.side_effect = RuntimeError("boom")

        state = self.workflow.export_browser_job(url="https://example.com/article")

        self.assertEqual(state.status, "failed")
        self.assertEqual(state.error.code, "unexpected_error")
        self.assertEqual(state.error.stage, "workflow")
        self.assertEqual(state.error.cause_type, "RuntimeError")


if __name__ == "__main__":
    unittest.main()
