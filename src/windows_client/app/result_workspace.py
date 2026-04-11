from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from windows_client.app.coverage_stats import CoverageStats, compute_coverage
from windows_client.app.evidence_resolver import (
    EvidenceSnippet,
    load_evidence_index,
    resolve_evidence_for_item,
)
from windows_client.app.insight_brief import InsightBriefV2, adapt_from_structured_result


@dataclass(slots=True)
class ResultWorkspaceEntry:
    job_id: str
    state: str
    analysis_state: str | None
    updated_at: float
    job_dir: Path | None
    source_url: str | None
    title: str | None
    author: str | None
    published_at: str | None
    platform: str | None
    canonical_url: str | None
    summary: str
    preview_text: str | None
    metadata_path: Path | None
    analysis_json_path: Path | None
    normalized_json_path: Path | None
    normalized_md_path: Path | None
    status_path: Path | None
    error_path: Path | None
    details: dict[str, Any]
    coverage: CoverageStats | None = None


def load_job_result(shared_root: Path, job_id: str) -> ResultWorkspaceEntry | None:
    processed_dir = _resolve_processed_job_dir(shared_root, job_id)
    if processed_dir.exists():
        return _load_processed_result(processed_dir)

    failed_dir = shared_root / "failed" / job_id
    if failed_dir.exists():
        return _load_failed_result(failed_dir)

    processing_dir = shared_root / "processing" / job_id
    if processing_dir.exists():
        return _load_processing_result(processing_dir)

    incoming_dir = shared_root / "incoming" / job_id
    if incoming_dir.exists():
        return _load_pending_result(incoming_dir)

    archived_dir = shared_root / "archived" / job_id
    if archived_dir.exists():
        return _load_archived_result(archived_dir)

    return None


def _resolve_processed_job_dir(shared_root: Path, job_id: str) -> Path:
    processed_dir = shared_root / "processed" / job_id
    active_version_path = processed_dir / "active_version.json"
    if not active_version_path.exists():
        return processed_dir
    try:
        active_version = _read_json_file(active_version_path)
    except Exception:
        return processed_dir
    active_job_id = _coerce_str(active_version.get("active_job_id"))
    if not active_job_id:
        return processed_dir
    active_dir = shared_root / "processed" / active_job_id
    if active_dir.exists():
        return active_dir
    return processed_dir


def load_latest_result(shared_root: Path) -> ResultWorkspaceEntry | None:
    results = list_recent_results(shared_root, limit=1)
    if not results:
        return None
    return results[0]


def list_recent_results(shared_root: Path, *, limit: int = 20) -> list[ResultWorkspaceEntry]:
    candidates = (
        list((shared_root / "processed").glob("*"))
        + list((shared_root / "failed").glob("*"))
        + list((shared_root / "processing").glob("*"))
        + list((shared_root / "incoming").glob("*"))
        + list((shared_root / "archived").glob("*"))
    )
    candidates = [path for path in candidates if path.is_dir()]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    processed_candidates = _dedupe_processed_candidates(shared_root, candidates)
    results: list[ResultWorkspaceEntry] = []
    for job_dir in processed_candidates:
        try:
            if job_dir.parent.name == "processed":
                results.append(_load_processed_result(job_dir))
            elif job_dir.parent.name == "failed":
                results.append(_load_failed_result(job_dir))
            elif job_dir.parent.name == "processing":
                results.append(_load_processing_result(job_dir))
            elif job_dir.parent.name == "archived":
                results.append(_load_archived_result(job_dir))
            else:
                results.append(_load_pending_result(job_dir))
        except Exception:
            continue
        if len(results) >= limit:
            break
    return results


def _dedupe_processed_candidates(shared_root: Path, candidates: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen_processed_job_ids: set[str] = set()
    for job_dir in candidates:
        if job_dir.parent.name != "processed":
            deduped.append(job_dir)
            continue
        resolved_dir = _resolve_processed_job_dir(shared_root, job_dir.name)
        resolved_job_id = resolved_dir.name
        if resolved_job_id in seen_processed_job_ids:
            continue
        seen_processed_job_ids.add(resolved_job_id)
        deduped.append(resolved_dir)
    return deduped


def _load_processed_result(job_dir: Path) -> ResultWorkspaceEntry:
    normalized_json_path = job_dir / "normalized.json"
    metadata_path = job_dir / "metadata.json"
    normalized_md_path = job_dir / "normalized.md"
    status_path = job_dir / "status.json"
    if not normalized_json_path.exists():
        raise FileNotFoundError(f"normalized.json not yet written: {normalized_json_path}")
    normalized = _read_json_file(normalized_json_path)
    asset = _coerce_dict(normalized.get("asset"))
    status = _read_json_file(status_path) if status_path.exists() else {}
    metadata = _resolve_processed_metadata(normalized, asset)
    llm_processing = _coerce_dict(metadata.get("llm_processing"))
    structured_result = _coerce_dict(asset.get("result"))
    analysis_json_path = _resolve_analysis_json_path(job_dir, llm_processing)
    analysis_state = _derive_analysis_state(structured_result=structured_result, llm_processing=llm_processing)

    preview_text = _build_processed_preview(normalized_md_path)
    summary = _build_processed_summary(
        asset=asset,
        structured_result=structured_result,
        llm_processing=llm_processing,
        analysis_state=analysis_state,
        preview_text=preview_text,
        markdown_exists=normalized_md_path.exists(),
    )

    evidence_index = load_evidence_index(job_dir)
    _inject_resolved_evidence(structured_result, evidence_index)
    coverage = compute_coverage(job_dir)
    brief = adapt_from_structured_result(structured_result, evidence_index, coverage)
    llm_image_input, visual_findings = _read_llm_image_input(analysis_json_path)

    details: dict[str, Any] = {
        "normalized": normalized,
        "status": status,
        "metadata": _read_json_file(metadata_path) if metadata_path.exists() else {},
        "llm_processing": llm_processing,
        "structured_result": structured_result,
        "product_view": _coerce_dict(structured_result.get("product_view")),
        "insight_brief": brief,
        "llm_image_input": llm_image_input,
        "visual_findings": visual_findings,
        "insight_card_path": _resolve_insight_card_path(job_dir),
    }
    if coverage is not None:
        details["coverage"] = coverage

    return ResultWorkspaceEntry(
        job_id=str(normalized.get("job_id") or job_dir.name),
        state="processed",
        analysis_state=analysis_state,
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(asset.get("source_url")),
        title=_coerce_str(asset.get("title")),
        author=_coerce_str(asset.get("author")),
        published_at=_coerce_str(asset.get("published_at")),
        platform=_coerce_str(asset.get("source_platform")),
        canonical_url=_coerce_str(asset.get("canonical_url")),
        summary=summary,
        preview_text=preview_text,
        metadata_path=metadata_path if metadata_path.exists() else None,
        analysis_json_path=analysis_json_path,
        normalized_json_path=normalized_json_path if normalized_json_path.exists() else None,
        normalized_md_path=normalized_md_path if normalized_md_path.exists() else None,
        status_path=status_path if status_path.exists() else None,
        error_path=None,
        details=details,
        coverage=coverage,
    )


def _load_failed_result(job_dir: Path) -> ResultWorkspaceEntry:
    metadata_path = job_dir / "metadata.json"
    status_path = job_dir / "status.json"
    error_path = job_dir / "error.json"
    metadata = _read_json_file(metadata_path) if metadata_path.exists() else {}
    error = _read_json_file(error_path) if error_path.exists() else {}

    return ResultWorkspaceEntry(
        job_id=str(metadata.get("job_id") or job_dir.name),
        state="failed",
        analysis_state="failed",
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=None,
        author=None,
        published_at=None,
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary=_coerce_str(error.get("error_message")) or "Processing failed.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
        analysis_json_path=None,
        normalized_json_path=None,
        normalized_md_path=None,
        status_path=status_path if status_path.exists() else None,
        error_path=error_path if error_path.exists() else None,
        details={
            "error": error,
            "status": _read_json_file(status_path) if status_path.exists() else {},
            "metadata": metadata,
        },
    )


def _load_archived_result(job_dir: Path) -> ResultWorkspaceEntry:
    if (job_dir / "normalized.json").exists():
        entry = _load_processed_result(job_dir)
        entry.state = "archived"
        return entry
    if (job_dir / "error.json").exists():
        entry = _load_failed_result(job_dir)
        entry.state = "archived"
        return entry
    metadata_path = job_dir / "metadata.json"
    metadata = _read_json_file(metadata_path) if metadata_path.exists() else {}
    return ResultWorkspaceEntry(
        job_id=str(metadata.get("job_id") or job_dir.name),
        state="archived",
        analysis_state=None,
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=_coerce_str(metadata.get("title") or metadata.get("title_hint")),
        author=None,
        published_at=None,
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary="Archived.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
        analysis_json_path=None,
        normalized_json_path=None,
        normalized_md_path=None,
        status_path=None,
        error_path=None,
        details={"metadata": metadata},
    )


def _load_processing_result(job_dir: Path) -> ResultWorkspaceEntry:
    metadata_path = job_dir / "metadata.json"
    metadata = _read_json_file(metadata_path) if metadata_path.exists() else {}
    return ResultWorkspaceEntry(
        job_id=str(metadata.get("job_id") or job_dir.name),
        state="processing",
        analysis_state="processing",
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=_coerce_str(metadata.get("title_hint")),
        author=_coerce_str(metadata.get("author_hint")),
        published_at=_coerce_str(metadata.get("published_at_hint")),
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary="Being analysed.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
        analysis_json_path=None,
        normalized_json_path=None,
        normalized_md_path=None,
        status_path=None,
        error_path=None,
        details={"metadata": metadata},
    )


def _load_pending_result(job_dir: Path) -> ResultWorkspaceEntry:
    metadata_path = job_dir / "metadata.json"
    metadata = _read_json_file(metadata_path) if metadata_path.exists() else {}
    return ResultWorkspaceEntry(
        job_id=str(metadata.get("job_id") or job_dir.name),
        state="pending",
        analysis_state="pending",
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=_coerce_str(metadata.get("title_hint")),
        author=_coerce_str(metadata.get("author_hint")),
        published_at=_coerce_str(metadata.get("published_at_hint")),
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary="Queued for analysis.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
        analysis_json_path=None,
        normalized_json_path=None,
        normalized_md_path=None,
        status_path=None,
        error_path=None,
        details={"metadata": metadata},
    )


def _read_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    return _coerce_str(_read_json_file(path).get(key))


def _read_text(path: Path, *, limit: int) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")[:limit]


def _inject_resolved_evidence(
    structured_result: dict[str, Any],
    evidence_index: dict[str, EvidenceSnippet],
) -> None:
    """Mutate structured_result items to add resolved_evidence lists."""
    for section_key in ("key_points", "analysis_items", "verification_items"):
        items = structured_result.get(section_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            snippets = resolve_evidence_for_item(item, evidence_index)
            item["resolved_evidence"] = [
                {
                    "preview_text": s.text[:200],
                    "kind": s.kind,
                    "start_ms": s.start_ms,
                }
                for s in snippets
            ]


def _build_processed_preview(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    paragraphs = _extract_preview_paragraphs(text)
    if not paragraphs:
        return None
    preview = "\n\n".join(paragraphs[:2]).strip()
    return preview[:900]


def _build_processed_summary(
    *,
    asset: dict[str, Any],
    structured_result: dict[str, Any],
    llm_processing: dict[str, Any],
    analysis_state: str | None,
    preview_text: str | None,
    markdown_exists: bool,
) -> str:
    summary_payload = _coerce_dict(structured_result.get("summary"))
    summary_headline = _coerce_str(summary_payload.get("headline"))
    summary_short_text = _coerce_str(summary_payload.get("short_text"))
    if summary_headline and summary_short_text and summary_short_text != summary_headline:
        return f"{summary_headline}: {summary_short_text}"
    if summary_short_text:
        return summary_short_text
    if summary_headline:
        return summary_headline

    asset_summary = _coerce_str(asset.get("summary"))
    if asset_summary:
        return asset_summary

    if preview_text is None and markdown_exists:
        return "Content was captured, but the preview text looks unreadable."
    if analysis_state == "skipped":
        skip_reason = _format_skip_reason(llm_processing)
        return f"Content was captured, but analysis was skipped{skip_reason}."
    if analysis_state == "failed":
        return "Content was captured, but analysis failed before a structured result was written."
    if analysis_state == "normalized_only":
        return "Content was captured, but the analysis stage did not produce a structured result."
    return "Content processed successfully."


def _resolve_processed_metadata(normalized: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    asset_metadata = _coerce_dict(asset.get("metadata"))
    if asset_metadata:
        return asset_metadata
    return _coerce_dict(normalized.get("metadata"))


def _resolve_analysis_json_path(job_dir: Path, llm_processing: dict[str, Any]) -> Path | None:
    output_path = _coerce_str(llm_processing.get("output_path"))
    if output_path:
        candidate = Path(output_path)
        if not candidate.is_absolute():
            candidate = job_dir / output_path
        if candidate.exists():
            return candidate
    candidate = job_dir / "analysis" / "llm" / "analysis_result.json"
    if candidate.exists():
        return candidate
    return None


def _derive_analysis_state(*, structured_result: dict[str, Any], llm_processing: dict[str, Any]) -> str:
    if structured_result:
        return "ready"
    llm_status = (_coerce_str(llm_processing.get("status")) or "").lower()
    if llm_status in {"pass", "success"}:
        return "normalized_only"
    if llm_status == "skipped":
        return "skipped"
    if llm_status in {"failed", "error"}:
        return "failed"
    return "normalized_only"


def _format_skip_reason(llm_processing: dict[str, Any]) -> str:
    skip_reason = _coerce_str(llm_processing.get("skip_reason"))
    if not skip_reason:
        return ""
    return f": {skip_reason}"


def _extract_preview_paragraphs(text: str) -> list[str]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n", cleaned) if block.strip()]
    paragraphs: list[str] = []
    for block in blocks:
        if block.startswith("#"):
            continue
        if block == "---":
            continue
        if block.startswith("- "):
            continue
        block = re.sub(r"\s+", " ", block).strip()
        if not block:
            continue
        if _looks_unreadable_text(block):
            continue
        paragraphs.append(block)
        if len(paragraphs) >= 2:
            break
    return paragraphs


def _looks_unreadable_text(text: str) -> bool:
    stripped = "".join(ch for ch in text if not ch.isspace())
    if not stripped:
        return False
    replacement_ratio = stripped.count("\ufffd") / len(stripped)
    control_ratio = sum(1 for ch in stripped if ord(ch) < 32) / len(stripped)
    readable_ratio = sum(1 for ch in stripped if _is_readable_preview_char(ch)) / len(stripped)
    meaningful_chars = sum(1 for ch in stripped if ch.isalnum() or _is_cjk_char(ch))
    if len(stripped) < 20 and meaningful_chars < 8:
        return True
    return replacement_ratio > 0.02 or control_ratio > 0.01 or readable_ratio < 0.70


def _is_readable_preview_char(ch: str) -> bool:
    codepoint = ord(ch)
    if ch.isascii() and (ch.isalnum() or ch in " .,;:!?-_()/[]{}'\"@#%&*+=<>|"):
        return True
    if _is_cjk_char(ch):
        return True
    # CJK extension: compatibility ideographs, radicals
    if 0x2E80 <= codepoint <= 0x2FFF:
        return True
    # CJK punctuation & symbols, full-width forms
    if 0x3000 <= codepoint <= 0x303F:
        return True
    if 0xFF00 <= codepoint <= 0xFFEF:
        return True
    # Hiragana / Katakana
    if 0x3040 <= codepoint <= 0x30FF:
        return True
    # Korean Hangul syllables
    if 0xAC00 <= codepoint <= 0xD7AF:
        return True
    # Latin Extended (accented chars: é ü ñ etc.)
    if 0x00C0 <= codepoint <= 0x02FF:
        return True
    # Cyrillic
    if 0x0400 <= codepoint <= 0x04FF:
        return True
    # Arabic
    if 0x0600 <= codepoint <= 0x06FF:
        return True
    # General punctuation (curly quotes, dashes, ellipsis …)
    if 0x2000 <= codepoint <= 0x206F:
        return True
    return False


def _is_cjk_char(ch: str) -> bool:
    codepoint = ord(ch)
    return 0x4E00 <= codepoint <= 0x9FFF


def _read_llm_image_input(path: Path | None) -> tuple[dict[str, Any], list[Any]]:
    """Return (image_input_meta, visual_findings) from analysis_result.json."""
    if path is None:
        return {}, []
    try:
        data = _read_json_file(path)
        image_meta = {
            "image_input_truncated": bool(data.get("image_input_truncated", False)),
            "image_input_count": int(data.get("image_input_count") or 0),
            "image_selection_warnings": list(data.get("image_selection_warnings") or []),
        }
        raw_findings = data.get("visual_findings")
        visual_findings = list(raw_findings) if isinstance(raw_findings, list) else []
        return image_meta, visual_findings
    except Exception:
        return {}, []


def _resolve_insight_card_path(job_dir: Path) -> Path | None:
    p = job_dir / "analysis" / "insight_card.png"
    return p if p.exists() else None


def _coerce_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _coerce_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
