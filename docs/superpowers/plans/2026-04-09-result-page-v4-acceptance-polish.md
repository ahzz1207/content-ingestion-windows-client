# Result Page V4 Acceptance Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-value remaining result-page UX gaps after the first V4 visual parity pass so the page feels more like the approved V4 reading product in manual acceptance.

**Architecture:** Keep the current result-page semantics and structure, but tighten the visual hierarchy in four places: hero arrival, hero-to-summary continuity, stream de-cardification, and rail containment. Add the smallest responsive safeguard for narrow widths so the rail cannot over-compress the reading column.

**Tech Stack:** PySide6, Qt stylesheets, existing result renderer helpers, Python `unittest` + `pytest`

---

## File Map

- Modify: `src/windows_client/gui/inline_result_view.py`
  - refine hero composition, summary continuity, rail composition, and responsive stacking
- Modify: `src/windows_client/gui/main_window.py`
  - tune stylesheet rules for the refined hero, summary, stream, and rail surfaces
- Modify: `tests/unit/test_inline_result_view.py`
  - add structural tests for the new acceptance-polish hooks
- Verify: `tests/unit/test_main_window.py`
  - ensure stylesheet signals and existing GUI behavior remain stable

---

### Task 1: Bring the Hero Fully Inside the Reading Surface

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for a self-contained hero surface**

Add tests that assert the user-facing result actions no longer live above the page in the global top bar and instead remain inside the hero surface.

Use tests like:

```python
    def test_result_view_hero_shell_contains_primary_result_actions(self) -> None:
        view = InlineResultView()

        self.assertIs(view._reanalyze_btn.parentWidget().parentWidget(), view._hero_shell)
        self.assertIs(view._save_to_library_btn.parentWidget().parentWidget(), view._hero_shell)

    def test_result_view_top_bar_keeps_only_global_navigation_actions(self) -> None:
        view = InlineResultView()

        self.assertIs(view._new_url_button.parentWidget(), view._top_bar_widget)
        self.assertIs(view._history_btn.parentWidget(), view._top_bar_widget)
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "hero_shell_contains_primary_result_actions or top_bar_keeps_only_global_navigation_actions" -q
```

Expected: FAIL because the current top bar still mixes global and result-specific actions.

- [ ] **Step 3: Implement the minimal top-bar / hero split**

In `src/windows_client/gui/inline_result_view.py`:

- wrap the global top bar in a named widget like `ResultGlobalBar`
- keep only `新的链接` and `历史记录` in that global bar
- keep result-specific actions in `HeroActionStrip`

Do not change any action behavior.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "hero_shell_contains_primary_result_actions or top_bar_keeps_only_global_navigation_actions" -q
```

Expected: PASS.

---

### Task 2: Make the Image Summary a Real Continuation Block

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/main_window.py`

- [ ] **Step 1: Write the failing test for a dedicated image-summary surface**

Add a test that locks a distinct surface hook for the image-summary continuation block.

Use a test like:

```python
    def test_result_view_uses_dedicated_image_summary_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._card_frame.objectName(), "ImageSummaryCard")
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "dedicated_image_summary_surface" -q
```

Expected: FAIL because the frame still uses the old generic object name.

- [ ] **Step 3: Implement the minimal image-summary continuity update**

In `src/windows_client/gui/inline_result_view.py`:

- rename the insight/image frame object name to something dedicated like `ImageSummaryCard`
- keep the current heading and save action but preserve their secondary role

In `src/windows_client/gui/main_window.py`:

- add matching stylesheet rules that make this block feel like a continuation sheet from the hero rather than a utility frame

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "dedicated_image_summary_surface" -q
```

Expected: PASS.

---

### Task 3: Reduce Main-Stream Card Repetition

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`
- Modify: `src/windows_client/gui/main_window.py`

- [ ] **Step 1: Write the failing test for lighter stream sections**

Add tests that assert the main supporting sections expose a lighter stream object name instead of all relying on the same generic preview-card identity.

Use tests like:

```python
    def test_result_view_takeaways_use_stream_section_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._takeaways_frame.objectName(), "StreamSection")

    def test_result_view_gaps_use_stream_section_surface(self) -> None:
        view = InlineResultView()

        self.assertEqual(view._gaps_frame.objectName(), "StreamSection")
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "takeaways_use_stream_section_surface or gaps_use_stream_section_surface" -q
```

Expected: FAIL because those frames currently use older object names.

- [ ] **Step 3: Implement the minimal stream-surface unification**

In `src/windows_client/gui/inline_result_view.py`:

- reassign the lighter supporting sections to a shared `StreamSection` object name where appropriate

In `src/windows_client/gui/main_window.py`:

- add a calmer `#StreamSection` style that is lighter than `PreviewCard`
- keep warnings and the bottom-line card visually distinct

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "takeaways_use_stream_section_surface or gaps_use_stream_section_surface" -q
```

Expected: PASS.

---

### Task 4: Add a Narrow-Width Stack Fallback

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing test for narrow-width layout fallback**

Add a test that proves the result page can switch from side-by-side to stacked layout in a narrow state.

Use a test like:

```python
    def test_result_view_stacks_context_rail_below_stream_in_narrow_mode(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertEqual(view._content_shell_layout.getItemPosition(0), (0, 0, 1, 1))
        self.assertEqual(view._content_shell_layout.getItemPosition(1), (1, 0, 1, 1))
```

Adjust the exact indices based on the implementation, but the test must prove the rail stacks below the stream.

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "stacks_context_rail_below_stream_in_narrow_mode" -q
```

Expected: FAIL because no layout-mode method exists yet.

- [ ] **Step 3: Implement the smallest responsive fallback**

In `src/windows_client/gui/inline_result_view.py`:

- add a small helper like `_apply_layout_mode(available_width: int)`
- keep two-column layout for wide mode
- stack the rail below the reading stream for narrow mode
- call it from `resizeEvent`

Do not redesign the page for mobile; just prevent destructive over-compression.

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "stacks_context_rail_below_stream_in_narrow_mode" -q
```

Expected: PASS.

---

### Task 5: Run Full Verification and Manual Launch Check

**Files:**
- Verify only

- [ ] **Step 1: Run the main GUI suite**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.

- [ ] **Step 2: Run the broader regression suite**

Run:

```bash
python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.

- [ ] **Step 3: Launch the worktree GUI for manual acceptance**

Run:

```bash
python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console
```

Manual acceptance checks:

- hero feels more like a first screen and less like a top card
- image summary now reads as the first continuation block from hero
- reading stream feels less like repeated cards
- narrow window no longer crushes the main reading column
