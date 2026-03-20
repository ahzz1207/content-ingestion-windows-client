import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.coverage_stats import CoverageStats
from windows_client.app.evidence_resolver import EvidenceSnippet
from windows_client.app.insight_brief import adapt_from_structured_result


def _make_coverage(*, truncated: bool = False) -> CoverageStats:
    ratio = 0.5 if truncated else 1.0
    return CoverageStats(
        total_segments=100,
        used_segments=50 if truncated else 100,
        total_duration_ms=None,
        used_duration_ms=None,
        coverage_ratio=ratio,
        input_truncated=truncated,
    )


def _make_result(**overrides) -> dict:
    base = {
        "summary": {"headline": "Test Headline", "short_text": "One sentence summary."},
        "key_points": [
            {"title": "Point A", "details": "Detail A"},
            {"title": "Point B", "details": "Detail B"},
        ],
        "analysis_items": [
            {"statement": "Analysis statement", "kind": "observation"},
        ],
        "verification_items": [
            {"claim": "Claim one", "status": "supported", "rationale": "Evidence."},
        ],
        "synthesis": {
            "final_answer": "Overall conclusion.",
            "open_questions": ["Q1", "Q2"],
            "next_steps": ["Step 1"],
        },
    }
    base.update(overrides)
    return base


class TestAdaptFromStructuredResult(unittest.TestCase):
    def test_adapt_returns_none_for_empty_result(self) -> None:
        self.assertIsNone(adapt_from_structured_result(None, {}, None))
        self.assertIsNone(adapt_from_structured_result({}, {}, None))

    def test_adapt_returns_none_when_summary_missing(self) -> None:
        result = {"key_points": [{"title": "X", "details": "Y"}]}
        self.assertIsNone(adapt_from_structured_result(result, {}, None))

    def test_adapt_maps_summary_to_hero(self) -> None:
        brief = adapt_from_structured_result(_make_result(), {}, None)
        self.assertIsNotNone(brief)
        self.assertEqual(brief.hero.title, "Test Headline")
        self.assertEqual(brief.hero.one_sentence_take, "One sentence summary.")

    def test_adapt_merges_all_viewpoint_sources(self) -> None:
        brief = adapt_from_structured_result(_make_result(), {}, None)
        self.assertIsNotNone(brief)
        kinds = [v.kind for v in brief.viewpoints]
        self.assertIn("key_point", kinds)
        self.assertIn("analysis", kinds)
        self.assertIn("verification", kinds)

    def test_adapt_all_key_points_present(self) -> None:
        result = _make_result()
        result["key_points"] = [{"title": f"Point {i}", "details": f"Detail {i}"} for i in range(5)]
        brief = adapt_from_structured_result(result, {}, None)
        self.assertIsNotNone(brief)
        self.assertEqual(len(brief.quick_takeaways), 5)

    def test_adapt_passes_coverage_through(self) -> None:
        cov = _make_coverage(truncated=True)
        brief = adapt_from_structured_result(_make_result(), {}, cov)
        self.assertIsNotNone(brief)
        self.assertIs(brief.coverage, cov)
        self.assertTrue(brief.coverage.input_truncated)

    def test_adapt_collects_gaps_from_synthesis(self) -> None:
        brief = adapt_from_structured_result(_make_result(), {}, None)
        self.assertIsNotNone(brief)
        self.assertIn("Q1", brief.gaps)
        self.assertIn("Q2", brief.gaps)
        self.assertIn("Step 1", brief.gaps)

    def test_adapt_resolves_evidence_refs(self) -> None:
        index = {
            "ev-1": EvidenceSnippet("ev-1", "Some text", 0, 1000, "transcript"),
        }
        result = _make_result()
        result["key_points"][0]["evidence_segment_ids"] = ["ev-1"]
        brief = adapt_from_structured_result(result, index, None)
        self.assertIsNotNone(brief)
        kp_viewpoints = [v for v in brief.viewpoints if v.kind == "key_point"]
        self.assertTrue(any(len(v.evidence_refs) > 0 for v in kp_viewpoints))


if __name__ == "__main__":
    unittest.main()
