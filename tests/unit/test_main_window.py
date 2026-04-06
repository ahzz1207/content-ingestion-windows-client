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

from windows_client.app.service import ReinterpretRequest
from windows_client.app.view_models import DoctorSnapshot, JobExportSnapshot, OperationViewState
from windows_client.gui.main_window import (
    ANALYSIS_MODE_OPTIONS,
    MainWindow,
    UI_FONT_STACK,
    _normalize_url,
    _preview_html,
)
from windows_client.gui.result_renderer import PREVIEW_STYLESHEET


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

    def test_main_window_uses_chinese_friendly_ui_font_stack(self) -> None:
        stylesheet = self.window.styleSheet()

        self.assertIn(UI_FONT_STACK, stylesheet)
        self.assertNotIn("Georgia", stylesheet)
        self.assertNotIn("Times New Roman", stylesheet)

    def test_preview_stylesheet_uses_same_reading_font_stack(self) -> None:
        self.assertIn(UI_FONT_STACK, PREVIEW_STYLESHEET)
        self.assertIn(".preview-reading {", PREVIEW_STYLESHEET)

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

    def test_analysis_template_defaults_to_auto(self) -> None:
        self.assertEqual(self.window.analysis_mode_combo.currentData(), "auto")

    def test_selected_requested_mode_maps_to_backend_value(self) -> None:
        self.window.analysis_mode_combo.setCurrentIndex(2)

        self.assertEqual(self.window._selected_requested_mode(), "guide")

    def test_analysis_mode_options_include_expected_narrative_tuple(self) -> None:
        self.assertIn(("叙事导读", "narrative"), ANALYSIS_MODE_OPTIONS)

    def test_start_threads_requested_mode_only(self) -> None:
        self.window._watcher_running = True
        self.window.url_input.setText("https://example.com/article")
        self.window.analysis_mode_combo.setCurrentIndex(4)

        class _Signal:
            def connect(self, callback):
                self.callback = callback

        class _FakeThread:
            def __init__(self, task):
                self.task = task
                self.progress_changed = _Signal()
                self.completed = _Signal()
                self.crashed = _Signal()

            def start(self) -> None:
                self.task(lambda stage: None)

        with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread):
            self.window._start_from_input()

        self.assertEqual(self.workflow.export_url_calls, [
            {
                "url": "https://example.com/article",
                "platform": "generic",
                "requested_mode": "review",
                "video_download_mode": "audio",
            }
        ])

    def test_wechat_article_start_does_not_force_login_prompt(self) -> None:
        self.window._watcher_running = True
        self.window.url_input.setText("https://mp.weixin.qq.com/s/demo?__biz=abc&mid=1&sn=xyz&scene=1")

        class _Signal:
            def connect(self, callback):
                self.callback = callback

        class _FakeThread:
            def __init__(self, task):
                self.task = task
                self.progress_changed = _Signal()
                self.completed = _Signal()
                self.crashed = _Signal()

            def start(self) -> None:
                self.task(lambda stage: None)

        with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread), patch(
            "windows_client.gui.main_window.LoginPromptDialog"
        ) as login_prompt:
            self.window._start_from_input()

        login_prompt.assert_not_called()
        self.assertEqual(self.workflow.export_url_calls, [
            {
                "url": "https://mp.weixin.qq.com/s/demo?__biz=abc&mid=1&sn=xyz",
                "platform": "wechat",
                "requested_mode": "auto",
                "video_download_mode": "audio",
            }
        ])

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
        self.assertTrue(self.window.result_inline._browser.isHidden())
        self.assertEqual(self.window.result_inline._hero_title.text(), "Test Title")

    def test_completed_job_with_product_view_and_brief_prefers_product_view_in_main_result_page(self) -> None:
        class _FakeBrief:
            class hero:
                title = "Local brief title"
                one_sentence_take = "Local brief take."
                content_kind = None
                author_stance = None

            quick_takeaways = ["Local point"]
            viewpoints = []
            coverage = None
            gaps = []

        entry = _processed_entry("job-product-view")
        entry.title = "Legacy title"
        entry.summary = "Legacy summary"
        entry.details = {
            "insight_brief": _FakeBrief(),
            "product_view": {
                "hero": {
                    "title": "WSL product title",
                    "dek": "WSL product dek",
                },
                "sections": [
                    {
                        "id": "takeaways",
                        "title": "Takeaways",
                        "priority": 1,
                        "blocks": [
                            {"type": "paragraph", "text": "WSL-owned paragraph."},
                        ],
                    }
                ],
            },
        }

        with patch(
            "windows_client.gui.main_window.load_job_result",
            return_value=entry,
        ):
            self.window._refresh_current_job_result()

        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)
        self.assertFalse(self.window.result_inline._browser.isHidden())
        self.assertIn("WSL product title", self.window.result_inline._browser.toHtml())
        self.assertNotEqual(self.window.result_inline._hero_title.text(), "Local brief title")

    def test_completed_job_with_product_view_still_shows_truncation_warnings(self) -> None:
        class _FakeCoverage:
            input_truncated = True
            coverage_ratio = 0.5
            used_segments = 3
            total_segments = 6

        class _FakeBrief:
            class hero:
                title = "Local brief title"
                one_sentence_take = "Local brief take."
                content_kind = None
                author_stance = None

            quick_takeaways = ["Local point"]
            viewpoints = []
            coverage = _FakeCoverage()
            gaps = []

        entry = _processed_entry("job-product-view-truncation")
        entry.details = {
            "insight_brief": _FakeBrief(),
            "llm_image_input": {
                "image_input_truncated": True,
                "image_input_count": 4,
            },
            "product_view": {
                "hero": {
                    "title": "WSL product title",
                    "dek": "WSL product dek",
                },
                "sections": [
                    {
                        "id": "takeaways",
                        "title": "Takeaways",
                        "priority": 1,
                        "blocks": [
                            {"type": "paragraph", "text": "WSL-owned paragraph."},
                        ],
                    }
                ],
            },
        }

        with patch(
            "windows_client.gui.main_window.load_job_result",
            return_value=entry,
        ):
            self.window._refresh_current_job_result()

        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)
        self.assertFalse(self.window.result_inline._coverage_banner.isHidden())
        self.assertIn("only 50% of source segments were analysed", self.window.result_inline._coverage_label.text())
        self.assertFalse(self.window.result_inline._image_truncation_banner.isHidden())
        self.assertIn("4 image(s) were sent to the model", self.window.result_inline._image_truncation_label.text())

    def test_result_load_exception_shows_retry_message(self) -> None:
        with patch(
            "windows_client.gui.main_window.load_job_result",
            side_effect=RuntimeError("broken result payload"),
        ):
            state = self.window._refresh_current_job_result(from_auto_poll=True)

        self.assertEqual(state, "unavailable")
        self.assertIn("Retrying automatically", self.window.result_summary.text())
        self.assertIsNone(self.window._latest_result_entry)

    def test_load_entry_into_result_view_passes_resolved_mode(self) -> None:
        entry = _processed_entry("job-mode")
        entry.details = {
            "normalized": {
                "metadata": {
                    "llm_processing": {
                        "resolved_mode": "guide",
                    }
                }
            }
        }

        with patch.object(self.window.result_inline, "load_entry") as load_entry:
            self.window._load_entry_into_result_view(entry)

        self.assertTrue(load_entry.called)
        self.assertEqual(load_entry.call_args.kwargs["resolved_mode"], "guide")

    def test_reset_to_ready_state_resets_requested_mode_to_auto(self) -> None:
        self.window.analysis_mode_combo.setCurrentIndex(3)

        self.window._reset_to_ready_state()

        self.assertEqual(self.window.analysis_mode_combo.currentData(), "auto")

    def test_start_reinterpretation_uses_service_request_and_loads_new_entry(self) -> None:
        entry = _processed_entry("job-123--reinterpret-01")
        self.window._latest_result_entry = entry

        class _Signal:
            def connect(self, callback):
                self.callback = callback

        class _FakeThread:
            def __init__(self, task):
                self.task = task
                self.progress_changed = _Signal()
                self.completed = _Signal()
                self.crashed = _Signal()

            def start(self) -> None:
                result = self.task(lambda stage: None)
                self.completed.callback(result)

            def isRunning(self) -> bool:
                return False

        with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread):
            self.window._start_reinterpretation(
                ReinterpretRequest(
                    job_id="job-123",
                    reading_goal="guide",
                    domain_template="market-intel",
                )
            )

        self.assertEqual(self.workflow.service.reinterpret_calls, [
            {
                "job_id": "job-123",
                "reading_goal": "guide",
                "domain_template": "market-intel",
            }
        ])
        self.assertEqual(self.window._latest_result_entry.job_id, "job-123--reinterpret-01")
        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)

    def test_start_reinterpretation_preserves_selected_version_job_id(self) -> None:
        self.window._latest_result_entry = _processed_entry("job-123--reinterpret-02")

        class _Signal:
            def connect(self, callback):
                self.callback = callback

        class _FakeThread:
            def __init__(self, task):
                self.task = task
                self.progress_changed = _Signal()
                self.completed = _Signal()
                self.crashed = _Signal()

            def start(self) -> None:
                result = self.task(lambda stage: None)
                self.completed.callback(result)

            def isRunning(self) -> bool:
                return False

        with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread):
            self.window._start_reinterpretation(
                ReinterpretRequest(
                    job_id=self.window._latest_result_entry.job_id,
                    reading_goal="review",
                    domain_template="briefing",
                )
            )

        self.assertEqual(self.workflow.service.reinterpret_calls[-1], {
            "job_id": "job-123--reinterpret-02",
            "reading_goal": "review",
            "domain_template": "briefing",
        })


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
        self.export_url_calls: list[dict[str, object]] = []

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

    def export_url_job(
        self,
        *,
        url: str,
        platform: str | None = None,
        requested_mode: str = "auto",
        video_download_mode: str = "audio",
        on_progress=None,
    ) -> OperationViewState:
        self.export_url_calls.append(
            {
                "url": url,
                "platform": platform,
                "requested_mode": requested_mode,
                "video_download_mode": video_download_mode,
            }
        )
        if on_progress is not None:
            on_progress("collecting")
            on_progress("exporting")
        return OperationViewState(
            operation="export-url-job",
            status="success",
            summary="ok",
            job=JobExportSnapshot(
                job_id="job-456",
                job_dir=self.service.settings.effective_shared_inbox_root / "incoming" / "job-456",
                payload_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-456" / "payload.html",
                metadata_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-456" / "metadata.json",
                ready_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-456" / "READY",
            ),
        )


class _FakeService:
    def __init__(self, shared_root: Path) -> None:
        self.settings = _FakeSettings(shared_root)
        self.reinterpret_calls: list[dict[str, str]] = []

    def reinterpret_result(self, request: ReinterpretRequest, *, shared_root: Path | None = None):
        self.reinterpret_calls.append(
            {
                "job_id": request.job_id,
                "reading_goal": request.reading_goal,
                "domain_template": request.domain_template,
            }
        )
        return _processed_entry("job-123--reinterpret-01")


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
