# GUI Convergence Checkpoint 2026-03-14

## Purpose

This document records the current GUI boundary after the first result-workspace slice was implemented.

It answers one question:

- what is now stable enough to treat as the current GUI baseline
- what still remains intentionally outside the boundary

---

## Current Stable GUI Boundary

The Windows GUI can now be treated as stable at this level:

- one-window desktop shell
- one primary URL input
- automatic routing for WeChat, Xiaohongshu, YouTube, and generic URLs
- browser login guidance for known browser-first routes
- coarse real progress stages during Windows-side export
- Windows export success/failure presentation
- current-job WSL result checks
- a result workspace for browsing recent `incoming`, `processing`, `processed`, and `failed` jobs
- read-only result inspection with `Open Folder`, `Open JSON`, and `Open Markdown`
- refresh throttling for result polling

This is enough to support the product claim:

- the GUI is no longer only a URL submission shell
- it is now a lightweight cross-repo result browser

---

## What Is Intentionally Good Enough For Now

The following areas are not perfect, but are good enough to stop expanding before the next product step:

- result workspace uses a compact master-detail layout rather than a richer reading canvas
- result refresh is poll-based, not event-based
- current result copy is concise and operational, not editorial
- known-platform routing is heuristic and intentionally conservative
- browser profile readiness is still inferred from profile presence, not a deeper session check

These are acceptable constraints for the current boundary.

---

## What Is Still Outside The Boundary

The GUI should still avoid absorbing these concerns right now:

- real-time WSL event streaming
- persistent job history management beyond the recent result list
- result filtering, search, grouping, or tagging
- attachment browsing
- multi-URL queue management
- settings and environment editing inside the GUI
- richer site-specific browser strategy tuning
- analysis authoring, summaries, or downstream editorial workflows

If those are started too early, the GUI will sprawl before the current result-workspace shape is validated.

---

## Next Valuable Product Step

The next step should not be "more buttons".

The next step should be:

- make the right-hand result panel feel more like a reading surface than a file inspector

Concretely, that means:

- stronger hierarchy for title, source, author, and published date
- a cleaner preview block for normalized content
- a smaller and calmer technical metadata section
- clearer state styling for `pending`, `processing`, `processed`, and `failed`

This is the most valuable refinement because it improves the meaning of the result workspace without widening scope.

The current implementation has already started this shift:

- title, source, and byline now sit above the preview
- metadata is hidden behind a secondary toggle
- result-state pills are more visually distinct
- processed previews are now extracted from the leading body paragraphs of `normalized.md`
- processed previews are rendered in a calmer reading style instead of a plain raw text box
- the recent-results column now uses card-like list items rather than raw text rows
- recent-result spacing and helper copy have been tightened as a final polish pass
- the overall visual system now uses a warmer, more editorial direction instead of a generic utility look
- layout emphasis is now less centered and more editorial, with eyebrow labels and stronger section hierarchy

---

## Decision

Current GUI development can be considered converged at the "Phase 1.5 result workspace baseline".

That means:

- keep the current URL-entry and result-tracking shape
- do not expand into settings/history/queue systems yet
- focus the next pass on result-reading quality and visual refinement
