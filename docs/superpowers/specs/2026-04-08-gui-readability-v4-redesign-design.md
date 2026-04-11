# GUI Readability V4 Redesign Design

**Date:** 2026-04-08  
**Status:** draft for review  
**Scope:** redesign the Windows result page and knowledge-library detail UI so the product feels more elegant, more readable, and more like a knowledge product than an analysis console.

---

## Summary

The current Windows GUI is functionally stronger than before, but it still feels too dense and too card-like. The result page exposes many useful elements, yet the screen reads more like a tool workspace than a refined reading surface. The knowledge-library detail page also works, but it can still feel like assembled panels rather than a coherent reading object.

This redesign keeps the product structure already approved in previous specs, but upgrades the GUI presentation with a new visual and editorial system:

- keep the source-centric library model
- keep image-first library detail
- keep result-page save-to-library as the primary product action
- redesign the reading surfaces so the user sees a continuous reading stream rather than a stack of equal-weight cards

The approved direction is the V4 mockup:

- `H:\demo-win\.worktrees\domain-aware-reader-v2\.superpowers\brainstorm\session-20260407-product-gap\content\gui-readability-v4.html`

V4 combines the best parts of the previous mockups:

- the calmer cream-and-blue palette and lighter first-screen feeling from V2
- the stronger reading structure, inline key points, and unified side context from V3
- a wider main reading column so long-form text no longer feels squeezed between the page edges and the side rail

---

## Problem

The current GUI has four design problems.

### 1. Too many same-level blocks

The result page exposes hero, image, takeaways, verification, long text, actions, and other material as a set of adjacent blocks with similar visual weight. This makes the user do too much work to decide what matters first.

### 2. The reading path is not decisive enough

The product already contains rich content, but the screen does not guide the user through a clear reading order. The user should first understand the interpretation, then choose an action, not the reverse.

### 3. The visual summary is important but still underleveraged

The image summary has very high information density and is the fastest way to communicate the current interpretation. When its area is too small, the page over-invests in title text and under-invests in the strongest summary surface.

### 4. The product still feels too much like a backend tool

The previous implementation improved functionality, but the overall feeling is still too close to an analysis dashboard. The product should feel like a knowledge-reading system with actions attached, not an action surface with reading attached.

---

## Goal

Turn the result page and knowledge-library detail page into cleaner, calmer, more editorial reading surfaces without changing the already-approved product semantics.

Success means:

1. the result page feels like one coherent reading flow
2. the visual summary is clearly large enough to carry first-screen comprehension
3. the long interpretation becomes easier to read than in the current UI
4. the side context remains useful but no longer competes with the main reading surface
5. the knowledge-library detail page feels like a retained reading object, not a metadata browser

---

## Non-Goals

- changing the source-centric library object model
- changing save / re-save / restore semantics
- redesigning ingestion, processing, or WSL pipeline flows
- introducing a brand-new navigation system for the whole app
- adding search, recommendation, folders, or tagging beyond the already-approved minimal library surface

---

## Chosen Direction

Use the approved V4 direction:

### Visual language

- soft cream-beige and pale blue palette
- subtle acrylic surfaces, but lighter and less theatrical than V3
- elegant modern sans-serif for UI and headings
- readable serif for long-form body text

### Structural language

- one continuous reading stream in the result page main surface
- a unified side rail for context instead of multiple unrelated side cards
- image-first library detail with stronger editorial rhythm

### Product tone

- calm, refined, and confident
- less dashboard-like
- less “AI output container” feeling
- more like a premium knowledge product

---

## Core Principles

### 1. Reading before tooling

The main interface should answer: “What is this interpretation saying?” before it answers: “What can I click?”

Actions remain visible, but they must not dominate the first-screen hierarchy.

### 2. One reading stream, not many competing cards

The user should move through the page in a stable order:

1. visual summary
2. title and identity
3. key points
4. long interpretation
5. supporting context

### 3. Visual summary earns more space than the title

The image summary is a high-density reading surface and should be large enough to carry real first-screen meaning. The title should still be strong, but it should not consume more attention than the summary itself.

### 4. Side context should feel unified and light

The side rail should no longer be a stack of separate big cards. It should feel like one quiet, persistent context material panel.

### 5. The library detail page is a retained reading object

The knowledge library is not just a place to inspect artifacts. It is the durable product surface for saved reading objects. The detail page should feel settled, legible, and trustworthy.

---

## Result Page Design

## Overall Structure

The result page uses two layers:

- main reading shell
- side context rail

The main reading shell is dominant and substantially wider than in the current implementation.

Recommended desktop relationship:

- wide main reading area
- narrow right context rail

The main reading column should feel comfortably editorial rather than narrow and compressed.

## Hero Area

The first screen should feel integrated rather than stacked.

Required characteristics:

- large integrated hero background / illustration area
- title positioned inside the hero region, not in a detached oversized text slab
- lighter cream-and-blue atmosphere rather than a heavy dark overlay
- compact metadata line directly below the title/dek
- restrained action strip at the top edge or upper-right area

Typography rules:

- title remains bold and prominent, but smaller than in the earlier mockups where it dominated the whole screen
- dek remains concise and easier to scan than a paragraph block
- metadata is compact and secondary

The first-screen message should be:

- image summary is the primary comprehension surface
- the title supports it
- metadata confirms identity

## Action Placement

Actions such as save, reinterpret, re-analyze, export, and open folder should remain visible but become more discreet.

Rules:

- `保存进知识库` remains the primary action
- secondary actions remain available but not visually louder than the reading content
- utility actions such as copy, export, and open folder should live in the side rail or a restrained action strip, not as a dominant bottom toolbar block

## Image Summary Section

This remains the most important block after the hero.

Required changes:

- make the visual summary area significantly larger than in earlier result-page experiments
- preserve strong image prominence without making the page feel poster-like or theatrical
- keep a short caption below it that explains why the summary exists, not just what the file is

This section should be the strongest bridge between fast understanding and deep reading.

## Key Points Section

The previous card-based 01 / 02 / 03 presentation should be retired for this redesign.

Required replacement:

- render key points as numbered inline sections within the main reading flow
- each numbered item has:
  - a compact numeric marker
  - a formatted sub-headline
  - a supporting paragraph in readable body text

Why:

- this preserves scannability
- it reduces the “panel soup” feeling
- it better matches the editorial tone of the page

## Long Interpretation Section

The long interpretation is the real reading core.

Required characteristics:

- one continuous reading column
- wider than the current GUI implementation
- serif body text for long-form readability
- modern sans-serif for labels and headings
- enough line-height to feel calm, but not so much that the page becomes floaty

Important text requirement:

- no pseudo-Chinese or corrupted placeholder copy may remain in mockups or implementation
- the production version must use real, readable Chinese text
- the opening paragraph should begin correctly, for example:
  - `这一项结果最重要的改变，是让“解读正文”重新成为页面的绝对主角...`

## Inline Figures

Charts and flow diagrams should not appear as detached side widgets.

Required behavior:

- integrate charts and flow diagrams directly into the main reading stream
- they may appear as indented editorial figures between paragraphs
- they should feel like part of the argument, not attachments

Examples:

- a bar chart explaining route efficiency
- a flowchart showing battle order or execution sequence

---

## Library Context Rail

The right rail should be reconceived as one unified contextual surface.

Recommended label:

- `Library Context`
or
- `Related Content`

This rail should contain:

- lightweight action pills or tool shortcuts
- a concise scrollable list of library entries or related entries
- a small `Version Timeline` block near the bottom

Each entry row should emphasize:

- title
- author / source
- date
- tiny route or state indicators
- whether image summary exists

This rail should not feel like a stack of chunky cards. It should feel like one calm contextual companion to the main reading flow.

---

## Knowledge Library Detail Design

The knowledge-library detail page keeps the previously approved information order:

1. image summary first
2. source second
3. long interpretation last

But the visual treatment is now refined to match the V4 system.

## Detail Hero

The image summary remains the hero of the page.

Required characteristics:

- large image-first hero surface
- lighter palette, consistent with V4 result-page direction
- route / saved-at / state metadata integrated quietly into the hero footer or hero lower area
- enough size to make the entry immediately recognizable

## Source Section

The source section should continue to act as a trustworthy anchor.

It should include:

- source title
- source URL
- platform and author
- published and captured time where available
- source snapshot references in a calm, compact layout

The source area should feel like editorial metadata, not raw file inspection.

## Interpretation Section

The current interpretation section should feel like a real retained reading object.

Required characteristics:

- full-width readable text surface
- serif body text
- fewer visible widget boundaries than in the current implementation
- strong continuity with the result-page long-reading style

## Related Content / Timeline Column

The detail page can continue to use a narrow side/context column, but it should inherit the V4 lighter treatment.

This area should hold:

- adjacent entries or related entry list
- version timeline
- restore affordance for trashed interpretations

It should feel secondary and stable, not loud.

---

## Typography

Typography is a critical part of this redesign.

### Heading / UI Typography

Use a clean modern sans-serif stack, such as:

- `Inter`
- `SF Pro Text`
- `Segoe UI`
- `PingFang SC`
- `Microsoft YaHei`
- `sans-serif`

This stack is used for:

- page titles
- section labels
- buttons
- pills
- metadata labels

### Long-Form Typography

Use a legible serif stack for interpretation body copy, such as:

- `Noto Serif SC`
- `Source Han Serif SC`
- `Songti SC`
- `STSong`
- `serif`

This stack is used for:

- long interpretation paragraphs
- numbered key-point body text
- longer source/knowledge explanatory body text when reading comfort matters more than UI sharpness

Reason:

- sans-serif headings keep the product modern
- serif body text improves long-form reading comfort and perceived editorial quality

---

## Color And Material System

The approved palette direction is closer to V2 than V3.

### Required palette feeling

- multi-tonal cream / beige neutrals
- soft pale blues
- restrained dark ink text
- only selective stronger blue accents for primary actions and route emphasis

### Material rules

- use subtle acrylic / frosted surfaces only where they help layering
- avoid heavy dark overlays or over-dramatic glass panels
- use borders, soft shadow, and tonal separation more than blur intensity

The product should feel elegant and advanced, not flashy.

---

## Responsiveness

Even though the primary target is desktop, the layout must degrade sensibly.

### Tablet width

- keep the reading flow dominant
- move the right context rail below the main reading content if necessary
- collapse side content into a lower section rather than squeezing the reading column too hard

### Narrow screens

- convert the layout into a single-column reading stream
- keep image summary first
- move context and timeline below the main reading content
- the library list should become a lighter stacked or collapsible section instead of a persistent side pane

### Important rule

- never preserve desktop three-part or two-part layout at the cost of reading comfort

---

## Performance Constraints

The redesign should not rely on unrealistic browser-only effects.

### Images

- use appropriately sized rendered assets
- prefer efficient formats such as WebP for web references or optimized raster assets where applicable
- never depend on oversize original images for hero display

### Blur / acrylic

- use blur sparingly
- provide a visual fallback through opacity, border, and shadow layering if blur is expensive or unsupported in the final GUI framework

### PySide reality check

In the Windows GUI implementation, visual references from HTML should be translated pragmatically:

- keep the visual feel
- do not insist on exact CSS-level blur behavior if native GUI rendering cost is too high
- prefer stable, lightweight approximations that preserve hierarchy and calmness

---

## Text Integrity Rules

The mockup-to-implementation path must enforce copy correctness.

Rules:

- no pseudo-Chinese, corrupted characters, or visual placeholder text in final implementation
- all long interpretation sections must use accurate Chinese copy
- empty states, banners, metadata labels, and timeline labels must also be corrected to real product copy

This is mandatory because readability is one of the primary goals of the redesign.

---

## Files Likely To Change In Implementation

- `src/windows_client/gui/inline_result_view.py`
- `src/windows_client/gui/library_panel.py`
- `src/windows_client/gui/main_window.py`
- `src/windows_client/gui/result_renderer.py`
- possibly supporting styles embedded in the Qt widget configuration within `main_window.py`
- related GUI tests under `tests/unit/`

---

## Risks And Guardrails

### Risk: the redesign becomes too decorative

Guardrail:

- reading hierarchy always wins over novelty
- the interface must remain calm and legible

### Risk: the side rail becomes another card pile

Guardrail:

- treat the rail as one contextual surface
- avoid stacking many equally loud blocks

### Risk: the reading column becomes too narrow again during implementation

Guardrail:

- explicitly preserve a wide editorial reading width
- do not let side rails steal too much horizontal space

### Risk: HTML effects cannot map cleanly to PySide

Guardrail:

- preserve layout and hierarchy first
- approximate advanced material effects rather than forcing expensive rendering tricks

---

## Acceptance Criteria

1. The result page reads as one continuous editorial surface rather than a collection of same-weight cards.
2. The visual summary occupies more meaningful first-screen area than in the current UI.
3. The title is still prominent, but no longer overwhelms the first screen.
4. The main reading column is wide enough to avoid a squeezed long-form experience.
5. The key points appear inline in the reading flow rather than as separate cards.
6. The side rail feels like unified context, not a second main surface.
7. The library detail page feels image-first, source-anchored, and interpretation-led.
8. Final implementation uses real Chinese text and a serif/sans typography split consistent with the design.
9. Tablet and narrow-screen states preserve readability rather than preserving desktop symmetry.
