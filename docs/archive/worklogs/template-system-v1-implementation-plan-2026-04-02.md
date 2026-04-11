# Template System v1 Implementation Plan

**Date:** 2026-04-02  
**Status:** planning draft  
**Scope:** introduce a small, user-selectable analysis template system for URL submission, backed by a shared editorial contract and mode-specific WSL synthesis behavior

---

## Why This Exists

The processor now has stronger structural understanding, but it still risks treating very different content types as if they all deserve the same analysis style.

That is not always desirable.

Examples:

- a macro commentary video often benefits from thesis, evidence, tension, and uncertainty extraction
- a game guide is more useful when turned into steps, tips, and pitfalls
- an album or exhibition recommendation is more useful when framed as highlights, tone, and audience fit

At the same time, a fully automatic taxonomy is not enough on its own.

When users submit a URL, they often already know what kind of reading output they want. The system should therefore support:

- automatic routing by default
- user-specified analysis templates when the user already knows the intended reading goal

This plan defines a v1 that is intentionally small, maintainable, and easy to validate.

---

## Product Goal

Template System v1 should let the user choose how the content should be read, without forcing them to understand internal taxonomy names.

The user-facing goal is:

- give the system a URL
- optionally choose what kind of output they want
- receive a result that clearly reflects that choice

The engineering goal is:

- keep one shared editorial backbone
- allow a few mode-specific sections
- avoid fragmenting the processor into many unrelated pipelines

---

## v1 Scope

### User-Facing Template Options

Template System v1 exposes exactly four choices in URL-submission surfaces:

- `Auto`
- `深度分析`
- `实用提炼`
- `推荐/导览`

### Internal Mapping

- `Auto` -> classifier chooses `resolved_mode`
- `深度分析` -> `argument`
- `实用提炼` -> `guide`
- `推荐/导览` -> `review`

### Explicit Non-Goals for v1

Do not expose the following yet:

- `informational`
- `narrative`
- many fine-grained sub-templates
- source-specific template catalogs
- user-managed template libraries

These may be added later, but not in v1.

---

## Core Design Principles

- Few visible choices: the user should not face a long template menu.
- Shared editorial spine: all modes should write into one common editorial contract.
- Mode-specific depth: only some sections vary by mode.
- Auto first, override second: the system still works when the user does nothing.
- Reading goals over technical labels: UI should expose user intent, not internal taxonomy terms.
- Expand later, not now: the architecture should support more templates in the future, but the UI should remain intentionally small in v1.

---

## Contract Design

### New Top-Level Mode Fields

All processed results should carry:

- `requested_mode`
- `resolved_mode`
- `mode_confidence`

Definitions:

- `requested_mode`
  - what the user asked for at submission time
  - expected values in v1:
    - `auto`
    - `argument`
    - `guide`
    - `review`
- `resolved_mode`
  - the mode actually used by the processor
  - if `requested_mode != auto`, this should normally equal `requested_mode`
  - if `requested_mode == auto`, this is chosen by classifier / routing logic
- `mode_confidence`
  - confidence in the resolved mode
  - most useful when `requested_mode == auto`

### Routing Rules

1. If the user explicitly selects a template, the processor should honor it.
2. If the user selects `Auto`, the processor should infer the best mode.
3. The result should always record both the request and the final resolution.

This is important for:

- debugging routing behavior
- client display
- future re-analysis / rerun options

---

## Editorial Schema v1

Template System v1 depends on a shared editorial schema with mode-specific extensions.

### Shared Base Fields

All modes should provide the following shared base fields:

- `analysis_mode`
- `mode_confidence`
- `core_summary`
- `bottom_line`
- `content_kind`
- `author_stance`
- `audience_fit`
- `save_worthy_points`
- `coverage_signal`
- `visual_contribution`

Purpose of the shared base:

- let GUI, API, browser extensions, and Obsidian consume a stable minimum result shape
- avoid making every client branch hard on template-specific fields

### Mode-Specific Fields

#### Argument Mode

For `argument`, the editorial result should emphasize:

- `author_thesis`
- `argument_map`
- `evidence_backed_points`
- `interpretive_points`
- `what_is_new`
- `tensions`
- `uncertainties`

#### Guide Mode

For `guide`, the editorial result should emphasize:

- `goal`
- `recommended_steps`
- `tips`
- `pitfalls`
- `prerequisites`
- `quick_win`
- `decision_shortcuts`

#### Review Mode

For `review`, the editorial result should emphasize:

- `overall_judgment`
- `highlights`
- `style_and_mood`
- `what_stands_out`
- `who_it_is_for`
- `reservation_points`

### Important Boundary

These mode-specific sections should not become three fully separate result systems.

The intended shape is:

- one shared editorial contract
- optional fields or sections activated by the resolved mode

---

## WSL Implementation Strategy

### Reader Pass

Reader should remain mostly shared across modes.

Reason:

- content structure detection is still useful regardless of the final reading goal
- it is cheaper and cleaner to reuse one structure pass than to fork three unrelated readers

Reader continues to produce:

- chapter map
- argument skeleton
- content signals
- structural thesis

### Synthesizer Pass

Synthesizer becomes mode-aware.

This is where v1 should branch.

The synthesizer should:

- receive the shared Reader output
- receive `requested_mode` and `resolved_mode`
- use mode-specific instructions and output sections

This yields three synthesizer variants in practice:

- `argument` synthesizer
- `guide` synthesizer
- `review` synthesizer

The critique pass and future visual map work remain out of scope for this v1 template rollout.

### Artifact Expectations

At minimum, the WSL processor should write mode information into:

- `analysis_result.json`
- `normalized.json`
- any downstream structured result object consumed by Windows clients

The final contract should allow clients to know:

- what the user asked for
- what the processor decided to do
- which sections should be emphasized

---

## Windows-Side Surface Changes

### URL Submission UI

The following surfaces should expose a template selector:

- Windows GUI URL submit flow
- browser extension manual submit flow
- Obsidian manual submit flow

Each should use the same compact set of user-facing choices:

- `Auto`
- `深度分析`
- `实用提炼`
- `推荐/导览`

### UI Labeling Rule

The UI should expose reading goals, not internal mode names.

Do not show:

- `argument`
- `guide`
- `review`

Instead show:

- `深度分析`
- `实用提炼`
- `推荐/导览`

### Result Display

Result consumers should eventually surface:

- requested mode
- resolved mode

But this should be lightweight, for example:

- a small template pill
- an optional tooltip or secondary line

v1 should not add heavy template-management UI.

---

## Insight Card Implications

Template System v1 does not yet require a full visual template engine rollout.

However, it should prepare for one.

The intended future model is:

- editorial result first
- card sections selected from editorial result
- card layout chosen based on resolved mode

For v1, the main requirement is:

- results must be mode-distinguishable in content
- the card layer can stay relatively simple until the editorial contract stabilizes

This avoids making visual rendering the primary driver of analysis structure.

---

## Implementation Batches

### Batch T1: Contract + Schema

Goal:

- define the editorial contract and mode-routing fields before changing UI or prompts deeply

Tasks:

- define `requested_mode`, `resolved_mode`, `mode_confidence`
- formalize shared editorial fields
- formalize mode-specific fields for `argument`, `guide`, `review`
- document routing rules

### Batch T2: WSL Routing + Mode-Aware Synthesis

Goal:

- make the processor honor explicit user template choices and support auto-routing

Tasks:

- extend handoff / metadata to carry `requested_mode`
- add lightweight mode resolver
- keep Reader shared
- make Synthesizer mode-aware
- write mode fields into result artifacts

### Batch T3: Windows Entry Surfaces

Goal:

- allow the user to select a reading goal when submitting a URL

Tasks:

- add template selector to GUI submit page
- add template selector to browser submit UI
- add template selector to Obsidian submit UI
- propagate field through API

### Batch T4: Presentation Refinement

Goal:

- reflect template choice in result emphasis

Tasks:

- show resolved mode in result surfaces
- emphasize different sections in GUI / Obsidian based on mode
- optionally introduce simple mode-aware card section presets

---

## Acceptance Criteria

Template System v1 is successful when all of the following are true:

- a user can submit a URL without choosing a template
- a user can explicitly choose one of the three visible templates
- the processor records both `requested_mode` and `resolved_mode`
- `argument`, `guide`, and `review` outputs are materially different in structure, not just renamed summaries
- clients can surface the chosen/resolved mode without overwhelming the UI
- the shared editorial contract remains stable enough for GUI, API, browser extensions, and Obsidian to consume

---

## Expansion Rules

This system should be designed for future growth, but growth should be governed.

Before adding a new template, require all three of the following:

1. It serves a real and recurring user need.
2. Its output differs substantially from existing templates.
3. It needs genuinely different editorial sections, not only different wording.

If these conditions are not met, do not add the template.

This keeps the system powerful without letting it become a template explosion.

---

## Recommended v1 Decision

The recommended v1 posture is:

- architect for many templates later
- expose only a few templates now

In product terms:

- broad capability underneath
- disciplined choice surface on top

This gives the project a stable next step without prematurely overfitting the UI or the processor to a large template catalog.
