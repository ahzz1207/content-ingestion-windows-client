# WSL U1-U4 Closeout Review

**Date:** 2026-03-29  
**Status:** review complete  
**Scope:** summarize the implemented U1-U4 upgrade work in the WSL repository and record the final review outcome after iterative fixes

---

## Context

This document records the closeout state of the WSL-side upgrade batch that followed the completed repair work.

Reference documents:

- `docs/wsl-processing-upper-bound-design-2026-03-28.md`
- `docs/wsl-upgrade-execution-plan-2026-03-28.md`

The implementation under review lives in the WSL repository at:

- `/home/ahzz1207/codex-demo`

The goal of this batch was to move the processor beyond the earlier single-pass summary pattern and lay the first structural foundation for stronger long-form understanding.

---

## Scope Completed

### U1: Input Quality Upgrade

#### U1a: Xiaohongshu denoise

Implemented in:

- `src/content_ingestion/raw/html_parser.py`

Shipped changes:

- added `xiaohongshu`-specific trimming branch in `parse_html()`
- added `_trim_xiaohongshu_block_records()`
- extended generic container signals with:
  - `note-text`
  - `desc`

Behavior added:

- remove pure hashtag lines
- remove interaction filler lines
- truncate tail once interaction noise streak crosses threshold
- trim excessive emoji tails
- keep denoise stats available for debug / validation

#### U1b: Long-content block budgeting

Implemented in:

- `src/content_ingestion/pipeline/llm_contract.py`
- `src/content_ingestion/core/config.py`

Shipped changes:

- added `llm_max_content_chars` to `Settings`
- added `CONTENT_INGESTION_LLM_MAX_CONTENT_CHARS`
- replaced fixed `blocks[:80]` truncation with `_select_blocks_within_budget()`
- added `_truncate_text()` for plain text fields

Final behavior:

- `content_text` and `transcript_text` now get head/tail truncation under a character budget
- block sampling is now strict-budgeted and type-aware
- headings count against budget
- quotes and list items have a capped share of remaining budget
- normal paragraphs are sampled across head / tail / middle with per-block budget guards

#### U1c: Evidence coverage expansion

Implemented in:

- `src/content_ingestion/pipeline/llm_contract.py`
- `src/content_ingestion/core/config.py`

Shipped changes:

- `llm_max_evidence_segments` default raised from `100` to `200`
- added `_select_evidence_within_budget()` with start / middle / end coverage logic

---

## U2: Reader + Synthesizer Prompt Split

Implemented in:

- `src/content_ingestion/core/models.py`
- `src/content_ingestion/pipeline/llm_contract.py`
- `src/content_ingestion/pipeline/llm_pipeline.py`

### Data model additions

Added dataclasses:

- `ChapterEntry`
- `ArgumentSkeletonItem`

Extended dataclasses:

- `SynthesisResult`
  - `what_is_new`
  - `tensions`
- `StructuredResult`
  - `chapter_map`
- `LlmAnalysisResult`
  - `reader_result_path`
  - `synthesizer_result_path`

### Pipeline changes

`analyze_asset()` was refactored into two serial text passes:

1. `Reader pass`
   - `build_reader_envelope()`
   - `_reader_instructions()`
   - `READER_SCHEMA`
   - writes `reader_request.json`
   - writes `reader_result.json`

2. `Synthesizer pass`
   - `build_synthesizer_envelope(reader_output=...)`
   - `_synthesizer_instructions()`
   - extended `TEXT_ANALYSIS_SCHEMA`
   - writes `text_request.json` for backward compatibility
   - writes `synthesizer_result.json`

### New output semantics

The processor now has first-class support for:

- chapter structure
- argument skeleton
- `what_is_new`
- `tensions`

These are carried into the structured result instead of being implied only through prose.

---

## U3: Visual / Contract Preparation

This batch did not complete the full rendered `visual_map` pipeline described in the execution plan.

However, the batch did preserve and strengthen visual-related structure on the analysis side:

- `visual_findings` remain a first-class output field
- they are kept distinct from `analysis_items`
- serialization paths remain clean and separate

This means the contract is in a better state for future visual-map work, even though the rendering stage is not yet part of this closeout.

---

## U4: Critique-Pass Readiness

This batch did not ship the full third-pass `Critique` implementation described in the longer-term plan.

What did land in this batch:

- clearer separation between structural understanding and deep synthesis
- stronger synthesis fields (`what_is_new`, `tensions`)
- a cleaner path for future critique layering

In other words:

- U4 as a standalone third LLM pass remains future work
- but U1-U2 successfully prepared the contract and pipeline shape needed to add it later

---

## Additional Quality Fixes Landed During Review

During review and follow-up fixes, the following issues were found and closed:

### 1. Repair path dropped `chapter_map`

Problem:

- after evidence-reference repair, `_build_structured_result(repaired_payload)` was called without the original `reader_payload`
- this caused repaired results to lose `chapter_map`

Fix:

- repair path now calls `_build_structured_result(repaired_payload, reader_payload=reader_payload)`

### 2. Reader pass lacked transcript visibility

Problem:

- `build_reader_envelope()` initially omitted `transcript_text`
- this weakened audio/video structure recognition

Fix:

- `transcript_text` now enters the reader context
- `transcript_truncated` is now surfaced separately from block truncation

### 3. Block sampler was not truly strict-budgeted

Problem:

- earlier sampling logic could still overshoot the intended budget in some edge cases

Fix:

- strict type-aware three-phase budget logic introduced
- middle sampling now uses per-block budget guards
- hidden off-by-one-style overflow path was removed

### 4. Test environment leakage

Problem:

- some tests used raw environment mutation and leaked state into later test cases

Fix:

- updated tests to use `monkeypatch.setenv(...)`

---

## Review Outcome

Final review status:

- no blocking review findings remain
- the batch is acceptable as a completed structural-upgrade milestone

What was specifically verified:

- long-text / transcript inputs now expose truncation signals
- reader and synthesizer outputs are both written as artifacts
- repair path preserves chapter structure
- synthesis carries `what_is_new` and `tensions`
- strict block budgeting no longer has the earlier soft-overflow behavior

---

## Tests

Final observed test baseline during review:

- `python3 -m pytest -q`
- result: `63 passed`

Test areas covered include:

- llm sampling behavior
- reader / synthesizer double-pass flow
- repair path preserving `chapter_map`
- xiaohongshu denoise
- transcript truncation flags

---

## Post-Closeout Follow-up (2026-03-29)

After closeout, two fresh processed jobs revealed a remaining mismatch between
the final consumer artifact (`normalized.json`) and the debugging artifact
(`analysis_result.json`):

- `normalized.json` already contained:
  - `result.chapter_map`
  - `result.synthesis.what_is_new`
  - `result.synthesis.tensions`
- but `analysis_result.json` still omitted:
  - top-level `reader_result_path`
  - top-level `synthesizer_result_path`
  - `result.chapter_map`
  - `result.synthesis.what_is_new`
  - `result.synthesis.tensions`

### Root Cause

The main analysis pipeline correctly built a full in-memory `StructuredResult`,
and the processor correctly carried that into `normalized.json`.

However, the separate `analysis_result.json` serialization path in
`src/content_ingestion/pipeline/llm_pipeline.py` still used an older manual
writeout shape:

- top-level `reader_result_path` / `synthesizer_result_path` were not written
- `_serialize_structured_result()` did not yet include:
  - `chapter_map`
  - `synthesis.what_is_new`
  - `synthesis.tensions`

### Follow-up Fix

Updated in:

- `src/content_ingestion/pipeline/llm_pipeline.py`
- `tests/unit/test_llm_pipeline.py`

Shipped corrections:

- `analysis_result.json` now includes:
  - `reader_result_path`
  - `synthesizer_result_path`
- serialized `result` now includes:
  - `chapter_map`
  - `synthesis.what_is_new`
  - `synthesis.tensions`
- regression tests now read the actual written `analysis_result.json`, instead
  of asserting only against the in-memory `StructuredResult`

### Follow-up Verification

- `python3 -m pytest tests/unit/test_llm_pipeline.py -q` -> `7 passed`
- `python3 -m pytest -q` -> `63 passed`

### Final Interpretation

The earlier user-facing validation was still correct because the final
consumer-facing artifact path already worked.

The issue was specifically:

- not a broken final result
- but an out-of-sync debugging / intermediate artifact

This follow-up closes that gap and brings `analysis_result.json` back into
contract parity with `normalized.json`.

---

## Net Result

This batch materially changed the WSL processor in three important ways:

1. input quality is less naive
2. long-form understanding no longer depends on a single monolithic pass
3. the structured result contract is more capable of supporting differentiated downstream outputs

The processor is still not at the full “research assistant” target.

But this batch successfully established the first meaningful foundation for:

- intent-aware analysis
- richer editorial outputs
- future card-template generation
- future critique pass

---

## Recommended Next Discussion Track

Now that U1-U4 closeout is complete, the next planning track should shift from repair to product-level output design:

- analysis mode taxonomy
- editorial schema
- insight card section atoms
- card template system by content intent

This is the layer where the processor can stop behaving like a generic summarizer and start behaving like a differentiated understanding engine.
