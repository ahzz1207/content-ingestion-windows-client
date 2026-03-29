# WSL Processing Upper-Bound Design

**Date:** 2026-03-28  
**Status:** exploratory design draft  
**Scope:** define the next-stage WSL processing direction by capability ceiling first, before token compression work

---

## Why This Exists

The current system can already produce a usable result card and a digest-oriented artifact.

That is not enough to create a meaningful product gap.

If the output is only a short summary, many existing tools can already do that. The WSL processor should instead aim to become a high-quality understanding engine for:

- long-form text
- image-rich articles and posts
- audio
- video

The target is not "shorter summary generation".

The target is:

- deeper structure understanding
- better distinction between fact, viewpoint, framing, and emotion
- clearer evidence grounding
- stronger multimodal understanding
- better save-worthy output for downstream clients such as GUI and Obsidian

---

## Product Goal

The user should feel that the system does more than summarize.

For a strong result, the user should be able to answer:

- What is the author really arguing?
- What is genuinely new or useful here?
- Which points are evidence-backed, and which are interpretive?
- What tensions, blind spots, or contradictions exist?
- Which exact moments, paragraphs, or visuals are worth revisiting?

This means the processor should produce a result that is closer to a research assistant output than a generic abstract.

---

## Non-Goals

This direction does not aim to:

- optimize token cost first
- collapse the pipeline back into a single prompt
- make Windows clients responsible for intelligence
- turn the processor into a full external API product
- broaden immediately into claim/topic/entity graph extraction

Token control matters later, but it should follow capability discovery rather than define the first design boundary.

---

## Core Design Principles

- Evidence first: every important conclusion should remain traceable to text segments, transcript segments, or visual evidence.
- Structure before summary: the processor should first understand the shape of the content, then summarize it.
- Local understanding before global synthesis: long content should not be understood only through one large end-to-end prompt.
- Multimodal grounding is selective and meaningful: images and frames are used to change understanding, not decorate the result.
- Presentation-ready output is part of the processor contract: Windows clients should render meaning, not invent it.

---

## Experience Target

The output should be layered.

### Layer 1: Skim

- one-sentence thesis
- three to five high-value takeaways
- verification or confidence signal
- coverage warning when important evidence is missing

### Layer 2: Insight

- author thesis
- key arguments
- evidence-backed points
- interpretation or implication
- tensions, caveats, and blind spots

### Layer 3: Navigation

- chapter map or scene map
- key paragraphs or key timestamps
- resolved evidence references
- visual findings separated from text findings

The user should be able to skim quickly, then dive into specific points without reopening the raw source immediately.

---

## Processing Architecture

The upper-bound WSL pipeline should evolve toward this shape:

```text
handoff
  -> normalize
  -> denoise
  -> structure
  -> local understanding
  -> global synthesis
  -> critique / verification
  -> optional multimodal grounding
  -> presentation-ready artifact writing
```

### 1. Normalize

Goal:

- convert the Windows handoff into a rich, inference-ready content asset

Requirements:

- preserve text blocks, headings, lists, quotes, captions, links, attachments
- preserve transcript text and transcript segments
- preserve frames and image assets when available
- preserve metadata about content type, content shape, source platform, collection path, and capture context

This stage should not yet decide what matters most.

It should make sure nothing important is thrown away too early.

### 2. Denoise

Goal:

- remove shell, repetition, recommendation rails, boilerplate, engagement chrome, and other misleading surface noise

Requirements:

- platform-aware cleanup remains allowed
- denoise must improve semantic fidelity, not only reduce length
- denoise output should remain inspectable and reversible through artifacts

The processor should not send obvious page shell or transcript junk into the main reasoning stage.

### 3. Structure

Goal:

- convert raw content into semantic units that can be reasoned over

Text targets:

- sections
- topic blocks
- argument transitions
- quote blocks
- evidence-heavy paragraphs

Audio / video targets:

- chapters
- topic turns
- speaker or stance shifts
- emphasis points
- scene or slide transitions

This stage creates the content skeleton.

### 4. Local Understanding

Goal:

- understand each semantic unit independently before attempting a whole-document conclusion

For each unit, the processor should aim to derive:

- what this unit is saying
- whether it introduces a new claim, a supporting point, context, or rhetoric
- which evidence segments support it
- whether visual context matters
- whether the unit is high-value or low-value for the final result

This is the stage where long content becomes manageable without immediately flattening everything into one global summary.

### 5. Global Synthesis

Goal:

- integrate high-value local understanding into a coherent whole

The global pass should answer:

- central thesis
- major argument map
- author stance
- strongest insights
- what is new versus repetitive
- what matters downstream for the user

This is where the processor should become meaningfully better than a normal summarizer.

### 6. Critique / Verification

Goal:

- distinguish evidence-backed interpretation from overreach

The processor should explicitly test:

- where the content is strongly grounded
- where claims are only partly supported
- where reasoning jumps occur
- where rhetoric or emotional framing outruns evidence
- where uncertainty should be preserved instead of smoothed over

This stage should not be treated as an optional polish pass.

It is a core differentiator.

### 7. Optional Multimodal Grounding

Goal:

- use images or frames only when they materially improve understanding

The multimodal layer should answer:

- what the visuals add that text alone misses
- whether visuals support or contradict the narration
- whether a visual artifact contains claim-relevant information
- whether an atmosphere, chart, demo, or slide changes the interpretation

This stage should remain semantically distinct from the text analysis layer.

Visual findings should not be collapsed into generic text analysis items.

### 8. Presentation-Ready Artifact Writing

Goal:

- produce artifacts that are directly consumable by GUI, API, browser clients, and Obsidian

The processor should write outputs that already encode:

- result hierarchy
- chapter or scene map
- key insights
- verification state
- visual findings
- evidence references
- result display hints

Windows should render these results, not redefine them.

---

## Model Role Design

The upper-bound system should not rely on one monolithic prompt for the whole job.

Instead, the processor should conceptually separate four roles.

### Reader

Responsible for:

- local comprehension
- chapter or scene interpretation
- identifying candidate insights

### Synthesizer

Responsible for:

- whole-asset thesis
- argument map
- integrated summary and synthesis

### Critic

Responsible for:

- evidence pressure
- overclaim detection
- ambiguity preservation
- verification downgrades

### Editor

Responsible for:

- shaping the final structured artifact
- producing concise, readable, save-worthy sections
- maintaining a clean presentation contract

These roles may still be implemented with the same underlying model family at first.

The important point is pipeline separation of responsibility.

---

## Modality-Specific Strategy

## Text and Image-Rich Articles

The processor should aim to understand:

- article structure
- rhetorical progression
- where images and captions carry meaning
- which sections are merely setup versus core claims
- whether screenshots, charts, or infographics add evidence not present in body text

The output should preserve:

- chapter-level takeaways
- image-aware findings
- differences between fact reporting and opinion framing

## Audio

The processor should not treat transcript as a plain article substitute.

It should aim to preserve:

- topic turns
- emphasis shifts
- repeated themes
- places where spoken delivery changes the meaning of the words

The output should highlight:

- strongest spoken claims
- moments of uncertainty
- recurring motifs
- best timestamps for revisiting

## Video

The processor should combine:

- transcript
- frames
- subtitles when available
- metadata and description context

It should aim to answer:

- what was said
- what was shown
- whether the visual layer materially changes the interpretation
- which moments are actually worth watching

Video understanding should not degrade into "transcript summary plus thumbnail".

---

## Result Contract Evolution

The current structured result already contains:

- summary
- key_points
- analysis_items
- verification_items
- synthesis

The upper-bound direction should evolve that contract rather than replace it abruptly.

The next practical additions should likely be:

- chapter_map or scene_map
- visual_findings as a first-class section
- novelty_signals
- tension_or_blind_spots
- save_worthy_moments
- stronger display_plan / presentation hints

These additions should still preserve compatibility with current Windows read models where possible.

---

## Implementation Strategy

This should be approached in three exploration layers.

### M1: Structural Understanding

Focus:

- denoise quality
- chaptering or scene segmentation
- local understanding units
- better global synthesis based on structured local outputs

Expected gain:

- much stronger long-form quality for text and transcript-heavy inputs

### M2: Critical Reasoning

Focus:

- explicit critique pass
- stronger verification and uncertainty handling
- clearer separation of evidence-backed and interpretive output

Expected gain:

- results feel more trustworthy and less generic

### M3: True Multimodal Understanding

Focus:

- targeted visual grounding
- scene-aware video reasoning
- visual findings as first-class output

Expected gain:

- video and image-rich content stop feeling like transcript summaries

Only after these are explored should the project decide which steps are worth compressing for cost.

---

## What Would Make This Clearly Better Than Existing Tools

The processor should consistently surface:

- what is actually new
- what the author is really arguing
- what is evidence-backed versus interpretive
- what is strategically important
- what is doubtful, missing, or overclaimed
- what is worth saving into a knowledge workflow

If the system cannot do those six things reliably, it is still too close to a commodity summarizer.

---

## Open Questions

- How much chaptering should be rule-based versus model-derived?
- Should local understanding be written to artifacts for traceability, or remain internal?
- What is the right contract shape for visual findings without bloating the main result schema?
- How should we distinguish author stance, narrator stance, and processor interpretation?
- Which parts of critique should affect the main summary, and which should remain side-band warnings?
- At what point should the processor emit "not enough signal" instead of forcing a polished digest?

---

## Provisional Direction

The next major WSL design direction should be:

```text
First, maximize understanding quality.
Then, observe where the expensive reasoning is genuinely valuable.
Only after that, compress the pipeline without sacrificing the parts that create product differentiation.
```

This document is intentionally a capability-first anchor for later implementation planning.
