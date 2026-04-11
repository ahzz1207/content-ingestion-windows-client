import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from windows_client.gui.result_renderer import (
    PREVIEW_STYLESHEET,
    _coverage_warning_html,
    _markdown_filename,
    _preview_html,
    _resolved_evidence_html,
    _structured_preview_html,
    entry_to_markdown,
)


def _app():
    return QApplication.instance() or QApplication([])


def _make_entry(**kwargs):
    """Minimal mock ResultWorkspaceEntry."""

    class _Entry:
        pass

    e = _Entry()
    e.state = kwargs.get("state", "processed")
    e.analysis_state = kwargs.get("analysis_state", "ready")
    e.summary = kwargs.get("summary", "")
    e.preview_text = kwargs.get("preview_text", None)
    e.job_id = kwargs.get("job_id", "test-job")
    e.title = kwargs.get("title", None)
    e.author = kwargs.get("author", None)
    e.published_at = kwargs.get("published_at", None)
    e.platform = kwargs.get("platform", None)
    e.source_url = kwargs.get("source_url", None)
    e.canonical_url = kwargs.get("canonical_url", None)
    e.metadata_path = None
    e.analysis_json_path = None
    e.normalized_json_path = None
    e.normalized_md_path = None
    e.status_path = None
    e.error_path = None
    e.details = kwargs.get("details", {})
    return e


def _structured_entry(key_points_count: int = 3) -> object:
    entry = _make_entry()
    key_points = [
        {
            "id": f"kp-{i}",
            "title": f"Point {i}",
            "details": f"Detail {i}",
            "resolved_evidence": [{"preview_text": f"Evidence {i}", "kind": "transcript", "start_ms": i * 1000}],
        }
        for i in range(key_points_count)
    ]
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "summary": {"headline": "Test", "short_text": "Brief summary."},
                    "key_points": key_points,
                }
            },
            "metadata": {"llm_processing": {"status": "pass"}},
        }
    }
    return entry


def _product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "summary": {"headline": "Legacy headline", "short_text": "Legacy summary."},
                    "key_points": [{"title": "Legacy point", "details": "Legacy detail"}],
                    "product_view": {
                        "layout": "review_curation",
                        "hero": {
                            "title": "Product hero",
                            "dek": "Product dek",
                            "bottom_line": "Product bottom line",
                        },
                        "chips": [{"label": "Audience", "value": "Operators"}],
                        "sections": [
                            {
                                "id": "section-1",
                                "title": "Product section",
                                "kind": "analysis",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [
                                    {"type": "paragraph", "text": "Product paragraph."},
                                    {"type": "bullet_list", "items": ["Bullet one", "Bullet two"]},
                                ],
                            }
                        ],
                        "render_hints": {"layout_family": "analysis_brief"},
                    },
                }
            },
            "metadata": {"llm_processing": {"status": "pass"}},
        }
    }
    return entry


def _product_view_only_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "narrative_digest",
                        "hero": {
                            "title": "Product-only hero",
                            "dek": "Product-only dek",
                            "bottom_line": "Product-only bottom line",
                        },
                        "sections": [
                            {
                                "id": "section-1",
                                "title": "Product-only section",
                                "kind": "analysis",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [
                                    {"type": "paragraph", "text": "Product-only paragraph."},
                                ],
                            }
                        ],
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass"}},
        }
    }
    return entry


def _argument_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "analysis_brief",
                        "hero": {
                            "title": "Policy claim is plausible but operationally weak",
                            "dek": "The article makes a case for direction, not for delivery readiness.",
                            "bottom_line": "You should separate the strategic argument from the execution claim.",
                        },
                        "sections": [
                            {
                                "id": "judgment",
                                "title": "核心判断",
                                "kind": "core_judgment",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "The argument works at the strategic layer."}],
                            },
                            {
                                "id": "arguments",
                                "title": "主要论点",
                                "kind": "main_arguments",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["Argument A", "Argument B"]}],
                            },
                            {
                                "id": "evidence",
                                "title": "关键论据",
                                "kind": "evidence",
                                "priority": 3,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["Evidence A", "Evidence B"]}],
                            },
                            {
                                "id": "tensions",
                                "title": "张力与漏洞",
                                "kind": "tensions",
                                "priority": 4,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["Risk A"]}],
                            },
                        ],
                        "render_hints": {"layout_family": "analysis_brief"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "argument"}},
        }
    }
    return entry


def _question_driven_analysis_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "analysis_brief",
                        "hero": {
                            "title": "先回答你真正会问的问题",
                            "dek": "把分析改写成读者更容易扫描的问答式结构。",
                            "bottom_line": "重点不是分类卡片，而是按阅读问题组织判断。",
                        },
                        "sections": [
                            {
                                "id": "question-1",
                                "title": "它解决了什么问题？",
                                "kind": "question_block",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "它先界定问题，再说明为什么值得关心。"}],
                            },
                            {
                                "id": "reader-value-1",
                                "title": "这对我意味着什么？",
                                "kind": "reader_value",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["先看是否影响你的判断", "再决定要不要继续深读"]}],
                            },
                        ],
                        "render_hints": {"layout_family": "analysis_brief"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "argument"}},
        }
    }
    return entry


def _guide_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "practical_guide",
                        "hero": {
                            "title": "一句话先看完",
                            "dek": "保留最关键的结论即可。",
                            "bottom_line": "别被长篇背景带走。",
                        },
                        "sections": [
                            {
                                "id": "summary",
                                "title": "一句话总结",
                                "kind": "one_line_summary",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "先抓结论，再看是否需要细节。"}],
                            },
                            {
                                "id": "takeaways",
                                "title": "核心要点",
                                "kind": "core_takeaways",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["要点 A", "要点 B", "要点 C"]}],
                            },
                            {
                                "id": "remember",
                                "title": "记住这件事",
                                "kind": "remember_this",
                                "priority": 3,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "真正改变判断的是最后一个结论。"}],
                            },
                        ],
                        "render_hints": {"layout_family": "practical_guide"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "guide"}},
        }
    }
    return entry


def _render_hints_only_guide_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "hero": {
                            "title": "Guide hero",
                            "dek": "Guide dek",
                        },
                        "sections": [
                            {
                                "id": "actions",
                                "title": "推荐步骤",
                                "kind": "actions",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "step_list", "items": ["先核对时间线", "再看财报"]}],
                            },
                            {
                                "id": "risks",
                                "title": "常见误区",
                                "kind": "risks",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "warning_list", "items": ["不要把相关性当因果"]}],
                            },
                        ],
                        "render_hints": {"layout_family": "practical_guide"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "guide"}},
        }
    }
    return entry


def _review_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "review_curation",
                        "hero": {
                            "title": "值得一读，但更适合已经在跟这个主题的人",
                            "dek": "亮点明确，但不是面向所有人的通用入门。",
                        },
                        "sections": [
                            {
                                "id": "highlights",
                                "title": "Highlights",
                                "kind": "highlights",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["亮点 A", "亮点 B"]}],
                            },
                            {
                                "id": "audience",
                                "title": "Who it's for",
                                "kind": "audience",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "适合已经在看这个板块的人。"}],
                            },
                            {
                                "id": "reservations",
                                "title": "Reservations",
                                "kind": "reservations",
                                "priority": 3,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["保留点 A"]}],
                            },
                        ],
                        "render_hints": {"layout_family": "review_curation"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "review"}},
        }
    }
    return entry


def _narrative_product_view_entry() -> object:
    entry = _make_entry()
    entry.details = {
        "normalized": {
            "asset": {
                "result": {
                    "product_view": {
                        "layout": "narrative_digest",
                        "hero": {
                            "title": "一段逐步失去确定感、又重新组织自我的经历",
                            "dek": "重点不在结论，而在叙事如何推进。",
                        },
                        "sections": [
                            {
                                "id": "beats",
                                "title": "Story beats",
                                "kind": "story_beats",
                                "priority": 1,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["起点", "转折", "收束"]}],
                            },
                            {
                                "id": "themes",
                                "title": "Themes",
                                "kind": "themes",
                                "priority": 2,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "bullet_list", "items": ["主题 A", "主题 B"]}],
                            },
                            {
                                "id": "takeaway",
                                "title": "Takeaway",
                                "kind": "takeaway",
                                "priority": 3,
                                "collapsed_by_default": False,
                                "blocks": [{"type": "paragraph", "text": "最后留下的是一条更个人化的结论。"}],
                            },
                        ],
                        "render_hints": {"layout_family": "narrative_digest"},
                    }
                }
            },
            "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "narrative"}},
        }
    }
    return entry


class TestStructuredPreviewHtmlNoTruncation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_all_key_points_rendered(self) -> None:
        entry = _structured_entry(key_points_count=5)
        html = _structured_preview_html(entry)
        self.assertIsNotNone(html)
        for i in range(5):
            self.assertIn(f"Point {i}", html)

    def test_no_cap_on_synthesis_items(self) -> None:
        entry = _make_entry()
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "summary": {"headline": "H", "short_text": "S"},
                        "synthesis": {
                            "final_answer": "done",
                            "next_steps": [f"Step {i}" for i in range(5)],
                            "open_questions": [f"Q{i}" for i in range(5)],
                        },
                    }
                },
                "metadata": {"llm_processing": {"status": "pass"}},
            }
        }
        html = _structured_preview_html(entry)
        self.assertIsNotNone(html)
        for i in range(5):
            self.assertIn(f"Step {i}", html)
            self.assertIn(f"Q{i}", html)

    def test_mode_pill_renders_when_resolved_mode_present(self) -> None:
        entry = _structured_entry()
        entry.details["normalized"]["metadata"] = {"llm_processing": {}}

        html = _structured_preview_html(entry, resolved_mode="guide")

        self.assertIsNotNone(html)
        self.assertIn("实用提炼", html)

    def test_mode_pill_renders_for_editorial_only_result_in_fallback(self) -> None:
        entry = _make_entry()
        entry.details = {
            "normalized": {
                "asset": {
                    "result": {
                        "editorial": {
                            "resolved_mode": "review",
                            "base": {"core_summary": {"value": "Review summary."}},
                        }
                    }
                },
                "metadata": {"llm_processing": {"resolved_mode": "review"}},
            }
        }

        html = _structured_preview_html(entry, resolved_mode="review")

        self.assertIsNotNone(html)
        self.assertIn("推荐导览", html)

    def test_product_view_renders_before_legacy_shape_when_present(self) -> None:
        entry = _product_view_entry()

        html = _structured_preview_html(entry)

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("Product hero", html)
        self.assertIn("Product section", html)
        self.assertIn("Product paragraph.", html)
        self.assertIn("Bullet one", html)
        self.assertNotIn("Legacy headline", html)
        self.assertNotIn("Legacy point", html)

    def test_product_view_falls_back_to_legacy_rendering_when_absent(self) -> None:
        entry = _structured_entry(key_points_count=1)

        html = _structured_preview_html(entry)

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("Test", html)
        self.assertIn("Point 0", html)

    def test_product_view_renders_from_normalized_payload_without_legacy_fields(self) -> None:
        entry = _product_view_only_entry()

        html = _structured_preview_html(entry)

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("Product-only hero", html)
        self.assertIn("Product-only section", html)
        self.assertIn("Product-only paragraph.", html)

    def test_argument_product_view_renders_as_analysis_brief_not_compact_takeaway(self) -> None:
        entry = _argument_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="argument")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("analysis-brief-layout", html)
        self.assertIn("analysis-hero", html)
        self.assertIn("核心判断", html)
        self.assertIn("主要论点", html)
        self.assertIn("关键论据", html)
        self.assertIn("张力与漏洞", html)
        self.assertNotIn("一句话总结", html)

    def test_question_driven_analysis_sections_render_literal_titles_as_headings(self) -> None:
        entry = _question_driven_analysis_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="argument")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("analysis-brief-layout", html)
        self.assertIn("先回答你真正会问的问题", html)
        self.assertIn("把分析改写成读者更容易扫描的问答式结构。", html)
        self.assertIn("重点不是分类卡片，而是按阅读问题组织判断。", html)
        self.assertIn("<h2>它解决了什么问题？</h2>", html)
        self.assertIn("<h2>这对我意味着什么？</h2>", html)
        self.assertEqual(html.count("analysis-section-label"), 0)
        self.assertEqual(html.count("analysis-card-grid"), 0)

    def test_reader_value_analysis_sections_do_not_relabel_to_legacy_argument_buckets(self) -> None:
        entry = _question_driven_analysis_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="argument")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertNotIn("核心判断", html)
        self.assertNotIn("主要论点", html)
        self.assertNotIn("analysis-section-label", html)

    def test_legacy_analysis_brief_sections_keep_badge_and_card_grid_presentation(self) -> None:
        entry = _argument_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="argument")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("analysis-section-label", html)
        self.assertIn("analysis-card-grid", html)
        self.assertIn("核心判断", html)
        self.assertIn("主要论点", html)

    def test_explicit_layout_wins_over_conflicting_render_hints_layout_family(self) -> None:
        entry = _product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="review")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("review-curation-layout", html)
        self.assertIn("review-curation-hero", html)
        self.assertNotIn("analysis-brief-layout", html)
        self.assertNotIn("analysis-hero", html)

    def test_guide_product_view_renders_as_compact_takeaway_not_analysis_brief(self) -> None:
        entry = _guide_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="guide")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("guide-digest-layout", html)
        self.assertIn("guide-compact-hero", html)
        self.assertIn("一句话总结", html)
        self.assertIn("核心要点", html)
        self.assertIn("记住这件事", html)
        self.assertNotIn("关键论据", html)

    def test_product_view_uses_render_hints_layout_family_for_guide_detection(self) -> None:
        entry = _render_hints_only_guide_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="guide")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("guide-digest-layout", html)
        self.assertIn("Guide hero", html)
        self.assertIn("推荐步骤", html)

    def test_review_product_view_renders_as_curated_recommendation_layout(self) -> None:
        entry = _review_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="review")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("review-curation-layout", html)
        self.assertIn("review-curation-hero", html)
        self.assertIn("Highlights", html)
        self.assertIn("Who it&#x27;s for", html)
        self.assertIn("Reservations", html)

    def test_narrative_product_view_renders_as_story_shaped_layout(self) -> None:
        entry = _narrative_product_view_entry()

        html = _structured_preview_html(entry, resolved_mode="narrative")

        self.assertIsNotNone(html)
        assert html is not None
        self.assertIn("narrative-digest-layout", html)
        self.assertIn("narrative-digest-hero", html)
        self.assertIn("Story beats", html)
        self.assertIn("Themes", html)
        self.assertIn("Takeaway", html)

    def test_preview_stylesheet_supports_editorial_serif_body_typography(self) -> None:
        self.assertIn("Noto Serif SC", PREVIEW_STYLESHEET)
        self.assertIn("serif", PREVIEW_STYLESHEET.lower())

    def test_preview_stylesheet_supports_v4_editorial_reading_surface(self) -> None:
        self.assertIn(".result-hero", PREVIEW_STYLESHEET)
        self.assertIn("box-shadow", PREVIEW_STYLESHEET)
        self.assertIn("border-radius: 24px", PREVIEW_STYLESHEET)

    def test_coverage_warning_html_uses_chinese_product_copy(self) -> None:
        class _FakeCoverage:
            input_truncated = True
            coverage_ratio = 0.5
            used_segments = 3
            total_segments = 6

        entry = _make_entry()
        entry.details = {"coverage": _FakeCoverage()}

        html = _coverage_warning_html(entry)

        self.assertIn("覆盖范围提示", html)
        self.assertIn("50%", html)
        self.assertIn("3/6", html)


class TestResolvedEvidenceHtmlUsesAllRefs(unittest.TestCase):
    def test_all_refs_rendered(self) -> None:
        item = {
            "resolved_evidence": [
                {"preview_text": f"Evidence {i}", "kind": "transcript", "start_ms": 0}
                for i in range(5)
            ]
        }
        html = _resolved_evidence_html(item)
        for i in range(5):
            self.assertIn(f"Evidence {i}", html)

    def test_empty_when_no_resolved_evidence(self) -> None:
        self.assertEqual(_resolved_evidence_html({}), "")


class TestCoverageWarningAppearsWhenTruncated(unittest.TestCase):
    def test_coverage_warning_html_when_truncated(self) -> None:
        class _FakeCoverage:
            input_truncated = True
            coverage_ratio = 0.08
            used_segments = 30
            total_segments = 378

        entry = _make_entry()
        entry.details = {"coverage": _FakeCoverage()}
        html = _coverage_warning_html(entry)
        self.assertIn("8%", html)
        self.assertIn("30/378", html)
        self.assertIn("coverage-warning", html)

    def test_no_warning_when_not_truncated(self) -> None:
        class _FakeCoverage:
            input_truncated = False
            coverage_ratio = 1.0
            used_segments = 100
            total_segments = 100

        entry = _make_entry()
        entry.details = {"coverage": _FakeCoverage()}
        html = _coverage_warning_html(entry)
        self.assertEqual(html, "")

    def test_no_warning_when_no_coverage_data(self) -> None:
        entry = _make_entry()
        html = _coverage_warning_html(entry)
        self.assertEqual(html, "")


class _FakeBrief:
    class hero:
        title = "Test Article"
        one_sentence_take = "A concise take."

    quick_takeaways = ["Point A", "Point B"]
    gaps = ["Open question 1"]
    synthesis_conclusion = "Final answer here."
    coverage = None
    viewpoints = []


class TestEntryToMarkdown(unittest.TestCase):
    def test_full_brief_includes_all_sections(self) -> None:
        entry = _make_entry(
            title="Test Article",
            author="Alice",
            published_at="2026-03-22",
            platform="WeChat",
            source_url="https://example.com/a",
        )
        entry.details = {"insight_brief": _FakeBrief()}
        md = entry_to_markdown(entry)
        self.assertIn("# Test Article", md)
        self.assertIn("A concise take.", md)
        self.assertIn("1. Point A", md)
        self.assertIn("2. Point B", md)
        self.assertIn("Final answer here.", md)
        self.assertIn("Open question 1", md)
        self.assertIn("https://example.com/a", md)
        self.assertNotIn("<", md)  # no HTML tags

    def test_no_brief_falls_back_to_entry_fields(self) -> None:
        entry = _make_entry(title="Fallback Title", summary="Summary text.")
        entry.details = {"insight_brief": None}
        md = entry_to_markdown(entry)
        self.assertIn("# Fallback Title", md)
        self.assertIn("Summary text.", md)

    def test_no_title_uses_untitled(self) -> None:
        entry = _make_entry(title=None, summary="")
        entry.details = {}
        md = entry_to_markdown(entry)
        self.assertIn("# 未命名结果", md)

    def test_empty_sections_omitted(self) -> None:
        class _MinimalBrief:
            class hero:
                title = "T"
                one_sentence_take = "S"

            quick_takeaways = []
            gaps = []
            synthesis_conclusion = None
            coverage = None

        entry = _make_entry()
        entry.details = {"insight_brief": _MinimalBrief()}
        md = entry_to_markdown(entry)
        self.assertNotIn("## 要点提炼", md)
        self.assertNotIn("## 核心结论", md)
        self.assertNotIn("## 问题", md)


class TestEntryToMarkdownVisualFindings(unittest.TestCase):
    def test_visual_findings_included_in_markdown(self) -> None:
        entry = _make_entry(title="Video Article")
        entry.details = {
            "visual_findings": [
                {"id": "vf-1", "frame_timestamp_ms": 5000, "description": "Speaker points at map"},
                {"id": "vf-2", "frame_timestamp_ms": 62000, "description": "Chart displayed"},
            ]
        }
        md = entry_to_markdown(entry)
        self.assertIn("视觉证据", md)
        self.assertIn("Speaker points at map", md)
        self.assertIn("Chart displayed", md)

    def test_visual_findings_omitted_when_empty(self) -> None:
        entry = _make_entry()
        entry.details = {"visual_findings": []}
        md = entry_to_markdown(entry)
        self.assertNotIn("视觉证据", md)


class TestMarkdownFilename(unittest.TestCase):
    def test_ascii_title_produces_slug(self) -> None:
        entry = _make_entry(title="Hello World Article")
        name = _markdown_filename(entry)
        self.assertIn("hello-world-article", name)
        self.assertTrue(name.endswith(".md"))

    def test_no_title_uses_result(self) -> None:
        entry = _make_entry(title=None)
        name = _markdown_filename(entry)
        self.assertIn("result", name)

    def test_special_chars_are_slugified(self) -> None:
        entry = _make_entry(title="Title: A/B? Test!")
        name = _markdown_filename(entry)
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)
        self.assertNotIn("?", name)
        self.assertTrue(name.endswith(".md"))

    def test_long_title_is_truncated(self) -> None:
        entry = _make_entry(title="a" * 100)
        name = _markdown_filename(entry)
        # slug portion should not exceed 48 chars
        slug_part = name[len("2026-03-22-"):]
        self.assertLessEqual(len(slug_part.replace(".md", "")), 48)


if __name__ == "__main__":
    unittest.main()
