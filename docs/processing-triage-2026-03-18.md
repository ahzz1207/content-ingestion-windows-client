# Processing Triage - 2026-03-18

## Scope

This note records confirmed issues found while investigating the current Windows + WSL ingestion flow.

Focus areas:

- WeChat image-heavy articles
- Bilibili audio transcription quality
- LLM execution and result visibility
- GUI result workspace file targeting

---

## Confirmed Findings

### 1. WeChat image content is not preserved as analyzable assets

Severity: high

Confirmed facts:

- The WeChat extractor strips `#js_content` down to plain text and removes all HTML tags, including image structure.
- The current extractor returns only `content_text` and does not emit image attachments.
- A real processed WeChat job at `data/shared_inbox/processed/20260316_191459_a9f88b` contains only:
  - `visible_text`
  - `media_manifest`
  - `capture_validation`
- The same sample still records image URLs in `attachments/derived/media_manifest.json`, but those images are not downloaded, attached, OCR'd, or sent to the LLM.

Code evidence:

- WeChat HTML is flattened to text in `/home/ahzz1207/codex-demo/src/content_ingestion/sources/wechat/extractor.py:36`
- HTML tags are removed in `/home/ahzz1207/codex-demo/src/content_ingestion/sources/wechat/extractor.py:66`

Impact:

- image-only charts, tables, and infographic content are effectively lost
- article output can look coherent while omitting core information
- LLM image grounding never happens for WeChat because no image attachments exist

Required fix direction:

- download and persist WeChat article images as attachments
- attach positional references from article body to image assets
- add OCR or image-caption extraction for image-only sections
- include retained images in the LLM text-image envelope

---

### 2. Bilibili transcription defaults to Whisper `base`

Severity: high

Confirmed facts:

- WSL processing uses the `whisper` CLI, not a newer transcription stack.
- The default model is `base` unless `CONTENT_INGESTION_WHISPER_MODEL` overrides it.
- Video input is converted to mono 16 kHz WAV before transcription.

Code evidence:

- Default model is set in `/home/ahzz1207/codex-demo/src/content_ingestion/core/config.py:88`
- Whisper CLI is invoked in `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/media_pipeline.py:68`
- The actual transcription subprocess is built in `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/media_pipeline.py:261`

Impact:

- the current default is not strong enough for noisy long-form Chinese video
- there is no language hint, domain prompt, or segmentation strategy
- downstream analysis quality is capped by a weak transcript baseline

Required fix direction:

- replace the current default with a stronger ASR path
- likely candidates are a larger Whisper-family model or a more modern Chinese-friendly ASR stack
- add explicit language handling for Chinese
- keep transcript JSON with timestamps, but improve source quality first

---

### 3. Transcript text is sent to the LLM in code, but the sampled Bilibili job never reached the LLM

Severity: critical

Confirmed facts:

- Media processing writes `asset.transcript_text` and `asset.analysis_text`.
- The text-analysis envelope includes `transcript_text`, evidence segments, and attachments.
- However, the sampled processed Bilibili job `20260317_235750_f22aee` has:
  - `llm_processing_status = skipped`
  - `llm_skip_reason = missing OPENAI_API_KEY`
- That means the bad result quality in that sample is not because the transcript was ignored by prompt assembly. The LLM stage did not run at all.

Code evidence:

- Transcript and analysis text are prepared in `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/media_pipeline.py:74`
- Transcript and evidence segments are included in the LLM request in `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_contract.py:124`
- LLM processing aborts when the API key is missing in `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py:172`

Impact:

- the pipeline can look "successful" at the job level while producing no real analysis
- users can misread normalized output as LLM output
- current GUI presentation does not make this failure prominent enough

Required fix direction:

- surface LLM skip/failure status as a first-class result state
- fail louder when the user's intent requires analysis but no LLM credentials exist
- optionally block video "analysis" runs unless the LLM stage is configured

---

### 4. GUI result workspace had two real output-targeting bugs

Severity: high

Confirmed facts before fix:

- The GUI loaded `normalized.get("metadata")` instead of `normalized["asset"]["metadata"]`, so `llm_processing` metadata was not being read correctly.
- "Open JSON" pointed to `normalized.json` first, not `analysis/llm/analysis_result.json`.
- "Open Markdown" pointed to `normalized.md`, which is normalized source content, not an LLM-authored analysis artifact.

Code evidence before fix:

- Processed result loading in [result_workspace.py](H:\demo-win\src\windows_client\app\result_workspace.py#L81)
- Preview/result selection in [main_window.py](H:\demo-win\src\windows_client\gui\main_window.py#L145)
- Open-file actions in [main_window.py](H:\demo-win\src\windows_client\gui\main_window.py#L892)

Changes applied in this turn:

- fixed processed-result metadata lookup to read `asset.metadata`
- added `analysis_result_path` to processed result entries
- changed "Open JSON" to prefer `analysis/llm/analysis_result.json`
- changed the button label to `Open Analysis JSON` when that file exists
- changed the markdown button label to `Open Normalized Markdown`
- improved preview hint text so LLM skip reasons can surface

Remaining gap:

- there is still no dedicated markdown analysis artifact, only JSON
- the UI still needs a more explicit "analysis unavailable" state

---

## Priority Order

1. Fix LLM configuration visibility and failure behavior
2. Replace the default transcription path for video/audio
3. Preserve WeChat images as first-class assets
4. Add OCR / image grounding for image-heavy articles
5. Tighten result workspace semantics around normalized vs analysis outputs

---

## Recommended Next Build Slice

### Slice A

- fail clearly when LLM credentials are missing
- show LLM status in the GUI as a top-level state
- keep the current GUI frozen aside from truthfulness fixes

### Slice B

- replace default Whisper `base`
- add language-aware transcription configuration
- validate on one Chinese Bilibili sample and one Mandarin speech sample

### Slice C

- download WeChat images into attachments
- wire those images into the LLM text-image request path
- add OCR fallback for images with dense text

This order addresses the most misleading failure first: the system currently produces "results" even when the analysis stage is skipped.
