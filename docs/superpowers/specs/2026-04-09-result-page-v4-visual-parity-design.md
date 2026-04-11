# Result Page V4 Visual Parity Design

**Date:** 2026-04-09  
**Status:** draft for review  
**Scope:** bring the PySide result page materially closer to the approved HTML V4 reading experience without changing approved product semantics.

---

## Summary

The current PySide result page is functionally in a good place. The result hierarchy, save-to-library flow, and knowledge-loop behavior are broadly acceptable. The remaining gap is mainly visual: the live GUI still feels more like a styled desktop tool than the premium editorial reading surface shown in the approved V4 mockup.

This pass is intentionally narrower than the earlier V4 redesign. It does not revisit result semantics, library semantics, or workflow behavior. It focuses only on the **result page as a whole reading object**, with the strongest priority on recovering the missing **Hero immersion** from the HTML V4 direction.

Reference inputs:

- approved broad redesign spec: `docs/superpowers/specs/2026-04-08-gui-readability-v4-redesign-design.md`
- approved V4 mockup: `H:\demo-win\.worktrees\domain-aware-reader-v2\.superpowers\brainstorm\session-20260407-product-gap\content\gui-readability-v4.html`
- current implementation: `src/windows_client/gui/inline_result_view.py`, `src/windows_client/gui/main_window.py`, `src/windows_client/gui/result_renderer.py`

---

## Problem

The current result page now has the right bones, but it still misses the emotional and editorial quality of V4.

### 1. The hero is still a card, not an immersive first screen

The current `HeroCard` presents title, dek, byline, source link, and chips correctly, but it still reads as a regular rounded card sitting at the top of the page. In the HTML V4 direction, the hero behaves more like an integrated cover surface with depth, atmosphere, and a stronger sense of arrival.

### 2. The page still feels like stacked components instead of one reading object

Even after the earlier redesign, the PySide result page still exposes several sections as separate surfaces with similar visual treatment. This weakens the editorial rhythm. The user should feel they are moving through one calm reading stream, not browsing a collection of utility cards.

### 3. The side rail is structurally correct but visually too lightweight

The `ContextRail` now has the right role, but it still behaves more like a pale side card than the quieter, better-contained context shell shown in the V4 mockup. It needs clearer outer separation and a stronger inner-shell treatment so it reads as supporting context rather than a parallel page.

### 4. The material system is not yet coherent enough

The current GUI uses lighter colors and better typography than before, but the result page still lacks a complete V4 material language:

- the background field is not layered enough
- hero, summary, reading stream, and rail do not feel like members of one family
- radius, border strength, spacing, and surface depth are not yet disciplined enough to produce a premium reading atmosphere

---

## Goal

Turn the full result page into a calmer, more immersive, more editorial reading surface that feels recognizably closer to the approved HTML V4 template.

Success means:

1. the first screen feels more immersive and more premium than the current PySide result page
2. the hero reads as a true reading introduction rather than a header card
3. the main reading stream feels more continuous and less card-fragmented
4. the context rail feels quieter and more contained
5. the result page is visually stronger without changing approved behavior

---

## Non-Goals

- changing save / re-save / restore semantics
- redesigning the library dialog in this pass
- adding new result-page features
- moving result-page sections into a new semantic order
- replacing PySide with HTML for this iteration
- implementing expensive blur or animation systems that are fragile in Qt

---

## Chosen Direction

Use a **Hero-first visual parity pass** for the **entire result page**.

This means:

- the biggest upgrade goes into the hero and first-screen atmosphere
- the rest of the page is adjusted so it feels like the same visual system
- the result page should move closer to V4 as a whole, but without trying to reproduce every HTML detail literally

This is not a pixel-perfect port of the HTML mockup. It is a PySide-native translation of the same visual intent.

---

## Core Principles

### 1. Atmosphere before ornament

The goal is not to decorate the page with more effects. The goal is to make the page feel more settled, more premium, and more editorial. Every change should strengthen reading mood and hierarchy, not add visual noise.

### 2. One result page, one visual object

The result page should feel like one composed reading surface. Hero, summary, key points, deep reading, and context should feel related, with a stable rhythm between them.

### 3. Hero is the main visual recovery target

If only one thing becomes dramatically better in this pass, it should be the first screen. The user has explicitly prioritized recovering **Hero immersion**.

### 4. PySide should approximate V4 with realistic Qt techniques

Qt stylesheet support is not HTML/CSS. This pass should use techniques that are robust in PySide:

- layered gradients
- nested translucent shells
- better spacing and radius systems
- selective `QGraphicsDropShadowEffect` on a small number of key surfaces if needed
- careful typography and section rhythm

Avoid relying on effects that Qt stylesheets do not support reliably, such as direct HTML-style `backdrop-filter` parity.

### 5. Reading remains dominant over action chrome

The page can still expose actions clearly, but they must remain subordinate to interpretation, image summary, and long reading.

---

## Result Page Design

## Overall Surface

The result page should feel closer to an editorial canvas.

Required changes:

- strengthen the page background with a clearer cream-blue layered field
- create a stronger sense of top-screen light and atmospheric depth
- make the main reading zone feel like it sits inside a composed environment rather than on a flat app background

The background should support the hero without becoming visually theatrical or noisy.

## Hero

The hero is the highest-priority area in this pass.

Required characteristics:

- noticeably taller hero than the current implementation
- more integrated internal structure, with title, dek, metadata, source link, chips, and actions feeling like one composition
- a richer layered gradient field that recalls the V4 cream-blue atmosphere
- more negative space and stronger first-screen breathing room
- action controls kept visible but visually restrained at the upper edge

The hero should convey:

- this is a reading product
- the interpretation is the main event
- the user is entering a composed page, not a dashboard card

The hero should **not** become dark, theatrical, or poster-like. It should stay in the lighter V4 language.

## Transition from Hero to Summary

The page currently has the right macro order: hero first, then visual summary, then the deeper reading surfaces. That order remains intact.

What changes in this pass:

- the transition from hero into `视觉总结` should feel more deliberate
- the summary block should look like a continuation of the hero language, not a disconnected next card
- spacing and section-entry rhythm should make the user feel naturally guided downward

## Reading Stream

The reading stream should feel less like repeated cards and more like editorial sections on a continuous surface.

Required changes:

- reduce the sense that every section is an equally heavy card
- introduce a more consistent stream rhythm using spacing, separators, and lighter section shells
- bring numbered key-point sections closer to the V4 editorial treatment
- make the deep-reading area feel more like the page's anchor instead of one more widget

Specific intent by block:

- `作者观点` should feel like structured editorial takeaways, not a dashboard summary list
- warnings should remain visible but become calmer and more integrated
- `深度解读` should feel like the stable reading core
- the browser surface should read as a paper-like reading slab instead of a generic Qt text pane

## Context Rail

The right rail should stay present but visually quieter.

Required changes:

- make the outer rail boundary clearer relative to the main reading stream
- add a stronger inner shell treatment so the rail feels like one contained context object
- keep `视觉证据` and utility actions inside the rail, but reduce their tendency to compete with the main stream
- align spacing, radius, and surface language with the hero and reading stream

The rail should feel like a calm companion panel, not a second main column.

## Material System

This pass should establish a tighter material hierarchy for the result page.

Target system:

- large-radius immersive hero surface
- softer secondary summary shell
- lighter stream sections with restrained borders
- quiet translucent rail shell
- consistent blue-accent usage for emphasis only

Visual variables to tighten:

- radius scale
- border opacity scale
- padding rhythm
- title/dek/body spacing
- chip prominence
- warning-state integration

---

## Typography

Typography should reinforce the editorial hierarchy more clearly than the current result page.

Required changes:

- slightly stronger hero title scale and spacing
- calmer dek and metadata rhythm
- consistent distinction between UI labels and reading text
- preserve serif body treatment for long-form reading where already introduced
- avoid returning to oversized, shouty title treatment from earlier mockups

The hero should feel strong but not heavy.

---

## Implementation Boundaries

This pass should be implemented with the smallest set of structural changes that can materially improve the reading experience.

Expected primary files:

- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/gui/result_renderer.py`
- `tests/unit/test_inline_result_view.py`
- `tests/unit/test_main_window.py`
- `tests/unit/test_result_renderer.py`

Implementation should prefer:

- object-name and layout refinements inside `InlineResultView`
- Qt stylesheet updates in `MainWindow._apply_styles()`
- small renderer adjustments only where they directly support the result-page reading atmosphere

Avoid broad refactoring or unrelated cleanup in this pass.

---

## Testing and Validation

This pass is visual, but it still needs meaningful automated coverage.

Required verification strategy:

1. add structural tests for any new hero/context containers or object-name signals introduced for the V4 parity pass
2. add tests for any revised section-order or action-placement contract that becomes explicit
3. run the existing GUI unit suites to ensure no behavior regressions
4. perform manual visual comparison against the approved V4 mockup after implementation

Automated verification should prove:

- result-page behavior did not regress
- the new containers / structure expected by the visual pass are present
- renderer content still works in both rich and degraded result states

Manual acceptance should focus on:

- first-screen atmosphere
- hero immersion
- reading-flow continuity
- side-rail quietness

---

## Acceptance Criteria

This pass is successful when all of the following are true:

1. the result page first screen feels noticeably closer to HTML V4 than the current PySide implementation
2. the hero no longer reads like a plain top card
3. the result page feels more like a continuous reading object and less like a card stack
4. the context rail feels visually calmer and more contained
5. no core save / export / reinterpret / library behaviors regress
