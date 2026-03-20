from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from windows_client.app.coverage_stats import CoverageStats
from windows_client.app.evidence_resolver import EvidenceSnippet, resolve_evidence_for_item


@dataclass(slots=True)
class HeroBrief:
    title: str
    one_sentence_take: str
    content_kind: str | None
    author_stance: str | None


@dataclass(slots=True)
class ViewpointItem:
    statement: str
    kind: str  # "key_point" | "analysis" | "verification"
    why_it_matters: str | None
    support_level: str | None
    evidence_refs: list[EvidenceSnippet] = field(default_factory=list)


@dataclass(slots=True)
class InsightBriefV2:
    hero: HeroBrief
    quick_takeaways: list[str]
    viewpoints: list[ViewpointItem]
    coverage: CoverageStats | None
    gaps: list[str]


def adapt_from_structured_result(
    result: dict[str, Any] | None,
    evidence_index: dict[str, EvidenceSnippet],
    coverage: CoverageStats | None,
) -> InsightBriefV2 | None:
    """Adapt a structured LLM result dict into InsightBriefV2.

    Returns None when result is None/empty or the summary block is missing.
    Degrades gracefully for any missing sub-fields.
    """
    if not result:
        return None

    summary = result.get("summary")
    if not isinstance(summary, dict):
        return None

    headline = str(summary.get("headline") or "").strip()
    short_text = str(summary.get("short_text") or "").strip()
    if not headline and not short_text:
        return None

    hero = HeroBrief(
        title=headline or short_text,
        one_sentence_take=short_text or headline,
        content_kind=str(result.get("content_kind") or "").strip() or None,
        author_stance=str(result.get("author_stance") or "").strip() or None,
    )

    # quick_takeaways from key_points titles (all of them, no cap)
    key_points = result.get("key_points")
    quick_takeaways: list[str] = []
    if isinstance(key_points, list):
        for kp in key_points:
            if isinstance(kp, dict):
                title = str(kp.get("title") or "").strip()
                if title:
                    quick_takeaways.append(title)

    # viewpoints: key_points + analysis_items + verification_items merged
    viewpoints: list[ViewpointItem] = []
    if isinstance(key_points, list):
        for item in key_points:
            if not isinstance(item, dict):
                continue
            statement = str(item.get("details") or item.get("title") or "").strip()
            if not statement:
                continue
            viewpoints.append(
                ViewpointItem(
                    statement=statement,
                    kind="key_point",
                    why_it_matters=str(item.get("why_it_matters") or "").strip() or None,
                    support_level=str(item.get("support_level") or "").strip() or None,
                    evidence_refs=resolve_evidence_for_item(item, evidence_index),
                )
            )

    analysis_items = result.get("analysis_items")
    if isinstance(analysis_items, list):
        for item in analysis_items:
            if not isinstance(item, dict):
                continue
            statement = str(item.get("statement") or "").strip()
            if not statement:
                continue
            viewpoints.append(
                ViewpointItem(
                    statement=statement,
                    kind="analysis",
                    why_it_matters=str(item.get("why_it_matters") or "").strip() or None,
                    support_level=str(item.get("support_level") or "").strip() or None,
                    evidence_refs=resolve_evidence_for_item(item, evidence_index),
                )
            )

    verification_items = result.get("verification_items")
    if isinstance(verification_items, list):
        for item in verification_items:
            if not isinstance(item, dict):
                continue
            statement = str(item.get("claim") or "").strip()
            if not statement:
                continue
            viewpoints.append(
                ViewpointItem(
                    statement=statement,
                    kind="verification",
                    why_it_matters=str(item.get("rationale") or "").strip() or None,
                    support_level=str(item.get("status") or "").strip() or None,
                    evidence_refs=resolve_evidence_for_item(item, evidence_index),
                )
            )

    # gaps: open_questions + next_steps from synthesis
    synthesis = result.get("synthesis")
    gaps: list[str] = []
    if isinstance(synthesis, dict):
        open_questions = synthesis.get("open_questions")
        if isinstance(open_questions, list):
            gaps.extend(str(q) for q in open_questions if q)
        next_steps = synthesis.get("next_steps")
        if isinstance(next_steps, list):
            gaps.extend(str(s) for s in next_steps if s)

    return InsightBriefV2(
        hero=hero,
        quick_takeaways=quick_takeaways,
        viewpoints=viewpoints,
        coverage=coverage,
        gaps=gaps,
    )
