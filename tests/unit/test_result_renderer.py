import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from windows_client.gui.result_renderer import (
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
        self.assertIn("# Untitled", md)

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
        self.assertNotIn("## Key Points", md)
        self.assertNotIn("## Bottom Line", md)
        self.assertNotIn("## Questions", md)


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
        self.assertIn("Visual Evidence", md)
        self.assertIn("Speaker points at map", md)
        self.assertIn("Chart displayed", md)

    def test_visual_findings_omitted_when_empty(self) -> None:
        entry = _make_entry()
        entry.details = {"visual_findings": []}
        md = entry_to_markdown(entry)
        self.assertNotIn("Visual Evidence", md)


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
