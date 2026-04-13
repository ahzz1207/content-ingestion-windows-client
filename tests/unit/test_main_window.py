import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent, QImage, QKeyEvent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTextBrowser

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
        self.shared_root = shared_root
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
        self.assertIn("Noto Serif SC", PREVIEW_STYLESHEET)
        self.assertIn(".preview-reading {", PREVIEW_STYLESHEET)

    def test_main_window_stylesheet_supports_v4_immersive_result_page(self) -> None:
        stylesheet = self.window.styleSheet()

        self.assertIn("#ImmersiveHero", stylesheet)
        self.assertIn("#HeroTopBar", stylesheet)
        self.assertIn("#HeroActionStrip", stylesheet)
        self.assertIn("#HeroMetaRow", stylesheet)
        self.assertIn("#ReadingStreamShell", stylesheet)
        self.assertIn("#ContextRailShell", stylesheet)

    def test_main_window_stylesheet_contains_inline_result_compact_layout_hooks(self) -> None:
        stylesheet = self.window.styleSheet()

        self.assertIn('QFrame#ImmersiveHero[isNarrowLayout="true"]', stylesheet)
        self.assertIn('QFrame#ImageSummaryCard[hasInsightCard="true"]', stylesheet)

    def test_main_window_stylesheet_contains_drag_active_hook_for_url_input(self) -> None:
        stylesheet = self.window.styleSheet()

        self.assertIn('#UrlInput[dragActive="true"]', stylesheet)

    def test_render_success_starts_result_polling_without_manual_refresh_button(self) -> None:
        metadata_path = self.window._current_state.job.metadata_path
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text("{}", encoding="utf-8")

        self.window._render_success(self.window._current_state)

        self.assertTrue(self.window._result_poll_timer.isActive())
        self.assertFalse(hasattr(self.window, "refresh_result_button"))

    def test_render_success_shows_in_page_banner_when_processed_result_already_ready(self) -> None:
        metadata_path = self.window._current_state.job.metadata_path
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text("{}", encoding="utf-8")
        processed_entry = _processed_entry("job-123")
        processed_entry.details = {
            "normalized": {
                "metadata": {
                    "llm_processing": {
                        "resolved_mode": "guide",
                    }
                }
            }
        }

        with patch("windows_client.gui.main_window.load_job_result", return_value=processed_entry):
            self.window._render_success(self.window._current_state)

        self.assertFalse(self.window.result_inline._update_banner_frame.isHidden())
        self.assertIn("结果已更新", self.window.result_inline._update_banner_label.text())

    def test_render_success_does_not_restart_polling_when_result_is_already_processed(self) -> None:
        metadata_path = self.window._current_state.job.metadata_path
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text("{}", encoding="utf-8")

        with patch("windows_client.gui.main_window.load_job_result", return_value=_processed_entry("job-123")):
            self.window._render_success(self.window._current_state)

        self.assertFalse(self.window._result_poll_timer.isActive())
        self.assertFalse(self.window._elapsed_timer.isActive())
        self.assertTrue(self.window._elapsed_label.isHidden())
        self.assertIs(self.window.stack.currentWidget(), self.window.result_inline)

    def test_render_success_fails_fast_for_wechat_gate_page_result(self) -> None:
        metadata_path = self.window._current_state.job.metadata_path
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text("{}", encoding="utf-8")
        gate_entry = _processed_entry("job-gate")
        gate_entry.summary = "The captured page is an access/interruption screen."
        gate_entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "summary": {
                            "headline": "The captured page is not the intended article content",
                            "short_text": "The current environment is abnormal and verification is required.",
                        }
                    }
                },
                "metadata": {
                    "capture_validation": {
                        "is_gate_page": True,
                        "gate_reason": "wechat_captcha",
                    },
                    "llm_processing": {"resolved_mode": "argument"},
                },
            }
        }

        with patch("windows_client.gui.main_window.load_job_result", return_value=gate_entry):
            state = self.window._refresh_current_job_result(from_auto_poll=True)

        self.assertEqual(state, "failed")
        self.assertIn("验证", self.window.result_summary.text())
        self.assertFalse(self.window.retry_button.isHidden())

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

    def test_start_from_input_routes_long_text_to_local_submission(self) -> None:
        self.window.url_input.setText("这是一段很长的文章内容" * 10)

        with patch("windows_client.gui.main_window.submit_local", return_value="job-local-1") as submit_local:
            with patch.object(self.window, "_start_result_polling") as start_polling:
                self.window._start_from_input()

        payload = submit_local.call_args.args[0]
        self.assertEqual(type(payload).__name__, "TextPayload")
        self.assertEqual(payload.text, ("这是一段很长的文章内容" * 10).strip())
        self.assertEqual(submit_local.call_args.kwargs["shared_root"], self.shared_root)
        self.assertEqual(submit_local.call_args.kwargs["requested_mode"], "auto")
        self.assertEqual(self.window._current_state.job.job_id, "job-local-1")
        start_polling.assert_called_once_with()

    def test_open_file_routes_supported_file_to_local_submission(self) -> None:
        pdf = Path(self.temp_dir.name) / "report.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        with patch("windows_client.gui.main_window.QFileDialog.getOpenFileName", return_value=(str(pdf), "")):
            with patch("windows_client.gui.main_window.submit_local", return_value="job-local-2") as submit_local:
                with patch.object(self.window, "_start_result_polling") as start_polling:
                    with patch.object(self.window, "_trigger_watch_once") as trigger_watch:
                        self.window._on_open_file()

        payload = submit_local.call_args.args[0]
        self.assertEqual(type(payload).__name__, "FilePayload")
        self.assertEqual(payload.path, pdf)
        self.assertEqual(payload.content_type, "pdf")
        self.assertEqual(self.window._current_state.job.job_id, "job-local-2")
        start_polling.assert_called_once_with()
        trigger_watch.assert_called_once()

    def test_submit_local_payload_shows_footer_on_failure(self) -> None:
        from windows_client.app.input_router import TextPayload

        with patch("windows_client.gui.main_window.submit_local", side_effect=RuntimeError("disk full")):
            self.window._submit_local_payload(TextPayload(text="这是一段很长的文章内容" * 10))

        self.assertEqual(self.window.footer_label.text(), "提交失败：disk full")

    def test_drop_event_routes_local_file_to_local_submission(self) -> None:
        pdf = Path(self.temp_dir.name) / "drop.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(pdf))])
        event = QDropEvent(
            QPointF(10, 10),
            Qt.CopyAction,
            mime,
            Qt.LeftButton,
            Qt.NoModifier,
        )

        with patch.object(self.window, "_submit_local_payload") as submit_payload:
            self.window.dropEvent(event)

        payload = submit_payload.call_args.args[0]
        self.assertEqual(type(payload).__name__, "FilePayload")
        self.assertEqual(payload.path, pdf)
        self.assertFalse(self.window.url_input.property("dragActive"))

    def test_drag_enter_event_marks_url_input_drag_active(self) -> None:
        mime = QMimeData()
        mime.setText("拖入文本")

        class _Event:
            def __init__(self, mime_data):
                self._mime = mime_data
                self.accepted = False

            def mimeData(self):
                return self._mime

            def acceptProposedAction(self):
                self.accepted = True

        event = _Event(mime)
        self.window.dragEnterEvent(event)

        self.assertTrue(event.accepted)
        self.assertTrue(self.window.url_input.property("dragActive"))

    def test_event_filter_routes_clipboard_image_to_local_submission(self) -> None:
        image = QImage(2, 2, QImage.Format_ARGB32)
        image.fill(Qt.red)
        QApplication.clipboard().setImage(image)
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)

        with patch.object(self.window, "_submit_local_payload") as submit_payload:
            handled = self.window.eventFilter(self.window.url_input, event)

        self.assertTrue(handled)
        payload = submit_payload.call_args.args[0]
        self.assertEqual(type(payload).__name__, "ImagePayload")
        self.assertEqual(payload.suffix, ".png")
        self.assertEqual(self.window.footer_label.text(), "检测到图片，正在提交本地图片...")

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
        self.assertEqual(self.workflow.export_url_calls, [])
        self.assertEqual(self.workflow.export_browser_calls, [
            {
                "url": "https://mp.weixin.qq.com/s/demo?__biz=abc&mid=1&sn=xyz",
                "platform": "wechat",
                "requested_mode": "auto",
                "video_download_mode": "audio",
                "profile_dir": self.workflow.service.settings.browser_profiles_dir / "wechat",
                "wait_for_selector": "#js_content",
                "wait_for_selector_state": "visible",
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

    def test_failed_result_stops_elapsed_timer_and_hides_elapsed_label(self) -> None:
        failed_entry = _Entry(job_id="job-fail", state="failed", summary="pipeline error: whisper timed out")
        self.window._elapsed_label.setText("已用时 00:12")
        self.window._elapsed_label.show()
        self.window._elapsed_timer.start()

        with patch("windows_client.gui.main_window.load_job_result", return_value=failed_entry):
            state = self.window._refresh_current_job_result()

        self.assertEqual(state, "failed")
        self.assertFalse(self.window._elapsed_timer.isActive())
        self.assertTrue(self.window._elapsed_label.isHidden())

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
        self.assertIn("当前只分析了 50% 的原始分段", self.window.result_inline._coverage_label.text())
        self.assertFalse(self.window.result_inline._image_truncation_banner.isHidden())
        self.assertIn("本次共向模型发送了 4 张图片", self.window.result_inline._image_truncation_label.text())

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
        self.assertFalse(self.window.result_inline._update_banner_frame.isHidden())
        self.assertIn("结果已更新", self.window.result_inline._update_banner_label.text())

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

    def test_ready_page_library_button_opens_library_dialog(self) -> None:
        with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = 0

            self.window.library_button.click()

        dialog_cls.assert_called_once()

    def test_result_page_library_button_opens_library_dialog(self) -> None:
        with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = 0

            self.window.result_inline.open_library_requested.emit()

        dialog_cls.assert_called_once()

    def test_result_page_open_library_entry_signal_opens_dialog_for_saved_entry(self) -> None:
        with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = 0

            self.window.result_inline.open_library_entry_requested.emit("lib_0001")

        dialog_cls.assert_called_once()
        self.assertEqual(dialog_cls.call_args.kwargs["selected_entry_id"], "lib_0001")

    def test_open_library_dialog_connects_analysis_signal(self) -> None:
        with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = 0

            self.window._open_library_dialog(selected_entry_id="lib_0001")

        dialog.restore_requested.connect.assert_called_once_with(self.window._restore_library_interpretation)
        dialog.open_analysis_requested.connect.assert_called_once_with(self.window._open_library_analysis)

    def test_save_latest_result_to_library_runs_via_workflow_task_thread_and_shows_library_banner(self) -> None:
        entry = _processed_entry("job-123")
        self.window._latest_result_entry = entry
        self.window.result_inline.load_entry(entry, brief=None)

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
            self.window._save_latest_result_to_library()

        self.assertEqual(self.workflow.save_result_to_library_calls, [entry])
        self.assertFalse(self.window.result_inline._library_banner_frame.isHidden())
        self.assertIn("知识库", self.window.result_inline._library_banner_label.text())
        self.assertEqual(self.window.result_inline._library_banner_entry_id, "entry-123")
        self.assertFalse(self.window.result_inline._open_library_entry_btn.isHidden())
        self.assertEqual(self.window.result_inline._open_library_entry_btn.text(), "打开条目")
        self.assertFalse(self.window.result_inline._open_library_banner_btn.isHidden())
        self.assertEqual(self.window.result_inline._open_library_banner_btn.text(), "查看知识库")

    def test_save_latest_result_to_library_failure_uses_product_level_copy(self) -> None:
        with patch("windows_client.gui.main_window.QMessageBox.warning") as warning:
            self.window._on_save_to_library_completed(
                OperationViewState(
                    operation="save-result-to-library",
                    status="failed",
                    summary="Traceback: disk unavailable",
                )
            )

        warning.assert_called_once()
        self.assertEqual(warning.call_args.args[1], "Save to library failed")
        self.assertEqual(warning.call_args.args[2], "无法保存到知识库。请稍后重试。")

    def test_first_save_to_library_success_copy_does_not_claim_old_versions_exist(self) -> None:
        self.window._on_save_to_library_completed(
            OperationViewState(
                operation="save-result-to-library",
                status="success",
                summary="Saved to library: entry-123",
                library=type(
                    "LibrarySnapshot",
                    (),
                    {"entry_id": "entry-123", "trashed_interpretation_count": 0},
                )(),
            )
        )

        self.assertIn("Source 已保存到知识库", self.window.result_inline._library_banner_label.text())
        self.assertNotIn("旧版本", self.window.result_inline._library_banner_label.text())

    def test_repeat_save_to_library_success_copy_mentions_restorable_old_versions(self) -> None:
        self.window._on_save_to_library_completed(
            OperationViewState(
                operation="save-result-to-library",
                status="success",
                summary="Saved to library: entry-123",
                library=type(
                    "LibrarySnapshot",
                    (),
                    {"entry_id": "entry-123", "trashed_interpretation_count": 2},
                )(),
            )
        )

        self.assertIn("旧版本仍可在条目内恢复", self.window.result_inline._library_banner_label.text())

    def test_restore_library_interpretation_runs_via_workflow_task_thread_and_refreshes_open_dialog(self) -> None:
        dialog = _FakeLibraryDialog()
        self.window._library_dialog = dialog

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
            self.window._restore_library_interpretation("entry-123", "interp-456")

        self.assertEqual(
            self.workflow.restore_library_interpretation_calls,
            [("entry-123", "interp-456")],
        )
        self.assertEqual(dialog.reload_calls, 1)

    def test_restore_library_interpretation_failure_does_not_refresh_open_dialog(self) -> None:
        dialog = _FakeLibraryDialog()
        self.window._library_dialog = dialog

        with patch("windows_client.gui.main_window.QMessageBox.warning") as warning:
            self.window._on_restore_library_interpretation_completed(
                OperationViewState(
                    operation="restore-library-interpretation",
                    status="failed",
                    summary="restore failed",
                )
            )

        self.assertEqual(dialog.reload_calls, 0)
        self.assertEqual(self.window.footer_label.text(), "Automatic platform detection and browser guidance are enabled.")
        warning.assert_called_once()

    def test_save_success_updates_footer_with_library_confirmation(self) -> None:
        self.window._on_save_to_library_completed(
            OperationViewState(
                operation="save-result-to-library",
                status="success",
                summary="Saved to library: entry-123",
                library=type(
                    "LibrarySnapshot",
                    (),
                    {"entry_id": "entry-123", "trashed_interpretation_count": 0},
                )(),
            )
        )

        self.assertEqual(self.window.footer_label.text(), "Saved to knowledge library.")

    def test_main_window_library_analysis_loads_processed_entry_directly(self) -> None:
        entry = _processed_entry("job-123")
        dialog = _FakeLibraryDialog()
        self.window._library_dialog = dialog

        with patch("windows_client.gui.main_window.load_job_result", return_value=entry), patch.object(
            self.window,
            "_load_entry_into_result_view",
        ) as load_entry, patch.object(self.window, "_show_result_workspace") as show_result_workspace:
            self.window._open_library_analysis("job-123")

        self.assertEqual(dialog.accept_calls, 1)
        load_entry.assert_called_once_with(entry)
        show_result_workspace.assert_not_called()

    def test_main_window_library_analysis_falls_back_to_result_workspace_when_entry_missing(self) -> None:
        dialog = _FakeLibraryDialog()
        self.window._library_dialog = dialog

        with patch("windows_client.gui.main_window.load_job_result", return_value=None), patch.object(
            self.window,
            "_load_entry_into_result_view",
        ) as load_entry, patch.object(self.window, "_show_result_workspace") as show_result_workspace:
            self.window._open_library_analysis("job-123")

        self.assertEqual(dialog.accept_calls, 1)
        load_entry.assert_not_called()
        show_result_workspace.assert_called_once_with(
            shared_root=self.shared_root,
            selected_job_id="job-123",
        )

    def test_open_library_dialog_analysis_signal_loads_processed_entry_directly(self) -> None:
        entry = _processed_entry("job-123")

        class _Signal:
            def connect(self, callback):
                self.callback = callback

        class _FakeDialog:
            def __init__(self, *, parent, shared_root, selected_entry_id=None):
                self.parent = parent
                self.shared_root = shared_root
                self.selected_entry_id = selected_entry_id
                self.restore_requested = _Signal()
                self.open_analysis_requested = _Signal()

            def exec(self) -> int:
                self.open_analysis_requested.callback("job-123")
                return 0

            def accept(self) -> None:
                return None

        with patch("windows_client.gui.main_window.LibraryDialog", _FakeDialog), patch(
            "windows_client.gui.main_window.load_job_result",
            return_value=entry,
        ), patch.object(self.window, "_load_entry_into_result_view") as load_entry, patch.object(
            self.window,
            "_show_result_workspace",
        ) as show_result_workspace:
            self.window._open_library_dialog(selected_entry_id="lib_0001")

        load_entry.assert_called_once_with(entry)
        show_result_workspace.assert_not_called()

    def test_open_library_shows_error_dialog_when_library_dialog_fails(self) -> None:
        with patch(
            "windows_client.gui.main_window.LibraryDialog",
            side_effect=RuntimeError("library exploded"),
        ), patch("windows_client.gui.main_window.QMessageBox.critical") as critical:
            self.window._open_library()

        critical.assert_called_once()
        self.assertIn("library exploded", critical.call_args.args[2])


class LibraryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.shared_root = Path(self.temp_dir.name) / "shared_inbox"
        self.shared_root.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_reload_preserves_current_selection(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))
        store.save_entry(_library_processed_entry(self.shared_root, "job-2", source_url="https://example.com/2"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog.list_widget.setCurrentRow(1)

        dialog.reload()

        self.assertEqual(dialog.list_widget.currentRow(), 1)
        self.assertEqual(dialog.entries[1].entry_id, dialog._selected_entry_id)
        dialog.close()

    def test_recent_filter_orders_by_entry_updated_at_after_restore(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        first = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))
        second = store.save_entry(_library_processed_entry(self.shared_root, "job-2", source_url="https://example.com/2"))
        updated_first = store.save_entry(_library_processed_entry(self.shared_root, "job-3", source_url="https://example.com/1"))
        store.restore_interpretation(
            entry_id=updated_first.entry_id,
            interpretation_id=updated_first.trashed_interpretations[0].interpretation_id,
        )

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog.recent_entries_filter.setChecked(True)
        dialog.all_entries_filter.setChecked(True)
        dialog.reload()

        self.assertEqual(dialog.entries[0].entry_id, first.entry_id)
        self.assertNotEqual(dialog.entries[0].entry_id, second.entry_id)
        dialog.close()

    def test_filter_toggles_do_not_blank_list_when_recent_mode_selected(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog.all_entries_filter.setChecked(False)
        dialog.recent_entries_filter.setChecked(True)
        dialog.reload()

        self.assertEqual(len(dialog.entries), 1)
        dialog.close()

    def test_all_entries_filter_toggle_changes_list_visibility(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog.all_entries_filter.setChecked(False)
        dialog.recent_entries_filter.setChecked(False)
        dialog.reload()

        self.assertEqual(len(dialog.entries), 0)
        dialog.all_entries_filter.setChecked(True)
        dialog.reload()
        self.assertEqual(len(dialog.entries), 1)
        dialog.close()

    def test_list_item_text_includes_platform_route_and_image_presence(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        item_text = dialog.list_widget.item(0).text()

        self.assertIn(saved.source.platform or "", item_text)
        self.assertIn(saved.current_interpretation.route_key, item_text)
        self.assertIn("有图片摘要", item_text)
        dialog.close()

    def test_list_item_text_uses_compact_v4_context_copy(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        item_text = dialog.list_widget.item(0).text()

        self.assertIn("更新于", item_text)
        self.assertNotIn("个解读", item_text)
        self.assertNotIn("旧版本", item_text)
        dialog.close()

    def test_library_dialog_uses_v4_related_content_and_timeline_labels(self) -> None:
        from windows_client.gui.library_panel import LibraryDialog

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)

        self.assertEqual(dialog._list_heading.text(), "相关内容")
        self.assertEqual(dialog._timeline_heading.text(), "版本时间线")
        dialog.close()

    def test_library_dialog_uses_v4_context_heading(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        context_frame = dialog._build_context_section(dialog.entries[0])
        heading = context_frame.layout().itemAt(0).widget()

        self.assertEqual(heading.text(), "Library Context")
        dialog.close()

    def test_library_dialog_uses_v4_chinese_detail_section_labels(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        entry = dialog.entries[0]

        image_frame = dialog._build_image_section(entry)
        source_frame = dialog._build_source_section(entry)
        interpretation_frame = dialog._build_interpretation_section(entry)
        metadata_frame = dialog._build_current_metadata_section(entry)

        image_heading = image_frame.layout().itemAt(0).widget().text()
        source_heading = source_frame.layout().itemAt(0).widget().text()
        interpretation_heading = interpretation_frame.layout().itemAt(0).widget().text()
        metadata_heading = metadata_frame.layout().itemAt(0).widget().text()

        self.assertEqual(image_heading, "视觉总结")
        self.assertEqual(source_heading, "来源信息")
        self.assertEqual(interpretation_heading, "当前解读")
        self.assertEqual(metadata_heading, "当前版本")
        dialog.close()

    def test_library_dialog_context_and_timeline_rows_use_real_chinese_copy(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-2", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        entry = next(item for item in dialog.entries if item.entry_id == saved.entry_id)

        context_frame = dialog._build_context_section(entry)
        context_text = "\n".join(
            context_frame.layout().itemAt(index).widget().text()
            for index in range(1, context_frame.layout().count())
        )
        timeline_frame = dialog._build_trash_section(entry)
        timeline_row = timeline_frame.layout().itemAt(1).widget()
        timeline_text = timeline_row.layout().itemAt(0).widget().text()

        self.assertIn("共 2 个解读版本", context_text)
        self.assertIn(f"当前路线：{entry.current_interpretation.route_key}", context_text)
        self.assertIn(f"来源键：{entry.source_key}", context_text)
        self.assertIn("路线：", timeline_text)
        self.assertIn("归档时间：", timeline_text)
        self.assertIn("归档原因：被新的保存版本替换", timeline_text)
        dialog.close()

    def test_library_dialog_emits_open_analysis_requested_for_selected_entry(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        opened: list[str] = []
        dialog.open_analysis_requested.connect(opened.append)

        source_frame = dialog._build_source_section(saved)
        button = source_frame.findChild(QPushButton, "OpenFullAnalysisButton")
        self.assertIsNotNone(button)
        button.click()

        self.assertEqual(opened, ["job-1"])
        dialog.close()

    def test_library_dialog_uses_compact_source_header_surface(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        source_frame = dialog._build_source_section(dialog.entries[0])

        self.assertEqual(source_frame.objectName(), "SourceHeaderCard")
        dialog.close()

    def test_library_dialog_keeps_snapshot_paths_out_of_source_header(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        source_frame = dialog._build_source_section(dialog.entries[0])
        source_text = "\n".join(label.text() for label in source_frame.findChildren(QLabel))

        self.assertNotIn("Markdown 快照", source_text)
        self.assertNotIn("结构化 JSON", source_text)
        self.assertNotIn("元数据：", source_text)
        dialog.close()

    def test_library_dialog_interpretation_section_uses_primary_reading_surface(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        interpretation_frame = dialog._build_interpretation_section(dialog.entries[0])
        browser = interpretation_frame.findChild(QTextBrowser, "LibraryInterpretationBrowser")

        self.assertIsNotNone(browser)
        assert browser is not None
        self.assertGreaterEqual(browser.minimumHeight(), 420)
        dialog.close()

    def test_library_dialog_context_section_surfaces_source_snapshot_context(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        context_frame = dialog._build_context_section(dialog.entries[0])
        context_text = "\n".join(label.text() for label in context_frame.findChildren(QLabel))

        self.assertIn("来源任务：job-1", context_text)
        self.assertIn("来源快照：", context_text)
        self.assertNotIn("source/normalized.md", context_text)
        dialog.close()

    def test_library_dialog_uses_context_rail_shell_for_side_column(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog._render_entry(0)

        shell = dialog.detail_root_layout.itemAt(1).widget()
        self.assertIsNotNone(shell)
        assert shell is not None
        self.assertEqual(shell.objectName(), "ContextRailShell")
        self.assertEqual(dialog.side_column_layout.count(), 2)
        rail = dialog.side_column_layout.itemAt(0).widget()
        self.assertEqual(rail.objectName(), "ContextRail")
        self.assertEqual(rail.layout().itemAt(0).widget().text(), "Library Context")
        dialog.close()

    def test_library_dialog_stylesheet_sets_dark_selected_list_text_color(self) -> None:
        dialog = MainWindow(workflow=_FakeWorkflow(self.shared_root))

        stylesheet = dialog.styleSheet()

        self.assertIn(
            "QListWidget#ResultList::item:selected {\n                background: transparent;\n                border: none;\n                color: #152133;\n            }",
            stylesheet,
        )
        dialog.close()

    def test_library_dialog_renders_guide_interpretation_from_editorial_payload_when_product_view_missing(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_guide_entry(self.shared_root, "job-guide-1", source_url="https://example.com/guide"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        interpretation_html = dialog._interpretation_html(dialog.entries[0].current_interpretation)

        self.assertIn("guide-digest-layout", interpretation_html)
        self.assertIn("先核对换帅时间线", interpretation_html)
        self.assertNotIn("Step 1", interpretation_html)
        dialog.close()


class ResultWorkspaceDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_processed_entry_without_brief_still_has_open_analysis_button(self) -> None:
        from windows_client.app.result_workspace import ResultWorkspaceEntry
        from windows_client.gui.result_workspace_panel import ResultWorkspaceDialog

        entry = ResultWorkspaceEntry(
            job_id="job-123",
            state="processed",
            analysis_state="ready",
            updated_at=1712487960.0,
            job_dir=Path("."),
            source_url="https://example.com/article",
            title="Structured title",
            author="Author",
            published_at="2026-04-07",
            platform="wechat",
            canonical_url="https://example.com/article",
            summary="Structured summary",
            preview_text="Preview text",
            metadata_path=None,
            analysis_json_path=None,
            normalized_json_path=None,
            normalized_md_path=None,
            status_path=None,
            error_path=None,
            details={"product_view": {}},
        )

        with patch("windows_client.gui.result_workspace_panel.list_recent_results", return_value=[entry]):
            dialog = ResultWorkspaceDialog(parent=None, shared_root=Path("."))

        self.assertTrue(dialog.view_button.isEnabled())
        dialog.view_button.click()
        self.assertIs(dialog.entry_to_open, entry)
        dialog.close()


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


class WechatSubmitRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        shared_root = Path(self.temp_dir.name) / "shared_inbox"
        shared_root.mkdir(parents=True)
        self.workflow = _FakeWorkflow(shared_root)
        (self.workflow.service.settings.browser_profiles_dir / "wechat").mkdir(parents=True, exist_ok=True)
        self.window = MainWindow(workflow=self.workflow)
        self.window._watcher_running = True

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def test_wechat_submission_uses_browser_when_profile_exists(self) -> None:
        self.window.url_input.setText("https://mp.weixin.qq.com/s/demo")

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

        self.assertEqual(len(self.workflow.export_browser_calls), 1)
        self.assertEqual(len(self.workflow.export_url_calls), 0)
        self.assertEqual(self.workflow.export_browser_calls[0]["platform"], "wechat")

    def test_bilibili_watchlater_submission_uses_browser_when_profile_exists(self) -> None:
        (self.workflow.service.settings.browser_profiles_dir / "bilibili").mkdir(parents=True, exist_ok=True)
        self.window.url_input.setText("https://www.bilibili.com/watchlater/#/list")

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

        self.assertEqual(len(self.workflow.export_browser_calls), 1)
        self.assertEqual(len(self.workflow.export_url_calls), 0)
        self.assertEqual(self.workflow.export_browser_calls[0]["platform"], "bilibili")
        self.assertEqual(
            self.workflow.export_browser_calls[0]["profile_dir"],
            self.workflow.service.settings.browser_profiles_dir / "bilibili",
        )


class _FakeWorkflow:
    def __init__(self, shared_root: Path) -> None:
        self.service = _FakeService(shared_root)
        self.export_url_calls: list[dict[str, object]] = []
        self.export_browser_calls: list[dict[str, object]] = []
        self.save_result_to_library_calls: list[object] = []
        self.restore_library_interpretation_calls: list[tuple[str, str]] = []

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

    def export_browser_job(
        self,
        *,
        url: str,
        platform: str | None = None,
        requested_mode: str = "auto",
        video_download_mode: str = "audio",
        profile_dir: Path | None = None,
        wait_for_selector: str | None = None,
        wait_for_selector_state: str | None = None,
        on_progress=None,
    ) -> OperationViewState:
        self.export_browser_calls.append(
            {
                "url": url,
                "platform": platform,
                "requested_mode": requested_mode,
                "video_download_mode": video_download_mode,
                "profile_dir": profile_dir,
                "wait_for_selector": wait_for_selector,
                "wait_for_selector_state": wait_for_selector_state,
            }
        )
        if on_progress is not None:
            on_progress("collecting")
            on_progress("exporting")
        return OperationViewState(
            operation="export-browser-job",
            status="success",
            summary="ok",
            job=JobExportSnapshot(
                job_id="job-789",
                job_dir=self.service.settings.effective_shared_inbox_root / "incoming" / "job-789",
                payload_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-789" / "payload.html",
                metadata_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-789" / "metadata.json",
                ready_path=self.service.settings.effective_shared_inbox_root / "incoming" / "job-789" / "READY",
            ),
        )

    def save_result_to_library(self, entry) -> OperationViewState:
        self.save_result_to_library_calls.append(entry)
        return OperationViewState(
            operation="save-result-to-library",
            status="success",
            summary="Saved to library: entry-123",
            library=type(
                "LibrarySnapshot",
                (),
                {"entry_id": "entry-123", "trashed_interpretation_count": 0},
            )(),
        )

    def restore_library_interpretation(self, entry_id: str, interpretation_id: str) -> OperationViewState:
        self.restore_library_interpretation_calls.append((entry_id, interpretation_id))
        return OperationViewState(
            operation="restore-library-interpretation",
            status="success",
            summary=f"Restored library entry: {entry_id}",
            library=type(
                "LibrarySnapshot",
                (),
                {"entry_id": entry_id, "trashed_interpretation_count": 1},
            )(),
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
        self.browser_profiles_dir = shared_root / "profiles"
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


def _library_processed_entry(shared_root: Path, job_id: str, *, source_url: str) -> _Entry:
    entry = _processed_entry(job_id)
    job_dir = shared_root / "processed" / job_id
    (job_dir / "analysis" / "llm").mkdir(parents=True, exist_ok=True)
    (job_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (job_dir / "normalized.json").write_text("{}", encoding="utf-8")
    (job_dir / "normalized.md").write_text("# Headline\n\nBody", encoding="utf-8")
    (job_dir / "analysis" / "llm" / "analysis_result.json").write_text("{}", encoding="utf-8")
    (job_dir / "analysis" / "insight_card.png").write_bytes(b"png")
    entry.job_dir = job_dir
    entry.source_url = source_url
    entry.title = "Macro Note"
    entry.author = "Author"
    entry.published_at = "2026-04-07"
    entry.platform = "wechat"
    entry.metadata_path = job_dir / "metadata.json"
    entry.analysis_json_path = job_dir / "analysis" / "llm" / "analysis_result.json"
    entry.normalized_json_path = job_dir / "normalized.json"
    entry.normalized_md_path = job_dir / "normalized.md"
    entry.details = {
        "metadata": {
            "source_url": source_url,
            "final_url": source_url,
            "platform": "wechat",
            "collection_mode": "browser",
            "content_type": "html",
            "collected_at": "2026-04-07T18:32:00+08:00",
        },
        "structured_result": {
            "summary": {"headline": "Headline", "short_text": "Short"},
            "product_view": {"layout": "analysis_brief", "title": "Headline", "sections": []},
            "editorial": {
                "resolved_reading_goal": "argument",
                "resolved_domain_template": "macro_business",
                "route_key": "argument.macro_business",
            },
        },
        "product_view": {"layout": "analysis_brief", "title": "Headline", "sections": []},
        "normalized": {
            "metadata": {
                "llm_processing": {
                    "resolved_mode": "argument",
                    "resolved_reading_goal": "argument",
                    "resolved_domain_template": "macro_business",
                    "route_key": "argument.macro_business",
                }
            }
        },
        "insight_card_path": job_dir / "analysis" / "insight_card.png",
    }
    return entry


def _library_guide_entry(shared_root: Path, job_id: str, *, source_url: str) -> _Entry:
    entry = _library_processed_entry(shared_root, job_id, source_url=source_url)
    entry.details["structured_result"] = {
        "summary": {"headline": "Guide headline", "short_text": "Guide short summary"},
        "key_points": [
            {
                "title": "Step 1",
                "details": "先把事实与可核对清单列出来。",
            }
        ],
        "editorial": {
            "resolved_mode": "guide",
            "base": {
                "core_summary": {"value": "Guide core summary."},
                "bottom_line": {"value": "Guide bottom line."},
            },
            "mode_payload": {
                "recommended_steps": [{"value": "先核对换帅时间线"}],
                "tips": [{"value": "先看接任者背景是否匹配问题"}],
                "pitfalls": [{"value": "不要把相关性直接当因果"}],
                "prerequisites": [{"value": "先准备财报和区域数据"}],
                "quick_win": {"value": "先搭一页品牌诊断看板。"},
            },
        },
        "product_view": {},
    }
    entry.details["product_view"] = {}
    entry.details["normalized"]["metadata"]["llm_processing"].update(
        {
            "resolved_mode": "guide",
            "resolved_reading_goal": "guide",
            "route_key": "guide.generic",
        }
    )
    return entry


class _FakeLibraryDialog:
    def __init__(self) -> None:
        self.reload_calls = 0
        self.accept_calls = 0

    def reload(self) -> None:
        self.reload_calls += 1

    def accept(self) -> None:
        self.accept_calls += 1


if __name__ == "__main__":
    unittest.main()
