import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.insight_brief import HeroBrief, InsightBriefV2
from windows_client.gui.inline_result_view import InlineResultView


def _app():
    return QApplication.instance() or QApplication([])


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


if __name__ == "__main__":
    unittest.main()
