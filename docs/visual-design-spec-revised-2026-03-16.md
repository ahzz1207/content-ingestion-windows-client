# Revised Visual Design Spec - 2026-03-16

## 1. Purpose

This document revises the new `docs/visual-design-spec.md` into a version that fits the current repository and implementation path.

It keeps the strongest parts of the original spec:

- the product identity
- the premium, editorial, terminal-adjacent mood
- the tokenized visual system
- the command-first interaction model

It changes one major assumption:

- this revised spec is implementation-aware for the current `PySide6` application
- it does not assume an immediate migration to `Tauri + React + Tailwind`

---

## 2. Design Identity

The GUI should feel like:

- a knowledge instrument

The interface should sit between:

- a developer tool
- a reading tool
- a high-trust intelligence workspace

The correct emotional qualities are:

- calm
- dense
- exact
- contemporary
- premium

The GUI should not feel like:

- a generic enterprise dashboard
- a form-heavy desktop utility
- a decorative AI toy

---

## 3. Visual Strategy

### Theme Direction

Ship a dark-first theme.

Recommended position:

- dark is the primary identity
- the token system should still allow a later secondary theme

This keeps the visual signature strong without locking the product into a permanent one-theme future.

### Aesthetic Tone

The product should feel like:

- terminal precision plus editorial reading quality

That means:

- restrained glow
- sharp layout rhythm
- strong mono plus sans pairing
- occasional serif-style emphasis in result display if the chosen toolkit supports it cleanly

---

## 4. Framework-Aware Design Rule

The current implementation path is:

- `PySide6`

Therefore this spec must optimize for:

- reusable Qt widgets
- token-driven stylesheets
- structured screen components
- low-risk desktop rendering

It must not assume:

- browser-only effects that are impractical in Qt
- framework-specific Tailwind utility composition
- web-only motion behavior as a requirement for shipping

---

## 5. Primary User Flows

The GUI should center on four flows.

### Flow A: Ingest

The user pastes a URL and starts processing.

### Flow B: Observe

The user understands what the system is doing and why it is waiting.

### Flow C: Read

The user consumes the processed result as a concise intelligence brief.

### Flow D: Promote

The user moves the result into a knowledge workflow:

- open in Obsidian
- reveal in vault
- create topic note later
- compare later

---

## 6. Screen Model

### Ready Screen

Required elements:

- command-ribbon URL surface
- one dominant action
- environment rail
- a small recent-intelligence strip

Design goal:

- the app should feel alive before the user starts a task

### Progress Screen

Required elements:

- strong current-stage headline
- compact pipeline or stage rail
- detected platform and domain capsule
- optional evidence preview area when available

Design goal:

- the user should feel that a disciplined system is working, not that a modal spinner is blocking

### Result Screen

Required elements:

- result hero section
- summary lead
- key point cards
- verification band
- warnings area when present
- knowledge action cluster

Design goal:

- the processed result becomes the star of the interface

### Workspace Screen

Required elements:

- left navigation rail
- central reading pane
- right metadata and action pane

Design goal:

- the workspace becomes a lightweight intelligence desk rather than a file browser

---

## 7. Component Model For PySide6

The current oversized `main_window.py` should be broken down around these components:

- `CommandRibbon`
- `EnvironmentRail`
- `StageRail`
- `ResultHero`
- `VerificationBand`
- `EvidenceStrip`
- `ActionCluster`
- `ResultListRail`
- `MetadataPane`

Recommended screen modules:

- `ready_view.py`
- `progress_view.py`
- `result_view.py`
- `workspace_view.py`

Recommended support modules:

- `design_tokens.py`
- `styles.py`
- `icons.py`

This translation layer is necessary before the visual design can be applied cleanly.

---

## 8. Token System

The original spec's token approach is correct and should be preserved.

Required token groups:

- color
- typography
- spacing
- radius
- elevation
- motion

Implementation rule:

- the token system should be defined once and consumed by the whole widget tree
- repeated inline stylesheet blocks should be reduced over time

---

## 9. Typography

Recommended practical direction for the current desktop app:

- sans for interface chrome
- mono for identifiers, URLs, logs, and status details
- a restrained high-contrast display style for result headlines

The next milestone should prioritize:

- stronger hierarchy
- more consistent mono usage
- clearer result headline treatment

It does not need to solve every font-packaging decision immediately.

---

## 10. Motion

Motion should remain:

- meaningful
- restrained
- consistent

Recommended for the next PySide6 milestone:

- subtle screen crossfades
- staged result-section reveal
- hover lift on interactive cards
- pulse on active processing state

Avoid:

- motion that depends on heavy custom scene rendering
- decorative looping animations
- transitions that create lag or input ambiguity

---

## 11. Information Hierarchy

The GUI should use this default reading order:

1. result title
2. summary
3. verification or trust signal
4. key points
5. warnings or disagreement
6. metadata
7. raw details

This rule should shape the next result-screen rewrite.

The interface should never make technical details visually heavier than the user-facing result.

---

## 12. What To Keep From The Original Spec

Keep with little change:

- command-centered interaction
- dark-first identity
- terminal and editorial hybrid tone
- tokenized color and spacing system
- strong icon consistency
- explicit motion rules
- status colors and progress semantics

---

## 13. What To Change From The Original Spec

Change before implementation:

- remove the assumption that the next milestone uses Tauri
- add explicit PySide6 component mapping
- soften the dark-only rule into dark-first
- prioritize result and knowledge actions over visual novelty
- avoid web-first effect expectations that do not translate well to Qt

---

## 14. Immediate GUI Build Order

The next GUI batch should be:

1. refactor the current window into component and screen modules
2. add a centralized token and style layer
3. implement the command ribbon
4. rebuild the result screen around result hero, verification, and action cluster
5. upgrade the workspace layout into a clearer three-zone reading model

This sequence will produce a visibly better interface without requiring a framework restart.

---

## 15. Working Conclusion

The original visual design spec is valuable as a design-language document.
It should guide the look and behavior of the application.

The current repository should implement that direction through:

- `PySide6`
- component refactoring
- tokenization
- result-first layout

not through an immediate framework rewrite.
