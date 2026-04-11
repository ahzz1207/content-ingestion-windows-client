# Session Memory - 2026-04-08 Source-Centric Knowledge Library Closeout

## Read This First Tomorrow

If work resumes tomorrow, read these files in this order:

1. `docs/session-memory-2026-04-08-source-centric-knowledge-library-closeout.md`
2. `docs/superpowers/specs/2026-04-07-source-centric-knowledge-library-design.md`
3. `docs/superpowers/plans/2026-04-07-source-centric-knowledge-library.md`
4. `docs/session-memory-2026-04-07-round-closeout.md`
5. `docs/session-memory-2026-04-07-argument-guide-handoff.md`

Then inspect the implementation files:

6. `src/windows_client/app/library_store.py`
7. `src/windows_client/app/service.py`
8. `src/windows_client/app/workflow.py`
9. `src/windows_client/app/view_models.py`
10. `src/windows_client/gui/inline_result_view.py`
11. `src/windows_client/gui/library_panel.py`
12. `src/windows_client/gui/main_window.py`
13. `tests/unit/test_library_store.py`
14. `tests/unit/test_service.py`
15. `tests/unit/test_workflow.py`
16. `tests/unit/test_inline_result_view.py`
17. `tests/unit/test_main_window.py`

Reference mockup if needed:

- `H:\demo-win\.worktrees\domain-aware-reader-v2\.superpowers\brainstorm\session-20260407-product-gap\content\knowledge-library-v2.html`

---

## Current Goal

This round pushed the Windows product from a result reader toward a durable knowledge loop.

The current target is a minimum viable source-centric knowledge library:

- the result page has a primary save-to-library action
- the library is source-centric, not job-centric
- one source maps to one durable library entry
- saving the same source again replaces the current interpretation
- the replaced interpretation moves into entry-local trash and can be restored
- library detail is image-first, then source, then long interpretation
- the first version reuses `insight_card.png` when it exists, but save does not depend on it

---

## Locked Product Decisions

These decisions are already settled and should not be re-litigated tomorrow unless the user explicitly changes them:

- Result-page primary action is save to library.
- The library object model is source-centric.
- Re-saving the same source does not create duplicate entries.
- Re-save semantics are replace-current plus trash-old-current.
- Trash is entry-local in v1, not a separate global trash page.
- Image summary is an interpretation asset, not a top-level library object.
- Initial entry creation copies the source snapshot.
- Later saves add new interpretation snapshots but do not overwrite the original source snapshot.

---

## What Was Completed

### 1. Design and plan were written

Files:

- `docs/superpowers/specs/2026-04-07-source-centric-knowledge-library-design.md`
- `docs/superpowers/plans/2026-04-07-source-centric-knowledge-library.md`

These are the canonical design and implementation references for this feature.

### 2. Library storage model was implemented

New files:

- `src/windows_client/app/library_store.py`
- `tests/unit/test_library_store.py`

Implemented behavior:

- file-backed local library store under the shared root
- source-key resolution with fallback precedence
- new entry creation from processed result data
- repeated save for same source moves old current interpretation into trash
- restore from trashed interpretation back to current
- source snapshot copy on first save
- interpretation snapshot copy on each save
- image asset reuse from `insight_card.png` when present
- save still succeeds when no image asset exists

### 3. Service and workflow plumbing were implemented

Modified files:

- `src/windows_client/app/service.py`
- `src/windows_client/app/workflow.py`
- `src/windows_client/app/view_models.py`
- `tests/unit/test_service.py`
- `tests/unit/test_workflow.py`

Implemented behavior:

- service-level save-to-library operation
- service-level restore-library-interpretation operation
- workflow wrappers for GUI task threads
- minimal library snapshot data exposed back to the GUI

### 4. Result-page library actions were implemented

Modified files:

- `src/windows_client/gui/inline_result_view.py`
- `tests/unit/test_inline_result_view.py`

Implemented behavior:

- save-to-library action in the result page
- open-library action in the result page
- save-to-library is the primary action
- success banner with open-entry and open-library affordances
- graceful save/export handling around markdown and image-card actions

### 5. Dedicated library dialog was implemented

New file:

- `src/windows_client/gui/library_panel.py`

Modified files:

- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`

Implemented behavior:

- dedicated library dialog
- source-centric list view
- image-first detail layout
- restore controls for trashed interpretations
- ready-page library entry point
- result-page library entry point

### 6. Save and restore flows were wired through background tasks

Modified files:

- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`

Implemented behavior:

- background-threaded save-to-library flow
- background-threaded restore-library-interpretation flow
- result-page success feedback after save
- dialog reload after restore when the dialog is open

### 7. Final cleanup pass was completed today

This was the last unresolved quality block from the previous handoff.

Fixed today:

- `main_window.py`: `_render_success()` no longer restarts result polling when the first refresh already reaches `processed` or `failed`
- `main_window.py`: failed terminal result path now stops `_elapsed_timer` and hides `_elapsed_label`
- `inline_result_view.py`: `load_entry()` now clears stale update and library banners before loading a different entry
- `inline_result_view.py`: update-banner hide logic now uses a generation guard so an old hide callback cannot dismiss a newer banner

### 8. Additional UX and robustness fixes were completed after the first handoff draft

These were found during a deeper independent code review after the initial cleanup.

Fixed after that review:

- save success now distinguishes first save from re-save
  - first save does not falsely claim that old versions exist
  - re-save copy does mention restorable old versions
- save success banner now carries the saved `entry_id`
  - `打开条目` now opens the library dialog focused on the newly saved entry
  - it no longer behaves the same as `查看知识库`
- library dialog now preserves the current selection across `reload()`
  - restore no longer snaps the user back to row 0 or the wrong entry
- recent sorting now uses entry-level `updated_at`
  - restore updates entry recency and list ordering correctly
- library list cards now show stronger browse identity
  - platform
  - current route
  - image-summary presence
  - interpretation count
  - trashed-state summary
- corrupt library entry manifests are now isolated
  - one bad `entry.json` no longer bricks list loading or unrelated saves
- `全部条目` now behaves like a real browse toggle instead of a no-op

---

## Fresh Verification Evidence

Focused regression checks for the final cleanup:

- `python -m pytest tests/unit/test_main_window.py -k "render_success_does_not_restart_polling_when_result_is_already_processed or failed_result_stops_elapsed_timer_and_hides_elapsed_label" -q`
  - result: `2 passed, 40 deselected`
- `python -m pytest tests/unit/test_inline_result_view.py -k "clears_existing_update_and_library_banners or stale_update_banner_hide_callback_does_not_hide_newer_banner" -q`
  - result: `2 passed, 10 deselected`

Broader library-related verification run after the fixes:

- `python -m pytest tests/unit/test_library_store.py -q`
  - result: `10 passed`
- `python -m pytest tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `81 passed`

Extra local suite run during cleanup:

- `python -m pytest tests/unit/test_inline_result_view.py -q`
  - result: `12 passed`

I also ran `python -m pytest tests/unit/test_main_window.py -q` during cleanup and it passed before stopping.

Additional verification after the deeper review and follow-up fixes:

- `python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `102 passed`
- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_main_window.py tests/unit/test_inline_result_view.py -q`
  - result: `89 passed`

---

## Current Worktree State

Windows worktree:

- `H:\demo-win\.worktrees\domain-aware-reader-v2`

Current branch:

- `feature/domain-aware-reader-v2`

Current git status before stopping:

Modified tracked files:

- `src/windows_client/app/service.py`
- `src/windows_client/app/view_models.py`
- `src/windows_client/app/workflow.py`
- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/main_window.py`
- `tests/unit/test_inline_result_view.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_service.py`
- `tests/unit/test_workflow.py`

Untracked files and directories:

- `.superpowers/`
- `docs/superpowers/plans/2026-04-07-source-centric-knowledge-library.md`
- `docs/superpowers/specs/2026-04-07-source-centric-knowledge-library-design.md`
- `src/windows_client/app/library_store.py`
- `src/windows_client/gui/library_panel.py`
- `tests/unit/test_library_store.py`

Important note:

- No commit was created yet.
- No branch cleanup was done yet.
- The feature is unit-verified but not yet taken through a final manual GUI smoke pass in this session.

---

## What Still Needs To Happen

The main implementation work is effectively done. The remaining work is finish-quality work, not architecture discovery.

Most likely next steps tomorrow:

1. Do a manual GUI smoke test on one real article or one saved processed result.
2. Verify the save-to-library flow end to end:
   - save from result page
   - open library dialog
   - confirm image-first detail ordering
   - save the same source again after reinterpretation
   - restore a trashed interpretation
3. Review the worktree diff for any last UI wording or polish adjustments.
4. Decide whether `.superpowers/` should stay local-only or be excluded from any eventual commit.
5. Commit only after the manual pass looks good.

At this point, the highest-value remaining work is manual product validation rather than more unit work.

---

## Suggested First Moves Tomorrow

If resuming tomorrow, the fastest sensible sequence is:

1. Read this handoff doc, then the spec and plan.
2. Open the mockup once if visual intent needs a refresher.
3. Run one manual GUI flow for save, reopen, re-save, and restore.
4. If manual behavior looks good, inspect `git diff` and prepare a commit.
5. If a bug appears, start in this order:
   - `src/windows_client/gui/main_window.py`
   - `src/windows_client/gui/inline_result_view.py`
   - `src/windows_client/gui/library_panel.py`
   - `src/windows_client/app/library_store.py`

Tomorrow should not start with redesign unless the user explicitly changes scope.

## Manual Acceptance Path

When doing hands-on review in the GUI, use this path:

1. Open one processed result that has a normal structured reading view.
2. Confirm the result page shows:
   - `保存进知识库` as primary action
   - `知识库` as secondary action
3. Click `保存进知识库` for the first time.
4. Confirm the success banner:
   - appears in-page
   - includes `打开条目`
   - includes `查看知识库`
   - does not falsely mention old versions on first save
5. Click `打开条目`.
6. In the library dialog, confirm:
   - it opens focused on the saved entry
   - main column order is image summary, then source, then long interpretation
   - sidebar shows current interpretation metadata and trash/context sections
   - list card shows enough identity to distinguish entries quickly
7. Reinterpret the same source into a different mode and save again.
8. Confirm:
   - the same library entry is reused
   - the new interpretation is current
   - the banner now mentions recoverable old versions
   - the entry shows at least one trashed interpretation
9. Restore one trashed interpretation.
10. Confirm:
   - restore keeps you on the same entry
   - current/trash swap is immediately visible
   - recent ordering and metadata reflect the restore
11. Optionally toggle library filters:
   - `全部条目`
   - `按最近保存排序`
   - `有图片摘要`
   - `有旧版本`
   and confirm the list behavior feels coherent instead of surprising

---

## Summary

The source-centric knowledge library minimum loop is implemented and unit-verified.

The previous open cleanup issues in `MainWindow` and `InlineResultView` were fixed, and a second review pass also closed the main remaining UX and robustness gaps in save/re-save/restore behavior and library browsing.

The best resume point is now a short manual GUI validation pass followed by final diff review and commit prep.

---

## V4 GUI Readability Update

After this closeout draft, the approved V4 readability redesign was also implemented across the result page and library detail surfaces.

Fresh acceptance cues for manual review:

1. Result page first screen should now feel calmer and more editorial than dashboard-like.
2. `视觉总结` should appear before `深度解读`, with the long reading area clearly framed as the primary reading surface.
3. The right side of the result page should read as one lighter `Library Context` rail instead of several competing cards.
4. Library detail should keep the image-first -> source -> current interpretation order in the main column.
5. Library detail side content should now read as one unified `Library Context` surface containing `当前版本`, `版本时间线`, and context metadata.
6. Result-page and library-detail product copy should no longer show obvious English section headings in the main reading flow.

Fresh verification evidence for the V4 pass:

- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `106 passed`
- `python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `117 passed`

---

## 2026-04-09 Night Closeout

This session continued past the original library closeout and moved into two separate areas:

1. finishing the V4 PySide readability pass so the GUI is structurally aligned with the approved mockup
2. manually validating the running GUI and identifying the next visual-parity gap

### What was completed tonight

Files changed in this session:

- `src/windows_client/app/library_store.py`
- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/result_renderer.py`
- `tests/unit/test_library_store.py`
- `tests/unit/test_inline_result_view.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_result_renderer.py`

Implemented and verified tonight:

- `LibraryDialog` V4 structure moved closer to the approved mockup
  - main column remains image-first -> source -> current interpretation
  - side column is now a unified `ContextRail` instead of several separate cards
  - list copy, detail headings, context copy, and timeline copy were rewritten into real Chinese product language
- result page V4 copy was brought much closer to the HTML direction
  - section labels like `事实核验`, `核心结论`, `问题与下一步`, `视觉证据`
  - actions like `打开目录`, `导出 JSON`, `复制`, `保存 Markdown`
  - markdown export headings and preview fallback headings were also localized
- review-driven fixes were completed after a deeper code review
  - saving a normalized-only result to the library now preserves interpretation content instead of degrading to an empty current interpretation
  - save success banner no longer shows `打开条目` when no concrete `entry_id` is available

### Fresh verification from tonight

- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `106 passed`
- `python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `118 passed`

### GUI launch debugging outcome

An important debugging detail was discovered while manually launching the GUI:

- launching with plain `python -c "from windows_client.gui.app import launch_gui ..."` can resolve `windows_client` from `H:\demo-win\src` instead of the worktree
- this can make the machine open an older GUI build even though the current worktree has newer code
- the reliable launch path for this worktree is:
  - `python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console`
- when validating tomorrow, prefer the worktree `main.py` entrypoint, not a bare `python -c` import

WSL watch status during closeout:

- WSL watch was confirmed running successfully
- `python main.py wsl-watch-status` reported `running=True`

### Latest user feedback before stopping

Manual product feedback from the user after seeing the real PySide GUI:

- functionality is broadly fine
- the remaining dissatisfaction is mostly visual, not behavioral
- the biggest gap is **overall PySide visual atmosphere versus the approved HTML V4 mockup**
- when forced to pick one missing source of atmosphere, the user chose:
  - **Hero 沉浸感** as the top priority to recover next

This is the most important next-session product signal.

The user did **not** say the feature is broken.
The user did say that PySide still feels visibly less premium than the HTML exploration.

### Open visual gap to address next

The current PySide implementation appears to have mostly matched:

- information hierarchy
- section ordering
- Chinese product copy
- save / open library / restore interaction model

But it still has a noticeable gap against the approved V4 HTML in:

- first-screen emotional impact
- layered background and material feel
- hero immersion and sense of editorial scale
- card radius / surface / shadow depth
- overall "reading product" atmosphere versus "styled desktop tool"

The next work should focus on **visual parity**, not on inventing new product behavior.

### Best restart point tomorrow

If work resumes tomorrow, start from this exact sequence:

1. Read this file first.
2. Re-open the approved V4 mockup:
   - `H:\demo-win\.worktrees\domain-aware-reader-v2\.superpowers\brainstorm\session-20260407-product-gap\content\gui-readability-v4.html`
3. Launch the current worktree GUI using:
   - `python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console`
4. Compare the live PySide hero / first-screen against the V4 mockup specifically for atmosphere, not for feature checklist parity.
5. Resume brainstorming from this product question:
   - how to recover V4 `Hero 沉浸感` inside PySide without changing the approved product structure

### Immediate next tasks for tomorrow

The next session should do these in order:

1. continue the brainstorming flow for visual parity
2. narrow the next redesign scope to the result page hero / first-screen atmosphere
3. propose 2-3 implementation approaches for bringing PySide visually closer to HTML V4
4. once approved, write a small spec / plan for that focused parity pass
5. only then implement

Do **not** start by changing save / restore / library semantics again.
Those behaviors are already in a good place and are not the main complaint now.

---

## 2026-04-09 Follow-up Closeout

Work continued after the night closeout in two parallel tracks:

1. deeper product-direction thinking for the next post-library object
2. a focused acceptance-polish pass for the current result-page V4 GUI iteration

### Product-direction outcome

A new design document was created:

- `docs/superpowers/specs/2026-04-09-analysis-report-query-artifacts-design.md`

This document locks the following high-level direction:

- the product's first wedge remains **high-quality / multimodal / source-grounded / strongly reasoned analysis with premium reading UX**
- the product should **not** drift into being another Obsidian or generic PKM tool
- the next durable object above the current source-centric library should be an **Analysis Report**
- this report object is the preferred way to absorb Karpathy's “query results become persistent knowledge objects” idea

Important additional insight from the user's preferred research-summary template:

- future `Analysis Report` objects should be organized around **question-driven analytical sections**, not source-order summaries
- the default report skeleton should prefer patterns like:
  - `核心变化 / What changed?`
  - `增量信息 / What is genuinely new?`
  - `核心论证链 / Why does the answer hold?`
  - `哪里被低估、误判或错定价？`
  - `风险、反例与短期扰动`
  - `一句大白话结论`
- this is a strong fit for the product because it optimizes for **mental-model update**, not generic summarization

### GUI acceptance-polish outcome

An additional plan was created:

- `docs/superpowers/plans/2026-04-09-result-page-v4-acceptance-polish.md`

The following result-page polish work was implemented after the first visual parity pass:

1. result-specific actions were pulled fully into the hero surface so the top bar keeps only global navigation (`新的链接`, `历史记录`)
2. the image-summary block now uses a dedicated `ImageSummaryCard` continuation surface instead of a transparent utility frame
3. some supporting stream sections now use a lighter `StreamSection` surface to reduce card-stack feeling
4. narrow-width fallback now stacks the context rail below the reading stream **and clears the side gutter correctly**

This last point matters: an intermediate version stacked the rail but still kept the old two-column gutter. That bug was caught in review and fixed.

### Latest verification evidence

After the acceptance-polish fixes:

- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `123 passed`
- `python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`
  - result: `134 passed`

### Current reliable launch command

For this worktree, continue using:

- `python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console`

Do not use a bare `python -c "from windows_client.gui.app import launch_gui ..."` import path launch, because on this machine it can resolve `windows_client` from `H:\demo-win\src` and open an older GUI build.

### Best restart point after this closeout

If work resumes from here, use this order:

1. read this session-memory file
2. read `docs/superpowers/specs/2026-04-09-analysis-report-query-artifacts-design.md`
3. compare the live GUI against `gui-readability-v4.html`
4. decide whether the current GUI is good enough to branch-close or still needs one more visual polish pass
5. if product-direction work is resumed, continue from `Analysis Report` object model rather than drifting into generic note management

---

## 2026-04-09 Library Dialog Reading-Density Closeout

Work continued after the result-page acceptance polish and focused on the next blocked GUI area: the library detail reading experience.

### New design / plan documents

- `docs/superpowers/specs/2026-04-09-library-dialog-v4-reading-density-design.md`
- `docs/superpowers/plans/2026-04-09-library-dialog-v4-reading-density.md`

These documents lock the next GUI refinement as a **reading-density pass**, not a semantics change.

### What was implemented

Modified files:

- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/gui/result_workspace_panel.py`
- `tests/unit/test_main_window.py`

Implemented behavior:

- `LibraryDialog` now exposes `open_analysis_requested`
- `来源信息` is compressed into a lighter `SourceHeaderCard`
- the source header now contains `查看完整分析`
- the source header no longer renders raw markdown/json/metadata snapshot paths in the main reading flow
- the current interpretation browser is now a dedicated `LibraryInterpretationBrowser` surface with a larger minimum reading height
- the side column is now wrapped in `ContextRailShell` so the rail reads as a calmer supporting surface
- source snapshot context is still available, but only as weaker copy inside the rail context section

### Important review-driven follow-up fix

An independent review found a real interaction inconsistency after the first implementation:

- the new library `查看完整分析` button selected the right job id, but the downstream history/workspace flow could still strand processed entries that had no `insight_brief`
- `ResultWorkspaceDialog` had been disabling `查看完整分析` unless a brief existed, even though the product already supports opening degraded processed results directly

That inconsistency was fixed by:

- making `MainWindow._open_library_analysis()` prefer directly loading a processed result via `load_job_result()` when available
- falling back to the existing result workspace only when the processed entry cannot be resolved directly
- re-enabling `ResultWorkspaceDialog.view_button` for any processed entry, not only processed entries with `insight_brief`

This matters because the new library jump should behave like a real one-click return to the full result, not a fragile indirect hop.

### Fresh verification evidence

Focused library-detail red/green checks during implementation:

- `python -m pytest tests/unit/test_main_window.py -k "open_analysis_requested or open_library_dialog_connects_analysis_signal or open_result_workspace_from_library_analysis_action or compact_source_header_surface or snapshot_paths_out_of_source_header or primary_reading_surface or source_snapshot_context or context_rail_shell_for_side_column" -q`
  - result: `7 passed`

Focused review-follow-up checks:

- `python -m pytest tests/unit/test_main_window.py -k "library_analysis_loads_processed_entry_directly or library_analysis_falls_back_to_result_workspace_when_entry_missing or analysis_signal_loads_processed_entry_directly or processed_entry_without_brief_still_has_open_analysis_button" -q`
  - result: `4 passed`

Latest focused regression run:

- `python -m pytest tests/unit/test_main_window.py -k "library_dialog or open_library_analysis or processed_entry_without_brief_still_has_open_analysis_button" -q`
  - result: `16 passed, 53 deselected`

Latest GUI suite:

- `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py tests/unit/test_result_workspace.py -q`
  - result: `159 passed`

Latest broader regression suite:

- `python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py tests/unit/test_result_workspace.py -q`
  - result: `170 passed`

### Best manual acceptance focus after this pass

When reopening the GUI, the highest-value checks are now:

1. open a saved library entry and confirm `来源信息` reads like a compact header, not a large content block
2. confirm `当前解读` is visually the main reading surface
3. confirm the right rail feels more supportive and less competitive
4. click `查看完整分析` from the source header and confirm it lands in the expected full result view even when the result is processed-but-degraded

### Reliable GUI launch command remains unchanged

- `python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console`

Do not use a bare `python -c "from windows_client.gui.app import launch_gui ..."` import path launch on this machine, because it can still resolve to the wrong `windows_client` package.

---

## 2026-04-10 Bugfix And Handoff Closeout

Work continued after the library-detail reading-density pass and moved into a bug-fix heavy acceptance cycle driven by manual GUI testing.

### What was fixed in this round

Modified files:

- `src/windows_client/gui/platform_router.py`
- `src/windows_client/app/service.py`
- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/result_renderer.py`
- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/app/coverage_stats.py`
- `tests/unit/test_platform_router.py`
- `tests/unit/test_service.py`
- `tests/unit/test_inline_result_view.py`
- `tests/unit/test_result_renderer.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_coverage_stats.py`

Implemented and verified behavior:

1. bilibili login-state routing / cookies
   - `watchlater` URLs now route through the browser/profile path instead of plain HTTP
   - regular bilibili HTTP exports now reuse the local `bilibili` browser profile for yt-dlp cookies when that profile exists
   - this was a real product bug, not a WSL failure and not a generic GUI regression

2. guide rendering cleanup
   - guide mode in the inline result view now uses compact step items instead of reusing the oversized argument-style key-point cards
   - product-view detection now honors `render_hints.layout_family`, so practical-guide payloads can hit the guide renderer even when `layout` is incomplete
   - library detail fallback now renders guide interpretations from `editorial.mode_payload` when `product_view` is empty, preventing raw `Step 1 / Step 2` structured cards from leaking into the saved-library reading surface

3. coverage-warning bug discovered during manual testing
   - the GUI warning `覆盖范围提示：当前只分析了 0% 的原始分段 (0/167)` was investigated against the real processed job `20260409_235405_528166`
   - this warning was **not trustworthy** in that form
   - the job had a full transcript (`167` segments) and real transcript evidence in `analysis/llm/text_request.json`
   - the root cause was a historical format mismatch:
     - `compute_coverage()` still looked for top-level `evidence_segments`
     - current `text_request.json` stores them under `document.evidence_segments`
   - after the fix, the same real artifact computes to:
     - `used_segments = 88`
     - `total_segments = 167`
     - `coverage_ratio ≈ 52.7%`
   - so the old `0/167` display was a false-zero bug, while the broader “coverage is incomplete” warning can still legitimately remain when coverage is partial

4. knowledge-library selected-row style regression
   - manual testing found that clicking a left-side library entry could turn the selected row text white and effectively invisible on the light background
   - root cause: `QListWidget#ResultList::item:selected` had transparent background but no explicit foreground color, so the platform highlight text color could be inherited as white
   - fixed by explicitly setting selected text color to the normal dark foreground

### Fresh verification evidence

Focused red/green checks while implementing:

- `python -m pytest tests/unit/test_platform_router.py -k "watchlater" -q`
  - result after fix: `1 passed`
- `python -m pytest tests/unit/test_service.py -k "existing_bilibili_profile" -q`
  - result after fix: `1 passed`
- `python -m pytest tests/unit/test_inline_result_view.py -k "compact_step_items" -q`
  - result after fix: `1 passed`
- `python -m pytest tests/unit/test_result_renderer.py -k "render_hints_layout_family" -q`
  - result after fix: `1 passed`
- `python -m pytest tests/unit/test_main_window.py -k "guide_interpretation_from_editorial_payload or bilibili_watchlater_submission_uses_browser" -q`
  - result after fix: `2 passed`
- `python -m pytest tests/unit/test_coverage_stats.py -k "document_payload" -q`
  - result after fix: `1 passed`
- `python -m pytest tests/unit/test_main_window.py -k "dark_selected_list_text_color" -q`
  - result after fix: `1 passed`

Real-artifact verification for the coverage fix:

- `python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path(r'H:\demo-win\.worktrees\domain-aware-reader-v2\src'))); from windows_client.app.coverage_stats import compute_coverage; p=Path(r'H:\demo-win\.worktrees\domain-aware-reader-v2\data\shared_inbox\processed\20260409_235405_528166'); print(compute_coverage(p))"`
  - result after fix: `CoverageStats(total_segments=167, used_segments=88, total_duration_ms=None, used_duration_ms=306320, coverage_ratio=0.5269461077844312, input_truncated=True)`

Broader regression runs after the fixes:

- `python -m pytest tests/unit/test_platform_router.py tests/unit/test_service.py tests/unit/test_inline_result_view.py tests/unit/test_result_renderer.py tests/unit/test_main_window.py -q`
  - surrounding updated suites passed
- `python -m pytest tests/unit/test_workflow.py tests/unit/test_video_downloader.py -q`
  - result: `18 passed`
- `python -m pytest tests/unit/test_coverage_stats.py tests/unit/test_main_window.py tests/unit/test_inline_result_view.py tests/unit/test_result_renderer.py -q`
  - result: `146 passed`
- `python -m pytest tests/unit/test_result_workspace.py tests/unit/test_insight_brief.py -q`
  - result: `39 passed`

### Product-direction takeaway from this round

The user explicitly clarified the next strategic priority:

- the current Windows GUI is temporary
- the product will later need to become multi-platform
- the deeper moat is **LLM processing quality**, not PySide polish by itself
- near-term work should continue to fix obvious GUI blockers, but the core mission is now to raise analysis quality until the experience becomes genuinely useful and habit-forming

This means the next iteration should treat GUI work as a delivery shell, while product energy shifts toward:

- better prompt/runtime quality
- better source grounding and evidence behavior
- more stable guide / argument / review outputs
- fewer AI-smelling artifacts and template failures
- better practical usefulness, not just nicer presentation

### Best restart point next round

If work resumes next round, the best sequence is:

1. read this session-memory file first
2. re-open the current processed artifacts that exposed guide / coverage issues, especially:
   - `data/shared_inbox/processed/20260409_235405_528166/`
   - `data/shared_inbox/library/entries/lib_0006/`
3. treat GUI as a shell and re-prioritize the next work around LLM quality
4. specifically inspect where the current runtime/prompt stack is generating:
   - unstable guide phrasing
   - weak evidence linkage
   - generic or AI-smelling framing
   - poor user trust signals in practical outputs

### Next-iteration focus recommendation

The strongest next round is likely **not** another broad GUI polish pass.

Instead, the next round should probably focus on one or more of:

1. locating the actual runtime/prompt layer that produces current guide / argument outputs
2. improving guide-mode reliability and practical usefulness at the source
3. improving evidence alignment so product trust indicators reflect real source usage cleanly
4. defining what "usable and lovable" means for the analysis output itself, independent of the current Windows shell

That is the main strategic handoff from this round.
