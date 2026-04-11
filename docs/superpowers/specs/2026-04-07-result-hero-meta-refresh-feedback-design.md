# Result Hero, Meta, And Refresh Feedback Design

**Date:** 2026-04-07  
**Status:** draft for review  
**Scope:** refine the result page so the first screen has cleaner hero hierarchy, clearer template/domain identity, and stronger reinterpret/reanalysis completion feedback.

---

## Problem

The current result page has three usability issues:

1. The hero repeats the same summary twice.
2. The current result identity is not obvious enough.
3. Reinterpretation completion feedback is too weak.

From the user's feedback:

- the large hero text and the smaller text below it are effectively the same content
- the hero typography feels too heavy and visually awkward
- users should see the current template and inferred domain near the source/author area
- when reinterpretation finishes and the result auto-refreshes, users may not notice that anything changed

This is a first-screen product issue, not a backend or data issue.

---

## Goal

Make the result page first screen feel cleaner, more informative, and more responsive to reinterpretation updates.

Success criteria:

- the hero no longer repeats the same text twice
- current template and inferred domain are visible near source metadata
- reinterpretation completion becomes obvious without using a blocking modal

---

## Chosen Approach

Use the minimal integrated UI refinement approach:

1. simplify the hero block
2. elevate result identity metadata
3. add an in-page completion banner

This keeps the current screen structure intact while fixing the most visible UX issues.

---

## Design

### 1. Hero Simplification

Current issue:

- the title-sized block and the smaller block below it communicate the same summary twice

Required change:

- keep a single hero headline only
- remove the repeated secondary summary when it duplicates the headline
- reserve the smaller line area for true metadata, not repeated copy

Typography adjustments:

- reduce title visual weight slightly
- tighten line-height so long Chinese headlines feel less bloated
- keep the headline prominent, but not oversized and overwhelming

Behavior rule:

- if a secondary line is meaningfully different, it may remain
- if it is just a duplicate or near-duplicate of the title, hide it

### 2. Result Identity Metadata

Current issue:

- the user cannot immediately tell what reading template and inferred domain they are viewing

Required change:

- place result identity pills near author/time/source metadata
- show at least these two pills:
  - current template label
  - inferred domain label

Expected placement:

- near author/source/time metadata in the hero area
- not buried lower in the page

Visual treatment:

- template pill uses stronger emphasis
- domain pill uses softer secondary emphasis

Content rules:

- template label should use user-facing Chinese naming
- domain label should prefer user-friendly naming when available
- if no domain is resolved, show a stable fallback such as `通用` rather than raw emptiness

### 3. In-Page Completion Banner

Current issue:

- reinterpretation finishes and auto-refreshes the page, but the user can easily miss it

Required change:

- show a clear in-page banner near the top of the result page after reinterpretation or reanalysis completes
- banner should not block interaction
- banner should be dismissible or auto-fade after a short period

Banner content:

- communicate that the result has been updated
- include current template and domain if available

Example:

- `结果已更新：要点提炼 · 宏观商业`

Behavior:

- display immediately after the new result loads
- remain visible long enough to be noticed
- avoid modal dialogs or system-notification dependency

---

## Implementation Boundaries

This round should only touch the first-screen experience.

Included:

- hero content deduplication
- hero typography refinement
- template/domain pill placement in the hero metadata area
- in-page success banner after reinterpret/reanalysis completion

Not included:

- major page layout redesign
- changes to WSL routing semantics
- changes to product-view structural generation
- notification systems outside the current window

---

## Files Likely To Change

- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/gui/result_renderer.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_result_renderer.py`

---

## Risks And Guardrails

### Risk: hiding useful secondary text

Guardrail:

- only suppress the smaller hero line when it is duplicate or near-duplicate of the headline

### Risk: metadata pills become noisy

Guardrail:

- limit first-screen identity pills to template and domain
- keep author/source/time as plain metadata text

### Risk: completion banner becomes visual spam

Guardrail:

- only show banner for explicit refresh-producing actions such as reinterpretation/reanalysis completion
- do not show it on every ordinary page render

---

## Acceptance Criteria

1. The result hero no longer shows the same summary twice.
2. The first screen clearly shows current template and inferred domain.
3. Reinterpretation completion produces a visible in-page reminder.
4. The reminder does not interrupt the user with a modal dialog.
5. The page feels visually cleaner than the current implementation.
