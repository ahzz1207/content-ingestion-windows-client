import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPointingDevice
from PySide6.QtWidgets import QApplication, QLabel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.insight_brief import HeroBrief, InsightBriefV2, ViewpointItem
from windows_client.gui.inline_result_view import InlineResultView


def _app():
    return QApplication.instance() or QApplication([])


def _write_valid_png(path: Path) -> None:
    image = QImage(1, 1, QImage.Format_ARGB32)
    image.fill(QColor("#3a67d6"))
    image.save(str(path), "PNG")


def _make_entry():
    class _Entry:
        pass

    entry = _Entry()
    entry.state = "processed"
    entry.analysis_state = "ready"
    entry.summary = ""
    entry.preview_text = None
    entry.job_id = "job-1"
    entry.title = "Title"
    entry.author = "Author"
    entry.published_at = "2026-04-02"
    entry.platform = "generic"
    entry.source_url = "https://example.com/item"
    entry.canonical_url = None
    entry.metadata_path = None
    entry.analysis_json_path = None
    entry.normalized_json_path = None
    entry.normalized_md_path = None
    entry.status_path = None
    entry.error_path = None
    entry.job_dir = None
    entry.details = {"visual_findings": []}
    return entry


class InlineResultViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_processed_entry_enables_save_to_library_button(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertFalse(view.save_to_library_button.isHidden())
        self.assertTrue(view.save_to_library_button.isEnabled())
        self.assertEqual(view.save_to_library_button.objectName(), "PrimaryButton")
        self.assertEqual(view.new_url_button.objectName(), "GhostButton")

    def test_processed_entry_shows_open_library_button(self) -> None:
        view = InlineResultView()

        view.load_entry(_make_entry(), brief=None, resolved_mode="argument")

        self.assertFalse(view.open_library_button.isHidden())
        self.assertTrue(view.open_library_button.isEnabled())

    def test_local_file_entry_hides_raw_file_url_in_hero_source(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.platform = "local"
        entry.source_url = "file:///H:/docs/report.pdf"

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertTrue(view._hero_source.isHidden())
        self.assertIn("report.pdf", view._hero_byline.text())

    def test_local_virtual_source_hides_raw_local_url_in_hero_source(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.platform = "local"
        entry.source_url = "local://text/job-1"

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertTrue(view._hero_source.isHidden())
        self.assertIn("本地文件", view._hero_byline.text())

    def test_local_entry_without_title_uses_untitled_document_fallback(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.platform = "local"
        entry.title = ""
        entry.source_url = "local://text/job-1"

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertEqual(view._hero_title.text(), "未命名文档")

    def test_show_library_save_banner_makes_feedback_visible(self) -> None:
        view = InlineResultView()

        view.show_library_banner("Source 已保存到知识库")

        self.assertFalse(view._library_banner_frame.isHidden())
        self.assertIn("知识库", view._library_banner_label.text())
        self.assertTrue(view._open_library_entry_btn.isHidden())
        self.assertFalse(view._open_library_banner_btn.isHidden())
        self.assertEqual(view._open_library_banner_btn.text(), "查看知识库")

    def test_show_library_banner_reuses_single_hide_timer(self) -> None:
        view = InlineResultView()

        view.show_library_banner("First")
        first_timer = view._library_banner_timer
        view.show_library_banner("Second")

        self.assertIs(view._library_banner_timer, first_timer)
        self.assertTrue(view._library_banner_timer.isActive())
        self.assertEqual(view._library_banner_label.text(), "Second")

    def test_open_library_entry_button_emits_saved_entry_id(self) -> None:
        view = InlineResultView()
        opened_entry_ids: list[str] = []
        view.open_library_entry_requested.connect(opened_entry_ids.append)

        view.show_library_banner("Saved", entry_id="lib_0001")

        self.assertFalse(view._open_library_entry_btn.isHidden())
        self.assertEqual(view._open_library_entry_btn.text(), "打开条目")
        view._open_library_entry_btn.click()

        self.assertEqual(opened_entry_ids, ["lib_0001"])

    def test_open_library_entry_button_falls_back_to_library_dialog_without_saved_entry_id(self) -> None:
        view = InlineResultView()
        open_requests: list[bool] = []
        view.open_library_requested.connect(lambda: open_requests.append(True))

        view.show_library_banner("Saved")
        view._open_library_entry_btn.click()

        self.assertEqual(open_requests, [True])

    def test_load_entry_clears_existing_update_and_library_banners(self) -> None:
        view = InlineResultView()

        view.show_update_banner("Updated")
        view.show_library_banner("Saved")
        view.load_entry(_make_entry(), brief=None, resolved_mode="argument")

        self.assertTrue(view._update_banner_frame.isHidden())
        self.assertEqual(view._update_banner_label.text(), "")
        self.assertTrue(view._library_banner_frame.isHidden())
        self.assertEqual(view._library_banner_label.text(), "")
        self.assertFalse(view._library_banner_timer.isActive())

    def test_stale_update_banner_hide_callback_does_not_hide_newer_banner(self) -> None:
        view = InlineResultView()

        view.show_update_banner("First")
        first_generation = view._update_banner_generation
        view.show_update_banner("Second")
        view._hide_update_banner(first_generation)

        self.assertFalse(view._update_banner_frame.isHidden())
        self.assertEqual(view._update_banner_label.text(), "Second")

    def test_visual_evidence_stays_hidden_when_no_valid_rows_render(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.details = {
            "visual_findings": [
                {"description": "   "},
                {"frame_timestamp_ms": 1200},
                "not-a-dict",
            ]
        }

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertTrue(view._visual_frame.isHidden())

    def test_save_as_markdown_handles_write_errors_gracefully(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        view.load_entry(entry, brief=None, resolved_mode="argument")

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "result.md"
            with patch("windows_client.gui.inline_result_view.QFileDialog.getSaveFileName", return_value=(str(target), "")):
                with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                    view._save_as_markdown()

        self.assertEqual(view._save_btn.text(), "保存失败")
        self.assertTrue(view._save_btn.isEnabled())

    def test_save_insight_card_handles_copy_errors_gracefully(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.details = {"visual_findings": [], "insight_card_path": Path(__file__)}
        view.load_entry(entry, brief=None, resolved_mode="argument")

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "card.png"
            with patch("windows_client.gui.inline_result_view.QFileDialog.getSaveFileName", return_value=(str(target), "")):
                with patch("shutil.copy2", side_effect=OSError("permission denied")):
                    view._save_insight_card()

        self.assertEqual(view._card_save_btn.text(), "保存失败")
        self.assertTrue(view._card_save_btn.isEnabled())

    def test_load_entry_shows_mode_chip_for_brief_view(self) -> None:
        view = InlineResultView()
        brief = InsightBriefV2(
            hero=HeroBrief(
                title="Core summary",
                one_sentence_take="One sentence",
                content_kind="analysis",
                author_stance="critical",
            ),
            quick_takeaways=[],
            viewpoints=[],
            coverage=None,
            gaps=[],
            synthesis_conclusion=None,
        )

        view.load_entry(_make_entry(), brief=brief, resolved_mode="guide")

        self.assertFalse(view._mode_chip.isHidden())
        self.assertEqual(view._mode_chip.text(), "实用提炼")

    def test_guide_brief_uses_compact_step_items_instead_of_editorial_key_point_cards(self) -> None:
        view = InlineResultView()
        brief = InsightBriefV2(
            hero=HeroBrief(
                title="Guide summary",
                one_sentence_take="Guide take",
                content_kind="analysis",
                author_stance="pragmatic",
            ),
            quick_takeaways=[],
            viewpoints=[
                ViewpointItem(
                    statement="先核对换帅时间线",
                    kind="key_point",
                    why_it_matters=None,
                    support_level=None,
                )
            ],
            coverage=None,
            gaps=[],
            synthesis_conclusion=None,
        )

        view.load_entry(_make_entry(), brief=brief, resolved_mode="guide")

        step_item = view._takeaways_list_layout.itemAt(0).widget()
        self.assertIsNotNone(step_item)
        assert step_item is not None
        self.assertEqual(step_item.objectName(), "GuideStepItem")
        labels = step_item.findChildren(QLabel)
        self.assertTrue(any(label.text() == "步骤 1" for label in labels))
        self.assertFalse(any(label.objectName() == "TakeawayIndexed" for label in labels))

    def test_product_view_hides_duplicate_hero_take_when_same_as_title(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "product_view": {
                            "hero": {
                                "title": "同一段摘要文本",
                                "dek": "同一段摘要文本",
                            },
                            "sections": [
                                {
                                    "id": "s1",
                                    "title": "Section",
                                    "priority": 1,
                                    "blocks": [{"type": "paragraph", "text": "Body"}],
                                }
                            ],
                        }
                    }
                },
                "metadata": {
                    "llm_processing": {
                        "status": "pass",
                        "resolved_mode": "argument",
                        "resolved_domain_template": "macro_business",
                    }
                },
            }
        }

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertEqual(view._hero_title.text(), "同一段摘要文本")
        self.assertTrue(view._hero_take.isHidden())

    def test_product_view_shows_mode_and_domain_chips_in_hero_area(self) -> None:
        view = InlineResultView()
        entry = _make_entry()
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "product_view": {
                            "hero": {
                                "title": "标题",
                                "dek": "不同的短摘要",
                            },
                            "sections": [
                                {
                                    "id": "s1",
                                    "title": "Section",
                                    "priority": 1,
                                    "blocks": [{"type": "paragraph", "text": "Body"}],
                                }
                            ],
                        }
                    }
                },
                "metadata": {
                    "llm_processing": {
                        "status": "pass",
                        "resolved_mode": "guide",
                        "resolved_domain_template": "macro_business",
                    }
                },
            }
        }

        view.load_entry(entry, brief=None, resolved_mode="guide")

        self.assertFalse(view._hero_tags_row.isHidden())
        self.assertEqual(view._mode_chip.text(), "实用提炼")
        self.assertFalse(view._content_kind_chip.isHidden())
        self.assertEqual(view._content_kind_chip.text(), "宏观商业")

    def test_long_reading_section_uses_v4_product_label(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._long_reading_heading.text(), "深度解读")

    def test_image_summary_section_precedes_long_reading_section(self) -> None:
        view = InlineResultView()

        self.assertLess(
            view._reading_stream_layout.indexOf(view._card_frame),
            view._reading_stream_layout.indexOf(view._long_reading_heading),
        )

    def test_result_view_uses_dedicated_reading_stream_container(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._reading_stream_frame.objectName(), "ReadingStream")

    def test_result_view_uses_dedicated_context_rail(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._context_rail_frame.objectName(), "ContextRail")

    def test_result_view_uses_v4_chinese_section_and_action_copy(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._context_title.text(), "Library Context")
        self.assertIn("上下文", view._context_summary.text())
        self.assertEqual(view._image_summary_heading.text(), "视觉总结")
        self.assertEqual(view._long_reading_heading.text(), "深度解读")
        self.assertEqual(view._open_folder_btn.text(), "打开目录")
        self.assertEqual(view._export_json_btn.text(), "导出 JSON")
        self.assertEqual(view._copy_btn.text(), "复制")
        self.assertEqual(view._save_btn.text(), "保存 Markdown")

    def test_long_reading_heading_hides_when_brief_result_has_no_browser_surface(self) -> None:
        view = InlineResultView()
        brief = InsightBriefV2(
            hero=HeroBrief(
                title="Title",
                one_sentence_take="Take",
                content_kind="analysis",
                author_stance="critical",
            ),
            quick_takeaways=[],
            viewpoints=[],
            coverage=None,
            gaps=[],
            synthesis_conclusion=None,
        )

        view.load_entry(_make_entry(), brief=brief, resolved_mode="argument")

        self.assertTrue(view._browser.isHidden())
        self.assertTrue(view._long_reading_heading.isHidden())

    def test_result_view_uses_v4_chinese_supporting_section_labels(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._verification_frame.layout().itemAt(0).widget().text(), "事实核验")
        self.assertEqual(view._bottom_line_frame.layout().itemAt(0).widget().text(), "核心结论")
        self.assertEqual(view._gaps_frame.layout().itemAt(0).widget().text(), "问题与下一步")
        self.assertEqual(view._visual_frame.layout().itemAt(0).widget().text(), "视觉证据")

    def test_result_view_uses_dedicated_hero_shell_container(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._hero_shell.objectName(), "ImmersiveHero")

    def test_result_view_places_primary_actions_inside_hero_shell(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._hero_topbar.objectName(), "HeroTopBar")
        self.assertIs(view._hero_action_strip.parentWidget(), view._hero_topbar)
        self.assertIs(view._hero_topbar.parentWidget(), view._hero_shell)

    def test_result_view_uses_dedicated_hero_meta_row(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._hero_meta_row.objectName(), "HeroMetaRow")

    def test_result_view_uses_reading_stream_shell(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._reading_stream_shell.objectName(), "ReadingStreamShell")

    def test_result_view_uses_context_rail_shell(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._context_rail_shell.objectName(), "ContextRailShell")

    def test_result_view_hero_shell_contains_primary_result_actions(self) -> None:
        view = InlineResultView()

        self.assertIs(view._reanalyze_btn.parentWidget().parentWidget(), view._hero_topbar)
        self.assertIs(view._save_to_library_btn.parentWidget().parentWidget(), view._hero_topbar)
        self.assertIs(view._hero_topbar.parentWidget(), view._hero_shell)

    def test_result_view_top_bar_keeps_only_global_navigation_actions(self) -> None:
        view = InlineResultView()

        self.assertIs(view._new_url_button.parentWidget(), view._top_bar_widget)
        self.assertIs(view._history_btn.parentWidget(), view._top_bar_widget)

    def test_result_view_uses_dedicated_image_summary_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._card_frame.objectName(), "ImageSummaryCard")

    def test_result_view_takeaways_use_stream_section_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._takeaways_frame.objectName(), "StreamSection")

    def test_result_view_gaps_use_stream_section_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._gaps_frame.objectName(), "StreamSection")

    def test_result_view_stacks_context_rail_below_stream_in_narrow_mode(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertEqual(view._content_shell_layout.getItemPosition(0), (0, 0, 1, 1))
        self.assertEqual(view._content_shell_layout.getItemPosition(1), (1, 0, 1, 1))

    def test_result_view_narrow_mode_clears_side_gutter(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertEqual(view._content_shell_layout.columnStretch(0), 1)
        self.assertEqual(view._content_shell_layout.columnStretch(1), 0)
        self.assertEqual(view._content_shell_layout.horizontalSpacing(), 0)

    def test_result_view_marks_narrow_layout_state_when_below_breakpoint(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertTrue(view.property("isNarrowLayout"))

    def test_result_view_clears_narrow_layout_state_when_above_breakpoint(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)
        view._apply_layout_mode(available_width=1400)

        self.assertFalse(view.property("isNarrowLayout"))

    def test_load_entry_marks_image_led_state_when_valid_insight_card_loads(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "insight_card.png"
            _write_valid_png(png_path)
            entry.details = {"visual_findings": [], "insight_card_path": png_path}

            view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertFalse(view._card_frame.isHidden())
        self.assertTrue(view.property("hasInsightCard"))

    def test_load_entry_keeps_compact_text_state_when_insight_card_is_missing(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertTrue(view._card_frame.isHidden())
        self.assertFalse(view.property("hasInsightCard"))

    def test_clicking_insight_card_opens_fullscreen_preview(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "insight_card.png"
            _write_valid_png(png_path)
            entry.details = {"visual_findings": [], "insight_card_path": png_path}
            view.load_entry(entry, brief=None, resolved_mode="argument")

            with patch.object(view, "_open_card_fullscreen") as open_preview:
                event = QMouseEvent(
                    QMouseEvent.MouseButtonPress,
                    QPointF(view._card_image_label.rect().center()),
                    QPointF(view._card_image_label.rect().center()),
                    QPointF(view._card_image_label.rect().center()),
                    Qt.LeftButton,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    QPointingDevice.primaryPointingDevice(),
                )
                view._card_image_label.mousePressEvent(event)

        open_preview.assert_called_once_with()

    def test_result_view_uses_tighter_stream_spacing_in_narrow_mode(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertEqual(view._reading_stream_layout.spacing(), 16)

    def test_missing_insight_card_clears_any_previous_pixmap(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "insight_card.png"
            _write_valid_png(png_path)
            entry.details = {"visual_findings": [], "insight_card_path": png_path}
            view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertIsNotNone(view._card_image_label.pixmap())

        view.load_entry(_make_entry(), brief=None, resolved_mode="argument")

        self.assertTrue(view._card_frame.isHidden())
        pixmap = view._card_image_label.pixmap()
        self.assertTrue(pixmap is None or pixmap.isNull())

    def test_key_point_items_use_editorial_object_names(self) -> None:
        item = InlineResultView._make_key_point_item(1, "Statement", "Details")

        self.assertEqual(item.objectName(), "EditorialKeyPoint")

    def test_warning_banners_use_editorial_warning_surface(self) -> None:
        banner, _label = InlineResultView._make_warning_banner()

        self.assertEqual(banner.objectName(), "EditorialWarning")


if __name__ == "__main__":
    unittest.main()
