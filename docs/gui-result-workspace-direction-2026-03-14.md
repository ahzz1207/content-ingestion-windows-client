# GUI Result Workspace Direction 2026-03-14

## Purpose

This document records the next GUI product direction after the first desktop shell became usable.

The key shift is:

- the GUI should no longer be treated only as a URL submission surface
- the GUI should begin becoming an entry point for browsing and understanding processed results

This is where the long-term product value lives.

---

## Why This Matters

Submitting a URL is not the real end goal.

The meaningful product outcome is:

- a URL is processed
- the processing chain can be followed
- the resulting normalized content can be reviewed
- the output can be summarized, analyzed, and reused

Without a result-focused surface, the GUI risks becoming only a thin shell over the Windows exporter.

---

## Product Reframing

Old emphasis:

- paste URL
- export job
- show export success

New emphasis:

- paste URL
- follow Windows -> WSL processing
- review the processed result
- make the result easy to revisit and inspect

This means the GUI should evolve toward a lightweight result workspace.

---

## Phase Split

### Phase 1

Already implemented:

- single URL entry
- automatic routing
- login guidance
- export progress and basic result state

### Phase 1.5

Delivered minimal result-workspace step:

- add a GUI entry into WSL processed results
- support the current job's processed result when available
- support opening recent pending, processing, processed, or failed results
- show normalized output in a result-focused surface
- provide a small recent-results list so the user can move between recent jobs across all current states
- provide an explicit refresh action so the workspace can be used to re-check a job without leaving the dialog

### Phase 2

Later full result workspace:

- recent job history
- filtering by processed / failed / pending
- stronger cross-repo task tracking
- richer normalized content browsing
- retry and revisit flows

---

## Phase 1.5 Standard

Phase 1.5 should achieve four things:

1. the user can open a processed result from inside the GUI
2. the current job can be checked against WSL output directories
3. the GUI can show whether the job is pending, processing, processed, or failed
4. the user can inspect a concise summary and open the underlying result files

This should still remain deliberately smaller than a full workspace or job browser.

---

## Minimal Result Model

The GUI needs a cross-repo result model that hides the file layout.

The minimum useful fields are:

- `job_id`
- result state: `pending`, `processing`, `processed`, `failed`
- `job_dir`
- `source_url`
- `platform`
- `title`
- `author`
- `published_at`
- `canonical_url`
- short summary
- preview text when available
- file paths for opening the underlying artifacts

This model should unify:

- `processed/<job_id>/normalized.json`
- `processed/<job_id>/normalized.md`
- `processed/<job_id>/status.json`
- `failed/<job_id>/error.json`
- `incoming/<job_id>/metadata.json`
- `processing/<job_id>/metadata.json`

---

## UI Direction

The first result-workspace entry should be simple:

- a `Result Workspace` entry on the ready screen
- a `Check WSL Result` action after export success
- an `Open Result` action once a processed or failed result exists
- intermediate `pending` and `processing` states may also be opened as "track in workspace"

The result surface itself should focus on:

- a compact recent-results list
- title or job identity
- result state
- source/platform summary
- concise metadata
- read-only preview
- open-folder / open-json / open-markdown actions

This is intentionally a focused inspection surface, not yet a full history browser.

---

## Constraints

Phase 1.5 should still avoid:

- real-time WSL watcher event streaming
- search
- tagging
- result editing
- analysis orchestration

A compact recent-results list is acceptable in Phase 1.5.
What remains out of scope is a richer job workspace with filtering, grouping, or persistent history management.

Those belong to later workspace phases.

---

## Engineering Implications

To support Phase 1.5 cleanly, the Windows GUI needs:

- a local result reader that understands the shared inbox result directories
- a result view model that abstracts over `processed/` and `failed/`
- GUI actions that refresh or open results without exposing raw folder structure

This should stay independent from the WSL codebase.
The Windows side should consume the shared inbox outputs, not import WSL modules.

---

## Success Criteria

This direction is successful if:

1. a user can start from the GUI and reach a processed result without leaving the app
2. the current job can be checked and opened after WSL finishes
3. failed results are inspectable without digging through folders manually
4. the GUI starts to feel like an entry point into output review, not only into URL submission

---

## Decision

The GUI should now be developed with two parallel priorities:

- keep the input flow simple
- steadily elevate the processed result into the primary object the user can inspect

The current stable stopping point for this phase is recorded in:

- `docs/gui-convergence-checkpoint-2026-03-14.md`
