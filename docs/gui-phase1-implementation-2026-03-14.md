# GUI Phase 1 Implementation 2026-03-14

## Purpose

This document records the first implemented GUI slice after the design and pre-GUI checkpoint were finalized.

It should be read as:

- what now exists in code
- what was intentionally kept small
- what still remains for the next GUI pass

---

## Current Implementation

The Windows repository now includes a first PySide6 desktop shell under:

- `src/windows_client/gui/app.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/gui/platform_router.py`
- `src/windows_client/gui/workers.py`

Launch command:

- `python main.py gui`
- `python main.py gui --debug-console`

Windows launch behavior:

- `python main.py gui` now detaches from the current terminal and launches the GUI with the console hidden on Windows
- `--debug-console` keeps the console attached for Qt/debug output

---

## Implemented Phase 1 Features

Current GUI behavior:

- single-window desktop shell
- one primary URL input
- a `Result Workspace` entry from the ready state
- automatic platform routing for WeChat, Xiaohongshu, YouTube, and generic URLs
- browser-first routing for known platforms
- HTTP-first routing for generic URLs
- explicit `Retry in Browser` action instead of silent HTTP -> browser fallback
- login guidance dialog for browser platforms when the expected profile directory is missing
- coarse stage display during work
- minimal success state with completion status and follow-up actions, without detailed content preview
- `Check WSL Result` and `Open Result` actions for the current job when WSL output exists
- after a successful Windows export, the GUI now briefly auto-polls WSL result state before falling back to manual checking
- a recent-results workspace dialog with a left-side result list and a right-side detail panel
- the result workspace now includes `pending`, `processing`, `processed`, and `failed` items from the shared inbox
- the result workspace supports in-dialog `Refresh` so the user can keep watching a job move through WSL states
- refresh actions are now rate-limited to once every 2 seconds so repeated clicks do not spam shared-inbox reads
- the result detail panel now prioritizes title, source, byline, and preview, while metadata is collapsed behind a secondary toggle
- processed-result preview now behaves like a short reading extract from `normalized.md`, not a raw file dump
- processed-result preview is now rendered as a reading surface, while non-processed states still fall back to raw structured details
- the recent-results list is now rendered as selectable card items instead of plain text rows, improving title and state readability
- recent-result spacing and copy have been tightened so the workspace reads more like a focused tool and less like a debug panel
- the latest visual pass shifts the GUI toward a warmer editorial look with stronger section hierarchy and less template-like symmetry
- failure state with human-readable summary and expandable technical details
- environment pills for browser readiness, inbox readiness, and profile presence
- `Back` and `New URL` return to a cleared input state

---

## Progress Model In Code

The workflow now supports coarse stage callbacks.

Stages currently emitted by the service/workflow path:

- `checking_runtime`
- `opening_browser`
- `waiting_for_login`
- `collecting`
- `exporting`

The GUI adds `analyzing_url` locally before dispatching work.

This is real stage information, not a fake numeric progress percentage.

---

## Browser Login Flow

The browser login path was extended so it can work without terminal `input()`.

Current behavior:

- CLI path still blocks on terminal confirmation as before
- GUI path passes a custom completion waiter
- the browser window stays open while the GUI dialog waits
- the user confirms completion in the GUI with `I've Logged In`

This preserves the existing browser warm-up behavior while making it usable from a desktop window.

---

## Entry Point Changes

The CLI parser now includes:

- `gui`

This command launches the PySide6 shell and keeps the rest of the CLI intact.

The project optional dependencies now also include:

- `gui = ["PySide6>=6.8,<7"]`

---

## Validation

Validated after implementation:

- Windows unit tests: `53` passed
- offscreen Qt construction smoke test: success
- `PySide6` installed successfully in the active Windows Python environment

Residual note:

- the pre-existing Windows test `ResourceWarning` for mocked sockets still appears

---

## Known Gaps

Still intentionally missing from this first GUI slice:

- real WSL processing progress tracking
- browser login freshness detection beyond profile-directory existence
- result filtering or search
- settings page
- multi-URL queue
- attachment browsing
- polished animation pass
- richer site-specific strategy tuning for Xiaohongshu and YouTube

---

## Important Behavioral Constraints

Current GUI constraints to remember:

- the GUI only wraps the Windows export flow
- it now exposes cross-repo result state by reading the shared inbox folders, but it still does not stream live WSL events
- generic URLs do not auto-open a browser on HTTP failure
- profile existence is only a heuristic for whether login guidance should be shown up front

These are deliberate scope controls, not accidental omissions.

---

## Recommended Next GUI Pass

The next most valuable GUI improvements are:

1. visual polish pass on spacing, typography, and state transitions
2. more refined progress copy and stage presentation
3. optional workflow/service progress hooks for finer browser-state visibility
4. better login-needed recovery after browser export failure
5. screenshot-based visual review and iterative UI tuning
