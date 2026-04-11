# Review Narrative Rendering Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Windows presentation layer for `推荐导览` and `叙事导读` so every GUI-exposed reading mode has a dedicated rendering family.

**Architecture:** Reuse the existing WSL `product_view` payloads and add two new specialized renderer branches in `result_renderer.py` keyed by layout. Keep all routing, reinterpretation, and WSL schema generation unchanged.

**Tech Stack:** Python 3.10, PySide6, pytest

---

## File Map

| File | Responsibility |
|------|----------------|
| `src/windows_client/gui/result_renderer.py` | Add specialized HTML renderers for `review_curation` and `narrative_digest` |
| `tests/unit/test_result_renderer.py` | Lock visible rendering differences for `review` and `narrative` product views |
| `tests/unit/test_main_window.py` | Smoke-test that product-view-first result loading still remains stable |

---

### Task 1: Add `review_curation` specialized rendering

**Files:**
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] Write a failing test asserting `review_curation` product views use a dedicated recommendation-style layout instead of the generic section renderer.
- [ ] Run `python -m pytest tests/unit/test_result_renderer.py -k review -q` and confirm the new test fails.
- [ ] Implement the minimal dedicated renderer branch for `review_curation`.
- [ ] Re-run the targeted review renderer test and confirm it passes.

### Task 2: Add `narrative_digest` specialized rendering

**Files:**
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] Write a failing test asserting `narrative_digest` product views use a dedicated narrative-style layout instead of the generic section renderer.
- [ ] Run `python -m pytest tests/unit/test_result_renderer.py -k narrative -q` and confirm the new test fails.
- [ ] Implement the minimal dedicated renderer branch for `narrative_digest`.
- [ ] Re-run the targeted narrative renderer test and confirm it passes.

### Task 3: Verify focused GUI compatibility

**Files:**
- Test: `tests/unit/test_result_renderer.py`
- Test: `tests/unit/test_main_window.py`

- [ ] Run `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_main_window.py -q` and confirm the GUI rendering surface remains green.
- [ ] If failures appear, make the smallest compatibility fix and rerun until green.

---

## Handoff Notes

- Do not widen this into a WSL payload redesign.
- Keep `review` visually lighter than `argument`.
- Keep `narrative` visually more story-shaped than `review`.
- Preserve the generic fallback for unknown layouts.
