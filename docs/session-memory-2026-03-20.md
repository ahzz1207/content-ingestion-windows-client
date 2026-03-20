# Session Memory - 2026-03-20

## Context

This note captures the current shared understanding from the 2026-03-20 review pass so the next session can resume without re-triaging the whole repo.

Primary user goal:

- make the final result feel like a product that helps users quickly understand what an article or video is saying
- make the output clearly extract viewpoints, not just produce a generic summary
- prioritize result quality over visual polish

Confirmed preference baseline:

- result product first
- phased rollout
- mixed article + video usage

## Current Product Judgment

The main product problem is still the result artifact, not just the shell UI.

What matters most:

1. success states are still too process-oriented in several places
2. the app only partially behaves like a result-first reading surface
3. long-video and image-heavy article understanding still depends heavily on upstream input quality

## Key Findings From This Session

### 1. Claude 2026-03-20 refactor doc is directionally good

Reviewed file:

- `docs/result-product-refactor-2026-03-20.md`

The document correctly identified:

- video transcript truncation as a root cause
- broken evidence chain in the UI
- silent result truncation in rendering
- the need to reduce infrastructure-heavy user-facing language

### 2. But the current implementation is not yet trustworthy on real samples

High-confidence issue:

- `src/windows_client/app/evidence_resolver.py`
- `src/windows_client/app/coverage_stats.py`

Both currently read `text_request.json` as if `evidence_segments` were top-level.

Real processed samples show:

- `evidence_segments` lives under `document.evidence_segments`
- `allowed_evidence_ids` lives under `document.allowed_evidence_ids`

Observed on real sample jobs:

- `20260319_005128_90f79e`
- `20260319_002315_3124af`

Practical effect on real data:

- `load_evidence_index(...)` returns zero snippets
- evidence injection appears implemented but does not actually work for current sample files
- video coverage is miscomputed

### 3. Coverage is also partially misread from transcript data

Real `analysis/transcript/transcript.json` samples use:

- `start_ms`
- `end_ms`

Current `coverage_stats.py` logic looks for `start` / `end` seconds in transcript segments.

Result:

- `total_duration_ms` can be wrong or missing
- current coverage warnings are not yet reliable enough to trust blindly

### 4. Tests currently overfit fake data shape

Relevant tests:

- `tests/unit/test_evidence_resolver.py`
- `tests/unit/test_coverage_stats.py`

These fixtures currently write `evidence_segments` at the top level of `text_request.json`, so they validate the wrong contract and can pass while production samples fail.

### 5. InsightBriefV2 exists, but has not fully taken over the reading experience

Relevant files:

- `src/windows_client/app/insight_brief.py`
- `src/windows_client/gui/inline_result_view.py`

Current state:

- hero and takeaways are present
- main reading body still renders through the older `_preview_html(entry)` path

Implication:

- result UX is improved, but not yet truly rebuilt around the new brief model

### 6. Missing-evidence empty state is still weak

Relevant file:

- `src/windows_client/gui/result_renderer.py`

Current behavior:

- if a card has no resolved evidence, the UI renders nothing extra

Why this matters:

- user cannot distinguish between "no evidence exists", "evidence was not parsed", and "evidence was intentionally omitted"

### 7. Some visible polish regressions exist

Observed issue:

- inline result view contains stray `路` characters in separators / bullets

Relevant file:

- `src/windows_client/gui/inline_result_view.py`

This is minor compared with data-contract issues, but it weakens trust and finish quality.

## Most Important Next Steps

### Phase A - Fix real-data contract alignment first

Must do before declaring the refactor successful:

- update evidence resolver to read `document.evidence_segments`
- update coverage stats to read the real request shape
- update coverage stats to use real transcript segment fields (`start_ms`, `end_ms`)
- replace test fixtures so they match real file structure

### Phase B - Make InsightBriefV2 the true primary reading model

- stop relying on old preview HTML as the main inline reading surface
- render `viewpoints` and `gaps` directly from the brief object
- show explicit fallback text when evidence is unavailable

### Phase C - Continue upstream content-quality work

Windows-side display fixes are not enough by themselves.

Remaining upstream work still needed:

- WSL long-video segmented summarization instead of front-slice truncation
- WeChat OCR / image text extraction
- eventual native upstream `InsightBriefV2` and coverage output

## Stable Conclusions To Reuse Next Session

- do not spend the next session mostly on visual polish
- first restore correctness of evidence + coverage on real processed jobs
- after that, make the brief model actually own the main reading experience
- only then evaluate whether the product now feels like "users can quickly get what this article/video says and what viewpoints can be extracted"

## Useful Sample Jobs

- `data/shared_inbox/processed/20260319_005128_90f79e`
- `data/shared_inbox/processed/20260319_002315_3124af`
- `data/shared_inbox/processed/20260319_004615_2340ff`
- `data/shared_inbox/processed/20260318_221635_907833`

## Note

There is also one pre-existing unrelated test failure still present in the suite:

- `tests/unit/test_service.py`

Cause:

- environment-variable-sensitive expectation around `wsl_llm_credentials_available`
