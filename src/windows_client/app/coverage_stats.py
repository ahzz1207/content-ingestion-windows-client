from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CoverageStats:
    total_segments: int
    used_segments: int
    total_duration_ms: int | None
    used_duration_ms: int | None
    coverage_ratio: float
    input_truncated: bool  # True when coverage_ratio < 0.85


def compute_coverage(job_dir: Path) -> CoverageStats | None:
    """Compute transcript coverage statistics for a processed job.

    - Loads analysis/transcript/transcript.json → total_segments, total_duration_ms
    - Loads analysis/llm/text_request.json → used_segments (evidence_segments
      where kind == "transcript")
    - Returns None if either file is missing or cannot be parsed.
    """
    transcript_path = job_dir / "analysis" / "transcript" / "transcript.json"
    request_path = job_dir / "analysis" / "llm" / "text_request.json"

    if not transcript_path.exists() or not request_path.exists():
        return None
    try:
        transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    segments = transcript_data.get("segments")
    if not isinstance(segments, list):
        return None
    total_segments = len(segments)

    # Derive total duration from transcript segment end times (seconds → ms)
    total_duration_ms: int | None = None
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        end = seg.get("end")
        if isinstance(end, (int, float)):
            end_ms = int(end * 1000)
            if total_duration_ms is None or end_ms > total_duration_ms:
                total_duration_ms = end_ms

    # Count used transcript segments from evidence list
    evidence_segments = request_data.get("evidence_segments")
    if not isinstance(evidence_segments, list):
        used_segments = 0
        used_duration_ms: int | None = None
    else:
        used_segments = sum(
            1
            for s in evidence_segments
            if isinstance(s, dict) and str(s.get("kind") or "").strip() == "transcript"
        )
        used_duration_ms = None
        for seg in evidence_segments:
            if not isinstance(seg, dict):
                continue
            if str(seg.get("kind") or "").strip() != "transcript":
                continue
            end = seg.get("end_ms")
            if isinstance(end, (int, float)):
                end_ms = int(end)
                if used_duration_ms is None or end_ms > used_duration_ms:
                    used_duration_ms = end_ms

    coverage_ratio = used_segments / total_segments if total_segments > 0 else 1.0
    input_truncated = coverage_ratio < 0.85

    return CoverageStats(
        total_segments=total_segments,
        used_segments=used_segments,
        total_duration_ms=total_duration_ms,
        used_duration_ms=used_duration_ms,
        coverage_ratio=coverage_ratio,
        input_truncated=input_truncated,
    )
