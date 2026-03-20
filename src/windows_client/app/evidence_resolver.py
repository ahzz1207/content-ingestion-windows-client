from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EvidenceSnippet:
    segment_id: str
    text: str
    start_ms: int | None
    end_ms: int | None
    kind: str | None  # "transcript" | "text_block" | "danmaku" | ...


def load_evidence_index(job_dir: Path) -> dict[str, EvidenceSnippet]:
    """Read job_dir/analysis/llm/text_request.json evidence_segments array.

    Returns id→snippet dict. Returns empty dict if the file does not exist or
    cannot be parsed.
    """
    path = job_dir / "analysis" / "llm" / "text_request.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    segments = data.get("evidence_segments")
    if not isinstance(segments, list):
        return {}
    index: dict[str, EvidenceSnippet] = {}
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_id = str(seg.get("id") or "").strip()
        if not seg_id:
            continue
        text = str(seg.get("text") or "").strip()
        start_ms_raw = seg.get("start_ms")
        end_ms_raw = seg.get("end_ms")
        start_ms = int(start_ms_raw) if isinstance(start_ms_raw, (int, float)) else None
        end_ms = int(end_ms_raw) if isinstance(end_ms_raw, (int, float)) else None
        kind = str(seg.get("kind") or "").strip() or None
        index[seg_id] = EvidenceSnippet(
            segment_id=seg_id,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
            kind=kind,
        )
    return index


def resolve_evidence_for_item(
    item: dict[str, object], index: dict[str, EvidenceSnippet]
) -> list[EvidenceSnippet]:
    """Resolve item["evidence_segment_ids"] IDs into EvidenceSnippet list.

    Skips IDs that are not in the index.
    """
    ids = item.get("evidence_segment_ids")
    if not isinstance(ids, list):
        return []
    snippets: list[EvidenceSnippet] = []
    for seg_id in ids:
        seg_id_str = str(seg_id).strip()
        snippet = index.get(seg_id_str)
        if snippet is not None:
            snippets.append(snippet)
    return snippets
