# Final Handoff 2026-04-11 Main Acceptance And Worktree Cleanup

This document records the current stopping point after the Windows GUI repo and the WSL processing repo were both merged locally into `main` acceptance worktrees, verified, and partially cleaned up.

## What Landed

### Windows

The Windows-side feature work was merged locally into a dedicated `main` acceptance worktree at:

- `H:\demo-win\.worktrees\main-acceptance`

The merged Windows work includes:

- source-centric knowledge library flow
- save / restore library interpretation support
- improved deep-analysis reading layout
- improved result rendering for question-driven sections
- question-driven `product_view` consumption in the Windows reader
- coverage fallback for nested `document.evidence_segments`
- bilibili / watchlater routing and profile reuse fixes

The key feature branch commit that was folded into local `main` was:

- `e08a222` `feat: complete source-centric reading workflow`

### WSL

The WSL-side generation work was merged locally into a dedicated `main` acceptance worktree at:

- `/home/ahzz1207/codex-demo/.worktrees/main-acceptance`

The merged WSL work includes:

- `StructuredResult.product_view`
- question-driven `argument` mode product-view generation
- hero fields for direct conclusion presentation
- question-block sections for deep analysis
- final `reader_value` section titled `这对我意味着什么？`
- serialization into both `analysis_result.json` and `normalized.json`

The key feature branch commit that was folded into local `main` was:

- `5c64b96` `feat: add question-driven product view output`

---

## Current Verified State

### Windows main acceptance

Worktree:

- `H:\demo-win\.worktrees\main-acceptance`

Branch state at verification time:

- `main...origin/main [ahead 9]`

Verification command:

```bash
python -m pytest tests/unit/test_result_workspace.py tests/unit/test_insight_brief.py tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_api/test_job_manager.py tests/unit/test_main_window.py -q
```

Verified result:

- `211 passed, 1 skipped in 7.13s`

### WSL main acceptance

Worktree:

- `/home/ahzz1207/codex-demo/.worktrees/main-acceptance`

Branch state at verification time:

- `main...origin/main [ahead 4]`

Verification command:

```bash
python3 -m pytest tests/unit/test_llm_pipeline.py tests/unit/test_processor.py -q
```

Verified result:

- `28 passed in 11.56s`

### End-to-end runtime alignment

The local merged acceptance environment was launched using:

- Windows GUI from `H:\demo-win\.worktrees\main-acceptance`
- WSL watcher rooted at `/home/ahzz1207/codex-demo/.worktrees/main-acceptance`

Environment link used by the Windows GUI:

- `CONTENT_INGESTION_WSL_PROJECT_ROOT=/home/ahzz1207/codex-demo/.worktrees/main-acceptance`

This means the last acceptance pass was performed against the locally merged `main` acceptance worktrees, not against the feature worktrees directly.

---

## Why The Knowledge Library Looked Empty

This was **not** caused by `.gitignore`.

The knowledge library appeared empty because the acceptance run used a different `shared_inbox` root.

The merged acceptance GUI reads from:

- `H:\demo-win\.worktrees\main-acceptance\data\shared_inbox`

The older library data lives in the previous feature worktree under:

- `H:\demo-win\.worktrees\domain-aware-reader-v2\data\shared_inbox\library`

So the observed behavior was a path switch, not data loss.

In short:

- switching worktrees changed the runtime `shared_inbox`
- the old library data was not deleted
- `.gitignore` only affects Git tracking, not application reads

---

## Current Worktree Inventory

### Windows repo: `H:\demo-win`

Current `git worktree list` state after cleanup:

- `H:\demo-win` -> `codex/template-system-v1`
- `H:\demo-win\.worktrees\domain-aware-reader-v2` -> `feature/domain-aware-reader-v2`
- `H:\demo-win\.worktrees\domain-aware-reader-v2-plan` -> `plan/domain-aware-reader-v2`
- `H:\demo-win\.worktrees\main-acceptance` -> `main`

### WSL repo: `/home/ahzz1207/codex-demo`

Current `git worktree list` state after cleanup:

- `/home/ahzz1207/codex-demo` -> `codex/template-system-v1`
- `/home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2` -> `feature/domain-aware-reader-v2`
- `/home/ahzz1207/codex-demo/.worktrees/main-acceptance` -> `main`

---

## What Was Cleaned Up

### Removed successfully

Windows:

- `H:\demo-win\.worktrees\domain-aware-reader-v2-wsl`

WSL:

- `/home/ahzz1207/codex-demo/.worktrees/question-driven-analysis`

### Removal that partially failed

The following Windows directory was removed from Git worktree tracking, but the folder itself could not be deleted due to a local permission / file-lock issue:

- `H:\demo-win\.worktrees\domain-aware-reader-v2-wsl-gen`

Important distinction:

- it is no longer present in `git worktree list`
- the remaining problem is directory deletion on disk, not Git state

It can be deleted later once no process is holding files under it.

---

## What Was Intentionally Kept

### Windows feature worktree

Kept:

- `H:\demo-win\.worktrees\domain-aware-reader-v2`

Reason:

- it still contains the older `data\shared_inbox\library` runtime data
- removing it now would risk deleting the only easily accessible copy of the previous knowledge library state

At verification time this worktree also still had intentionally untracked local-only paths:

- `.superpowers/`
- `data/shared_inbox/library/`

These were never meant to be committed.

### Plan worktree

Kept:

- `H:\demo-win\.worktrees\domain-aware-reader-v2-plan`

Reason:

- plan/history retention only

### WSL feature worktree

Kept:

- `/home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2`

Reason:

- no immediate cleanup pressure
- safe to retain until remote main promotion is settled

---

## Current Merge Meaning

At this stopping point, the work is **merged locally into `main` acceptance worktrees**, but **not yet described here as pushed to remote `origin/main`**.

That distinction matters.

The acceptance worktrees are the current source of truth for:

- what passed tests
- what was run together end-to-end
- what should be used if the next step is remote main promotion

---

## Next Recommended Actions

### If the goal is to publish merged main remotely

Use these worktrees as the push points:

Windows:

- `H:\demo-win\.worktrees\main-acceptance`

WSL:

- `/home/ahzz1207/codex-demo/.worktrees/main-acceptance`

That keeps remote promotion aligned with the exact worktree state that was tested.

### If the goal is to continue using the old knowledge library data

Keep:

- `H:\demo-win\.worktrees\domain-aware-reader-v2`

because the older library state is still easiest to access there.

### If the goal is more cleanup later

Safe next candidates after confirming no needed local runtime data remains:

- `H:\demo-win\.worktrees\domain-aware-reader-v2`
- `H:\demo-win\.worktrees\domain-aware-reader-v2-plan`
- `/home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2`

Do not remove the acceptance worktrees until remote main promotion is complete or no longer needed.

---

## Minimal Summary For The Next Person

The shortest accurate summary is:

- Windows feature work is merged locally into `H:\demo-win\.worktrees\main-acceptance` on `main`
- WSL feature work is merged locally into `/home/ahzz1207/codex-demo/.worktrees/main-acceptance` on `main`
- Windows merged acceptance tests passed: `211 passed, 1 skipped`
- WSL merged acceptance tests passed: `28 passed`
- the final acceptance run used the merged acceptance GUI and merged acceptance WSL watcher together
- the old knowledge library did not disappear; the runtime `shared_inbox` root changed with the worktree
- one obsolete Windows worktree directory remains on disk due to file locking, but is already removed from Git tracking

The main open question is no longer implementation. It is operational:

- whether to promote the acceptance `main` worktrees to remote `origin/main`
- and when to remove the remaining retained worktrees with local runtime data
