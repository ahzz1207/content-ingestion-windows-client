# GUI Closeout 2026-03-14

## Purpose

This document marks the current stopping point for the Windows GUI before the next cross-repo verification pass.

It is meant to answer:

- what the GUI now does reliably
- what should be treated as frozen for now
- what should be validated against the WSL side next

---

## Current GUI Baseline

The current GUI now reliably covers:

- single URL entry
- automatic route selection for known platforms and generic URLs
- browser login guidance for browser-first routes
- coarse Windows-side progress stages
- Windows export success and failure presentation
- current-job result checking against the shared inbox
- short-lived automatic WSL result polling after a successful export
- WSL watcher visibility through the environment pills
- recent result browsing across `incoming`, `processing`, `processed`, and `failed`
- a result-reading surface that prioritizes title, origin, byline, and preview
- collapsed metadata and open-file actions for deeper inspection

This is sufficient to treat the GUI as the current product-facing baseline.

---

## Frozen GUI Boundary

The following parts should now be treated as intentionally frozen unless a concrete issue is found:

- the single-window information architecture
- the current URL-first interaction model
- the current result-workspace scope
- refresh throttling behavior
- the current "reading surface first, metadata second" result layout

What should not be expanded right now:

- settings
- history management beyond the recent list
- search and filtering
- batch or queue workflows
- attachment browsing
- real-time WSL event streaming inside the GUI

---

## Why This Is A Good Stop Point

The GUI is no longer just a launcher.

It now provides:

- a stable export entry
- a stable result entry
- a stable bridge into WSL outputs

That is enough value to pause GUI expansion and switch attention back to end-to-end behavior.

---

## Next Verification Focus

The next useful step is not more GUI surface area.

The next step is to verify the current GUI baseline against the full Windows -> WSL chain:

- Windows export still writes the expected shared-inbox contract
- WSL still consumes the same contract cleanly
- processed outputs still match what the GUI expects to render
- the recent-result workspace reflects real WSL states correctly

---

## Decision

The Windows GUI can now be treated as "feature-converged for Phase 1.5".

From this point, changes should default to:

- bug fixes
- visual polish
- contract alignment with WSL outputs

not broader GUI feature growth.
