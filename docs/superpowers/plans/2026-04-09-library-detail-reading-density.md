# Library Detail Reading Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the library detail view denser and more readable, and add a direct `查看完整分析` action from a saved library entry back to the full analysis workspace.

**Architecture:** Keep the current source-centric semantics intact, but compress the source block into a lighter header, promote the interpretation browser as the dominant reading slab, reduce wasted vertical space, and add a new library-to-result-workspace signal flow.

**Tech Stack:** PySide6, Qt signals/slots, existing `LibraryDialog` and `MainWindow` workspace opening flow, Python `unittest` + `pytest`

---

## File Map

- Modify: `src/windows_client/gui/library_panel.py`
  - compact the source header, add open-full-analysis action, reduce main-column waste, and emit a new signal
- Modify: `src/windows_client/gui/main_window.py`
  - wire the new library signal to the existing result-workspace opening flow
- Modify: `tests/unit/test_main_window.py`
  - add red/green coverage for the new action signal and workspace jump

---

### Task 1: Add `查看完整分析` Signal and Button

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`

- [ ] **Step 1: Write the failing tests for the new library action**

Add tests in `tests/unit/test_main_window.py` that lock the new behavior.

Use tests like:

```python
    def test_library_dialog_emits_open_analysis_requested_for_selected_entry(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        opened: list[str] = []
        dialog.open_analysis_requested.connect(opened.append)

        button = dialog._build_source_section(saved).findChild(QPushButton, "OpenFullAnalysisButton")
        button.click()

        self.assertEqual(opened, ["job-1"])
        dialog.close()

    def test_main_window_opens_result_workspace_from_library_analysis_action(self) -> None:
        self.window._open_library_analysis("job-123")

        self.assertEqual(self.window._show_result_workspace_calls[-1]["selected_job_id"], "job-123")
```

Use the existing `_show_result_workspace` patching pattern already present in this test file.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "open_analysis_requested_for_selected_entry or opens_result_workspace_from_library_analysis_action" -q
```

Expected: FAIL because the new signal and handler do not exist yet.

- [ ] **Step 3: Implement the minimal signal and button wiring**

In `src/windows_client/gui/library_panel.py`:

- add a new signal:

```python
open_analysis_requested = Signal(str)
```

- in `_build_source_section(entry)`, create a `QPushButton("查看完整分析")`
- set its object name to `GhostButton`
- set `button.setObjectName("OpenFullAnalysisButton")` only if needed for the test to find it by name
- emit `open_analysis_requested` with `entry.current_interpretation.saved_from_job_id` when available

In `src/windows_client/gui/main_window.py`:

- connect the new dialog signal in `_open_library_dialog`
- add `_open_library_analysis(job_id: str)`
- route that handler into the existing `_show_result_workspace(..., selected_job_id=job_id)` flow

Do not change result-workspace semantics.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "open_analysis_requested_for_selected_entry or opens_result_workspace_from_library_analysis_action" -q
```

Expected: PASS.

---

### Task 2: Compress the Source Block into a Real Header

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`

- [ ] **Step 1: Write the failing test for the compact source header hook**

Add a test that locks a dedicated object name for the lighter source header so the layout is no longer just another generic `DetailCard`.

Use a test like:

```python
    def test_library_dialog_uses_compact_source_header_surface(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        frame = dialog._build_source_section(saved)

        self.assertEqual(frame.objectName(), "SourceHeaderCard")
        dialog.close()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "compact_source_header_surface" -q
```

Expected: FAIL because `_build_source_section` still returns a generic `DetailCard`.

- [ ] **Step 3: Implement the compact source header**

In `src/windows_client/gui/library_panel.py`:

- make `_build_source_section(entry)` use a dedicated object name like `SourceHeaderCard`
- keep only:
  - source title
  - byline
  - source link
  - one compact provenance line at most
  - `查看完整分析` button row
- remove the tall stack of snapshot-path lines from the default main reading flow in this pass

Do not move those technical lines elsewhere yet if doing so widens scope. It is acceptable to omit them from the main default reading surface for now.

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "compact_source_header_surface" -q
```

Expected: PASS.

---

### Task 3: Promote the Interpretation Browser and Reduce Dead Space

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`

- [ ] **Step 1: Write the failing tests for the denser interpretation layout**

Add tests that lock two structural outcomes:

```python
    def test_library_dialog_does_not_add_main_column_stretch_after_interpretation(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        dialog._render_entry(0)

        last_item = dialog.main_column_layout.itemAt(dialog.main_column_layout.count() - 1)
        self.assertFalse(last_item.spacerItem() is not None)
        dialog.close()

    def test_library_dialog_interpretation_browser_has_larger_minimum_height(self) -> None:
        from windows_client.app.library_store import LibraryStore
        from windows_client.gui.library_panel import LibraryDialog

        store = LibraryStore(shared_root=self.shared_root)
        saved = store.save_entry(_library_processed_entry(self.shared_root, "job-1", source_url="https://example.com/1"))

        dialog = LibraryDialog(parent=None, shared_root=self.shared_root)
        browser = dialog._build_interpretation_section(saved).findChild(QTextBrowser)

        self.assertGreaterEqual(browser.minimumHeight(), 420)
        dialog.close()
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "does_not_add_main_column_stretch_after_interpretation or interpretation_browser_has_larger_minimum_height" -q
```

Expected: FAIL because the layout currently adds a stretch and the browser minimum height is still small.

- [ ] **Step 3: Implement the denser reading layout**

In `src/windows_client/gui/library_panel.py`:

- remove the `main_column_layout.addStretch(1)` in `_render_entry`
- increase the interpretation browser minimum height materially (e.g. from `260` to `420` or nearby)
- keep the current main-column order the same

This task should not redesign the HTML inside the browser. It is only about promoting the reading slab and reducing obvious empty waste.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "does_not_add_main_column_stretch_after_interpretation or interpretation_browser_has_larger_minimum_height" -q
```

Expected: PASS.

---

### Task 4: Run Full Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the library-dialog focused suite**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "library_dialog or open_analysis_requested_for_selected_entry or opens_result_workspace_from_library_analysis_action" -q
```

Expected: all PASS.

- [ ] **Step 2: Run the full GUI suite**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.

- [ ] **Step 3: Run the broader regression suite**

Run:

```bash
python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: all PASS.
