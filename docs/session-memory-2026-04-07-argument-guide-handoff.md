# Session Memory - 2026-04-07 Argument vs Guide Handoff

## Read This First Tomorrow

If you want to resume quickly tomorrow, read these files first in this order:

1. `docs/session-memory-2026-04-07-argument-guide-handoff.md`
2. `docs/superpowers/specs/2026-04-07-argument-vs-guide-reader-separation-design.md`
3. `docs/superpowers/plans/2026-04-07-argument-vs-guide-reader-separation.md`

Then inspect the implementation files:

4. `src/windows_client/app/service.py`
5. `src/content_ingestion/inbox/processor.py`
6. `src/content_ingestion/pipeline/llm_pipeline.py`
7. `src/windows_client/gui/result_renderer.py`

---

## Session Goal

This session had two major goals:

1. Fix reinterpretation so it performs a real rerun instead of local-clone metadata rewriting.
2. Make `argument` vs `guide` feel like two different reading products rather than one shared template with lightly different copy.

---

## What Was Fixed Today

### 1. Reinterpretation is now a real rerun

Previous behavior:

- `reinterpret_result()` in `src/windows_client/app/service.py` copied an already processed result directory
- metadata changed, but WSL did not rerun analysis
- this caused `auto`, `深度分析`, and `实用提炼` to look effectively identical

Current behavior:

- reinterpretation creates a fresh `incoming/<new-job-id>` job from the selected processed version
- original payload and capture artifacts are copied into the new incoming job
- `requested_reading_goal` and `requested_domain_template` are written into metadata
- Windows runs `watch_once` through `WslBridge`
- only after a new processed result exists does the code update `active_version.json`

Key files:

- `src/windows_client/app/service.py`
- `src/content_ingestion/inbox/processor.py`
- `src/content_ingestion/pipeline/llm_pipeline.py`

### 2. WSL generic `argument` vs `guide` product views were split more strongly

Previous behavior:

- `argument.generic` was basically summary + key points
- `guide.generic` was basically summary + steps
- the difference was too weak for the user to feel like template switching happened

Current behavior:

- `argument.generic` now emits:
  - `core_judgment`
  - `main_arguments`
  - `evidence`
  - `tensions`
  - `verification`
- `guide.generic` now emits:
  - `one_line_summary`
  - `core_takeaways`
  - `remember_this`
- `guide.generic` takeaway count is capped to 5 for compression

Key file:

- `src/content_ingestion/pipeline/llm_pipeline.py`

### 3. Windows GUI rendering was split for analysis vs compressed guide reading

Previous behavior:

- `product_view` mostly rendered through one shared section renderer
- user-visible difference was mostly content wording, not layout rhythm

Current behavior:

- `analysis_brief` / `argument.*` goes through a dedicated analytical renderer
- `practical_guide` / `guide.*` goes through a dedicated compact renderer
- new CSS/layout markers were introduced:
  - `analysis-brief-layout`
  - `analysis-hero`
  - `guide-digest-layout`
  - `guide-compact-hero`

Key file:

- `src/windows_client/gui/result_renderer.py`

---

## New Design/Plan Documents Added Today

- `docs/superpowers/specs/2026-04-07-argument-vs-guide-reader-separation-design.md`
- `docs/superpowers/plans/2026-04-07-argument-vs-guide-reader-separation.md`

These documents are specifically for the stronger separation of `深度分析` and `要点提炼`.

---

## User Feedback That Drove This Round

The user explicitly said the previous reinterpretation result still did not count as a real template change.

What the user wants:

- different templates must have different reading style
- different summary length and density
- different structure
- different visual guidance
- `深度分析` should be longer and expose arguments + evidence
- `要点提炼` should be short, dense, and highly compressed

Important product direction:

- this is not a copywriting tweak
- this is a reading-product separation problem

---

## Tests Run Today

### Reinterpretation and override plumbing

- `python -m pytest tests/unit/test_result_workspace.py -q`
  - result: `26 passed`
- `wsl.exe -d Ubuntu-22.04 bash -lc "cd /home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2 && python3 -m pytest tests/unit/test_processor.py -q"`
  - result: `12 passed`
- `python -m pytest tests/unit/test_main_window.py tests/unit/test_workflow.py tests/unit/test_service.py -q`
  - result: `54 passed`

### Argument vs guide separation

- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_main_window.py -q`
  - result: `55 passed`
- `wsl.exe -d Ubuntu-22.04 bash -lc "cd /home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2 && python3 -m pytest tests/unit/test_llm_pipeline.py -q"`
  - result: `37 passed`

All of the above were green before ending the session.

---

## What Still Needs Real User Validation

Even though focused tests passed, the next important step is manual product validation in the GUI.

Recommended manual checks tomorrow:

1. Open the GUI on this branch and submit or reuse one normal article.
2. Compare `深度分析` vs `要点提炼` on the same article.
3. Check whether the difference is now visible at first screen:
   - hero length
   - section count
   - argument/evidence presence
   - compressed takeaway rhythm
4. Decide whether the current split is strong enough or still needs another iteration.

This is likely the next decision point.

---

## Suggested Next Steps Tomorrow

### If the user says the new split is finally obvious enough

Then next likely follow-up work is:

- polish the guide compact layout further
- improve argument visual hierarchy further
- apply the same standard to `review`

### If the user says the split is still not strong enough

Then next likely work is:

- make `guide` even shorter and more aggressive
- reduce guide hero/body length further
- hide more secondary structure from guide mode
- make argument evidence blocks more card-like and explicit
- possibly add richer block rendering for argument evidence/verification

### If the user reports a new reinterpretation bug

Start by re-reading:

- `src/windows_client/app/service.py`
- `src/content_ingestion/inbox/processor.py`
- `src/content_ingestion/pipeline/llm_pipeline.py`

because reinterpretation correctness now depends on all three.

---

## Branch / Workspace State

- Windows worktree: `H:\demo-win\.worktrees\domain-aware-reader-v2`
- Branch: `feature/domain-aware-reader-v2`
- WSL worktree: `/home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2`
- WSL branch: `feature/domain-aware-reader-v2`

The user explicitly allowed commit and push at the end of this session.

---

## Key Takeaway

Today's most important product correction was this:

- reinterpretation is now real
- template separation is now moving from "content variation" toward "different reading products"

Tomorrow's job is not to rediscover architecture.

Tomorrow's job is to validate whether the current `argument` vs `guide` split is subjectively strong enough in the GUI, then iterate from that user experience.
