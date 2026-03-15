import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from windows_client.app.view_models import DoctorSnapshot, JobExportSnapshot, OperationViewState
from windows_client.gui.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        shared_root = Path(self.temp_dir.name) / "shared_inbox"
        shared_root.mkdir(parents=True)
        self.workflow = _FakeWorkflow(shared_root)
        self.window = MainWindow(workflow=self.workflow)
        self.window._current_state = OperationViewState(
            operation="export-mock-job",
            status="success",
            summary="ok",
            job=JobExportSnapshot(
                job_id="job-123",
                job_dir=shared_root / "incoming" / "job-123",
                payload_path=shared_root / "incoming" / "job-123" / "payload.html",
                metadata_path=shared_root / "incoming" / "job-123" / "metadata.json",
                ready_path=shared_root / "incoming" / "job-123" / "READY",
            ),
        )

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def test_poll_stops_when_terminal_result_is_found(self) -> None:
        with patch("windows_client.gui.main_window.load_job_result", return_value=_processed_entry("job-123")):
            self.window._start_result_polling()
            self.window._poll_current_job_result()

        self.assertEqual(self.window._latest_result_entry.state, "processed")
        self.assertFalse(self.window._result_poll_timer.isActive())
        self.assertEqual(self.window.result_summary.text(), "WSL processed this job. Open the result workspace to review it.")

    def test_poll_times_out_with_stable_message(self) -> None:
        with patch("windows_client.gui.main_window.load_job_result", return_value=None):
            for _ in range(6):
                self.window._poll_current_job_result()

        self.assertIn("check again later", self.window.result_summary.text())

    def test_technical_details_area_has_visible_height(self) -> None:
        self.assertGreaterEqual(self.window.details_text.minimumHeight(), 180)

    def test_render_success_starts_result_polling_without_manual_refresh_button(self) -> None:
        metadata_path = self.window._current_state.job.metadata_path
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text("{}", encoding="utf-8")

        self.window._render_success(self.window._current_state)

        self.assertTrue(self.window._result_poll_timer.isActive())
        self.assertFalse(hasattr(self.window, "refresh_result_button"))

    def test_video_download_controls_show_for_video_routes_only(self) -> None:
        self.window._sync_video_download_controls("https://www.bilibili.com/video/BV1demo/")
        self.assertFalse(self.window.save_video_checkbox.isHidden())
        self.assertFalse(self.window.video_mode_hint.isHidden())

        self.window._sync_video_download_controls("https://example.com/article")
        self.assertTrue(self.window.save_video_checkbox.isHidden())
        self.assertTrue(self.window.video_mode_hint.isHidden())

    def test_video_download_mode_defaults_to_audio(self) -> None:
        self.window.save_video_checkbox.setChecked(False)
        route = self.window._current_route = type("Route", (), {"is_video": True})()

        self.assertEqual(self.window._selected_video_download_mode(route), "audio")

    def test_video_download_mode_switches_to_video_when_checked(self) -> None:
        self.window.save_video_checkbox.setChecked(True)
        route = self.window._current_route = type("Route", (), {"is_video": True})()

        self.assertEqual(self.window._selected_video_download_mode(route), "video")


class _FakeWorkflow:
    def __init__(self, shared_root: Path) -> None:
        self.service = _FakeService(shared_root)

    def run_doctor(self) -> OperationViewState:
        return OperationViewState(
            operation="doctor",
            status="success",
            summary="ok",
            doctor=DoctorSnapshot(
                lines=[],
                values={
                    "browser_collector_available": "True",
                    "shared_inbox_exists": "True",
                    "browser_profiles_dir": str(self.service.settings.effective_shared_inbox_root / "profiles"),
                },
            ),
        )


class _FakeService:
    def __init__(self, shared_root: Path) -> None:
        self.settings = _FakeSettings(shared_root)


class _FakeSettings:
    def __init__(self, shared_root: Path) -> None:
        self.effective_shared_inbox_root = shared_root


class _Entry:
    def __init__(self, *, job_id: str, state: str) -> None:
        self.job_id = job_id
        self.state = state
        self.summary = "WSL processed this job successfully."
        self.job_dir = Path(".")
        self.source_url = None
        self.title = None
        self.author = None
        self.published_at = None
        self.platform = None
        self.canonical_url = None
        self.preview_text = None
        self.metadata_path = None
        self.normalized_json_path = None
        self.normalized_md_path = None
        self.status_path = None
        self.error_path = None
        self.details = {}


def _processed_entry(job_id: str) -> _Entry:
    return _Entry(job_id=job_id, state="processed")


if __name__ == "__main__":
    unittest.main()
