# Deep Analysis Question-Driven Output Design

**Date:** 2026-04-10  
**Status:** draft for later review  
**Scope:** improve the default deep-analysis / practical-extraction output structure so results read like clear answers to important questions rather than long, loosely structured model summaries.

---

## Summary

The next quality push should focus on prompt/output structure rather than more GUI polish.

The target shape is inspired by strong paper-summary products, but should not mechanically copy their style. The important pattern to absorb is a **question-driven reading skeleton**:

- start with a one-sentence conclusion
- organize the body into 3-5 explicit question blocks
- keep each block short and scannable
- end with a fixed "what this means for me" section

This should apply first to the default deep-analysis / practical-extraction template. It does **not** need to force the same shape onto all current modes such as guide, review, or narrative.

---

## User Direction Captured Today

The user explicitly liked this target structure:

- `top: one-sentence conclusion`
- `body: 3-5 question blocks`
- `each block: length-limited, short bullets first`
- `ending: what this means for me`

The user also ranked the desired improvements in this priority order:

1. question-driven sectioning
2. stronger conclusion / clearer final takeaway
3. shorter, less noisy expression
4. better plain-language explanation

The user also clarified an important boundary:

- this style is most suitable for `deep analysis / practical extraction`
- it should not be copied blindly into every other output mode

---

## Problem

Current outputs can still feel too much like structured model artifacts instead of polished reading products.

Even when the content is decent, the result may still suffer from one or more of these issues:

- the most important judgment is not stated immediately
- sections do not feel like answers to user-relevant questions
- outputs can become long or noisy before delivering the takeaway
- the ending does not land with enough force
- the reader may understand many facts but still not know the practical conclusion

This is a prompt/schema/output-shaping problem first, not mainly a rendering problem.

---

## Goals

The revised default deep-analysis output should:

1. let the reader understand the core conclusion within a few seconds
2. read like a sequence of answers to important questions
3. keep the body concise enough for scanning without losing substance
4. preserve evidence-grounded reasoning instead of turning into unsupported simplification
5. finish with a clear user-value conclusion instead of trailing off

---

## Non-Goals

This iteration should not:

- redesign the full GUI around a new visual concept
- force guide/review/narrative into the same template immediately
- optimize for generic social-media-style summaries
- remove evidence grounding in exchange for brevity
- introduce a second parallel result model if the existing structured pipeline can carry the change

---

## Proposed Output Skeleton

## 1. One-Sentence Conclusion

The output should begin with a direct conclusion, not background.

Requirements:

- 1-2 sentences max
- answer the main judgment first
- should be readable on its own as the result headline/dek
- should not spend the first sentence defining context unless absolutely necessary

Example intent:

- "This paper's main contribution is X, and its real significance is Y."
- "The practical takeaway is that Z works, but only under these conditions."

## 2. Three To Five Question Blocks

The body should be framed as 3-5 explicit question blocks.

Each block should:

- have a question-form title
- answer exactly one important reader question
- use 2-4 short bullets by default
- lead with the judgment, then brief support/explanation
- avoid long narrative paragraphs unless a short paragraph is truly clearer

Example question types:

- `What is the core claim or idea?`
- `Why does the author think this works?`
- `What changed compared with prior approaches?`
- `What are the real limits or costs?`
- `What should I retain from this?`

The exact questions should be content-dependent rather than rigidly fixed.

## 3. Embedded Supporting Basis

The output should stay grounded, but grounding should be woven into the question blocks rather than dumped into a detached citation pile.

This means:

- each block may include a small number of supporting bullets
- support should explain why the conclusion is credible
- evidence should stay selective and useful
- the product should still preserve detailed provenance in the underlying structure where available

## 4. What This Means For Me

The output should end with a fixed practical landing section.

This section should answer questions like:

- why should I care?
- who is this useful for?
- is this worth saving / following / applying?
- what is the practical next takeaway?

This is the main mechanism for strengthening the product's conclusion quality.

---

## Fit With Existing Pipeline

The preferred implementation direction is to adapt the current pipeline rather than inventing a new one.

Relevant existing structures already present in the app:

- `structured_result`
- `product_view`
- `editorial`
- `insight_brief`

Initial mapping direction:

- `product_view.hero` carries the one-sentence conclusion
- `product_view.sections` carries the 3-5 question blocks
- `editorial.base.bottom_line` or equivalent carries the final practical landing
- `insight_brief` should prefer extracting from the new question-driven structure rather than from loose key-point lists when available

This keeps the change concentrated in:

- prompt instructions
- structured output/schema shaping
- light adaptation in result mapping/rendering where necessary

---

## Why This Approach Is Preferred

### Option A. Question-Driven Skeleton

This is the recommended option.

Why:

- directly targets the user's preferred reading shape
- improves structure, conclusion strength, and scanability at the same time
- keeps the solution centered on product quality rather than decorative UI work
- fits the existing product-view pipeline

### Option B. Make Current Outputs Shorter

This is useful but insufficient on its own.

Why not enough:

- shorter text can still be poorly organized
- does not guarantee stronger conclusions
- does not create a stable reading pattern users can rely on

### Option C. Solve It Mainly In The Renderer

This is not preferred.

Why not:

- a renderer can rearrange weak material but cannot make the underlying analysis more decisive
- the underlying structured result still needs a better shape
- this risks polishing a weak payload instead of improving it

---

## Validation Criteria

The redesign should be considered successful only if real outputs satisfy most of the following:

1. the top of the result communicates the core judgment within 5 seconds
2. the body reliably becomes 3-5 question-led sections
3. each section feels short enough to scan quickly
4. the ending reliably answers "so what"
5. the result feels more like an explanation for a human reader and less like model exhaust

---

## Open Questions For Tomorrow

These items were intentionally left unresolved:

1. which current prompt/schema file(s) should become the main insertion point for this template?
2. should question blocks live only in `product_view.sections`, or also gain an explicit editorial field for downstream reuse?
3. how strict should the block count and per-block length limits be?
4. should the final "what this means for me" section be a dedicated section kind or part of hero/footer editorial data?
5. how much should this template vary between research-paper analysis and general technical-content analysis?

---

## Suggested Next Step

Tomorrow's first implementation step should be to inspect the generation path that currently produces the default deep-analysis payload, then decide the smallest schema/prompt change that can reliably produce:

- a direct conclusion hero
- 3-5 question-driven sections
- a fixed practical closing section

Only after that should code changes begin.
