# Library Detail Reading Density Design

**Date:** 2026-04-09  
**Status:** draft for review  
**Scope:** refine the `LibraryDialog` detail surface so saved entries are actually readable, reduce layout waste, and add a direct path from a library entry back to the full analysis workspace.

---

## Summary

The current `LibraryDialog` is functionally valid but visually and structurally underperforming in the detail view. The main issue is no longer semantics. The issue is reading density and hierarchy.

The current detail surface gives too much height and emphasis to source metadata, leaves excessive empty space beneath the current interpretation, and does not clearly promote the interpretation browser as the primary reading surface. In addition, once a user opens a saved library entry, there is no direct affordance to jump back into the full analysis/result workspace.

This pass should make the library detail page feel like a readable saved-analysis view rather than a metadata dashboard.

---

## Problem

The current detail page has four specific problems:

### 1. The source block is oversized

`来源信息` currently behaves like a large card containing both source identity and technical snapshot details. This makes the source area too tall and visually heavier than it should be.

The user only needs a compact source header at this stage:

- source title
- lightweight byline
- source link
- a minimal provenance hint
- a direct `查看完整分析` action

The rest of the technical snapshot data should not consume premium reading height.

### 2. The main reading area is not dominant enough

`当前解读` contains the actual reading surface, but it appears after an oversized source block and is visually boxed in. The result is that the part the user most wants to read does not feel like the main object of the page.

### 3. There is too much empty space below the interpretation

The current detail layout creates a large dead zone beneath the `QTextBrowser`, which visually weakens the page and makes the reading area feel unfinished.

### 4. There is no direct return path to the full analysis workspace

Users can open a saved library entry, but once inside its detail view they cannot directly jump to the full result workspace / complete analysis surface for that source interpretation. This should exist as a first-class action.

---

## Goal

Turn the library detail page into a denser, more legible saved-reading surface with a clearer main reading area and a direct `查看完整分析` affordance.

Success means:

1. the source section becomes smaller and calmer
2. the current interpretation becomes the obvious visual center of the page
3. empty vertical waste is materially reduced
4. users can jump from a library entry to the full result workspace with one clear action

---

## Non-Goals

- changing source-centric save semantics
- changing restore semantics
- redesigning the sidebar filtering model
- changing how current/trashed interpretations are stored
- replacing the library detail with the result workspace entirely

---

## Chosen Direction

Use a **compact source header + dominant reading slab** model.

This means:

- compress `来源信息` into a lighter, shorter header block
- move technical snapshot details out of the premium reading height
- keep `当前解读` as the page's anchor reading surface
- keep version / context material in the side rail
- add `查看完整分析` inside the source header as the primary secondary action

---

## Detailed Design

## 1. Compact Source Header

The current `来源信息` block should become much shorter.

Required changes:

- keep source title, byline, and source link
- remove large stacked technical lines from the default reading path
- add one clear `查看完整分析` button in this header
- if needed, collapse technical source snapshot details into a lighter metadata subsection or hide them entirely in this pass

This block should feel like a contextual header, not a second hero card.

## 2. Promote `当前解读` to the main reading slab

The interpretation browser should become the dominant reading surface.

Required changes:

- tighter spacing between source header and interpretation block
- larger effective visual share for the interpretation block
- less competing card weight above it
- interpretation browser should read like the primary saved-reading surface

## 3. Reduce dead space beneath the interpretation

The current vertical composition leaves too much empty space after the reading content.

Required changes:

- reduce unnecessary stretch pressure in the main column
- avoid giving upper blocks more height than needed
- let the browser occupy the visual center more naturally

This does not require forcing the browser to fill all vertical space; it requires the page not to feel half-empty.

## 4. Keep the side rail clearly secondary

The side rail should continue to hold:

- current version metadata
- version timeline
- library context

But it should remain secondary to the main reading slab. This pass should not enlarge the side rail.

## 5. Add `查看完整分析`

The approved behavior for this pass is:

- place a `查看完整分析` button inside the compact source header
- clicking it should jump to the full analysis/result workspace for the corresponding saved interpretation's job

This should feel like a natural bridge from:

- saved compact library reading

to:

- full original analysis workspace

---

## UX Rules

1. source identity should remain visible, but should not dominate reading height
2. the interpretation browser is the page's main object
3. context/version material belongs in the side rail, not the main reading flow
4. technical snapshot paths should not occupy premium height in the default reading state
5. `查看完整分析` should be easy to find without forcing users to hunt in the side rail

---

## Implementation Boundaries

Expected primary files:

- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`

Likely supporting file:

- `tests/unit/test_inline_result_view.py` only if shared behavior or helper assumptions need to be adjusted, otherwise avoid touching it

This pass should prefer:

- small structural changes inside `LibraryDialog`
- one or two new signals for opening the full analysis workspace
- limited stylesheet updates if needed to support the denser source header / dominant reading slab treatment

---

## Testing and Validation

Required verification strategy:

1. add a failing test for the `查看完整分析` entry action signal
2. add failing structural tests for the compact source header if a new hook/object name is introduced
3. run the existing library-dialog and main-window GUI suites
4. manually verify that a library entry is now denser and easier to read

Manual acceptance should focus on:

- source header no longer wasting vertical space
- interpretation browser now being obviously readable
- reduced empty space below the reading area
- `查看完整分析` being discoverable and functional

---

## Acceptance Criteria

This pass is successful when:

1. `来源信息` becomes a compact source header rather than a large metadata card
2. `当前解读` feels like the main reading surface
3. the page no longer shows an obviously wasteful empty region beneath the reading area
4. a user can click `查看完整分析` from a library entry and jump to the full result workspace
5. restore and current-version behaviors remain unchanged
