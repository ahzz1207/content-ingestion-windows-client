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
from windows_client.gui.main_window import MainWindow, _normalize_url, _preview_html


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
        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)

    def test_poll_times_out_with_stable_message(self) -> None:
        # Simulate timeout by setting poll start time far in the past (> 720s)
        self.window._result_poll_start_time = 0.0
        import windows_client.gui.main_window as mw_module
        with patch.object(mw_module, "AUTO_RESULT_POLL_TIMEOUT_SECONDS", 0):
            with patch("windows_client.gui.main_window.load_job_result", return_value=None):
                self.window._poll_current_job_result()

        self.assertIn("Check back later", self.window.result_summary.text())

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

    def test_preview_html_prefers_structured_result_sections(self) -> None:
        entry = _processed_entry("job-structured")
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "summary": {"headline": "Signal", "short_text": "Structured summary from WSL."},
                        "key_points": [
                            {
                                "id": "kp-1",
                                "title": "Point one",
                                "details": "First key point.",
                                "resolved_evidence": [{"preview_text": "Evidence excerpt"}],
                            }
                        ],
                        "verification_items": [
                            {
                                "id": "vf-1",
                                "claim": "Claim one",
                                "status": "supported",
                                "rationale": "Evidence matches the claim.",
                                "resolved_evidence": [{"preview_text": "Transcript line"}],
                            }
                        ],
                    }
                },
                "metadata": {"llm_processing": {"status": "pass"}},
            }
        }

        rendered = _preview_html(entry)

        self.assertIn("Structured summary from WSL.", rendered)
        self.assertIn("Point one", rendered)
        self.assertIn("Claim one", rendered)
        self.assertIn("Evidence excerpt", rendered)

    def test_preview_html_renders_all_key_points_without_truncation(self) -> None:
        """Phase 3: All 5 key points must appear (no [:3] cap)."""
        entry = _processed_entry("job-no-cap")
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "summary": {"headline": "H", "short_text": "S"},
                        "key_points": [
                            {"id": f"kp-{i}", "title": f"KeyPoint{i}", "details": f"Detail {i}"}
                            for i in range(5)
                        ],
                    }
                },
                "metadata": {"llm_processing": {"status": "pass"}},
            }
        }
        rendered = _preview_html(entry)
        for i in range(5):
            self.assertIn(f"KeyPoint{i}", rendered)

    def test_processed_entry_without_brief_still_navigates_to_result_page(self) -> None:
        """Degraded path: no insight_brief — result page is still shown with HTML browser."""
        entry = _processed_entry("job-no-brief")
        # entry.details has no "insight_brief" key

        with patch("windows_client.gui.main_window.load_job_result", return_value=entry):
            self.window._refresh_current_job_result()

        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)
        self.assertEqual(self.window._latest_result_entry.state, "processed")

    def test_failed_result_shows_error_message_and_retry_button(self) -> None:
        """Direction 3: failed job surfaces error text and exposes retry button."""
        failed_entry = _Entry(job_id="job-fail", state="failed", summary="pipeline error: whisper timed out")

        with patch("windows_client.gui.main_window.load_job_result", return_value=failed_entry):
            self.window._refresh_current_job_result()

        self.assertIn("whisper timed out", self.window.result_summary.text())
        self.assertFalse(self.window.retry_button.isHidden())

    def test_retry_button_hidden_at_task_start(self) -> None:
        """Direction 3: retry button must be hidden when a new task begins."""
        from windows_client.gui.platform_router import resolve_platform_route
        route = resolve_platform_route("https://mp.weixin.qq.com/s/test")
        if route is None:
            self.skipTest("no route for test URL")
        self.window._set_task_state(route=route, url="https://mp.weixin.qq.com/s/test", stage="collecting")
        self.assertTrue(self.window.retry_button.isHidden())

    def test_completed_job_with_brief_navigates_to_result_page(self) -> None:
        """Phase 7: when result has insight_brief, stack should show inline result view."""

        class _FakeBrief:
            class hero:
                title = "Test Title"
                one_sentence_take = "Short take."
                content_kind = None
                author_stance = None

            quick_takeaways = ["Point A"]
            viewpoints = []
            coverage = None
            gaps = []

        entry = _processed_entry("job-brief")
        entry.details["insight_brief"] = _FakeBrief()

        with patch(
            "windows_client.gui.main_window.load_job_result",
            return_value=entry,
        ):
            self.window._refresh_current_job_result()

        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)

    def test_result_load_exception_shows_retry_message(self) -> None:
        with patch(
            "windows_client.gui.main_window.load_job_result",
            side_effect=RuntimeError("broken result payload"),
        ):
            state = self.window._refresh_current_job_result(from_auto_poll=True)

        self.assertEqual(state, "unavailable")
        self.assertIn("Retrying automatically", self.window.result_summary.text())
        self.assertIsNone(self.window._latest_result_entry)


class NormalizeUrlTests(unittest.TestCase):
    def test_wechat_strips_tracking_params(self) -> None:
        url = "https://mp.weixin.qq.com/s?__biz=ABC&mid=123&sn=xyz&chksm=deadbeef&scene=27"
        result = _normalize_url(url)
        self.assertIn("__biz=ABC", result)
        self.assertIn("mid=123", result)
        self.assertIn("sn=xyz", result)
        self.assertNotIn("chksm", result)
        self.assertNotIn("scene", result)

    def test_bilibili_strips_recommendation_params(self) -> None:
        url = "https://www.bilibili.com/video/BV1demo/?spm_id_from=333.999&vd_source=abc123"
        result = _normalize_url(url)
        self.assertNotIn("spm_id_from", result)
        self.assertNotIn("vd_source", result)

    def test_bilibili_preserves_page_param(self) -> None:
        url = "https://www.bilibili.com/video/BV1demo/?p=3&spm_id_from=foo"
        result = _normalize_url(url)
        self.assertIn("p=3", result)
        self.assertNotIn("spm_id_from", result)

    def test_other_domains_unchanged(self) -> None:
        url = "https://example.com/article?foo=bar&utm_source=twitter"
        self.assertEqual(_normalize_url(url), url)


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
        self.llm_credentials_available = True
        self.whisper_model_override = None


class _Entry:
    def __init__(
        self,
        *,
        job_id: str,
        state: str,
        analysis_state: str | None = None,
        summary: str = "Structured summary from WSL.",
    ) -> None:
        self.job_id = job_id
        self.state = state
        self.analysis_state = analysis_state
        self.summary = summary
        self.job_dir = Path(".")
        self.source_url = None
        self.title = None
        self.author = None
        self.published_at = None
        self.platform = None
        self.canonical_url = None
        self.preview_text = None
        self.metadata_path = None
        self.analysis_json_path = None
        self.normalized_json_path = None
        self.normalized_md_path = None
        self.status_path = None
        self.error_path = None
        self.details = {}


def _processed_entry(job_id: str) -> _Entry:
    return _Entry(job_id=job_id, state="processed", analysis_state="ready")


if __name__ == "__main__":
    unittest.main()
