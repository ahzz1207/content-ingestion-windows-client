# Result Hero Meta Refresh Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the first screen of the result page by removing duplicated hero copy, surfacing template/domain identity near the metadata line, and showing an in-page completion banner after reinterpretation or reanalysis updates.

**Architecture:** Keep the existing result page structure intact and refine only the first-screen presentation. `InlineResultView` will own the hero/meta/banner behavior, `MainWindow` will signal when a fresh reinterpretation/reanalysis result has arrived, and focused GUI tests will lock the expected rendering and refresh feedback.

**Tech Stack:** Python 3.10, PySide6, pytest

---

## File Map

### UI files

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/windows_client/gui/inline_result_view.py` | Deduplicate hero copy, add template/domain hero pills, add in-page banner state and typography refinements |
| `src/windows_client/gui/main_window.py` | Trigger the in-page banner when reinterpretation/reanalysis loads a fresh result |
| `src/windows_client/gui/result_renderer.py` | Keep preview rendering compatible if hero/meta assumptions change |

### Test files

| File | Responsibility in this plan |
|------|-----------------------------|
| `tests/unit/test_main_window.py` | Verify completion banner behavior and WeChat/refresh regressions stay correct |
| `tests/unit/test_result_renderer.py` | Verify product-view rendering still works after hero/meta cleanup |

---

### Task 1: Deduplicate hero copy and refine hero typography

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Test: `tests/unit/test_main_window.py`

- [ ] Write a failing test asserting that a product-view hero does not show duplicated `title` and `dek` text when they are identical or near-identical.
- [ ] Run `python -m pytest tests/unit/test_main_window.py -k hero -q` and confirm the new test fails.
- [ ] Implement the minimal hero deduplication rule and adjust hero label styling to reduce visual heaviness.
- [ ] Re-run the same targeted test and confirm it passes.

### Task 2: Surface template and domain near hero metadata

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/main_window.py`
- Test: `tests/unit/test_main_window.py`

- [ ] Write a failing test asserting the hero metadata region shows both the resolved template label and resolved domain label.
- [ ] Run `python -m pytest tests/unit/test_main_window.py -k domain -q` and confirm the new test fails.
- [ ] Implement the minimal hero metadata pill rendering using existing resolved mode/domain data paths.
- [ ] Re-run the targeted test and confirm it passes.

### Task 3: Add in-page completion banner for refresh-producing actions

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/main_window.py`
- Test: `tests/unit/test_main_window.py`

- [ ] Write a failing test asserting reinterpretation completion loads the new result and exposes a visible in-page update banner.
- [ ] Run `python -m pytest tests/unit/test_main_window.py -k reinterpretation -q` and confirm the new test fails for the expected reason.
- [ ] Implement the minimal banner state plumbing and banner rendering without adding modal dialogs.
- [ ] Re-run the targeted test and confirm it passes.

### Task 4: Verify preview compatibility and focused UI behavior

**Files:**
- Test: `tests/unit/test_result_renderer.py`
- Test: `tests/unit/test_main_window.py`

- [ ] Run `python -m pytest tests/unit/test_result_renderer.py -q` and confirm product-view rendering still passes.
- [ ] Run `python -m pytest tests/unit/test_main_window.py -q` and confirm the result-page UI behavior stays green.
- [ ] If either suite fails, fix the smallest regression and rerun until green.

---

## Handoff Notes

- Keep the banner scoped to explicit refresh-producing actions only.
- Do not add modal completion dialogs.
- Keep author/time/source text as plain metadata and limit hero pills to identity-level information.
- Do not redesign the whole page during this pass; the point is a cleaner first screen, not a new layout system.
