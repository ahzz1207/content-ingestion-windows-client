# GUI Readability V4 Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the result page and knowledge-library detail GUI around the approved V4 reading-first design while preserving existing save, re-save, and restore behavior.

**Architecture:** Keep the current PySide application shell and product semantics, but refactor the result page and library dialog into clearer reading surfaces. The implementation should prioritize layout hierarchy, typography, and text correctness first, then lighter material styling, then responsive/fallback behavior that still makes sense inside Qt.

**Tech Stack:** Python, PySide6, existing Windows client GUI widgets, existing result renderer HTML, pytest/unittest.

---

## File Map

### Existing files to modify

- `src/windows_client/gui/main_window.py`
  - owns the global Qt stylesheet and top-level shell widgets
  - will need palette, spacing, typography, button, and shared card/material updates
- `src/windows_client/gui/inline_result_view.py`
  - owns the result-page reading surface
  - will absorb most of the V4 layout restructuring
- `src/windows_client/gui/library_panel.py`
  - owns the library list/detail dialog
  - will be reworked toward the V4 image-first detail + unified related-content structure
- `src/windows_client/gui/result_renderer.py`
  - owns HTML rendering helpers and preview stylesheet used by QTextBrowser
  - will need typography and inline-figure support tuned for the V4 reading style
- `tests/unit/test_inline_result_view.py`
  - result-page GUI regression coverage
- `tests/unit/test_main_window.py`
  - integration coverage for dialog opening, save/restore feedback, and dialog behavior

### Existing files to inspect but likely minimize changes

- `src/windows_client/app/view_models.py`
  - only if more GUI-facing metadata is needed during implementation
- `tests/unit/test_result_renderer.py`
  - only if renderer helpers or preview stylesheet behavior changes enough to require direct coverage

### No new subsystem files unless implementation truly needs them

This redesign should prefer focused refactoring inside the current GUI files over inventing a new styling subsystem or large component framework.

---

## Task 1: Lock Copy And Typography Inputs

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/library_panel.py`
- Test: `tests/unit/test_inline_result_view.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write the failing tests for real Chinese copy and revised section labeling**

Add assertions to `tests/unit/test_inline_result_view.py` and `tests/unit/test_main_window.py` that reflect the V4 naming direction:

```python
def test_result_view_uses_real_chinese_copy_for_long_reading_sections() -> None:
    view = InlineResultView()
    entry = _make_entry()

    view.load_entry(entry, brief=None, resolved_mode="argument")

    assert "这一项结果最重要的改变" not in view._browser.toPlainText() or True


def test_library_dialog_uses_related_content_style_labels() -> None:
    dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
    assert dialog.windowTitle() == "知识库"
```

Refine the real test code to match the current fixtures and actual visible labels you expect to keep or rename.

- [ ] **Step 2: Run the focused tests to verify they fail for the right reason**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "copy or label" -q
python -m pytest tests/unit/test_main_window.py -k "library_dialog" -q
```

Expected:

- at least one assertion fails because current labels/copy still reflect the pre-V4 structure

- [ ] **Step 3: Replace placeholder or weak copy with canonical Chinese product copy**

In `src/windows_client/gui/inline_result_view.py` and `src/windows_client/gui/library_panel.py`:

- remove any remaining weak placeholder-like labels that conflict with the V4 design intent
- normalize section labels so they read like a product, not like debug structure
- ensure no pseudo-Chinese or visibly placeholder text remains in GUI-owned copy

Use product-facing labels such as:

```python
"保存进知识库"
"知识库"
"查看知识库"
"恢复为当前"
"当前解读"
"版本时间线"
"相关内容"
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -q
python -m pytest tests/unit/test_main_window.py -k "library_dialog" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add src/windows_client/gui/inline_result_view.py src/windows_client/gui/library_panel.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py
git commit -m "feat: normalize gui readability copy"
```

---

## Task 2: Rebuild The Result-Page Hierarchy Around One Reading Stream

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Test: `tests/unit/test_inline_result_view.py`

- [ ] **Step 1: Write the failing layout-state tests for the V4 result-page structure**

Add tests that assert the result-page surface now behaves like a reading-first hierarchy:

```python
def test_result_view_shows_library_actions_but_keeps_reading_surface_primary() -> None:
    view = InlineResultView()
    entry = _make_entry()

    view.load_entry(entry, brief=None, resolved_mode="argument")

    assert view.save_to_library_button.isVisible()
    assert view.open_library_button.isVisible()
    assert view._card_frame.isVisible()


def test_result_view_renders_key_points_inline_instead_of_only_card_stack() -> None:
    view = InlineResultView()
    brief = _make_brief_with_key_points()
    entry = _make_entry()

    view.load_entry(entry, brief=brief, resolved_mode="argument")

    assert view._takeaways_frame.isVisible()
```

Refine these tests so they assert the actual new widget structure you introduce.

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "reading_surface or key_points" -q
```

Expected:

- FAIL because the current widget structure still reflects the old card-heavy layout

- [ ] **Step 3: Refactor `InlineResultView` into a stronger editorial hierarchy**

In `src/windows_client/gui/inline_result_view.py` make these focused structural changes:

- reduce first-screen action clutter
- keep the save-to-library path visible
- enlarge the image-summary area
- reduce hero title dominance
- convert takeaway presentation away from “equal card weight” where possible
- make long-form reading visually dominant with wider text flow

Keep the implementation within the current file unless a small helper improves clarity.

- [ ] **Step 4: Update the Qt widget layout with explicit V4 structure**

Implement a structure conceptually equivalent to:

```python
root
  top actions
  scroll area
    update banner
    library banner
    integrated hero surface
    image summary section
    inline key point stream
    long interpretation section
    secondary evidence / utility sections
```

Do not introduce unnecessary new panels if the content can live in the same reading stream.

- [ ] **Step 5: Run the result-view suite**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -q
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add src/windows_client/gui/inline_result_view.py tests/unit/test_inline_result_view.py
git commit -m "feat: redesign result page reading hierarchy"
```

---

## Task 3: Apply The V4 Material, Typography, And Shared Styling System

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] **Step 1: Write a failing renderer/style test for serif body rendering and updated preview styling**

Add a focused test in `tests/unit/test_result_renderer.py` that checks the generated preview stylesheet or HTML contains the new typography intent:

```python
def test_preview_stylesheet_supports_editorial_body_typography() -> None:
    assert "serif" in PREVIEW_STYLESHEET.lower()
```

If `PREVIEW_STYLESHEET` is too broad to test directly, add a more concrete assertion against the relevant HTML helper output.

- [ ] **Step 2: Run the focused renderer test and verify failure**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py -k "typography or preview" -q
```

Expected:

- FAIL if serif/editorial support is not yet present

- [ ] **Step 3: Update the global Qt stylesheet in `main_window.py`**

Refactor the embedded stylesheet so it matches the approved V4 tone:

- lighter cream-and-blue palette
- calmer acrylic effect
- stronger separation between heading typography and body typography
- less heavy dark treatment than the current hero styling
- wider-feeling reading surfaces through spacing and card treatment, not only width

Preserve object names already used by tests and widgets where possible.

- [ ] **Step 4: Update `result_renderer.py` preview styling for long-form readability**

Adjust `PREVIEW_STYLESHEET` and any helper HTML classes so:

- long body text uses a readable serif stack
- headings remain sans-serif or appropriately weighty
- inline figures/cards do not feel like foreign fragments when embedded into the reading stream

- [ ] **Step 5: Run the renderer tests**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py -q
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add src/windows_client/gui/main_window.py src/windows_client/gui/result_renderer.py tests/unit/test_result_renderer.py
git commit -m "feat: apply v4 typography and material styling"
```

---

## Task 4: Redesign The Library Dialog Into A Related-Content + Image-First Surface

**Files:**
- Modify: `src/windows_client/gui/library_panel.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing library-dialog tests for the new V4 structure**

Extend `tests/unit/test_main_window.py` with library dialog tests such as:

```python
def test_library_dialog_keeps_image_source_interpretation_order(self) -> None:
    dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
    assert dialog.entries


def test_library_dialog_shows_compact_related_content_list(self) -> None:
    dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
    assert dialog.list_widget.count() >= 0
```

Refine these tests to check the real UI signals of the V4 redesign: lighter context rail, concise row text, stable detail ordering, and version timeline visibility.

- [ ] **Step 2: Run the focused library-dialog tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "library_dialog" -q
```

Expected:

- FAIL because the current dialog still reflects the pre-V4 organization

- [ ] **Step 3: Refactor `LibraryDialog` layout structure**

In `src/windows_client/gui/library_panel.py`:

- keep the approved image -> source -> interpretation order
- make the left list read more like related content / browsing context than a filter-heavy side app
- keep filters, but visually subordinate them
- make the restore timeline feel lighter and more version-oriented

Prefer reorganizing the current widget tree over adding a new dialog type.

- [ ] **Step 4: Simplify list-row copy and sharpen detail hierarchy**

Update list rows so they emphasize:

- title
- source/platform
- route
- image-summary presence
- updated time

Update the detail sections so the hero image area clearly leads, then source, then interpretation.

- [ ] **Step 5: Run the library-dialog tests**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "library_dialog" -q
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add src/windows_client/gui/library_panel.py tests/unit/test_main_window.py
git commit -m "feat: redesign library dialog around v4 detail flow"
```

---

## Task 5: Preserve Existing Save/Restore Semantics While Updating The Surface

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Modify: `src/windows_client/gui/inline_result_view.py`
- Test: `tests/unit/test_main_window.py`
- Test: `tests/unit/test_inline_result_view.py`

- [ ] **Step 1: Write failing regression tests for save/restore affordances after the redesign**

Add focused assertions that the V4 redesign did not regress product behavior:

```python
def test_save_success_banner_still_exposes_open_entry_and_open_library(self) -> None:
    ...


def test_open_library_entry_signal_still_targets_saved_entry(self) -> None:
    ...


def test_restore_flow_still_refreshes_library_dialog(self) -> None:
    ...
```

- [ ] **Step 2: Run the focused regression tests and verify failure if behavior drifted**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "save_latest_result_to_library or restore_library_interpretation or open_library_entry" -q
python -m pytest tests/unit/test_inline_result_view.py -k "library_banner or open_library_entry" -q
```

Expected:

- either PASS immediately or expose any accidental regressions introduced by the layout work

- [ ] **Step 3: Repair behavior regressions without weakening the redesign**

If any tests fail, fix only the behavior drift:

- save banner action behavior
- library entry targeting
- restore refresh behavior
- state visibility after refresh

Do not widen scope beyond these regressions.

- [ ] **Step 4: Run the focused regression suites again**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -q
python -m pytest tests/unit/test_inline_result_view.py -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add src/windows_client/gui/main_window.py src/windows_client/gui/inline_result_view.py tests/unit/test_main_window.py tests/unit/test_inline_result_view.py
git commit -m "fix: preserve library flows during gui redesign"
```

---

## Task 6: Full Verification And Manual Review Preparation

**Files:**
- Modify if needed: `docs/session-memory-2026-04-08-source-centric-knowledge-library-closeout.md`

- [ ] **Step 1: Run the full GUI-related automated verification**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected:

- all relevant suites pass

- [ ] **Step 2: Run a manual acceptance sweep against the approved V4 goals**

Manual checklist:

- result page first screen feels calmer and less dashboard-like
- visual summary is larger and stronger than before
- title is still prominent but no longer overwhelming
- key points read inline rather than as competing cards
- long interpretation is clearly easier to read
- side context feels unified and lighter
- library detail remains image-first, then source, then interpretation
- save, open entry, re-save, and restore still work

- [ ] **Step 3: Update handoff/session memory if the redesign meaningfully changes the acceptance path**

If the GUI review flow changes enough, append a concise update to the current session memory document with the new acceptance cues and any notable implementation constraints.

- [ ] **Step 4: Commit**

```bash
git add docs/session-memory-2026-04-08-source-centric-knowledge-library-closeout.md src/windows_client/gui/main_window.py src/windows_client/gui/inline_result_view.py src/windows_client/gui/library_panel.py src/windows_client/gui/result_renderer.py tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py
git commit -m "feat: complete v4 gui readability redesign"
```

---

## Spec Coverage Check

This plan covers the approved spec requirements as follows:

- continuous result-page reading flow: Task 2
- lighter V4 palette/materials: Task 3
- stronger image-summary emphasis: Task 2 and Task 3
- inline key points: Task 2
- serif/sans typography split: Task 3
- unified `Library Context` / related-content rail: Task 4
- image-first library detail with refined hierarchy: Task 4
- preserve save/re-save/restore semantics: Task 5
- real Chinese copy and text integrity: Task 1
- verification and review readiness: Task 6

No spec gaps remain.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-08-gui-readability-v4-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
