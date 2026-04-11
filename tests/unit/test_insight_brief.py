import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.coverage_stats import CoverageStats
from windows_client.app.evidence_resolver import EvidenceSnippet
from windows_client.app.insight_brief import InsightBriefV2, adapt_from_structured_result


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


def _make_question_driven_result(
    *,
    summary: dict | None = None,
    key_points: list[dict] | None = None,
    hero: dict | None = None,
    sections: list[dict] | None = None,
) -> dict:
    return {
        "summary": summary or {"headline": "Legacy headline", "short_text": "Legacy summary."},
        "key_points": key_points if key_points is not None else [{"title": "Legacy key point", "details": "Legacy detail."}],
        "product_view": {
            "hero": {
                "title": "Question-driven title",
                "dek": "Question-driven conclusion.",
                "bottom_line": "This matters because it lowers the barrier.",
                **(hero or {}),
            },
            "sections": sections
            if sections is not None
            else [
                {
                    "id": "q1",
                    "title": "核心问题是什么？",
                    "kind": "question_block",
                    "priority": 1,
                    "blocks": [{"type": "bullet_list", "items": ["结论 A", "结论 B"]}],
                },
                {
                    "id": "reader-value",
                    "title": "这对我意味着什么？",
                    "kind": "reader_value",
                    "priority": 2,
                    "blocks": [{"type": "bullet_list", "items": ["值得持续关注"]}],
                },
            ],
        },
    }


def _adapt_brief(
    result: dict,
    evidence_index: dict[str, EvidenceSnippet] | None = None,
    coverage: CoverageStats | None = None,
) -> InsightBriefV2:
    brief = adapt_from_structured_result(result, evidence_index or {}, coverage)
    assert brief is not None
    return brief


class TestAdaptFromStructuredResult(unittest.TestCase):
    def test_adapt_returns_none_for_empty_result(self) -> None:
        self.assertIsNone(adapt_from_structured_result(None, {}, None))
        self.assertIsNone(adapt_from_structured_result({}, {}, None))

    def test_adapt_returns_none_when_summary_missing(self) -> None:
        result = {"key_points": [{"title": "X", "details": "Y"}]}
        self.assertIsNone(adapt_from_structured_result(result, {}, None))

    def test_adapt_maps_summary_to_hero(self) -> None:
        brief = _adapt_brief(_make_result())
        self.assertEqual(brief.hero.title, "Test Headline")
        self.assertEqual(brief.hero.one_sentence_take, "One sentence summary.")

    def test_adapt_merges_all_viewpoint_sources(self) -> None:
        brief = _adapt_brief(_make_result())
        kinds = [v.kind for v in brief.viewpoints]
        self.assertIn("key_point", kinds)
        self.assertIn("analysis", kinds)
        self.assertIn("verification", kinds)

    def test_adapt_all_key_points_present(self) -> None:
        result = _make_result()
        result["key_points"] = [{"title": f"Point {i}", "details": f"Detail {i}"} for i in range(5)]
        brief = _adapt_brief(result)
        self.assertEqual(len(brief.quick_takeaways), 5)

    def test_adapt_passes_coverage_through(self) -> None:
        cov = _make_coverage(truncated=True)
        brief = _adapt_brief(_make_result(), coverage=cov)
        self.assertIs(brief.coverage, cov)
        self.assertTrue(brief.coverage.input_truncated)

    def test_adapt_collects_gaps_from_synthesis(self) -> None:
        brief = _adapt_brief(_make_result())
        self.assertIn("Q1", brief.gaps)
        self.assertIn("Q2", brief.gaps)
        self.assertIn("Step 1", brief.gaps)

    def test_adapt_captures_synthesis_conclusion(self) -> None:
        brief = _adapt_brief(_make_result())
        self.assertEqual(brief.synthesis_conclusion, "Overall conclusion.")

    def test_adapt_synthesis_conclusion_none_when_missing(self) -> None:
        result = _make_result()
        result["synthesis"] = {"final_answer": "", "open_questions": [], "next_steps": []}
        brief = _adapt_brief(result)
        self.assertIsNone(brief.synthesis_conclusion)

    def test_adapt_resolves_evidence_refs(self) -> None:
        index = {
            "ev-1": EvidenceSnippet("ev-1", "Some text", 0, 1000, "transcript"),
        }
        result = _make_result()
        result["key_points"][0]["evidence_segment_ids"] = ["ev-1"]
        brief = _adapt_brief(result, index)
        kp_viewpoints = [v for v in brief.viewpoints if v.kind == "key_point"]
        self.assertTrue(any(len(v.evidence_refs) > 0 for v in kp_viewpoints))

    def test_adapt_uses_editorial_argument_when_present(self) -> None:
        result = {
            "content_kind": "analysis",
            "author_stance": "critical",
            "editorial": {
                "resolved_mode": "argument",
                "base": {
                    "core_summary": {"value": "Core summary from editorial."},
                    "bottom_line": {"value": "Bottom line from editorial."},
                    "save_worthy_points": [{"value": "Point A"}, {"value": "Point B"}],
                },
                "mode_payload": {
                    "evidence_backed_points": [
                        {"title": "Evidence-backed point", "details": "Why it matters", "evidence_segment_ids": ["ev-1"]}
                    ],
                    "interpretive_points": [
                        {"statement": "Interpretive point", "evidence_segment_ids": ["ev-2"]}
                    ],
                    "uncertainties": [{"value": "Uncertainty one"}],
                },
            },
        }

        index = {
            "ev-1": EvidenceSnippet("ev-1", "Evidence one", 0, 1000, "transcript"),
            "ev-2": EvidenceSnippet("ev-2", "Evidence two", 1000, 2000, "transcript"),
        }

        brief = _adapt_brief(result, index)
        self.assertEqual(brief.hero.title, "Core summary from editorial.")
        self.assertEqual(brief.synthesis_conclusion, "Bottom line from editorial.")
        self.assertEqual(brief.quick_takeaways, ["Point A", "Point B"])
        self.assertIn("Uncertainty one", brief.gaps)
        self.assertTrue(any(v.statement == "Evidence-backed point" for v in brief.viewpoints))
        self.assertTrue(any(v.statement == "Evidence-backed point" and len(v.evidence_refs) == 1 for v in brief.viewpoints))
        self.assertTrue(any(v.statement == "Interpretive point" and len(v.evidence_refs) == 1 for v in brief.viewpoints))

    def test_adapt_uses_editorial_guide_when_present(self) -> None:
        result = {
            "editorial": {
                "resolved_mode": "guide",
                "base": {
                    "core_summary": {"value": "Guide summary."},
                    "bottom_line": {"value": "Guide bottom line."},
                    "save_worthy_points": [],
                },
                "mode_payload": {
                    "recommended_steps": [{"value": "Step one"}, {"value": "Step two"}],
                    "tips": [{"value": "Tip one"}],
                },
            },
        }

        brief = _adapt_brief(result)
        self.assertTrue(any(v.statement == "Step one" for v in brief.viewpoints))
        self.assertTrue(any(v.statement == "Tip one" for v in brief.viewpoints))

    def test_adapt_uses_editorial_review_when_present(self) -> None:
        result = {
            "editorial": {
                "resolved_mode": "review",
                "base": {
                    "core_summary": {"value": "Review summary."},
                    "bottom_line": {"value": "Review bottom line."},
                    "save_worthy_points": [{"value": "Keep this"}],
                },
                "mode_payload": {
                    "highlights": [{"value": "Highlight one"}],
                    "reservation_points": [{"value": "Reservation one"}],
                },
            },
        }

        brief = _adapt_brief(result)
        self.assertTrue(any(v.statement == "Highlight one" for v in brief.viewpoints))
        self.assertIn("Reservation one", brief.gaps)

    def test_adapt_prefers_product_view_hero_fields_over_legacy_summary_values(self) -> None:
        result = _make_question_driven_result(
            summary={"headline": "Legacy headline", "short_text": "Legacy summary."},
            hero={"title": "Preferred product title", "dek": "Preferred product dek."},
        )

        brief = _adapt_brief(result)
        self.assertEqual(brief.hero.title, "Preferred product title")
        self.assertEqual(brief.hero.one_sentence_take, "Preferred product dek.")

    def test_adapt_prefers_product_view_question_blocks_for_quick_takeaways(self) -> None:
        result = _make_question_driven_result()

        brief = _adapt_brief(result)
        self.assertEqual(brief.hero.title, "Question-driven title")
        self.assertEqual(brief.hero.one_sentence_take, "Question-driven conclusion.")
        self.assertEqual(brief.quick_takeaways, ["核心问题是什么？"])
        self.assertNotIn("Legacy key point", brief.quick_takeaways)

    def test_adapt_caps_question_block_quick_takeaways_at_three(self) -> None:
        result = _make_question_driven_result(
            sections=[
                {
                    "id": "q1",
                    "title": "Question 1",
                    "kind": "question_block",
                    "priority": 1,
                    "blocks": [{"type": "bullet_list", "items": ["Answer 1"]}],
                },
                {
                    "id": "q2",
                    "title": "Question 2",
                    "kind": "question_block",
                    "priority": 2,
                    "blocks": [{"type": "bullet_list", "items": ["Answer 2"]}],
                },
                {
                    "id": "q3",
                    "title": "Question 3",
                    "kind": "question_block",
                    "priority": 3,
                    "blocks": [{"type": "bullet_list", "items": ["Answer 3"]}],
                },
                {
                    "id": "q4",
                    "title": "Question 4",
                    "kind": "question_block",
                    "priority": 4,
                    "blocks": [{"type": "bullet_list", "items": ["Answer 4"]}],
                },
            ]
        )

        brief = _adapt_brief(result)
        self.assertEqual(brief.quick_takeaways, ["Question 1", "Question 2", "Question 3"])

    def test_adapt_uses_product_view_bottom_line_as_synthesis_conclusion(self) -> None:
        result = _make_question_driven_result()

        brief = _adapt_brief(result)
        self.assertEqual(brief.synthesis_conclusion, "This matters because it lowers the barrier.")

    def test_adapt_uses_reader_value_fallback_for_quick_takeaways(self) -> None:
        result = _make_question_driven_result(
            hero={"title": "Reader value title", "dek": "Reader value summary.", "bottom_line": None},
            sections=[
                {
                    "id": "reader-value",
                    "title": "Why this matters to readers",
                    "kind": "reader_value",
                    "priority": 1,
                    "blocks": [{"type": "bullet_list", "items": ["Useful fallback bullet"]}],
                },
            ],
        )

        brief = _adapt_brief(result)
        self.assertEqual(brief.quick_takeaways, ["Why this matters to readers"])


if __name__ == "__main__":
    unittest.main()
