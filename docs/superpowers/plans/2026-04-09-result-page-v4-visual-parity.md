# Result Page V4 Visual Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PySide result page feel materially closer to the approved HTML V4 reading experience, with the strongest improvement in hero immersion and whole-page editorial atmosphere.

**Architecture:** Keep the existing result-page semantics and flow intact, but tighten the visual system in three layers: a more immersive hero shell, a calmer continuous reading stream, and a better-contained context rail. Use small structural refinements in `InlineResultView`, stylesheet changes in `MainWindow`, and minimal renderer support where needed.

**Tech Stack:** PySide6, Qt stylesheets, existing result renderer helpers, Python `unittest` + `pytest`

---

## File Map

- Modify: `src/windows_client/gui/inline_result_view.py`
  - introduce the smallest structural hooks needed for an immersive hero and quieter stream rhythm
- Modify: `src/windows_client/gui/main_window.py`
  - update Qt stylesheet rules for hero, stream sections, context rail, buttons, and text surfaces
- Modify: `src/windows_client/gui/result_renderer.py`
  - make minimal reading-surface styling adjustments so browser-rendered content better matches the page atmosphere
- Modify: `tests/unit/test_inline_result_view.py`
  - add structural tests for new hero / stream / rail hooks
- Modify: `tests/unit/test_result_renderer.py`
  - add or adjust tests for reading-surface styling signals if the renderer stylesheet changes materially
- Verify: `tests/unit/test_main_window.py`
  - ensure broader GUI behavior still holds after the visual pass

---

### Task 1: Lock the Immersive Hero Structure

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for the new hero structure**

Add tests that lock the new visual-structure hooks instead of only style text values.

Use assertions along these lines in `tests/unit/test_inline_result_view.py`:

```python
    def test_result_view_uses_dedicated_hero_shell_container(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._hero_shell.objectName(), "ImmersiveHero")

    def test_result_view_places_primary_actions_inside_hero_shell(self) -> None:
        view = InlineResultView()

        action_parent = view._hero_action_strip.parentWidget()
        self.assertIs(action_parent, view._hero_shell)

    def test_result_view_uses_dedicated_hero_meta_row(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._hero_meta_row.objectName(), "HeroMetaRow")
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "dedicated_hero_shell_container or primary_actions_inside_hero_shell or dedicated_hero_meta_row" -q
```

Expected: FAIL because the new containers and object names do not exist yet.

- [ ] **Step 3: Implement the minimal hero-shell structure**

In `src/windows_client/gui/inline_result_view.py`, introduce a nested hero shell that keeps current semantics but gives the stylesheet a dedicated immersive surface to target.

Implementation requirements:

```python
        self._hero_shell = QFrame()
        self._hero_shell.setObjectName("ImmersiveHero")

        hero_shell_layout = QVBoxLayout(self._hero_shell)
        hero_shell_layout.setContentsMargins(0, 0, 0, 0)
        hero_shell_layout.setSpacing(0)

        self._hero_topbar = QWidget()
        self._hero_topbar.setObjectName("HeroTopBar")

        self._hero_action_strip = QWidget()
        self._hero_action_strip.setObjectName("HeroActionStrip")

        self._hero_meta_row = QWidget()
        self._hero_meta_row.setObjectName("HeroMetaRow")
```

Then move the existing hero content into this shell instead of adding `self._hero_frame` directly to the reading stream.

Keep the current action semantics intact:

- `重新分析`
- `切换解读方式`
- `保存进知识库`
- `知识库`

Do not change their behavior in this task.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "dedicated_hero_shell_container or primary_actions_inside_hero_shell or dedicated_hero_meta_row" -q
```

Expected: PASS.

---

### Task 2: Lock the Reading-Stream and Context-Rail Atmosphere Hooks

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for the calmer stream and contained rail hooks**

Add tests that assert the page now exposes dedicated wrappers for stream sections and a contained rail shell.

Add tests like:

```python
    def test_result_view_uses_reading_stream_shell(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._reading_stream_shell.objectName(), "ReadingStreamShell")

    def test_result_view_uses_context_rail_shell(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._context_rail_shell.objectName(), "ContextRailShell")
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "reading_stream_shell or context_rail_shell" -q
```

Expected: FAIL because these shells do not exist yet.

- [ ] **Step 3: Implement the minimal stream / rail shells**

In `src/windows_client/gui/inline_result_view.py`, add lightweight shell wrappers:

```python
        self._reading_stream_shell = QWidget()
        self._reading_stream_shell.setObjectName("ReadingStreamShell")

        self._context_rail_shell = QFrame()
        self._context_rail_shell.setObjectName("ContextRailShell")
```

Use them to:

- wrap the reading stream with clearer top/bottom padding and consistent section rhythm
- wrap the existing context rail content with a quieter inner shell

Do not reorder the actual content sections.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "reading_stream_shell or context_rail_shell" -q
```

Expected: PASS.

---

### Task 3: Apply the V4 Hero-First Material System

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Modify: `tests/unit/test_inline_result_view.py`

- [ ] **Step 1: Write the failing test for immersive hero stylesheet signals**

Add a test in `tests/unit/test_inline_result_view.py` that checks the active stylesheet contains the new object names and expected V4 visual hooks.

Use assertions like:

```python
    def test_main_window_stylesheet_supports_v4_immersive_result_page(self) -> None:
        from windows_client.gui.main_window import MainWindow

        window = MainWindow(workflow=_FakeWorkflow())
        stylesheet = window.styleSheet()

        self.assertIn("#ImmersiveHero", stylesheet)
        self.assertIn("#HeroActionStrip", stylesheet)
        self.assertIn("#ReadingStreamShell", stylesheet)
        self.assertIn("#ContextRailShell", stylesheet)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "immersive_result_page" -q
```

Expected: FAIL because the stylesheet does not yet define those rules.

- [ ] **Step 3: Update `MainWindow._apply_styles()` for the new V4 page language**

In `src/windows_client/gui/main_window.py`, add stylesheet rules for:

- `#ImmersiveHero`
- `#HeroTopBar`
- `#HeroActionStrip`
- `#HeroMetaRow`
- `#ReadingStreamShell`
- `#ContextRailShell`

Visual intent to encode:

- taller, more layered hero surface
- stronger cream-blue gradient and top-light atmosphere
- lighter but more coherent stream sections
- quieter contained rail shell
- browser surface closer to a paper slab

Do not replace the whole stylesheet. Update the existing V4 rules in place.

- [ ] **Step 4: Run the focused stylesheet test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "immersive_result_page" -q
```

Expected: PASS.

---

### Task 4: Bring Result Sections Closer to an Editorial Stream

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/main_window.py`
- Modify: `tests/unit/test_inline_result_view.py`

- [ ] **Step 1: Write the failing tests for editorialized section signals**

Add tests that assert key-point items and warning banners now expose dedicated visual object names that match the new editorial stream system.

Use tests like:

```python
    def test_key_point_items_use_editorial_object_names(self) -> None:
        item = InlineResultView._make_key_point_item(1, "Statement", "Details")

        self.assertEqual(item.objectName(), "EditorialKeyPoint")

    def test_warning_banners_use_editorial_warning_surface(self) -> None:
        banner, _label = InlineResultView._make_warning_banner()

        self.assertEqual(banner.objectName(), "EditorialWarning")
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "editorial_object_names or editorial_warning_surface" -q
```

Expected: FAIL because those object names are not in place.

- [ ] **Step 3: Implement the minimal editorial object-name updates**

In `src/windows_client/gui/inline_result_view.py`:

- update `_make_key_point_item()` to expose an editorial object name for the outer widget
- update `_make_warning_banner()` to expose a calmer dedicated warning surface object name

In `src/windows_client/gui/main_window.py`:

- add matching stylesheet rules for these new names

Do not change any warning logic or key-point behavior in this task.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "editorial_object_names or editorial_warning_surface" -q
```

Expected: PASS.

---

### Task 5: Tighten the Reading Surface Renderer Support

**Files:**
- Modify: `tests/unit/test_result_renderer.py`
- Modify: `src/windows_client/gui/result_renderer.py`

- [ ] **Step 1: Write the failing renderer test for calmer reading-surface styling**

Add a focused stylesheet test in `tests/unit/test_result_renderer.py` that checks for the extra reading-surface signals this pass needs.

Use a test like:

```python
def test_preview_stylesheet_supports_v4_editorial_reading_surface() -> None:
    self.assertIn(".preview-reading", PREVIEW_STYLESHEET)
    self.assertIn("border-radius", PREVIEW_STYLESHEET)
    self.assertIn("box-shadow", PREVIEW_STYLESHEET)
```

If those strings already exist, strengthen the assertion to the new selectors or values added in this pass.

- [ ] **Step 2: Run the focused renderer test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py -k "editorial_reading_surface" -q
```

Expected: FAIL on the new assertion.

- [ ] **Step 3: Make the smallest renderer stylesheet adjustments needed**

In `src/windows_client/gui/result_renderer.py`, update `PREVIEW_STYLESHEET` so the browser-rendered long reading surface better matches the new page atmosphere.

Target adjustments:

- calmer paper-like block feel
- slightly more disciplined section spacing
- retain serif long-form readability
- avoid adding HTML-only tricks Qt cannot render meaningfully

- [ ] **Step 4: Run the focused renderer test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py -k "editorial_reading_surface" -q
```

Expected: PASS.

---

### Task 6: Run Full GUI Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the main GUI suite**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.

- [ ] **Step 2: Run the broader regression suite touching result and library behavior**

Run:

```bash
python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.

- [ ] **Step 3: Launch the current worktree GUI with the correct entrypoint for manual validation**

Run:

```bash
python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console
```

Manual check against the approved V4 mockup should confirm:

- first-screen atmosphere improved materially
- hero feels less like a plain top card
- reading stream feels calmer and more continuous
- context rail reads as quiet supporting context

---

## Spec Coverage Check

This plan covers the focused spec requirements by:

- Task 1: immersive hero structure
- Task 2: reading stream shell and context rail shell
- Task 3: page-level material system updates in Qt stylesheet
- Task 4: editorial stream treatment for local result-page sections
- Task 5: renderer surface support for the long reading area
- Task 6: verification and manual V4 comparison

No spec gaps were intentionally left open.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-09-result-page-v4-visual-parity.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
