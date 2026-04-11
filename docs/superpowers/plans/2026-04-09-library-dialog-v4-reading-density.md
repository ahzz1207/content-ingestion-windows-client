# Library Dialog V4 Reading Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the library detail page read like a calmer V4 entry surface by compressing source chrome, elevating the current interpretation, and wiring a source-header jump back to the full analysis workspace.

**Architecture:** Keep the current source-centric dialog and save/restore semantics, but rebalance the detail view into three clearer layers: a compact source header in the main column, a dominant interpretation reading surface, and a quieter side rail wrapped in a shell. Route the new full-analysis action through an explicit `LibraryDialog` signal and the existing `MainWindow._show_result_workspace()` path.

**Tech Stack:** PySide6, Qt widgets and stylesheets, existing library store/result workspace helpers, Python `unittest` + `pytest`

---

## File Map

- Modify: `tests/unit/test_main_window.py`
  - add or update red tests for the new library-detail layout signals and full-analysis routing
- Modify: `src/windows_client/gui/library_panel.py`
  - add the new dialog signal, compact source header, stronger interpretation surface, and quieter side-rail shell
- Modify: `src/windows_client/gui/main_window.py`
  - connect the new dialog signal and route it into the existing result workspace
- Verify: `tests/unit/test_library_store.py`
  - regression only

---

### Task 1: Lock the Full-Analysis Navigation Contract

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`
- Modify: `src/windows_client/gui/main_window.py`

- [ ] **Step 1: Write or update the failing tests**

Lock three behaviors:

- `LibraryDialog` exposes `open_analysis_requested`
- clicking the source-header button emits the current interpretation job id
- `MainWindow` routes that job id into `_show_result_workspace(shared_root=..., selected_job_id=job_id)`

Use tests around:

```python
def test_library_dialog_emits_open_analysis_requested_for_selected_entry(self) -> None:
    ...

def test_open_library_dialog_connects_analysis_signal(self) -> None:
    ...

def test_main_window_opens_result_workspace_from_library_analysis_action(self) -> None:
    ...
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "open_analysis_requested or open_library_dialog_connects_analysis_signal or open_result_workspace_from_library_analysis_action" -q
```

Expected: FAIL because the signal and route are not fully implemented yet.

- [ ] **Step 3: Implement the minimal navigation path**

In `src/windows_client/gui/library_panel.py`:

- add `open_analysis_requested = Signal(str)`
- make the source-header action emit `current_interpretation.saved_from_job_id`

In `src/windows_client/gui/main_window.py`:

- connect the new signal inside `_open_library_dialog()`
- add `_open_library_analysis(job_id: str)` that closes the open library dialog and calls `_show_result_workspace(...)`

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 2: Compress the Source Block Into a Real Header

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`
- Modify: `src/windows_client/gui/main_window.py`

- [ ] **Step 1: Write the failing tests for the compact source header**

Add tests that lock the redesigned source section contract:

- the source section uses a dedicated compact surface such as `SourceHeaderCard`
- the full-analysis button is present in that surface
- raw snapshot-path copy is no longer rendered in the main source block

Use tests around:

```python
def test_library_dialog_uses_compact_source_header_surface(self) -> None:
    ...

def test_library_dialog_keeps_snapshot_paths_out_of_source_header(self) -> None:
    ...
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "compact_source_header_surface or snapshot_paths_out_of_source_header" -q
```

Expected: FAIL because the source section still renders as a heavy detail card with path text.

- [ ] **Step 3: Implement the minimal source-header redesign**

In `src/windows_client/gui/library_panel.py`:

- replace the generic detail-card source block with a compact header card
- keep title, byline, and URL
- place `查看完整分析` in the header row
- remove raw snapshot-path lines from the main source block

In `src/windows_client/gui/main_window.py`:

- add a stylesheet rule for the compact header surface

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 3: Make the Interpretation the Primary Reading Surface

**Files:**
- Modify: `tests/unit/test_main_window.py`
- Modify: `src/windows_client/gui/library_panel.py`
- Modify: `src/windows_client/gui/main_window.py`

- [ ] **Step 1: Write the failing tests for the interpretation surface**

Add tests that prove the interpretation section now exposes a dedicated browser surface and stronger layout role.

Use tests around:

```python
def test_library_dialog_interpretation_section_uses_primary_reading_surface(self) -> None:
    ...

def test_library_dialog_context_section_surfaces_source_snapshot_context(self) -> None:
    ...
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "primary_reading_surface or source_snapshot_context" -q
```

Expected: FAIL because the browser has no dedicated reading-surface hook yet and the snapshot context is not demoted into the rail.

- [ ] **Step 3: Implement the minimal reading-surface rebalance**

In `src/windows_client/gui/library_panel.py`:

- give the interpretation browser a dedicated object name such as `LibraryInterpretationBrowser`
- increase its minimum height so it dominates the detail page
- keep summary copy secondary
- add source snapshot context to the side-context section in weaker product copy
- wrap the side rail in a shell that uses the existing `ContextRailShell` styling

In `src/windows_client/gui/main_window.py`:

- add any focused stylesheet rules needed for the interpretation browser and source header

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 4: Run Regression Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the focused library GUI suite**

Run:

```bash
python -m pytest tests/unit/test_main_window.py -k "library_dialog or open_library_analysis" -q
```

Expected: PASS.

- [ ] **Step 2: Run the broader regression suite**

Run:

```bash
python -m pytest tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q
```

Expected: PASS.

- [ ] **Step 3: Launch the worktree GUI for manual acceptance**

Run:

```bash
python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console
```

Manual acceptance checks:

- `来源信息` now reads like a compact source header
- `当前解读` is visually the main reading destination
- the side rail feels quieter and less competitive
- `查看完整分析` jumps to the expected full result workspace
