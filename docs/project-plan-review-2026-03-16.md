# Review of PROJECT_PLAN.md and visual-design-spec.md - 2026-03-16

## 1. Purpose

This document reviews two newly added upstream planning documents:

- `PROJECT_PLAN.md`
- `docs/visual-design-spec.md`

The goal is not to reject them.
The goal is to:

- preserve their strongest product ideas
- identify where they conflict with the current repositories
- convert them into an implementation-safe direction

Important note:

- the local repository could not be updated through `git pull` during this review because GitHub connectivity failed twice from this environment
- the two documents were reviewed directly from the current GitHub remote content

---

## 2. Overall Assessment

Both documents are directionally strong.

`PROJECT_PLAN.md` is strong on:

- product ambition
- architectural long view
- Obsidian as a real destination rather than an afterthought
- clear module thinking

`visual-design-spec.md` is strong on:

- product identity
- visual coherence
- component-level design specificity
- raising the GUI bar well above the current utility-shell aesthetic

The problem is not that these documents are wrong.
The problem is that they currently mix:

- valid long-term direction
- outdated assumptions about current code state
- one major unstated technology pivot

They need a review layer before they can safely drive implementation.

---

## 3. Findings On PROJECT_PLAN.md

### 3.1 Strong Product Reframe

This is the document's biggest success.

It correctly repositions the system as:

- a personal knowledge pipeline

rather than:

- a Windows capture demo

This should be kept.

### 3.2 Obsidian Placement Is Correct

Treating Obsidian as the durable downstream knowledge workspace is a good decision.

The proposed split between:

- source archive
- processed note
- attachments

is consistent with the way this project already separates:

- payload
- normalized content
- structured output

This should be kept and implemented early.

### 3.3 Service Direction Is Reasonable But Premature As A Phase-1 Driver

The FastAPI direction is technically sound.

However, the current repositories are only recently in a stable local roundtrip state.
If service migration becomes the immediate center of gravity, the project risks destabilizing:

- transport
- GUI integration
- progress reporting
- operational debugging

Recommended correction:

- first define stable internal contracts
- migrate transport after the contracts are proven

### 3.4 Phase 1 Contains Outdated Bug Assumptions

This is the biggest operational flaw in the document.

The current Phase 1 still includes items such as:

- fixing broad WSL syntax errors
- fixing `_image_data_url` because of a missing `data:` prefix

Those do not match the current verified codebase.

Impact:

- engineers following the document would spend time chasing bugs that are already disproven
- the true priority order becomes blurred

Recommended correction:

- replace the current Phase 1 with the executable plan in `docs/executable-plan-2026-03-16.md`

### 3.5 The Audio / Transcription Strategy Is Useful But Not Properly Integrated

The WhisperX / AssemblyAI section is interesting and worth keeping.

Current issue:

- it appears appended rather than integrated into the main architecture and phase model

Recommended correction:

- promote it into a formal media-processing section
- define one normalized transcript schema
- keep provider choice downstream of that schema

### 3.6 BeautifulSoup Is A Good Direction But Not A Frontline Milestone

Moving away from regex-heavy HTML parsing is sensible.

But it should not be bundled into the same immediate batch as:

- service migration
- Obsidian writer introduction
- GUI modernization

Recommended correction:

- treat parser hardening as a targeted improvement track, not the first top-level milestone

---

## 4. Findings On visual-design-spec.md

### 4.1 The Product Identity Is Strong

This document is much sharper than the earlier GUI docs in one important way:

- it knows what the product should feel like

The "knowledge instrument" framing is strong and should be preserved.

The strongest parts are:

- the emphasis on density without clutter
- command-first interaction
- terminal influence without becoming retro cosplay
- attention to token-level design detail

### 4.2 The Design Language Is Better Than The Current GUI

The current `PySide6` GUI is functional but still conservative.
This visual spec provides a much stronger north star.

The following parts should be adopted regardless of framework:

- stronger typography hierarchy
- clearer component tokenization
- explicit motion system
- better status and progress semantics
- more intentional information density

### 4.3 The Stack Assumption Is The Document's Largest Conflict

The design spec is written for:

- `Tauri v2 + React + TailwindCSS`

The current application is:

- `PySide6`

This is not a styling tweak.
It is a full GUI technology fork.

Impact:

- if followed literally, the team would stop iterating on the existing app and start a rewrite
- the repository does not yet have the architectural stability to justify that move

Recommended correction:

- treat the visual spec as a design-language document, not a mandatory framework decision
- preserve `PySide6` as the mainline implementation path for now

### 4.4 The "Dark Theme Only" Rule Should Be Softened

The dark-only stance is coherent with the proposed identity.

But it is worth treating as:

- primary shipping theme

instead of:

- permanent hard rule

Reason:

- the product may later need a reading-heavy or publish-adjacent mode where a lighter theme is useful

Recommended correction:

- ship a dark-first identity
- keep the token system adaptable enough that a second theme remains possible later

### 4.5 The Visual Spec Needs A Repository-Aware Translation Layer

The document describes:

- tokens
- layout
- animation
- component catalog

What it does not yet describe is:

- how those ideas map onto the current Python desktop widget tree

Recommended correction:

- add a small implementation appendix for `PySide6`
- specify which current screens become which component modules

---

## 5. Main Conflicts Between The Two Documents And The Current Repo

### Conflict 1: Current-Code Accuracy

`PROJECT_PLAN.md` assumes some critical fixes that are no longer real.

Resolution:

- use the review follow-up as the source of truth for current code state

### Conflict 2: GUI Technology Path

`visual-design-spec.md` assumes a new frontend stack that the current repo does not use.

Resolution:

- keep `PySide6` as mainline
- allow the visual spec to drive design, not immediate framework replacement

### Conflict 3: Scope Compression

Together, the two documents implicitly suggest doing all of the following near one another:

- stability fixes
- Obsidian writer
- parser hardening
- service migration
- transcription upgrade
- GUI reinvention

That is too much simultaneous surface area.

Resolution:

- sequence the work aggressively
- ship Obsidian value before service migration
- ship GUI reframe before any framework rewrite discussion

---

## 6. Recommended Decisions

These decisions should now be treated as working defaults.

### Decision A

Keep the local shared-inbox pipeline as the active transport until internal contracts are stable.

### Decision B

Implement Obsidian writer MVP before FastAPI migration.

### Decision C

Keep `PySide6` as the main GUI implementation path for the next milestone.

### Decision D

Use `visual-design-spec.md` as the visual and interaction source of truth, but not as an immediate stack mandate.

### Decision E

Split media-transcription strategy into its own formal architecture section and define a normalized transcript schema first.

### Decision F

Use `docs/executable-plan-2026-03-16.md` as the operative build order.

---

## 7. What Should Be Kept

The following should be kept with minimal change:

- the knowledge-pipeline framing
- Obsidian as a first-class destination
- source note plus digest note structure
- tag and related-note ambitions
- long-term FastAPI direction
- stronger GUI identity and tokenized visual system
- command-centered interaction model
- premium, editorial, knowledge-first GUI tone

---

## 8. What Should Be Changed

The following should be changed before these documents are treated as build-driving specs:

- replace outdated Phase 1 bug items in `PROJECT_PLAN.md`
- move transcription strategy into a proper architecture section
- separate parser hardening from the first major milestone
- remove the implied requirement that the GUI must immediately switch to Tauri
- add a `PySide6` translation layer for the visual system

---

## 9. Working Conclusion

These two documents are valuable.
They should not be discarded.

Their best contribution is:

- giving the project a stronger product identity and a clearer long-term destination

Their main current weakness is:

- insufficient alignment with the present implementation reality

The right move is therefore:

- keep their direction
- correct their assumptions
- execute them through a narrower and safer build order

That narrower and safer build order is captured in:

- `docs/executable-plan-2026-03-16.md`
