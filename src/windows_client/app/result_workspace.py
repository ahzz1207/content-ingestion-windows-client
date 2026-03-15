from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ResultWorkspaceEntry:
    job_id: str
    state: str
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
    normalized_json_path: Path | None
    normalized_md_path: Path | None
    status_path: Path | None
    error_path: Path | None
    details: dict[str, Any]


def load_job_result(shared_root: Path, job_id: str) -> ResultWorkspaceEntry | None:
    processed_dir = shared_root / "processed" / job_id
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

    return None


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
    )
    candidates = [path for path in candidates if path.is_dir()]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    results: list[ResultWorkspaceEntry] = []
    for job_dir in candidates[:limit]:
        if job_dir.parent.name == "processed":
            results.append(_load_processed_result(job_dir))
        elif job_dir.parent.name == "failed":
            results.append(_load_failed_result(job_dir))
        elif job_dir.parent.name == "processing":
            results.append(_load_processing_result(job_dir))
        else:
            results.append(_load_pending_result(job_dir))
    return results


def _load_processed_result(job_dir: Path) -> ResultWorkspaceEntry:
    normalized_json_path = job_dir / "normalized.json"
    metadata_path = job_dir / "metadata.json"
    normalized_md_path = job_dir / "normalized.md"
    status_path = job_dir / "status.json"
    normalized = _read_json_file(normalized_json_path)
    asset = normalized.get("asset", {})
    status = _read_json_file(status_path)
    metadata = _coerce_dict(normalized.get("metadata"))
    llm_processing = _coerce_dict(metadata.get("llm_processing"))
    structured_result = _coerce_dict(asset.get("result"))

    preview_text = _build_processed_preview(normalized_md_path)
    summary = _build_processed_summary(
        asset=asset,
        structured_result=structured_result,
        llm_processing=llm_processing,
        preview_text=preview_text,
        markdown_exists=normalized_md_path.exists(),
    )

    return ResultWorkspaceEntry(
        job_id=str(normalized.get("job_id") or job_dir.name),
        state="processed",
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
        normalized_json_path=normalized_json_path if normalized_json_path.exists() else None,
        normalized_md_path=normalized_md_path if normalized_md_path.exists() else None,
        status_path=status_path if status_path.exists() else None,
        error_path=None,
        details={
            "normalized": normalized,
            "status": status,
            "metadata": _read_json_file(metadata_path) if metadata_path.exists() else {},
            "llm_processing": llm_processing,
            "structured_result": structured_result,
        },
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
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=None,
        author=None,
        published_at=None,
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary=_coerce_str(error.get("error_message")) or "WSL failed to process this job.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
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


def _load_processing_result(job_dir: Path) -> ResultWorkspaceEntry:
    metadata_path = job_dir / "metadata.json"
    metadata = _read_json_file(metadata_path) if metadata_path.exists() else {}
    return ResultWorkspaceEntry(
        job_id=str(metadata.get("job_id") or job_dir.name),
        state="processing",
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=_coerce_str(metadata.get("title_hint")),
        author=_coerce_str(metadata.get("author_hint")),
        published_at=_coerce_str(metadata.get("published_at_hint")),
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary="WSL is still processing this job.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
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
        updated_at=job_dir.stat().st_mtime,
        job_dir=job_dir,
        source_url=_coerce_str(metadata.get("source_url")),
        title=_coerce_str(metadata.get("title_hint")),
        author=_coerce_str(metadata.get("author_hint")),
        published_at=_coerce_str(metadata.get("published_at_hint")),
        platform=_coerce_str(metadata.get("platform")),
        canonical_url=_coerce_str(metadata.get("final_url")),
        summary="The job is waiting for the WSL watcher.",
        preview_text=None,
        metadata_path=metadata_path if metadata_path.exists() else None,
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

    llm_status = _coerce_str(llm_processing.get("status"))
    if llm_status and llm_status not in {"pass", "success"}:
        return "WSL normalized this job, but the LLM stage did not produce a structured result."
    if preview_text is None and markdown_exists:
        return "WSL processed this job, but the normalized preview text looks unreadable."
    return "WSL processed this job successfully."


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
    return replacement_ratio > 0.02 or control_ratio > 0.01 or readable_ratio < 0.85


def _is_readable_preview_char(ch: str) -> bool:
    codepoint = ord(ch)
    if ch.isascii() and (ch.isalnum() or ch in " .,;:!?-_()/[]{}'\"@#%&*+=<>|"):
        return True
    if _is_cjk_char(ch):
        return True
    if 0x3000 <= codepoint <= 0x303F:
        return True
    if 0xFF00 <= codepoint <= 0xFFEF:
        return True
    return False


def _is_cjk_char(ch: str) -> bool:
    codepoint = ord(ch)
    return 0x4E00 <= codepoint <= 0x9FFF


def _coerce_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _coerce_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
