# Inline Result First-Screen Image-Led Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the inline result page show a compact header plus an image-led first screen in narrow/non-fullscreen usage, while degrading gracefully when no insight card is available.

**Architecture:** Keep the existing `InlineResultView` structure and backend contract intact. Add the smallest possible presentation-state handling inside `InlineResultView` so narrow layouts can switch to a compact first-screen treatment, and tune the stylesheet in `main_window.py` so the hero and image card visually support that treatment. Use existing test coverage in `test_inline_result_view.py` to lock the new layout behavior before code changes.

**Tech Stack:** PySide6, Qt layouts and stylesheets, Python `unittest`, `pytest`

---

## File Map

- Modify: `src/windows_client/gui/inline_result_view.py`
  - add compact first-screen state handling, narrow-layout presentation updates, and image-led/fallback behavior
- Modify: `src/windows_client/gui/main_window.py`
  - tune hero and image-summary stylesheet rules for the compact image-led layout
- Modify: `tests/unit/test_inline_result_view.py`
  - add focused structural tests for compact layout and image-led fallback behavior
- Verify: `tests/unit/test_main_window.py`
  - confirm no regression in main-window result-page loading behavior

---

### Task 1: Lock the Narrow First-Screen Behavior with Tests

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for compact narrow layout state**

Add tests to `tests/unit/test_inline_result_view.py` that prove narrow mode does more than stack the context rail.

Add these tests near the existing narrow-layout assertions:

```python
    def test_result_view_marks_narrow_layout_state_when_below_breakpoint(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertTrue(view.property("isNarrowLayout"))

    def test_result_view_clears_narrow_layout_state_when_above_breakpoint(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)
        view._apply_layout_mode(available_width=1400)

        self.assertFalse(view.property("isNarrowLayout"))
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "marks_narrow_layout_state or clears_narrow_layout_state" -q
```

Expected: FAIL because `InlineResultView` does not currently expose any layout-state property.

- [ ] **Step 3: Implement the minimal narrow-layout state hook**

In `src/windows_client/gui/inline_result_view.py`, update `_apply_layout_mode()` so it also marks the widget tree with a narrow-layout property and refreshes style polish.

Use this implementation pattern:

```python
    def _set_layout_state(self, *, narrow: bool) -> None:
        widgets = (
            self,
            self._hero_shell,
            self._hero_frame,
            self._hero_topbar,
            self._hero_action_strip,
            self._card_frame,
            self._reading_stream_frame,
        )
        for widget in widgets:
            widget.setProperty("isNarrowLayout", narrow)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _apply_layout_mode(self, available_width: int) -> None:
        narrow = available_width <= self._NARROW_LAYOUT_BREAKPOINT
        self._set_layout_state(narrow=narrow)
        if narrow:
            self._content_shell_layout.setHorizontalSpacing(0)
            self._content_shell_layout.setColumnStretch(0, 1)
            self._content_shell_layout.setColumnStretch(1, 0)
            self._content_shell_layout.addWidget(self._reading_stream_shell, 0, 0)
            self._content_shell_layout.addWidget(self._context_rail_shell, 1, 0)
            return
        self._content_shell_layout.setHorizontalSpacing(24)
        self._content_shell_layout.setColumnStretch(0, 4)
        self._content_shell_layout.setColumnStretch(1, 1)
        self._content_shell_layout.addWidget(self._reading_stream_shell, 0, 0)
        self._content_shell_layout.addWidget(self._context_rail_shell, 0, 1)
```

Keep the existing stacking behavior unchanged; only add the state hook.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "marks_narrow_layout_state or clears_narrow_layout_state" -q
```

Expected: PASS.

---

### Task 2: Lock Image-Led vs Fallback First-Screen Behavior

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for insight-card presence state**

Add tests that prove the view distinguishes a renderable insight card from a missing/invalid one.

Add these tests to `tests/unit/test_inline_result_view.py`:

```python
    def test_load_entry_marks_image_led_state_when_valid_insight_card_loads(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "insight_card.png"
            png_path.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
                b"\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9d"
                b"\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            entry.details = {"visual_findings": [], "insight_card_path": png_path}

            view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertFalse(view._card_frame.isHidden())
        self.assertTrue(view.property("hasInsightCard"))

    def test_load_entry_keeps_compact_text_state_when_insight_card_is_missing(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertTrue(view._card_frame.isHidden())
        self.assertFalse(view.property("hasInsightCard"))
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "image_led_state or compact_text_state" -q
```

Expected: FAIL because the view does not currently publish a `hasInsightCard` state property.

- [ ] **Step 3: Implement the minimal image-state hook in `load_entry()`**

In `src/windows_client/gui/inline_result_view.py`, extract the insight-card loading branch into a helper that both renders the pixmap and sets a property indicating whether a valid card exists.

Use this implementation shape:

```python
    def _set_insight_card_state(self, has_card: bool) -> None:
        widgets = (self, self._card_frame, self._reading_stream_frame)
        for widget in widgets:
            widget.setProperty("hasInsightCard", has_card)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _load_insight_card(self, card_path: object) -> None:
        if card_path is None:
            self._card_image_label.clear()
            self._card_frame.hide()
            self._set_insight_card_state(False)
            return
        pixmap = QPixmap(str(card_path))
        if pixmap.isNull():
            self._card_image_label.clear()
            self._card_frame.hide()
            self._set_insight_card_state(False)
            return
        max_width = 820 if not self.property("isNarrowLayout") else 760
        if pixmap.width() > max_width:
            pixmap = pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
        self._card_image_label.setPixmap(pixmap)
        self._card_frame.show()
        self._set_insight_card_state(True)
```

Then replace the existing inline insight-card block in `load_entry()` with:

```python
        self._load_insight_card(entry.details.get("insight_card_path"))
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "image_led_state or compact_text_state" -q
```

Expected: PASS.

---

### Task 3: Compress the Hero and Promote the Image Card in Stylesheet Rules

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Verify: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write the failing stylesheet expectations test**

Add a test to `tests/unit/test_main_window.py` that locks the presence of the compact-layout selectors in the application stylesheet.

Add a test like:

```python
def test_main_window_stylesheet_contains_inline_result_compact_layout_hooks(qtbot) -> None:
    window = _make_window(qtbot)

    stylesheet = window.styleSheet()

    assert 'QFrame#ImmersiveHero[isNarrowLayout="true"]' in stylesheet
    assert 'QFrame#ImageSummaryCard[hasInsightCard="true"]' in stylesheet
```

Use the existing helper that the file uses for window creation.

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "compact_layout_hooks" -q
```

Expected: FAIL because those selectors are not yet present.

- [ ] **Step 3: Implement the minimal stylesheet updates**

In `src/windows_client/gui/main_window.py`, update `_apply_styles()` with compact-layout selectors instead of rewriting the whole base style.

Add rules in this shape:

```css
QFrame#ImmersiveHero[isNarrowLayout="true"] {
    border-radius: 28px;
}
QWidget#HeroTopBar[isNarrowLayout="true"] {
    background: transparent;
    border: none;
}
QFrame#HeroCard[isNarrowLayout="true"] {
    border-radius: 24px;
}
QWidget#HeroActionStrip[isNarrowLayout="true"] {
    border-radius: 18px;
    padding: 4px;
}
QFrame#ImageSummaryCard[hasInsightCard="true"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(58, 103, 214, 0.12);
}
QFrame#ImageSummaryCard[isNarrowLayout="true"][hasInsightCard="true"] {
    border-radius: 24px;
}
```

Then tighten the existing base paddings and radii to support the compact header even before the narrow-specific selectors apply:

- reduce `#ImmersiveHero` radius from `38px` to `30px`
- reduce `#HeroTopBar` interior spacing by lowering layout margins in `inline_result_view.py` rather than trying to do it all in CSS
- reduce `#HeroActionStrip` radius from `22px` to `18px`
- reduce `QTextBrowser` padding from `28px` to `24px`

Do not change unrelated result-page styling.

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "compact_layout_hooks" -q
```

Expected: PASS.

---

### Task 4: Tighten the Widget Layout for the Compact First Screen

**Files:**
- Modify: `tests/unit/test_inline_result_view.py`
- Modify: `src/windows_client/gui/inline_result_view.py`

- [ ] **Step 1: Write the failing tests for compact spacing and no empty image slot**

Add tests that assert the hero/card stack becomes tighter and the missing-image path does not reserve a visible block.

Add these tests to `tests/unit/test_inline_result_view.py`:

```python
    def test_result_view_uses_tighter_stream_spacing_in_narrow_mode(self) -> None:
        view = InlineResultView()

        view._apply_layout_mode(available_width=900)

        self.assertEqual(view._reading_stream_layout.spacing(), 16)

    def test_missing_insight_card_clears_any_previous_pixmap(self) -> None:
        view = InlineResultView()
        entry = _make_entry()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "insight_card.png"
            png_path.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
                b"\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9d"
                b"\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            entry.details = {"visual_findings": [], "insight_card_path": png_path}
            view.load_entry(entry, brief=None, resolved_mode="argument")

        self.assertIsNotNone(view._card_image_label.pixmap())

        view.load_entry(_make_entry(), brief=None, resolved_mode="argument")

        self.assertTrue(view._card_frame.isHidden())
        self.assertIsNone(view._card_image_label.pixmap())
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "tighter_stream_spacing_in_narrow_mode or clears_any_previous_pixmap" -q
```

Expected: FAIL because narrow mode does not currently change stream spacing and the insight-card branch does not explicitly clear state through a shared helper.

- [ ] **Step 3: Implement the minimal layout tightening**

In `src/windows_client/gui/inline_result_view.py`:

- lower the default reading-stream spacing from `20` to `18`
- in `_set_layout_state()`, set the reading-stream spacing dynamically:

```python
        self._reading_stream_layout.setSpacing(16 if narrow else 18)
```

- reduce layout margins in the hero area:

```python
        hero_topbar_layout.setContentsMargins(24, 18, 24, 0)
        hero_layout.setContentsMargins(24, 18, 24, 22)
        hero_layout.setSpacing(8)
        hero_meta_layout.setSpacing(6)
        tags_row_layout.setSpacing(6)
```

- in `_load_insight_card()`, call `self._card_image_label.clear()` whenever the image is absent or invalid

Do not reorder the main sections; only tighten spacing and state handling.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -k "tighter_stream_spacing_in_narrow_mode or clears_any_previous_pixmap" -q
```

Expected: PASS.

---

### Task 5: Run the Relevant Result-Page Verification Suite

**Files:**
- Verify: `tests/unit/test_inline_result_view.py`
- Verify: `tests/unit/test_main_window.py`

- [ ] **Step 1: Run the inline-result test file**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the main-window test file**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -q
```

Expected: PASS.

- [ ] **Step 3: Run the targeted combined regression check**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py tests/unit/test_main_window.py tests/unit/test_result_renderer.py -q
```

Expected: PASS.

- [ ] **Step 4: Manual verification in the GUI**

Launch the GUI and verify these cases manually:

```bash
python main.py gui --debug-console
```

Check:

- a non-fullscreen result with an actual `insight_card.png`
- a non-fullscreen result without `insight_card.png`
- the hero is visibly shorter than before
- the image card is the primary first-screen artifact when present
- there is no large empty placeholder when the image is absent

---

## Self-Review

- Spec coverage: covered compact hero, image-led first screen, text condensation, and fallback when the image is missing.
- Placeholder scan: no `TBD`/`TODO`/deferred implementation markers remain.
- Type consistency: uses existing `InlineResultView` widget names and adds only two explicit dynamic properties, `isNarrowLayout` and `hasInsightCard`.
