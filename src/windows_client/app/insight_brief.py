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
    synthesis_conclusion: str | None = None


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _editorial_scalar(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value")
    text = str(value or "").strip()
    return text or None


def _editorial_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        text = _editorial_scalar(item)
        if text:
            result.append(text)
    return result


def _adapt_from_editorial(
    result: dict[str, Any],
    editorial: dict[str, Any],
    evidence_index: dict[str, EvidenceSnippet],
    coverage: CoverageStats | None,
) -> InsightBriefV2 | None:
    base = _coerce_dict(editorial.get("base"))
    mode_payload = _coerce_dict(editorial.get("mode_payload"))
    resolved_mode = str(editorial.get("resolved_mode") or "argument").strip() or "argument"

    core_summary = _editorial_scalar(base.get("core_summary"))
    bottom_line = _editorial_scalar(base.get("bottom_line"))
    if not core_summary and not bottom_line:
        return None

    hero = HeroBrief(
        title=core_summary or bottom_line or "Untitled",
        one_sentence_take=core_summary or bottom_line or "Untitled",
        content_kind=str(result.get("content_kind") or "").strip() or None,
        author_stance=str(result.get("author_stance") or "").strip() or None,
    )

    quick_takeaways = _editorial_list(base.get("save_worthy_points"))
    viewpoints: list[ViewpointItem] = []
    gaps: list[str] = []

    if resolved_mode == "guide":
        for step in _editorial_list(mode_payload.get("recommended_steps")):
            viewpoints.append(ViewpointItem(statement=step, kind="key_point", why_it_matters=None, support_level=None))
        for tip in _editorial_list(mode_payload.get("tips")):
            viewpoints.append(ViewpointItem(statement=tip, kind="analysis", why_it_matters=None, support_level=None))
        gaps.extend(_editorial_list(mode_payload.get("pitfalls")))
    elif resolved_mode == "review":
        for highlight in _editorial_list(mode_payload.get("highlights")):
            viewpoints.append(ViewpointItem(statement=highlight, kind="key_point", why_it_matters=None, support_level=None))
        gaps.extend(_editorial_list(mode_payload.get("reservation_points")))
    else:
        evidence_points = mode_payload.get("evidence_backed_points")
        if isinstance(evidence_points, list):
            for item in evidence_points:
                payload = _coerce_dict(item)
                statement = str(payload.get("title") or payload.get("statement") or "").strip()
                if not statement:
                    continue
                why_it_matters = str(payload.get("details") or payload.get("statement") or "").strip() or None
                viewpoints.append(
                    ViewpointItem(
                        statement=statement,
                        kind="key_point",
                        why_it_matters=why_it_matters,
                        support_level="supported",
                        evidence_refs=resolve_evidence_for_item(payload, evidence_index),
                    )
                )
        interpretive_points = mode_payload.get("interpretive_points")
        if isinstance(interpretive_points, list):
            for item in interpretive_points:
                payload = _coerce_dict(item)
                statement = str(payload.get("statement") or payload.get("title") or "").strip()
                if not statement:
                    continue
                viewpoints.append(
                    ViewpointItem(
                        statement=statement,
                        kind="analysis",
                        why_it_matters=str(payload.get("details") or "").strip() or None,
                        support_level=None,
                        evidence_refs=resolve_evidence_for_item(payload, evidence_index),
                    )
                )
        gaps.extend(_editorial_list(mode_payload.get("uncertainties")))

    return InsightBriefV2(
        hero=hero,
        quick_takeaways=quick_takeaways,
        viewpoints=viewpoints,
        coverage=coverage,
        gaps=gaps,
        synthesis_conclusion=bottom_line,
    )


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

    editorial = result.get("editorial")
    if isinstance(editorial, dict):
        adapted = _adapt_from_editorial(result, editorial, evidence_index, coverage)
        if adapted is not None:
            return adapted

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
            statement = str(item.get("title") or "").strip()
            if not statement:
                continue
            viewpoints.append(
                ViewpointItem(
                    statement=statement,
                    kind="key_point",
                    why_it_matters=str(item.get("details") or "").strip() or None,
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

    # gaps: open_questions + next_steps from synthesis; conclusion from final_answer
    synthesis = result.get("synthesis")
    gaps: list[str] = []
    synthesis_conclusion: str | None = None
    if isinstance(synthesis, dict):
        open_questions = synthesis.get("open_questions")
        if isinstance(open_questions, list):
            gaps.extend(str(q) for q in open_questions if q)
        next_steps = synthesis.get("next_steps")
        if isinstance(next_steps, list):
            gaps.extend(str(s) for s in next_steps if s)
        final_answer = str(synthesis.get("final_answer") or "").strip()
        if final_answer:
            synthesis_conclusion = final_answer

    return InsightBriefV2(
        hero=hero,
        quick_takeaways=quick_takeaways,
        viewpoints=viewpoints,
        coverage=coverage,
        gaps=gaps,
        synthesis_conclusion=synthesis_conclusion,
    )
