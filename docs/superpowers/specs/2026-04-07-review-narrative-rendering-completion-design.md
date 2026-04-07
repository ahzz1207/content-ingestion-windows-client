# Review And Narrative Rendering Completion Design

**Date:** 2026-04-07  
**Status:** approved direction  
**Scope:** complete the product loop for `推荐导览` and `叙事导读` by adding Windows-specialized rendering paths for the existing WSL `review_curation` and `narrative_digest` product views.

---

## Problem

The GUI currently exposes four reading modes:

- `深度分析`
- `要点提炼`
- `推荐导览`
- `叙事导读`

But only the first two have clearly differentiated Windows rendering paths.

Current state:

- WSL already emits dedicated `product_view` layouts for `review.generic` and `narrative.personal_narrative`
- Windows only has dedicated renderer branches for:
  - `analysis_brief`
  - `practical_guide`
- `review_curation` and `narrative_digest` currently fall back to the generic section renderer

This means the GUI promises more complete mode support than it actually delivers.

---

## Goal

Make the two remaining GUI-exposed modes feel like real reading products instead of generic fallbacks.

Success means:

- `推荐导览` looks curated and recommendation-oriented
- `叙事导读` looks story-shaped and narrative-oriented
- all four GUI-exposed modes now have dedicated product presentation logic

---

## Why This Round Is Windows-Only

WSL already provides usable specialized structures for these modes:

- `review.generic` -> `review_curation`
- `narrative.personal_narrative` -> `narrative_digest`

So the missing product loop is on the Windows side.

This round should therefore:

- keep WSL product-view generation unchanged
- add dedicated Windows rendering branches for those existing layouts

This is the smallest correct completion step.

---

## Mode Definitions

### `review` / 推荐导览

Primary job:

- tell the user whether the source is worth their attention
- show what is most valuable about it
- clarify who it is for
- preserve reservations without turning into a full analytical brief

Required feel:

- curated
- lighter than `argument`
- more evaluative than `guide`
- recommendation-forward

Expected section emphasis:

- Highlights
- Who it's for
- Reservations

### `narrative` / 叙事导读

Primary job:

- help the user follow the story/experience arc
- preserve sequence and emotional/intellectual progression
- extract themes without flattening everything into bullets

Required feel:

- story-shaped
- smoother than `argument`
- less checklist-like than `guide`
- more reflective than `review`

Expected section emphasis:

- Story beats
- Themes
- Takeaway

---

## Windows Rendering Requirements

### `review_curation`

Rendering characteristics:

- recommendation-style hero
- moderate section density
- clear emphasis on `Highlights` and `Who it's for`
- reservations visible but visually lighter than the hero judgment

### `narrative_digest`

Rendering characteristics:

- softer narrative hero
- section rhythm should feel sequential rather than diagnostic
- `Story beats` should be visually readable as beats, not generic bullets only
- `Themes` and `Takeaway` should feel reflective, not evaluative

### Fallback policy

Generic rendering remains as fallback for unknown layouts.

But these two layouts must stop falling through:

- `review_curation`
- `narrative_digest`

---

## Acceptance Criteria

1. `推荐导览` no longer renders through the generic section fallback.
2. `叙事导读` no longer renders through the generic section fallback.
3. All four GUI-visible modes now map to visibly different result-page products.
4. This round does not require changing WSL route generation or section schemas.

---

## Boundary

This round does not redesign WSL review/narrative payloads.

If later user feedback says review or narrative content structure is still too weak, that becomes a separate WSL+Windows follow-up round.
