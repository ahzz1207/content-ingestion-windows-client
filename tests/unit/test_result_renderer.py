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
    _preview_html,
    _resolved_evidence_html,
    _structured_preview_html,
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


if __name__ == "__main__":
    unittest.main()
