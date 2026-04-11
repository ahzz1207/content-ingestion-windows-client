# Argument vs Guide Reader Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `argument` and `guide` outputs render as two clearly different reading products for the same source.

**Architecture:** Keep routing and reinterpretation behavior as-is, but strengthen `product_view` generation for `argument.generic` and `guide.generic`, then add explicit mode-aware rendering branches in the Windows GUI. Use focused tests to lock both structure and rendering differences before changing implementation.

**Tech Stack:** Python 3.12, dataclasses, PySide6, pytest

---

## File Map

### WSL files

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/content_ingestion/pipeline/llm_pipeline.py` | Redefine generic `argument` and `guide` `product_view` builders with stronger structural separation |
| `tests/unit/test_llm_pipeline.py` | Lock the new `argument.generic` and `guide.generic` shapes |

### Windows files

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/windows_client/gui/result_renderer.py` | Add mode-aware specialized HTML renderers for `argument` and `guide` product views |
| `src/windows_client/gui/inline_result_view.py` | Continue preferring `product_view`, but let mode-aware rendering surface through the shared preview path |
| `tests/unit/test_result_renderer.py` | Lock visible rendering differences between `argument` and `guide` product views |
| `tests/unit/test_main_window.py` | Smoke-test that product-view-first loading still works with the new renderer |

---

### Task 1: Strengthen WSL `argument.generic` product shape

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] Write a failing test that asserts `argument.generic` now emits analytical section kinds such as `core_judgment`, `main_arguments`, `evidence`, and `tensions`.
- [ ] Run `wsl.exe -d Ubuntu-22.04 bash -lc "cd /home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2 && python3 -m pytest tests/unit/test_llm_pipeline.py -k argument_generic -q"` and confirm the new test fails.
- [ ] Implement the minimal `argument.generic` product-view builder change in `src/content_ingestion/pipeline/llm_pipeline.py`.
- [ ] Re-run the same targeted test and confirm it passes.

### Task 2: Strengthen WSL `guide.generic` product shape

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] Write a failing test that asserts `guide.generic` emits a compressed structure with only `one_line_summary`, `core_takeaways`, and optional `remember_this`, with takeaway count capped.
- [ ] Run `wsl.exe -d Ubuntu-22.04 bash -lc "cd /home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2 && python3 -m pytest tests/unit/test_llm_pipeline.py -k guide_generic -q"` and confirm the new test fails.
- [ ] Implement the minimal `guide.generic` product-view builder change in `src/content_ingestion/pipeline/llm_pipeline.py`.
- [ ] Re-run the same targeted test and confirm it passes.

### Task 3: Add specialized Windows rendering for analytical briefs

**Files:**
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] Write a failing renderer test that asserts `argument` product views render analytical labels and argument/evidence groupings instead of only generic sections.
- [ ] Run `python -m pytest tests/unit/test_result_renderer.py -k argument -q` and confirm failure.
- [ ] Implement a minimal specialized HTML renderer path for `analysis_brief` / `argument.*` product views.
- [ ] Re-run the targeted renderer test and confirm pass.

### Task 4: Add specialized Windows rendering for compressed guide views

**Files:**
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] Write a failing renderer test that asserts `guide` product views render a short-summary + compact takeaway layout and omit analysis-heavy framing.
- [ ] Run `python -m pytest tests/unit/test_result_renderer.py -k guide -q` and confirm failure.
- [ ] Implement a minimal specialized HTML renderer path for `practical_guide` / `guide.*` product views.
- [ ] Re-run the targeted renderer test and confirm pass.

### Task 5: Verify GUI integration remains stable

**Files:**
- Test: `tests/unit/test_main_window.py`

- [ ] Run `python -m pytest tests/unit/test_main_window.py -q` and confirm the product-view-first result path still passes.
- [ ] Run `python -m pytest tests/unit/test_result_renderer.py tests/unit/test_main_window.py -q` and confirm the Windows rendering surface stays green.
- [ ] Run `wsl.exe -d Ubuntu-22.04 bash -lc "cd /home/ahzz1207/codex-demo/.worktrees/domain-aware-reader-v2 && python3 -m pytest tests/unit/test_llm_pipeline.py -q"` and confirm the WSL output contract stays green.

---

## Handoff Notes

- Keep this round focused on `argument` vs `guide` only.
- Do not redesign `review` in the same patch.
- Prefer a small number of stable section kinds over introducing another large abstraction layer.
- The user will validate the result visually in the GUI, so visible first-screen difference matters more than elegant internal generalization.
