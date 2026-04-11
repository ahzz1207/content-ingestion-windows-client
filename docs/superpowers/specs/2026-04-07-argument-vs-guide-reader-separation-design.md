# Argument vs Guide Reader Separation Design

**Date:** 2026-04-07  
**Status:** approved direction  
**Scope:** make `argument` and `guide` reinterpretation results feel like two different reading products instead of one shared template with light copy variation.

---

## Problem

The current reinterpretation fix makes `argument` and `guide` produce different output text, but the user experience still reads as the same product with minor content edits.

Current failure mode:

- `argument` and `guide` both render through nearly the same `product_view` section grammar
- GUI rendering uses the same visual container logic for both modes
- the visible difference is mostly point count and wording

This is not enough.

The product requirement for this round is stronger:

- different templates must imply different reading goals
- different reading goals must produce different result structure
- different result structures must produce different visual guidance
- users should be able to tell the difference at a glance before reading deeply

---

## Product Goal

For the same article, switching between `深度分析` and `要点提炼` should produce outputs that differ across all of the following dimensions:

- summary length
- section count
- section semantics
- information density
- reading rhythm
- visual hierarchy

Success means the user can immediately perceive:

- `argument` is a deeper analytical brief
- `guide` is a compressed extraction product

Failure means the result still feels like the same page with slightly rewritten paragraphs.

---

## Design Principles

1. WSL still owns structure and meaning.
2. GUI must not infer analytical shape from legacy fields.
3. Mode separation must be visible in both content and layout.
4. `guide` should remove information, not just rename sections.
5. `argument` should justify and unpack, not just summarize longer.

---

## Mode Definitions

### `argument` / 深度分析

Primary user job:

- understand the article's main claim
- see how the argument is built
- identify supporting evidence
- notice tensions, uncertainty, and weak spots

Required output character:

- analytical
- more complete
- explicitly structured
- comfortable with moderate reading length

Required hero behavior:

- allow 2-4 sentences across title/dek/bottom-line content
- prioritize framing, stance, and what is at stake

Required body shape:

- `核心判断`
- `主要论点`
- `关键论据`
- `张力与漏洞`
- `验证与保留意见` when available

Required visual feel:

- briefing-like
- strong section boundaries
- more cards and labeled groups
- evidence-oriented emphasis

### `guide` / 要点提炼

Primary user job:

- finish quickly
- retain only the highest-value information
- leave with a small number of memorable conclusions

Required output character:

- short
- compressed
- high-density
- low rhetorical overhead

Required hero behavior:

- extremely short
- 1-2 sentences total feel
- conclusion first, context second

Required body shape:

- `一句话总结`
- `核心要点` with 3-5 items max
- optional `记住这件事`

Explicitly disallowed in guide output for this phase:

- long supporting evidence sections
- many secondary subpoints
- verification-heavy diagnostic blocks
- argument scaffolding that slows reading

Required visual feel:

- compact
- fewer sections
- tighter spacing
- scan-first hierarchy

---

## WSL Contract Changes

The current `ProductView` model is too thin for this separation because it only exposes:

- `layout`
- `template`
- `title`
- `dek`
- `sections`

This round should keep the existing model shape for compatibility but strengthen the payload conventions.

### `argument` payload conventions

`argument` product views should:

- keep `layout="analysis_brief"`
- emit 4-5 sections in stable analytical order
- prefer section kinds such as:
  - `core_judgment`
  - `main_arguments`
  - `evidence`
  - `tensions`
  - `verification`
- use richer `items` payloads with title/body semantics

### `guide` payload conventions

`guide` product views should:

- keep `layout="practical_guide"` or a tighter guide-family layout already accepted by the GUI
- emit only 2-3 sections in stable compression order
- prefer section kinds such as:
  - `one_line_summary`
  - `core_takeaways`
  - `remember_this`
- cap takeaways at 3-5 items even if more source points exist
- trim explanatory detail aggressively

### Routing policy for this round

For generic routes:

- `argument.generic` should still render as a full analytical brief
- `guide.generic` should no longer behave like a reduced tutorial page; it should behave like a distilled extraction page

This is important because the current user complaint is about guide reinterpretation on normal article content, not only game tutorials.

---

## GUI Rendering Changes

The GUI currently renders most `product_view` results through a shared generic section renderer.

That renderer should remain as fallback, but this round needs explicit mode-aware rendering branches.

### `argument` rendering family

Expected treatment:

- larger hero block
- more breathing room between sections
- section headings that feel like analysis labels
- card-style groups for arguments and evidence
- warnings and verification remain visible

### `guide` rendering family

Expected treatment:

- smaller, denser hero block
- fewer visible sections
- bullet-first presentation
- much tighter rhythm
- emphasis on scanability over completeness

### Fallback rule

If the GUI cannot recognize a richer mode-specific section shape, it may fall back to the current generic block renderer.

But recognized `argument.generic` and `guide.generic` outputs should take the specialized path.

---

## Acceptance Criteria

For the same article:

1. `深度分析` visibly produces more sections than `要点提炼`.
2. `深度分析` shows argument/evidence/tension style structure.
3. `要点提炼` shows a short summary plus a small set of dense takeaways.
4. `要点提炼` does not expose long evidence scaffolding by default.
5. The two modes look different on first screen, not only after careful reading.

---

## Risks

### Risk 1: guide becomes too empty

If compression is too aggressive, `guide` may feel shallow.

Guardrail:

- require 3-5 strong takeaways when the source supports them
- keep one optional memorable closing block

### Risk 2: argument becomes verbose sludge

If we only add more text, the output becomes longer without becoming more analytical.

Guardrail:

- require section-level role separation
- force distinction between arguments, evidence, and tensions

### Risk 3: GUI and WSL diverge again

If GUI starts reconstructing missing semantics, mode separation will decay.

Guardrail:

- WSL emits stable section kinds
- GUI branches on explicit layout and section-kind cues

---

## This Round's Boundary

This round intentionally does not redesign `review`.

The goal is to make `argument` and `guide` clearly different first, validate the experience, and only then propagate the same standard to other reading goals.
