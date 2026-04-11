# Pre-GUI Checkpoint 2026-03-14

## Purpose

This document records the current convergence point before Windows GUI implementation starts.

It is the review baseline for:

- what is already done
- what has been validated recently
- what is intentionally not being changed before GUI work
- what remains as known risk or follow-up after GUI starts

---

## Current Position

As of 2026-03-14, the Windows and WSL repositories should be treated as a working cross-repo MVP with a stable handoff contract.

Mainline path:

```text
Windows URL input
  -> Windows collector/exporter
  -> shared_inbox/incoming/<job_id>/
  -> WSL validate/claim/process
  -> processed/<job_id>/
```

This is no longer a speculative architecture.
It is a verified path with real processed jobs and repeatable local checks.

---

## Scope Completed Before GUI

### Windows

Completed on the Windows side:

- `doctor`
- `export-mock-job`
- `export-url-job`
- `browser-login`
- `export-browser-job`
- browser profile warm-up and automatic profile reuse
- `wait-for-selector` and `wait-for-selector-state`
- structured CLI errors via `WindowsClientError`
- metadata hints for title, author, and published-at
- richer exported metadata including `final_url`, `collection_mode`, and browser capture context
- GUI-facing workflow adapter and view models in `src/windows_client/app/workflow.py` and `src/windows_client/app/view_models.py`

### WSL

Completed on the WSL side:

- inbox validation and claim flow
- processing for `payload.html`, `payload.txt`, and `payload.md`
- success and failure output writing
- hint-first parsing for `title_hint`, `author_hint`, and `published_at_hint`
- filtered handoff context written into `processed/<job_id>/normalized.json`

### Cross-Repo

Completed across the repo boundary:

- shared inbox env-var alignment through `CONTENT_INGESTION_SHARED_INBOX_ROOT`
- formal handoff contract documentation
- repeatable Windows -> WSL roundtrip script
- roundtrip verification for `metadata.json -> normalized.json` alignment

---

## Validation Baseline

Revalidated on 2026-03-14:

- Windows unit tests: `38` passed
- WSL unit tests: `22` passed
- Windows -> WSL roundtrip script: success
- latest successful roundtrip mock job id at the time of writing: `20260314_154630_33e9b1`

Roundtrip currently verifies:

- processed output files exist
- `normalized.job_id` and `content_type` match processed `metadata.json`
- `normalized.asset.source_url` matches exported `source_url`
- `normalized.asset.canonical_url` matches `final_url` when present
- `normalized.asset.metadata.handoff` matches exported handoff fields when present

Residual note:

- Windows unit tests still emit a `ResourceWarning` about an unclosed socket from mocked networking, but the suite passes
- the recorded roundtrip `job_id` above is historical reference only and should not be treated as a fixed regression artifact

---

## Frozen Boundary Before GUI

The following boundary should be treated as stable for GUI phase 1:

- Windows business entry point: `src/windows_client/app/service.py`
- Windows GUI-facing adapter: `src/windows_client/app/workflow.py`
- Windows GUI view models: `src/windows_client/app/view_models.py`
- cross-repo payload contract: `docs/windows-wsl-handoff-contract.md`
- roundtrip regression path: `scripts/run_windows_wsl_roundtrip.ps1`

Practical rule:

- GUI should call the workflow layer
- GUI should not parse CLI stdout/stderr
- GUI should not reach into collector/exporter internals directly

---

## Intentionally Deferred

These items are known and intentionally not being solved before GUI work starts:

- broader real-site sampling beyond the current WeChat-heavy validation
- browser-mode roundtrip automation with a guaranteed local login/profile prerequisite
- watcher `SIGTERM` handling on the WSL side
- CI automation for cross-repo validation
- deeper deduplication of HTML metadata extraction across Windows and WSL
- OpenClaw pipeline integration beyond the current stub
- final decision on legacy WSL `sources/` and `session/` modules

These remain valid follow-ups, but they are not blockers for beginning GUI phase 1.

---

## Remaining Risks Relevant To GUI

The main risks still relevant to GUI design are:

- browser workflows still depend on local runtime prerequisites such as Playwright availability and warmed profiles
- browser-mode success on real sites can still vary with selector choice and login freshness
- successful processing status still lives partly across repo boundaries, so GUI phase 1 should stay focused on Windows export outcomes unless we explicitly add WSL status polling
- the current Windows test suite passes, but the socket `ResourceWarning` should be cleaned up later

None of these invalidate starting the GUI.
They do affect how much "end-to-end job tracking" the first GUI iteration should promise.

---

## Recommended GUI Phase 1 Boundary

The recommended first GUI slice is:

1. show `doctor` status
2. accept a URL
3. choose export mode: mock / http / browser
4. expose the most important browser options only
5. show structured success or failure state from `OperationViewState`
6. surface paths for `job_dir`, `payload_path`, and `metadata_path`

Do not make phase 1 depend on:

- real-time WSL watcher streaming
- attachment browsing
- pipeline visualization
- advanced session management UI

---

## Review Entry Points

For review before GUI ideation, read in this order:

1. `README.md`
2. `docs/windows-client-kickoff.md`
3. `docs/pre-gui-checkpoint-2026-03-14.md`
4. `docs/gui-phase1-design-2026-03-14.md`
5. `docs/windows-wsl-handoff-contract.md`
6. `docs/windows-wsl-roundtrip.md`
7. `docs/cross-review-2026-03-14.md` as optional review history
8. `src/windows_client/app/workflow.py`
9. `src/windows_client/app/view_models.py`

---

## Decision

Current recommendation:

- freeze the current export/handoff layer as the GUI baseline
- treat remaining pre-GUI work as non-blocking follow-up
- move next into GUI information architecture and visual design review
