# Library Dialog V4 Reading Density Design

**Date:** 2026-04-09  
**Status:** approved for implementation  
**Scope:** tighten the library detail reading experience so saved entries feel closer to the approved V4 editorial direction without changing source-centric library semantics.

---

## Summary

The result page is now in an acceptable place for this iteration, but the library detail experience is still visibly behind. Manual review showed that the current detail page keeps the correct macro order, yet the reading density and hierarchy are wrong: the source block is too heavy, the long interpretation is too compressed, and the page lacks a direct way to jump back into the full analysis workspace.

This pass keeps the current library model intact and focuses only on **detail-page hierarchy, density, and navigation**.

Reference inputs:

- session memory and latest acceptance notes: `docs/session-memory-2026-04-08-source-centric-knowledge-library-closeout.md`
- current implementation: `src/windows_client/gui/library_panel.py`, `src/windows_client/gui/main_window.py`
- approved V4 direction: `docs/superpowers/specs/2026-04-08-gui-readability-v4-redesign-design.md`

---

## Problem

### 1. The source section is carrying too much visual and semantic weight

The current `来源信息` section behaves like a full detail card. It uses too much height, surfaces too many technical snapshot lines, and competes directly with the interpretation surface. The user should be able to identify the source quickly, but should not need to read file-path-like metadata before getting back to the actual analysis.

### 2. The interpretation is not yet the dominant reading surface

The current `当前解读` section is structurally correct, but in practice the browser surface feels secondary. Its footprint is too modest relative to the surrounding blocks, so the detail page does not read like an editorial reading destination.

### 3. Context is present, but not contained tightly enough

The right side already holds useful context, but it still feels like several adjacent utilities rather than a calmer supporting rail. This contributes to the perception that the main reading area is being squeezed by side information.

### 4. There is no direct path back to the full analysis workspace

When a user opens a saved library entry, they can inspect the current interpretation, but they cannot immediately jump back to the corresponding full analysis view. This breaks the reading loop between durable library entries and the deeper result workspace.

---

## Goal

Turn the library detail page into a calmer reading-oriented entry surface where:

1. source identity is compact and easy to scan
2. the current interpretation is clearly the primary reading area
3. context becomes supportive instead of competitive
4. the user can jump from a saved entry back to its full analysis in one click

---

## Non-Goals

- changing source-centric library semantics
- changing save / re-save / restore behavior
- redesigning the result page again in this pass
- adding generic PKM or note-editing affordances
- replacing the library dialog with a different screen model

---

## Chosen Direction

Use a **compact source header + dominant interpretation surface** layout.

This means:

- keep the main-column order as image summary -> source -> current interpretation
- compress `来源信息` into a light source header card with the entry identity and one action
- move technical snapshot context out of the main source block and into weaker side-context copy
- make the interpretation browser materially taller and visually more central
- add `查看完整分析` in the source header, using the current interpretation's `saved_from_job_id` to open the result workspace

---

## Design Details

## Main Column

### Image summary remains first

The image summary stays at the top when available. This preserves the current image-first library detail rhythm and the source-centric semantics already approved.

### Source becomes a compact header

The `来源信息` block should become a short scan-friendly header rather than a large detail card.

Required content:

- section label
- source title
- compact byline metadata
- source URL when available
- `查看完整分析` button aligned in the header area

Required removals from this block:

- raw snapshot-path lines such as markdown/json/metadata file paths
- stacked technical provenance text that pushes the interpretation downward

### Current interpretation becomes the page anchor

The `当前解读` block should become the largest and most stable surface in the detail page.

Required changes:

- keep the reading browser as the dominant element
- give the browser a clearly larger minimum height
- keep any short intro copy secondary to the browser, not equal to it
- make the section feel like the main reason the user opened the entry

---

## Side Column

The side column should read as one calmer context object.

Required changes:

- wrap the rail in a stronger shell so it feels separate from the main reading stream
- keep current-version metadata, version timeline, and source context in the rail
- surface source snapshot context in weaker product copy rather than raw file-path lists
- reduce the sense that the side rail is stealing width from the interpretation surface

The side rail remains useful, but it must not outrank the interpretation.

---

## Full Analysis Navigation

The new `查看完整分析` action belongs in the source header.

Behavior:

- the button opens the existing result workspace dialog
- it selects the job corresponding to the current interpretation's `saved_from_job_id`
- it does not change the underlying library entry
- it reuses existing result-workspace navigation instead of inventing a new full-analysis surface

If no `saved_from_job_id` is available, the button should stay hidden or disabled rather than pretending the action exists.

---

## Implementation Boundaries

Primary files:

- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`

Expected implementation shape:

- add a new dialog signal for opening the full analysis
- refactor the library source section into a lighter header-oriented card
- strengthen the interpretation surface and side-rail shell with minimal layout and stylesheet changes
- connect the new dialog signal to the already existing result-workspace flow in `MainWindow`

Avoid unrelated refactoring.

---

## Testing And Validation

Automated coverage should prove:

1. the library dialog emits a job-based full-analysis request from the source header
2. the main window routes that request into the existing result workspace dialog
3. source snapshot path copy no longer dominates the main source block
4. the interpretation section exposes a dedicated primary reading surface
5. the side column now uses a shell that reinforces the supporting-rail hierarchy

Manual acceptance should focus on:

1. source area feels noticeably smaller and calmer
2. the long reading area feels wide and readable enough to stay in the dialog
3. right-rail information feels supportive, not cramped and competitive
4. `查看完整分析` cleanly jumps to the expected analysis

---

## Acceptance Criteria

This pass is successful when all of the following are true:

1. the source block no longer visually dominates the top of the detail page
2. the interpretation browser is the clearest primary reading area
3. technical snapshot information is demoted out of the main reading flow
4. the source header contains a working `查看完整分析` action
5. existing save / restore / selection-preservation behavior continues to work
