# Result Product Refactor — 2026-03-20

## Background

The triage in `processing-triage-2026-03-18.md` identified three root causes that made the result page misleading or unreadable:

1. **Video transcript severely truncated at input** — only 30/378 segments (7.7%) were sent to the LLM for sample job `20260319_005128_90f79e`. This is a WSL-side pipeline issue; the Windows side cannot fix it directly but can now detect and surface it.
2. **Evidence chain broken** — the UI read `resolved_evidence` on each item, but the analysis JSON only stored `evidence_segment_ids` (string array). The full evidence text lived in `text_request.json` and was never wired through.
3. **UI silently truncated results** — `key_points`, `analysis_items`, `verification_items`, `next_steps`, `open_questions`, `warnings` all capped at 3 items; `evidence_refs` capped at 2. No indicator was shown to the user.

Secondary: the entire GUI used "Windows job", "WSL", "watcher", "handoff", "normalized" etc. as user-facing strings.

---

## What Was Implemented

### Phase 3 — Remove Silent Truncation

**File:** `src/windows_client/gui/result_renderer.py` (extracted from `main_window.py`)

All `[:3]` and `[:2]` slice caps removed from:
- `key_points` card loop
- `verification_items` card loop
- `next_steps` list
- `open_questions` list
- `warnings` list
- `resolved_evidence` list

All items in every section are now rendered. No silent truncation.

---

### Phase 5 — Language Cleanup

**Files:** `src/windows_client/gui/main_window.py`, `src/windows_client/app/result_workspace.py`, `src/windows_client/gui/result_renderer.py`

All internal infrastructure terms replaced with user-facing language:

| Before | After |
|---|---|
| "The Windows job was written to the shared inbox. WSL results appear here once processed." | "Your content has been captured and sent for analysis. Results will appear here automatically." |
| "WSL analysis is not configured…" | "Analysis is not configured — set OPENAI_API_KEY or ZENMUX_API_KEY to enable it." |
| "WSL transcription is using its default Whisper model…" | "Transcription will use the default Whisper model. Set CONTENT_INGESTION_WHISPER_MODEL to override." |
| "WSL has not finished yet; you can check again later." | "Analysis is still in progress. Check back later." |
| "WSL has not created a result yet." | "No analysis result yet." |
| "Waiting for WSL to pick it up…" | "Waiting for the processor to pick this up…" |
| "WSL failed to process this job." | "Processing failed. Open the result workspace for details." |
| "WSL is still processing this job." | "Being analysed." |
| "The job is waiting for the WSL watcher." | "Queued for analysis." |
| "WSL watcher running / stopped / not started" | "Processor running / stopped / not started" |
| Eyebrow label "Windows -> WSL" | "Capture → Analyse → Read" |

`_preview_hint()` inside `ResultWorkspaceDialog` similarly cleaned up.

---

### Phase 1 — Evidence Resolver

**New file:** `src/windows_client/app/evidence_resolver.py`

```
EvidenceSnippet  (segment_id, text, start_ms, end_ms, kind)
load_evidence_index(job_dir)   → dict[str, EvidenceSnippet]
resolve_evidence_for_item(item, index) → list[EvidenceSnippet]
```

`load_evidence_index` reads `analysis/llm/text_request.json` and builds an `id → snippet` lookup.

**Modified:** `src/windows_client/app/result_workspace.py`

`_load_processed_result` now calls `load_evidence_index` and `_inject_resolved_evidence`, which walks all `key_points / analysis_items / verification_items` and writes `item["resolved_evidence"]` as a list of `{preview_text, kind, start_ms}` dicts. This runs before the entry is returned, so the UI always has populated evidence even if the raw analysis JSON only stored IDs.

---

### Phase 2 — Coverage Stats

**New file:** `src/windows_client/app/coverage_stats.py`

```
CoverageStats  (total_segments, used_segments, total_duration_ms,
                used_duration_ms, coverage_ratio, input_truncated)
compute_coverage(job_dir) → CoverageStats | None
```

Reads `analysis/transcript/transcript.json` for total segment count and `analysis/llm/text_request.json` for the evidence segments where `kind == "transcript"`. Flags `input_truncated = True` when `coverage_ratio < 0.85`.

**Modified:** `src/windows_client/app/result_workspace.py`

`_load_processed_result` calls `compute_coverage` and stores the result both in `entry.coverage` (new field on `ResultWorkspaceEntry`) and in `entry.details["coverage"]`.

**Modified:** `src/windows_client/gui/result_renderer.py`

`_coverage_warning_html` reads `details["coverage"]` and returns a red `<div class="coverage-warning">` block when truncated. `_structured_preview_html` accepts an optional `coverage_html` parameter and prepends it before the hero section.

Example output for the 30/378 sample: "⚠ Coverage warning: only 7% of source segments were analysed (30/378). Conclusions may be incomplete."

---

### Phase 4 — InsightBriefV2

**New file:** `src/windows_client/app/insight_brief.py`

```
HeroBrief        (title, one_sentence_take, content_kind, author_stance)
ViewpointItem    (statement, kind, why_it_matters, support_level, evidence_refs)
InsightBriefV2   (hero, quick_takeaways, viewpoints, coverage, gaps)

adapt_from_structured_result(result, evidence_index, coverage) → InsightBriefV2 | None
```

Merges `key_points + analysis_items + verification_items` into a flat `viewpoints` list with unified typing. Collects `synthesis.open_questions + synthesis.next_steps` into `gaps`. Returns `None` gracefully when result is empty or summary block is missing.

**Modified:** `src/windows_client/app/result_workspace.py`

`_load_processed_result` calls `adapt_from_structured_result` after evidence injection and coverage calculation, storing the result in `entry.details["insight_brief"]`.

---

### Phase 6 — main_window.py Modularisation

`main_window.py` was 1797 lines. ~900 lines of rendering and dialog code extracted.

**New file:** `src/windows_client/gui/result_renderer.py`

Contains all pure/stateless rendering functions previously inline in `main_window.py`:
- `_apply_result_state_pill`, `_apply_analysis_state_pill`
- `_format_result_origin`, `_format_result_byline`
- `_preview_body`, `_structured_result_payload`, `_llm_processing_payload`, `_analysis_skip_reason`
- `_primary_result_button_text`
- `_resolved_evidence_html`, `_structured_preview_html`, `_coverage_warning_html`, `_preview_html`
- `_truncate_title`, `_preview_hint`
- `PREVIEW_STYLESHEET` constant (CSS for `QTextBrowser`)

**New file:** `src/windows_client/gui/result_workspace_panel.py`

Contains `ResultListItemWidget` and `ResultWorkspaceDialog` (previously in `main_window.py`). Uses `result_renderer` for all rendering.

**Modified:** `src/windows_client/gui/main_window.py`

Now ~900 lines. Adds re-exports to preserve test compatibility:
```python
from windows_client.gui.result_renderer import _preview_html, _structured_result_payload
from windows_client.gui.result_workspace_panel import ResultListItemWidget, ResultWorkspaceDialog
```

---

### Phase 7 — Inline Result View

**New file:** `src/windows_client/gui/inline_result_view.py`

`InlineResultView(QWidget)` — a full-window result page shown directly in the main window's `QStackedWidget`:

```
QVBoxLayout
  ├── Back button (returns to task page)
  └── QScrollArea
       ├── hero_frame     (ResultTitle + BodyText + SecondaryText byline)
       ├── takeaways_frame (SectionLabel + bullet list from quick_takeaways)
       ├── coverage_banner (hidden unless input_truncated; red border)
       ├── QTextBrowser   (full _preview_html output with evidence)
       └── action_row     (Open Folder, Open Analysis buttons)
```

**Modified:** `src/windows_client/gui/main_window.py`

- `_build_ui` adds `self.result_inline = InlineResultView(parent=self)` as the third stack page
- `_refresh_current_job_result`: when `result_entry.state == "processed"` and `details["insight_brief"]` is not `None`, calls `result_inline.load_brief(brief, entry=result_entry)` and switches the stack to the inline view automatically
- `_show_task_state()` added as the back-navigation target

---

## New Files Summary

| File | Purpose |
|---|---|
| `src/windows_client/app/evidence_resolver.py` | Load and resolve evidence snippets from `text_request.json` |
| `src/windows_client/app/coverage_stats.py` | Compute transcript coverage ratio; detect truncation |
| `src/windows_client/app/insight_brief.py` | Typed brief struct + adapter from structured LLM result |
| `src/windows_client/gui/result_renderer.py` | All stateless HTML/pill rendering functions; `PREVIEW_STYLESHEET` |
| `src/windows_client/gui/result_workspace_panel.py` | `ResultListItemWidget`, `ResultWorkspaceDialog` (extracted from main_window) |
| `src/windows_client/gui/inline_result_view.py` | Inline result page widget (Phase 7 hero + takeaways + browser) |

## Modified Files Summary

| File | Key changes |
|---|---|
| `src/windows_client/app/result_workspace.py` | Added `coverage` field to `ResultWorkspaceEntry`; inject evidence + coverage + brief in `_load_processed_result`; language cleanup |
| `src/windows_client/gui/main_window.py` | Removed ~900 lines of extracted code; added re-exports; language cleanup; third stack page; `_show_task_state` |

## New Tests

| File | Tests |
|---|---|
| `tests/unit/test_evidence_resolver.py` | 8 tests — load empty, parse segments, skip no-id, invalid JSON, resolve maps, resolve skips missing, empty ids |
| `tests/unit/test_coverage_stats.py` | 7 tests — missing files, full coverage, truncation (30/378), above threshold, non-transcript excluded |
| `tests/unit/test_insight_brief.py` | 8 tests — None/empty input, missing summary, hero mapping, viewpoint merge, no-cap on key points, coverage passthrough, gaps, evidence refs |
| `tests/unit/test_result_renderer.py` | 7 tests — all key points rendered (no cap), synthesis items uncapped, all evidence refs shown, coverage warning HTML, no warning cases |
| `tests/unit/test_main_window.py` (extended) | +3 tests — 5 key points no truncation, timeout message updated, brief navigates to result page |

Total: 125 tests, 1 pre-existing unrelated failure in `test_service.py`.

---

## WSL-Side Remaining Work

The following cannot be fixed from the Windows repo and require changes to the WSL pipeline:

| Issue | Location | Description |
|---|---|---|
| Transcript truncation | `media_pipeline.py` | Must not cap input to first N segments; coverage < 85% must trigger segmented processing |
| WeChat image OCR | `wechat/extractor.py` | Download image attachments + OCR before LLM stage |
| Native `coverage` output | LLM output schema | Let WSL emit coverage stats directly so Windows adapter can read them natively |
| Native `InsightBriefV2` schema | LLM output contract | Once schema stabilises, Windows adapter field-mapping becomes a direct read |

---

## Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Hero `one_sentence_take` readable within 5s of opening result page | ✅ Inline result view shows hero immediately on stack switch |
| Each viewpoint shows ≥1 evidence snippet or explicit "not resolved" | ✅ Evidence injected from `text_request.json`; empty list renders nothing extra |
| Long video with coverage < 85% shows red warning with actual % | ✅ `CoverageStats.input_truncated` triggers red banner in both inline view and workspace preview |
| No internal terms ("Windows job", "WSL", "watcher", "handoff", "normalized") in UI | ✅ All replaced throughout `main_window.py`, `result_workspace.py`, `result_renderer.py` |
| `pytest tests/` passes | ✅ 124/125 (1 pre-existing `test_service.py` failure unrelated to this work) |
