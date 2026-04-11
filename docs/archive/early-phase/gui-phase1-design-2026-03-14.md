# GUI Phase 1 Design 2026-03-14

## Purpose

This document defines the first GUI standard for the Windows client.

It is intentionally narrow.
The goal is to produce a GUI that feels modern and calm, while staying aligned with the already-verified Windows export flow.

---

## Product Goal

Phase 1 should feel like a single-purpose collector, not a parameter dashboard.

The user should be able to:

1. paste a URL
2. let the app choose the collection path automatically
3. complete browser login when required
4. understand the current stage
5. see a clear success or failure result

The GUI should not expose the CLI mental model.
Users should not need to know the difference between `export-url-job` and `export-browser-job`.

---

## Experience Principles

The intended feel is:

- modern
- quiet
- minimal
- Apple-inspired, but not a fake macOS clone
- tool-like, not dashboard-like

Phase 1 should optimize for:

- clarity over density
- one obvious action
- low cognitive load
- human-readable status
- predictable browser/login guidance

---

## Technical Direction

Recommended stack:

- `PySide6`

Reasoning:

- native Windows desktop app packaging path
- strong control over spacing, rounded corners, blur, and custom surfaces
- direct integration with the current Python service/workflow layer
- straightforward use of worker threads for blocking collection actions

Not recommended for Phase 1:

- Tauri
- Electron
- a web-first shell that introduces a separate frontend build system

Phase 1 engineering boundary:

- GUI calls `WindowsClientWorkflow`
- GUI does not parse CLI output
- GUI does not call collector or exporter internals directly

---

## Phase 1 User Model

The app should present one primary mental model:

- "Paste a URL and let the app handle the rest."

The app should own:

- platform detection
- strategy choice
- browser login prompting
- progress stage presentation

The app should not make the user choose:

- HTTP vs browser
- platform from a dropdown
- profile directory
- wait strategy
- selector strategy

Those remain internal defaults in Phase 1.

---

## Strategy Rules

Phase 1 routing should be explicit and conservative.

### Known Platforms

For known platforms, route directly to browser collection:

- `mp.weixin.qq.com` -> `wechat`
- `xiaohongshu.com` / `xhslink.com` -> `xiaohongshu`
- `youtube.com` / `youtu.be` -> `youtube`

Default behavior:

- use browser collection
- use the platform-specific profile when available
- offer login guidance when the workflow requires it

### Generic URLs

For generic URLs:

- try HTTP first
- if HTTP fails, show a clear "Retry in browser" action

Phase 1 should not silently auto-fallback from HTTP to browser.

Reasoning:

- it keeps the behavior more understandable
- it avoids surprising browser launches
- it makes error handling easier to reason about in the first GUI release

---

## Progress Model

Phase 1 should use real stage updates, not fake percentage progress.

Recommended coarse stages:

- `idle`
- `analyzing_url`
- `checking_runtime`
- `opening_browser`
- `waiting_for_login`
- `collecting`
- `exporting`
- `done`
- `failed`

UI should present these as short human labels, for example:

- `Checking link`
- `Preparing browser`
- `Waiting for login`
- `Capturing page`
- `Writing job`
- `Done`

Phase 1 should avoid:

- fake progress bars that imply numeric accuracy
- detailed live logs
- multi-step developer diagnostics in the main surface

If needed, the GUI can still render these stages as a stepper or indeterminate progress strip.

---

## Information Architecture

Phase 1 should use a single window with three top-level states.

### State A: Ready

Shown before a task starts.

Purpose:

- communicate what the app does
- show environment readiness
- make the URL input the only obvious action

### State B: In Progress

Shown while a job is being processed.

Purpose:

- show detected platform
- show current stage
- show whether browser/login action is needed

### State C: Result

Shown after success or failure.

Purpose:

- summarize the outcome
- show the next sensible action
- allow the user to go back and run another URL

The login-required case should be a modal or sheet layered on top of State B, not a separate navigation page.

---

## Window Layout

Recommended window structure:

1. top app bar
2. main content card
3. bottom status strip

### Top App Bar

Contents:

- product title
- short subtitle or one-line purpose
- optional small environment pills

Example:

- `Collect`
- `Turn a link into a processed job`

### Main Content Card

Ready state:

- large URL field
- one primary action button
- one short line explaining automatic platform detection

In-progress state:

- source domain
- detected platform label
- current stage label
- indeterminate progress treatment

Success state:

- resolved title
- author if available
- published date if available
- job output location
- actions: `Open Folder`, `Copy Job ID`, `New URL`

Failure state:

- plain-language failure summary
- suggested next action
- expandable technical details

### Bottom Status Strip

Small persistent environment pills, for example:

- `Browser ready`
- `Shared inbox ready`
- `WeChat profile available`

These should be compact and secondary, not the main focus of the interface.

---

## Wireframe

### Ready State

```text
+--------------------------------------------------------------+
| Collect                                        Browser ready |
| Turn a link into a processed job                Inbox ready  |
|                                                              |
|   +------------------------------------------------------+   |
|   | Paste a URL to get started...                        |   |
|   +------------------------------------------------------+   |
|                                                              |
|                     [ Start ]                                |
|                                                              |
|        Platform is detected automatically when possible      |
|                                                              |
|   WeChat profile ready    YouTube browser flow available     |
+--------------------------------------------------------------+
```

### In-Progress State

```text
+--------------------------------------------------------------+
| Back                                                         |
|                                                              |
| mp.weixin.qq.com                                             |
| WeChat Article                                               |
|                                                              |
| Capturing page                                               |
| [==============      ]                                       |
|                                                              |
| The browser may open if login is required.                   |
+--------------------------------------------------------------+
```

### Login Sheet

```text
+--------------------------------------------------+
| WeChat login required                            |
|                                                  |
| A browser window will open. Complete login,      |
| then return here to continue.                    |
|                                                  |
| [ Open Browser ]                 [ Cancel ]      |
+--------------------------------------------------+
```

### Success State

```text
+--------------------------------------------------------------+
| Back                                                         |
|                                                              |
| Done                                                         |
| "Example article title"                                      |
|                                                              |
| Author: Example author                                       |
| Published: 2026-03-14                                        |
| Job ID: 20260314_...                                         |
|                                                              |
| [ Open Folder ] [ Copy Job ID ] [ New URL ]                  |
+--------------------------------------------------------------+
```

### Failure State

```text
+--------------------------------------------------------------+
| Back                                                         |
|                                                              |
| Couldn't capture this page                                   |
| The site may require login or a browser-based retry.         |
|                                                              |
| [ Retry in Browser ] [ New URL ]                             |
|                                                              |
| Technical details                                            |
| error_code: http_status_error                                |
| stage: http_collect                                          |
+--------------------------------------------------------------+
```

---

## Visual Language

The visual direction should be:

- soft light surfaces
- generous spacing
- large rounded corners
- subtle depth
- restrained motion
- very limited color accents

Recommended style characteristics:

- warm or neutral light background
- one frosted or translucent main card
- soft shadows, not heavy elevation
- one accent color, likely blue-gray or muted teal
- strong typography hierarchy
- concise labels

Avoid:

- dark enterprise dashboard styling
- dense tables
- loud gradients
- multiple competing accent colors
- visible developer terminology in the primary UI

---

## Motion

Phase 1 motion should be minimal and meaningful:

- fade/slide transition between ready and in-progress state
- subtle progress pulse while collecting
- gentle sheet transition for login-required state

Avoid:

- decorative motion
- bouncing elements
- constantly moving status indicators

---

## Error Language

Primary error copy should be human-readable.

Examples:

- `This page needs a browser-based retry.`
- `Login is required before this page can be captured.`
- `The browser runtime is not ready on this machine.`

Technical details should still exist, but behind an expandable section.

The details panel can show:

- error code
- stage
- selected details from `GuiErrorState`

---

## Phase 1 Scope

### In Scope

- one URL input
- automatic platform detection
- browser login guidance
- workflow-driven success and failure states
- coarse real progress stages
- environment readiness pills
- single-task interaction model

### Explicitly Out Of Scope

- job history
- batch URLs
- WSL real-time processing tracking
- settings page
- attachment browsing
- profile management UI
- advanced debug console

---

## Workflow Layer Implications

The current `workflow.py` layer is close to sufficient, but Phase 1 GUI will benefit from one addition:

- coarse progress callbacks or stage events

Preferred direction:

- add a small optional progress callback that emits real stage transitions

Not preferred:

- simulating fake progress percentages on a timer

If the callback is deferred, the first GUI build can still ship with:

- `idle`
- `working`
- `done`
- `failed`

But the recommended target is real stage-level progress.

---

## Acceptance Standard

Phase 1 is successful if:

1. a first-time user immediately understands that they only need to paste a URL
2. a normal generic URL can be processed without exposing technical parameters
3. a login-required platform can guide the user into the browser flow clearly
4. the user can always tell what stage the app is in
5. success and failure both produce clear outcomes and next actions

---

## Recommended Next Step

Before visual implementation begins:

1. confirm `PySide6`
2. confirm the conservative routing policy
3. decide whether to add a real progress callback in `workflow/service`
4. sketch the final component list for the main window

After those four decisions, GUI implementation can start without changing the frozen export/handoff baseline.
