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


if __name__ == "__main__":
    unittest.main()
