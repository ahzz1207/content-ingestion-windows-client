# Changelog — 2026-03-22

## Session Summary

This session covered two phases: (1) a deep architecture review of both the Windows client and WSL backend to ensure correctness before further development, and (2) implementation of three UX improvements plus two robustness fixes that came out of the review.

---

## Architecture Review Findings

A comprehensive review of both repos produced `docs/architecture-2026-03-22.md`. Key findings:

### Gaps found and fixed this session
| Gap | Severity | Fix |
|---|---|---|
| `whisper_timeout_seconds` in memory but never actually implemented in WSL code | Critical | Implemented: `Settings` field + `subprocess` timeout + `TimeoutExpired` handler |
| `synthesis.final_answer` never surfaced in GUI | Major | Added `synthesis_conclusion` to `InsightBriefV2`; shown as "Bottom Line" card |
| Evidence segment cap too low (40) → coverage warnings on normal articles | Major | Default raised 40 → 80 in WSL `config.py` |
| Polling cut off at 60s max — video jobs (3–10+ min) never auto-displayed | Critical | Replaced attempt-count with time-based adaptive polling (12 min cap) |
| Image input truncation data read but never shown in GUI | Minor | Added image truncation banner to `InlineResultView` |

### Known gaps intentionally deferred
- `visual_findings` from multimodal analysis stored in `analysis_result.json` but not surfaced in GUI
- `ArtifactStore` class in `result_workspace.py` is legacy dead code — safe to delete later
- No copy-to-clipboard on result page (deferred until layout stable)

---

## Changes Made

### WSL Backend (`/home/ahzz1207/codex-demo/src/content_ingestion/`)

#### `core/config.py`
- Added `whisper_timeout_seconds: int` field to `Settings` dataclass (default: 300 seconds / 5 minutes)
- Env var override: `CONTENT_INGESTION_WHISPER_TIMEOUT_SECONDS`
- Raised `llm_max_evidence_segments` default: `40` → `80`
  - **Why:** 40 segments only covers ~60% of a typical 3,000-word article; coverage warning banners were firing on normal content

#### `pipeline/media_pipeline.py`
- Updated `_run_whisper_command()` to accept `timeout_seconds: int | None = None`
- Added `try/except subprocess.TimeoutExpired` — returns synthetic `CompletedProcess(returncode=1)` on timeout
- Updated `_transcribe_audio()` call site to pass `timeout_seconds=settings.whisper_timeout_seconds`
  - **Why:** Previously Whisper could run indefinitely; long audio files would block the WSL processor forever

---

### Windows Client (`H:\demo-win\src\windows_client\`)

#### `app/insight_brief.py`
- Added `synthesis_conclusion: str | None = None` field to `InsightBriefV2` dataclass (last field, satisfies `slots=True` ordering)
- In `adapt_from_structured_result()`: extracts `synthesis.final_answer` → `synthesis_conclusion`
  - **Why:** `synthesis.final_answer` is the LLM's bottom-line conclusion — the most actionable single output — but was previously only buried inside the HTML browser

#### `app/result_workspace.py`
- Added `_read_llm_image_input(path: Path | None) -> dict[str, Any]` helper
- Reads `image_input_truncated`, `image_input_count`, `image_selection_warnings` from `analysis_result.json`
- Stores result in `details["llm_image_input"]` for display layer consumption

#### `gui/inline_result_view.py`
- Added **Bottom Line card** (`QFrame#BottomLineCard`) — blue-tinted, shown between Key Points and coverage banners
  - Displays `brief.synthesis_conclusion` when non-empty; hidden otherwise
  - Hidden in degraded view (no brief)
- Added **Image truncation banner** (`QFrame#CoverageBanner` reusing existing style)
  - Shown when `entry.details["llm_image_input"]["image_input_truncated"]` is True
  - Shows count of images sent to model

Layout order (after changes):
1. Hero block (title + one-sentence take)
2. Key Points (numbered takeaways)
3. **Bottom Line card** ← new
4. Coverage warning banner (input truncated)
5. **Image truncation banner** ← new
6. HTML browser (viewpoints + evidence)
7. Questions & Next Steps (gaps)
8. Action row (Open Folder / Export JSON)

#### `gui/main_window.py`

**Polling: replaced attempt-count with time-based adaptive intervals**

Before:
```python
AUTO_RESULT_POLL_INTERVAL_MS = 3000
AUTO_RESULT_POLL_MAX_ATTEMPTS = 20      # 60s total — cut off video jobs
```

After:
```python
AUTO_RESULT_POLL_INTERVAL_MS = 3000         # 0–60s: fast (articles done quickly)
AUTO_RESULT_POLL_SLOW_INTERVAL_MS = 10_000  # 60s–5min: patient (transcription)
AUTO_RESULT_POLL_VERY_SLOW_MS = 20_000      # 5min–12min: long video
AUTO_RESULT_POLL_TIMEOUT_SECONDS = 720      # 12 min hard cap
```

- `self._result_poll_attempts` → `self._result_poll_start_time: float`
- New `_poll_elapsed_seconds()` method
- `_schedule_result_poll()` selects interval based on elapsed time
- `_poll_current_job_result()` checks elapsed vs timeout (not attempt count)

**Live stage progress (zero WSL changes)**

Added `_infer_processing_stage(processing_job_dir: Path) -> str` — checks intermediate files:

| File present | Stage label |
|---|---|
| `analysis/llm/text_request.json` | "正在等待 LLM 响应…" |
| `analysis/transcript/transcript.json` | "转录完成，AI 正在分析中…" |
| (neither) | "AI 正在分析中…" (unchanged) |

Called from `_refresh_current_job_result()` when the current job is in "processing" state.

**New STAGE_LABELS entries:**
```python
"transcript_done": "转录完成，AI 正在分析中…",
"awaiting_llm":    "正在等待 LLM 响应…",
```

**QSS addition for Bottom Line card:**
```css
#BottomLineCard {
    background: rgba(37, 99, 235, 0.06);
    border: 1px solid rgba(37, 99, 235, 0.18);
    border-radius: 14px;
}
```

---

### Tests

All tests: **129 passed** (`pytest tests/unit/ -q`)

#### `tests/unit/test_insight_brief.py`
- `test_adapt_captures_synthesis_conclusion` — verifies `synthesis.final_answer` populates `InsightBriefV2.synthesis_conclusion`
- `test_adapt_synthesis_conclusion_none_when_missing` — verifies field is None when synthesis block absent

#### `tests/unit/test_result_workspace.py`
- `test_llm_image_input_read_when_present` — `analysis_result.json` with `image_input_truncated: true` flows into `details["llm_image_input"]`
- `test_llm_image_input_empty_when_no_analysis_file` — graceful empty dict when file absent

#### `tests/unit/test_main_window.py`
- Updated `test_poll_times_out_with_stable_message`: now patches `AUTO_RESULT_POLL_TIMEOUT_SECONDS = 0` instead of calling `_poll_current_job_result()` 20 times
  - **Why:** time-based polling can't be triggered by call count; patching the constant to 0 makes any elapsed time exceed the cap

---

### Documentation

#### `docs/architecture-2026-03-22.md` (new)
Full system architecture reference:
- JSON schemas for all inter-process data contracts
- LLM schema (verified from `llm_pipeline.py TEXT_ANALYSIS_SCHEMA`)
- Evidence resolution pipeline
- Coverage stats calculation
- Known caps and limits
- Known gaps

---

## Deferred / Future Work

| Item | Notes |
|---|---|
| Surface `visual_findings` in GUI | In `analysis_result.json` → needs new section in InlineResultView or HTML renderer |
| Delete `ArtifactStore` dead code | In `result_workspace.py`, never used |
| Copy-to-clipboard on result page | Straightforward addition once layout is stable |
| Verification status badge colors | `supported/partial/unsupported/unclear` — only "supported" shown distinctly today |
| Paste-to-auto-start | Clipboard watch on Ready page; held back (misfire risk on partial URLs) |
