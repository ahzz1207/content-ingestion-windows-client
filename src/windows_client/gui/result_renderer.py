"""Pure rendering helpers for result entries.

Extracted from main_window.py so that the rendering logic can be tested and
reused independently of the main window's widget state.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime

from PySide6.QtWidgets import QLabel

from windows_client.app.result_workspace import ResultWorkspaceEntry


UI_FONT_STACK = "'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans CJK SC', 'Source Han Sans SC', 'Segoe UI', sans-serif"


# ---------------------------------------------------------------------------
# Pill styling helpers
# ---------------------------------------------------------------------------


def _apply_result_state_pill(label: QLabel, state: str) -> None:
    styles = {
        "pending": ("#9a3412", "rgba(249, 115, 22, 0.14)"),
        "processing": ("#1d4ed8", "rgba(37, 99, 235, 0.14)"),
        "processed": ("#15803d", "rgba(22, 163, 74, 0.14)"),
        "failed": ("#b91c1c", "rgba(239, 68, 68, 0.14)"),
    }
    foreground, background = styles.get(state, ("#475569", "rgba(148, 163, 184, 0.16)"))
    label.setStyleSheet(
        f"""
        QLabel {{
            background: {background};
            color: {foreground};
            border-radius: 14px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 600;
        }}
        """
    )
    label.setText(state.capitalize())


def _apply_analysis_state_pill(label: QLabel, analysis_state: str | None) -> None:
    styles = {
        "ready": ("#15803d", "rgba(22, 163, 74, 0.14)", "Analysis Ready"),
        "normalized_only": ("#475569", "rgba(148, 163, 184, 0.16)", "Normalized Only"),
        "skipped": ("#9a3412", "rgba(249, 115, 22, 0.14)", "Analysis Skipped"),
        "failed": ("#b91c1c", "rgba(239, 68, 68, 0.14)", "Analysis Failed"),
        "processing": ("#1d4ed8", "rgba(37, 99, 235, 0.14)", "Analysis Pending"),
        "pending": ("#9a3412", "rgba(249, 115, 22, 0.14)", "Analysis Pending"),
    }
    foreground, background, text = styles.get(
        analysis_state or "",
        ("#475569", "rgba(148, 163, 184, 0.16)", "Analysis Unknown"),
    )
    label.setStyleSheet(
        f"""
        QLabel {{
            background: {background};
            color: {foreground};
            border-radius: 14px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 600;
        }}
        """
    )
    label.setText(text)


# ---------------------------------------------------------------------------
# Entry metadata formatters
# ---------------------------------------------------------------------------


def _format_result_origin(entry: ResultWorkspaceEntry) -> str:
    if entry.canonical_url:
        return entry.canonical_url
    if entry.source_url:
        return entry.source_url
    return "Source unavailable"


def _format_result_byline(entry: ResultWorkspaceEntry) -> str:
    parts = [value for value in (entry.author, entry.published_at) if value]
    if not parts:
        return "Author and publication time are not available yet."
    return "  |  ".join(parts)


def _preview_body(entry: ResultWorkspaceEntry) -> str:
    if entry.preview_text:
        return entry.preview_text
    if entry.state == "processed":
        return "No readable markdown preview is available for this processed result yet."
    return json.dumps(entry.details, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Payload extractors
# ---------------------------------------------------------------------------


def _structured_result_payload(entry: ResultWorkspaceEntry) -> dict[str, object] | None:
    details_result = entry.details.get("structured_result")
    if isinstance(details_result, dict):
        result = details_result
        if any(
            result.get(key)
            for key in (
                "product_view",
                "summary",
                "key_points",
                "analysis_items",
                "verification_items",
                "synthesis",
                "editorial",
            )
        ):
            return result
    normalized = entry.details.get("normalized")
    if not isinstance(normalized, dict):
        return None
    asset = normalized.get("asset")
    if not isinstance(asset, dict):
        return None
    result = asset.get("result")
    if not isinstance(result, dict):
        return None
    if not any(
        result.get(key)
        for key in ("product_view", "summary", "key_points", "analysis_items", "verification_items", "synthesis", "editorial")
    ):
        return None
    return result


def _product_view_payload(entry: ResultWorkspaceEntry) -> dict[str, object] | None:
    direct_product_view = entry.details.get("product_view")
    if isinstance(direct_product_view, dict) and any(direct_product_view.get(key) for key in ("hero", "sections", "chips")):
        return direct_product_view
    result = _structured_result_payload(entry)
    if not isinstance(result, dict):
        return None
    product_view = result.get("product_view")
    if not isinstance(product_view, dict):
        return None
    if not any(product_view.get(key) for key in ("hero", "sections", "chips")):
        return None
    return product_view


def _llm_processing_payload(entry: ResultWorkspaceEntry) -> dict[str, object] | None:
    details_payload = entry.details.get("llm_processing")
    if isinstance(details_payload, dict):
        return details_payload
    normalized = entry.details.get("normalized")
    if not isinstance(normalized, dict):
        return None
    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        asset = normalized.get("asset")
        if not isinstance(asset, dict):
            return None
        metadata = asset.get("metadata")
    if not isinstance(metadata, dict):
        return None
    llm_processing = metadata.get("llm_processing")
    if not isinstance(llm_processing, dict):
        return None
    return llm_processing


def _resolved_mode(entry: ResultWorkspaceEntry) -> str | None:
    llm_processing = _llm_processing_payload(entry)
    if not isinstance(llm_processing, dict):
        return None
    value = str(llm_processing.get("resolved_mode") or "").strip().lower()
    return value or None


def _mode_pill_html(entry: ResultWorkspaceEntry, resolved_mode: str | None = None) -> str:
    labels = {
        "argument": "深度分析",
        "guide": "实用提炼",
        "review": "推荐导览",
        "narrative": "叙事",
    }
    resolved_mode = resolved_mode or _resolved_mode(entry)
    if resolved_mode not in labels:
        return ""
    return f"<div class='status-chip status-supported'>{html.escape(labels[resolved_mode])}</div>"


def _safe_priority(item: dict) -> int:
    try:
        return int(item.get("priority") or 0)
    except (TypeError, ValueError):
        return 0


def _analysis_skip_reason(entry: ResultWorkspaceEntry) -> str | None:
    llm_processing = _llm_processing_payload(entry)
    if llm_processing is None:
        return None
    reason = str(llm_processing.get("skip_reason") or "").strip()
    return reason or None


def _primary_result_button_text(entry: ResultWorkspaceEntry) -> str:
    if entry.analysis_json_path is not None:
        return "Open Final Result"
    if entry.normalized_json_path is not None:
        return "Open Processed Output"
    if entry.error_path is not None:
        return "Open Failure Details"
    if entry.metadata_path is not None:
        return "Open Handoff Metadata"
    return "Open Result"


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

# CSS injected into the preview QTextBrowser document
PREVIEW_STYLESHEET = """
.preview-reading {
    font-family: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', 'STSong', serif;
    font-size: 17px;
    line-height: 1.95;
    color: #33465e;
}
.preview-reading p {
    margin: 0 0 16px 0;
}
.preview-reading p:first-child {
    margin-top: 0;
}
.preview-reading h2,
.preview-reading h3,
.preview-reading blockquote {
    font-family: 'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans CJK SC', 'Source Han Sans SC', 'Segoe UI', sans-serif;
}
.preview-reading li {
    font-family: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', 'STSong', serif;
}
.structured-result {
    display: block;
}
.result-section {
    margin: 0 0 26px 0;
    padding: 0 0 20px 0;
    border-bottom: 1px solid rgba(21, 33, 51, 0.08);
}
.result-section:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
}
.result-section h2 {
    margin: 0 0 10px 0;
    font-size: 13px;
    font-weight: 700;
    color: #66758a;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.result-section h3 {
    margin: 0 0 12px 0;
    font-size: 20px;
    font-weight: 650;
    color: #152133;
    letter-spacing: -0.02em;
}
.preview-reading ul,
.preview-reading ol {
    margin: 12px 0 0 0;
    padding-left: 22px;
}
.preview-reading li {
    margin: 0 0 8px 0;
    color: #33465e;
}
.preview-reading blockquote {
    margin: 16px 0;
    padding: 0 0 0 16px;
    border-left: 3px solid rgba(58, 103, 214, 0.22);
    color: #516276;
}
.result-card {
    margin: 0 0 14px 0;
    padding: 16px 20px;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(21, 33, 51, 0.08);
    border-radius: 18px;
    box-shadow: 0 10px 24px rgba(21, 33, 51, 0.05);
}
.result-hero {
    padding: 22px 24px;
    background: linear-gradient(135deg, rgba(229, 238, 252, 0.9), rgba(247, 244, 238, 0.96));
    border: 1px solid rgba(21, 33, 51, 0.08);
    border-radius: 24px;
    box-shadow: 0 16px 36px rgba(21, 33, 51, 0.07);
}
.analysis-brief-layout {
    display: block;
}
.analysis-hero {
    padding: 22px 24px;
    background: linear-gradient(135deg, rgba(229, 238, 252, 0.9), rgba(247, 244, 238, 0.96));
    border: 1px solid rgba(21, 33, 51, 0.08);
    border-radius: 22px;
    margin: 0 0 20px 0;
}
.analysis-hero h2 {
    font-size: 24px;
    margin-bottom: 12px;
    color: #152133;
    letter-spacing: -0.03em;
}
.analysis-section-label {
    display: inline-block;
    margin: 0 0 10px 0;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(58, 103, 214, 0.12);
    color: #3a67d6;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.analysis-card-grid {
    display: block;
}
.guide-digest-layout {
    display: block;
}
.review-curation-layout {
    display: block;
}
.review-curation-hero {
    padding: 18px 20px;
    background: rgba(124, 58, 237, 0.06);
    border: 1px solid rgba(124, 58, 237, 0.14);
    border-radius: 18px;
    margin: 0 0 18px 0;
}
.review-curation-label {
    display: inline-block;
    margin: 0 0 8px 0;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(124, 58, 237, 0.10);
    color: #6d28d9;
    font-size: 11px;
    font-weight: 700;
}
.review-section {
    border-radius: 18px;
    padding: 16px 18px;
    border: 1px solid rgba(21, 33, 51, 0.08);
    background: rgba(255, 255, 255, 0.88);
    margin: 0 0 14px 0;
}
.review-section-highlight_block {
    background: rgba(124, 58, 237, 0.05);
}
.review-section-standout_block {
    background: rgba(236, 72, 153, 0.05);
}
.review-section-reservation_block {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.22);
}
.review-section-reader_value {
    background: rgba(59, 130, 246, 0.06);
    border-color: rgba(59, 130, 246, 0.18);
}
.narrative-digest-layout {
    display: block;
}
.narrative-digest-hero {
    padding: 20px 22px;
    background: rgba(219, 39, 119, 0.05);
    border: 1px solid rgba(219, 39, 119, 0.12);
    border-radius: 20px;
    margin: 0 0 18px 0;
}
.narrative-section-label {
    display: inline-block;
    margin: 0 0 8px 0;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(219, 39, 119, 0.10);
    color: #be185d;
    font-size: 11px;
    font-weight: 700;
}
.guide-compact-hero {
    padding: 14px 16px;
    background: rgba(229, 238, 252, 0.78);
    border: 1px solid rgba(21, 33, 51, 0.08);
    border-radius: 16px;
    margin: 0 0 16px 0;
}
.guide-compact-hero h2 {
    font-size: 19px;
    margin-bottom: 8px;
}
.guide-digest-layout .result-section {
    margin: 0 0 14px 0;
    padding: 0 0 12px 0;
}
.guide-section {
    border-radius: 16px;
    padding: 14px 16px;
    border: 1px solid rgba(21, 33, 51, 0.08);
    background: rgba(255, 255, 255, 0.88);
}
.guide-section-action_step {
    background: rgba(229, 238, 252, 0.55);
}
.guide-section-tip_block {
    background: rgba(16, 185, 129, 0.06);
    border-color: rgba(16, 185, 129, 0.18);
}
.guide-section-pitfall_warning {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.22);
}
.guide-section-reader_value {
    background: rgba(37, 99, 235, 0.07);
    border-color: rgba(37, 99, 235, 0.18);
}
.guide-section-label {
    display: inline-block;
    margin: 0 0 8px 0;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(58, 103, 214, 0.12);
    color: #3a67d6;
    font-size: 11px;
    font-weight: 700;
}
.result-takeaway {
    padding: 18px 20px;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(21, 33, 51, 0.08);
    border-radius: 20px;
}
.result-warnings {
    padding: 14px 16px;
    background: rgba(239, 68, 68, 0.06);
    border: 1px solid rgba(239, 68, 68, 0.14);
    border-radius: 16px;
}
.coverage-warning {
    padding: 14px 16px;
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.20);
    border-radius: 16px;
    color: #b91c1c;
    font-weight: 600;
    margin: 0 0 18px 0;
}
.status-chip {
    display: inline-block;
    margin: 0 0 10px 0;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.status-supported {
    background: rgba(22, 163, 74, 0.12);
    color: #15803d;
}
.status-partial {
    background: rgba(245, 158, 11, 0.14);
    color: #b45309;
}
.status-unsupported, .status-unclear {
    background: rgba(220, 38, 38, 0.10);
    color: #b91c1c;
}
.evidence-list {
    margin: 10px 0 0 0;
    padding-left: 18px;
    color: #516276;
}
pre {
    white-space: pre-wrap;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #334155;
}
"""


def _resolved_evidence_html(item: dict[str, object]) -> str:
    evidence_refs = item.get("resolved_evidence")
    if not isinstance(evidence_refs, list):
        return ""
    rendered: list[str] = []
    for evidence in evidence_refs:
        if not isinstance(evidence, dict):
            continue
        preview_text = str(evidence.get("preview_text") or "").strip()
        if not preview_text:
            continue
        rendered.append(f"<li>{html.escape(preview_text)}</li>")
    if not rendered:
        return ""
    return f"<ul class='evidence-list'>{''.join(rendered)}</ul>"


def _structured_preview_html(
    entry: ResultWorkspaceEntry,
    *,
    coverage_html: str = "",
    resolved_mode: str | None = None,
) -> str | None:
    result = _structured_result_payload(entry)
    if result is None:
        return None

    sections: list[str] = []

    # Prepend coverage warning if provided
    if coverage_html:
        sections.append(coverage_html)

    mode_pill = _mode_pill_html(entry, resolved_mode)
    if mode_pill:
        sections.append(mode_pill)

    product_view = _product_view_payload(entry)
    if product_view is not None:
        product_view_html = _product_view_html(product_view)
        if product_view_html:
            sections.append(product_view_html)
            return f"<div class='preview-reading structured-result'>{''.join(sections)}</div>"

    summary = result.get("summary")
    if isinstance(summary, dict):
        headline = str(summary.get("headline") or "").strip()
        short_text = str(summary.get("short_text") or "").strip()
        if headline or short_text:
            sections.append(
                "<section class='result-section result-hero'>"
                f"<h2>{html.escape(headline or '摘要')}</h2>"
                f"<p>{html.escape(short_text or headline)}</p>"
                "</section>"
            )

    def _render_cards(items: object, *, title: str, title_key: str, body_key: str) -> None:
        if not isinstance(items, list) or not items:
            return
        cards: list[str] = []
        for item in items:  # no truncation cap
            if not isinstance(item, dict):
                continue
            card_title = str(item.get(title_key) or "").strip()
            card_body = str(item.get(body_key) or "").strip()
            if not card_title and not card_body:
                continue
            evidence_html = _resolved_evidence_html(item)
            cards.append(
                "<article class='result-card'>"
                f"<h3>{html.escape(card_title or title)}</h3>"
                f"<p>{html.escape(card_body or card_title)}</p>"
                f"{evidence_html}"
                "</article>"
            )
        if cards:
            sections.append(
                "<section class='result-section'>"
                f"<h2>{html.escape(title)}</h2>"
                f"<div class='result-grid'>{''.join(cards)}</div>"
                "</section>"
            )

    _render_cards(result.get("key_points"), title="要点提炼", title_key="title", body_key="details")
    _render_cards(result.get("analysis_items"), title="分析展开", title_key="kind", body_key="statement")

    verification_items = result.get("verification_items")
    if isinstance(verification_items, list) and verification_items:
        cards: list[str] = []
        for item in verification_items:  # no truncation cap
            if not isinstance(item, dict):
                continue
            claim = str(item.get("claim") or "").strip()
            status = str(item.get("status") or "").strip() or "unclear"
            rationale = str(item.get("rationale") or "").strip()
            if not claim:
                continue
            cards.append(
                "<article class='result-card verification-card'>"
                f"<div class='status-chip status-{html.escape(status.lower())}'>{html.escape(status.title())}</div>"
                f"<h3>{html.escape(claim)}</h3>"
                f"<p>{html.escape(rationale or 'No rationale provided.')}</p>"
                f"{_resolved_evidence_html(item)}"
                "</article>"
            )
        if cards:
            sections.append(
                "<section class='result-section'>"
                "<h2>事实核验</h2>"
                f"<div class='result-grid'>{''.join(cards)}</div>"
                "</section>"
            )

    synthesis = result.get("synthesis")
    if isinstance(synthesis, dict):
        final_answer = str(synthesis.get("final_answer") or "").strip()
        next_steps = synthesis.get("next_steps")
        open_questions = synthesis.get("open_questions")
        extras: list[str] = []
        if isinstance(next_steps, list) and next_steps:
            extras.append(
                "<div><h3>下一步</h3><ul>"
                + "".join(f"<li>{html.escape(str(step))}</li>" for step in next_steps)
                + "</ul></div>"
            )
        if isinstance(open_questions, list) and open_questions:
            extras.append(
                "<div><h3>待解问题</h3><ul>"
                + "".join(f"<li>{html.escape(str(question))}</li>" for question in open_questions)
                + "</ul></div>"
            )
        if final_answer or extras:
            sections.append(
                "<section class='result-section result-takeaway'>"
                "<h2>核心结论</h2>"
                f"<p>{html.escape(final_answer)}</p>"
                f"{''.join(extras)}"
                "</section>"
            )

    warnings = result.get("warnings")
    if isinstance(warnings, list) and warnings:
        warning_items: list[str] = []
        for item in warnings:  # no truncation cap
            if not isinstance(item, dict):
                continue
            message = str(item.get("message") or "").strip()
            severity = str(item.get("severity") or "").strip()
            if not message:
                continue
            prefix = f"{severity.upper()}: " if severity else ""
            warning_items.append(f"<li>{html.escape(prefix + message)}</li>")
        if warning_items:
            sections.append(
                "<section class='result-section result-warnings'>"
                "<h2>风险提示</h2>"
                f"<ul>{''.join(warning_items)}</ul>"
                "</section>"
            )

    if not sections:
        return None
    return f"<div class='preview-reading structured-result'>{''.join(sections)}</div>"


def _product_view_html(product_view: dict[str, object]) -> str:
    sections_data = product_view.get("sections")
    if isinstance(sections_data, list):
        section_kinds = {str(item.get("kind") or "").strip() for item in sections_data if isinstance(item, dict)}
        layout = str(product_view.get("layout") or "").strip()
        render_hints = product_view.get("render_hints")
        layout_family = ""
        if isinstance(render_hints, dict):
            layout_family = str(render_hints.get("layout_family") or "").strip()
        selected_layout = layout or layout_family
        if selected_layout == "analysis_brief" or (not selected_layout and {"core_judgment", "main_arguments", "evidence"}.issubset(section_kinds)):
            return _analysis_product_view_html(product_view)
        if selected_layout == "practical_guide" or (not selected_layout and {"one_line_summary", "core_takeaways"}.issubset(section_kinds)):
            return _guide_product_view_html(product_view)
        if selected_layout == "review_curation":
            return _review_product_view_html(product_view)
        if selected_layout == "narrative_digest":
            return _narrative_product_view_html(product_view)

    sections: list[str] = []

    hero = product_view.get("hero")
    if isinstance(hero, dict):
        title = str(hero.get("title") or "").strip()
        dek = str(hero.get("dek") or "").strip()
        bottom_line = str(hero.get("bottom_line") or "").strip()
        worth_reading_reason = str(hero.get("worth_reading_reason") or "").strip()
        hero_bits = [
            f"<h2>{html.escape(title or '摘要')}</h2>",
        ]
        if dek:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        if bottom_line and bottom_line != dek:
            hero_bits.append(f"<p>{html.escape(bottom_line)}</p>")
        if worth_reading_reason:
            hero_bits.append(f"<p>{html.escape(worth_reading_reason)}</p>")
        if title or dek or bottom_line or worth_reading_reason:
            sections.append(f"<section class='result-section result-hero'>{''.join(hero_bits)}</section>")

    chips = product_view.get("chips")
    if isinstance(chips, list) and chips:
        chip_html: list[str] = []
        for chip in chips:
            if not isinstance(chip, dict):
                continue
            label = str(chip.get("label") or "").strip()
            value = str(chip.get("value") or "").strip()
            text = ": ".join(part for part in (label, value) if part)
            if text:
                chip_html.append(f"<div class='status-chip status-supported'>{html.escape(text)}</div>")
        if chip_html:
            sections.append("<section class='result-section'>" + "".join(chip_html) + "</section>")

    raw_sections = product_view.get("sections")
    if isinstance(raw_sections, list):
        sorted_sections = sorted(
            [item for item in raw_sections if isinstance(item, dict)],
            key=lambda item: _safe_priority(item),
        )
        for item in sorted_sections:
            title = str(item.get("title") or "").strip()
            blocks_html = _product_view_blocks_html(item.get("blocks"))
            if not blocks_html:
                continue
            heading = f"<h2>{html.escape(title)}</h2>" if title else ""
            sections.append(f"<section class='result-section'>{heading}{blocks_html}</section>")

    return "".join(sections)


def _analysis_product_view_html(product_view: dict[str, object]) -> str:
    def _uses_question_style_section(section_kind: str) -> bool:
        return section_kind in {"question_block", "reader_value"}

    parts: list[str] = ["<div class='analysis-brief-layout'>"]
    hero = product_view.get("hero")
    if isinstance(hero, dict):
        title = str(hero.get("title") or "").strip()
        dek = str(hero.get("dek") or "").strip()
        bottom_line = str(hero.get("bottom_line") or "").strip()
        hero_bits = [f"<h2>{html.escape(title or '深度分析')}</h2>"]
        if dek:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        if bottom_line and bottom_line != dek:
            hero_bits.append(f"<p>{html.escape(bottom_line)}</p>")
        parts.append(f"<section class='analysis-hero'>{''.join(hero_bits)}</section>")

    raw_sections = product_view.get("sections")
    if isinstance(raw_sections, list):
        sorted_sections = sorted(
            [item for item in raw_sections if isinstance(item, dict)],
            key=lambda item: _safe_priority(item),
        )
        for item in sorted_sections:
            title = str(item.get("title") or "").strip()
            section_kind = str(item.get("kind") or "").strip()
            blocks_html = _product_view_blocks_html(item.get("blocks"))
            if not blocks_html:
                continue
            uses_question_style = _uses_question_style_section(section_kind)
            label_html = ""
            if not uses_question_style and title:
                label_html = f"<div class='analysis-section-label'>{html.escape(title)}</div>"
            elif title:
                label_html = f"<h2>{html.escape(title)}</h2>"
            content_html = blocks_html
            if not uses_question_style:
                content_html = f"<div class='analysis-card-grid'>{blocks_html}</div>"
            parts.append(
                "<section class='result-section'>"
                f"{label_html}"
                f"{content_html}"
                "</section>"
            )
    parts.append("</div>")
    return "".join(parts)


def _guide_product_view_html(product_view: dict[str, object]) -> str:
    parts: list[str] = ["<div class='guide-digest-layout'>"]
    hero = product_view.get("hero")
    if isinstance(hero, dict):
        title = str(hero.get("title") or "").strip()
        dek = str(hero.get("dek") or "").strip()
        bottom_line = str(hero.get("bottom_line") or "").strip()
        hero_bits = [f"<h2>{html.escape(title or '要点提炼')}</h2>"]
        if dek:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        if bottom_line and bottom_line != dek:
            hero_bits.append(f"<p>{html.escape(bottom_line)}</p>")
        parts.append(f"<section class='guide-compact-hero'>{''.join(hero_bits)}</section>")

    raw_sections = product_view.get("sections")
    if isinstance(raw_sections, list):
        sorted_sections = sorted(
            [item for item in raw_sections if isinstance(item, dict)],
            key=lambda item: _safe_priority(item),
        )
        for item in sorted_sections:
            title = str(item.get("title") or "").strip()
            section_kind = str(item.get("kind") or "").strip()
            blocks_html = _product_view_blocks_html(item.get("blocks"))
            if not blocks_html:
                continue
            section_classes = "guide-section"
            if section_kind:
                section_classes += f" guide-section-{html.escape(section_kind)}"
            parts.append(
                f"<section class='result-section {section_classes}'>"
                f"<div class='guide-section-label'>{html.escape(title)}</div>"
                f"{blocks_html}"
                "</section>"
            )
    parts.append("</div>")
    return "".join(parts)


def _review_product_view_html(product_view: dict[str, object]) -> str:
    parts: list[str] = ["<div class='review-curation-layout'>"]
    hero = product_view.get("hero")
    if isinstance(hero, dict):
        title = str(hero.get("title") or "").strip()
        dek = str(hero.get("dek") or "").strip()
        bottom_line = str(hero.get("bottom_line") or "").strip()
        hero_bits = ["<div class='review-curation-label'>推荐导览</div>", f"<h2>{html.escape(title or '推荐导览')}</h2>"]
        if dek:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        if bottom_line and bottom_line != dek:
            hero_bits.append(f"<p>{html.escape(bottom_line)}</p>")
        parts.append(f"<section class='review-curation-hero'>{''.join(hero_bits)}</section>")

    raw_sections = product_view.get("sections")
    if isinstance(raw_sections, list):
        sorted_sections = sorted([item for item in raw_sections if isinstance(item, dict)], key=lambda item: int(item.get("priority") or 0))
        for item in sorted_sections:
            title = str(item.get("title") or "").strip()
            section_kind = str(item.get("kind") or "").strip()
            blocks_html = _product_view_blocks_html(item.get("blocks"))
            if not blocks_html:
                continue
            section_classes = "review-section"
            if section_kind:
                section_classes += f" review-section-{html.escape(section_kind)}"
            parts.append(
                f"<section class='result-section {section_classes}'>"
                f"<div class='review-curation-label'>{html.escape(title)}</div>"
                f"{blocks_html}"
                "</section>"
            )
    parts.append("</div>")
    return "".join(parts)


def _narrative_product_view_html(product_view: dict[str, object]) -> str:
    parts: list[str] = ["<div class='narrative-digest-layout'>"]
    hero = product_view.get("hero")
    if isinstance(hero, dict):
        title = str(hero.get("title") or "").strip()
        dek = str(hero.get("dek") or "").strip()
        hero_bits = ["<div class='narrative-section-label'>叙事导读</div>", f"<h2>{html.escape(title or '叙事导读')}</h2>"]
        if dek:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        parts.append(f"<section class='narrative-digest-hero'>{''.join(hero_bits)}</section>")

    raw_sections = product_view.get("sections")
    if isinstance(raw_sections, list):
        sorted_sections = sorted([item for item in raw_sections if isinstance(item, dict)], key=lambda item: int(item.get("priority") or 0))
        for item in sorted_sections:
            title = str(item.get("title") or "").strip()
            blocks_html = _product_view_blocks_html(item.get("blocks"))
            if not blocks_html:
                continue
            parts.append(
                "<section class='result-section'>"
                f"<div class='narrative-section-label'>{html.escape(title)}</div>"
                f"{blocks_html}"
                "</section>"
            )
    parts.append("</div>")
    return "".join(parts)


def _product_view_blocks_html(blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    rendered: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type") or "").strip().lower()
        if block_type == "paragraph":
            text = str(block.get("text") or "").strip()
            if text:
                rendered.append(f"<p>{html.escape(text)}</p>")
            continue
        if block_type in {"bullet_list", "step_list", "warning_list", "evidence_list"}:
            items = block.get("items")
            if not isinstance(items, list) or not items:
                continue
            tag = "ol" if block_type == "step_list" else "ul"
            rendered_items: list[str] = []
            for item in items:
                if isinstance(item, dict):
                    text = str(item.get("text") or item.get("value") or item.get("label") or "").strip()
                else:
                    text = str(item).strip()
                if text:
                    rendered_items.append(f"<li>{html.escape(text)}</li>")
            if rendered_items:
                rendered.append(f"<{tag}>{''.join(rendered_items)}</{tag}>")
            continue
        if block_type == "quote":
            text = str(block.get("text") or "").strip()
            if text:
                rendered.append(f"<blockquote><p>{html.escape(text)}</p></blockquote>")
    return "".join(rendered)


def _coverage_warning_html(entry: ResultWorkspaceEntry) -> str:
    """Return a coverage warning HTML block if the entry has truncation data."""
    coverage = entry.details.get("coverage")
    if coverage is None:
        return ""
    input_truncated = getattr(coverage, "input_truncated", False)
    if not input_truncated:
        return ""
    coverage_ratio = getattr(coverage, "coverage_ratio", 0.0)
    used = getattr(coverage, "used_segments", 0)
    total = getattr(coverage, "total_segments", 0)
    pct = int(coverage_ratio * 100)
    return (
        f"<div class='coverage-warning'>"
        f"&#9888; 覆盖范围提示：当前只分析了 {pct}% 的原始分段 "
        f"({used}/{total})。结论可能并不完整。"
        f"</div>"
    )


def _preview_html(entry: ResultWorkspaceEntry, *, resolved_mode: str | None = None) -> str:
    if entry.state == "processed":
        cov_html = _coverage_warning_html(entry)
        structured_html = _structured_preview_html(entry, coverage_html=cov_html, resolved_mode=resolved_mode)
        if structured_html is not None:
            return structured_html
        preview_text = _preview_body(entry)
        paragraphs = [part.strip() for part in preview_text.split("\n\n") if part.strip()]
        rendered = "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs)
        return f"<div class='preview-reading'>{rendered}</div>"
    return f"<pre>{html.escape(_preview_body(entry))}</pre>"


def _truncate_title(text: str, *, max_length: int = 64) -> str:
    stripped = text.strip()
    if len(stripped) <= max_length:
        return stripped
    return f"{stripped[: max_length - 1].rstrip()}..."


def _preview_hint(entry: ResultWorkspaceEntry) -> str:
    """Return a human-readable hint line for the preview section."""
    if entry.state == "processed":
        if _product_view_payload(entry) is not None:
            return "基于最新分析结果生成的阅读优先产品视图。"
        if _structured_result_payload(entry) is not None:
            return "基于最新分析结果整理出的结构化摘要、分析与证据。"
        if entry.analysis_state == "skipped":
            skip_reason = _analysis_skip_reason(entry)
            if skip_reason:
                return f"内容已抓取，但分析阶段被跳过：{skip_reason}。"
            return "内容已抓取，但在写出结构化结果前分析阶段被跳过。"
        if entry.analysis_state == "failed":
            return "内容已抓取，但在写出结构化结果前分析阶段失败。"
        if entry.analysis_state == "normalized_only":
            return "内容已抓取，但分析阶段没有附带结构化结果。"
        return "以下为抓取内容中的可读摘录。"
    if entry.state == "failed":
        return "以下为结果目录中的失败详情。"
    if entry.state == "processing":
        return "正在分析中，下方元数据反映的是最新状态。"
    return "任务已进入分析队列，下方信息来自抓取阶段的元数据。"


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------


def entry_to_markdown(entry: ResultWorkspaceEntry) -> str:
    """Serialise a ResultWorkspaceEntry to clean Markdown for clipboard/save."""
    brief = entry.details.get("insight_brief")

    if brief is not None:
        title = brief.hero.title
        one_take = brief.hero.one_sentence_take
        conclusion = brief.synthesis_conclusion
        takeaways = list(brief.quick_takeaways)
        gaps = list(brief.gaps)
    else:
        title = entry.title or "未命名结果"
        one_take = entry.summary or ""
        conclusion = None
        takeaways = []
        gaps = []

    lines: list[str] = [f"# {title}", ""]

    byline_parts = [v for v in (entry.author, entry.published_at, entry.platform) if v]
    if byline_parts:
        lines.append("**" + "** · **".join(byline_parts) + "**")
        lines.append("")

    source = entry.source_url or entry.canonical_url
    if source:
        lines += [f"来源链接：{source}", ""]

    if one_take:
        lines += ["## 摘要", "", one_take, ""]

    if takeaways:
        lines.append("## 要点提炼")
        lines.append("")
        for i, point in enumerate(takeaways, start=1):
            lines.append(f"{i}. {point}")
        lines.append("")

    if conclusion:
        lines += ["## 核心结论", "", conclusion, ""]

    if gaps:
        lines.append("## 问题与下一步")
        lines.append("")
        for gap in gaps:
            lines.append(f"- {gap}")
        lines.append("")

    visual_findings = [f for f in entry.details.get("visual_findings") or [] if isinstance(f, dict)]
    if visual_findings:
        lines.append("## 视觉证据")
        lines.append("")
        for finding in visual_findings:
            description = str(finding.get("description") or "").strip()
            if not description:
                continue
            ts_ms = finding.get("frame_timestamp_ms")
            if ts_ms is not None:
                try:
                    m, s = divmod(int(ts_ms) // 1000, 60)
                    prefix = f"[{m}:{s:02d}] "
                except (TypeError, ValueError):
                    prefix = ""
            else:
                prefix = ""
            lines.append(f"- {prefix}{description}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _markdown_filename(entry: ResultWorkspaceEntry) -> str:
    """Return a safe default filename like '2026-03-22-article-title.md'."""
    date_prefix = datetime.today().strftime("%Y-%m-%d")
    raw = entry.title or "result"
    slug = re.sub(r"[^\w]+", "-", raw, flags=re.UNICODE).strip("-").lower()[:48]
    slug = slug or "result"
    return f"{date_prefix}-{slug}.md"
