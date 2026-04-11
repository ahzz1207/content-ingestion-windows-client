# Analysis Report Query Artifacts Design

**Date:** 2026-04-09  
**Status:** draft for review  
**Scope:** define how the product should evolve beyond source-centric saved interpretations by turning high-value query results into durable analysis-report-style knowledge objects, without turning the product into a generic PKM or wiki tool.

---

## Summary

This product should not be framed first as a knowledge management tool. Its phase-1 wedge is stronger and more differentiated than that: it is a product for high-quality, multimodal, source-grounded, strongly argued analysis with an unusually strong reading experience.

The correct next strategic move is therefore not to drift into generic note-taking, document organization, or a markdown vault. Instead, the product should preserve its current source-centric interpretation model and add one new persistent object above it: the **analysis report query artifact**.

An analysis report query artifact is a saved, durable, report-like answer to a concrete question, built from one or more pinned source interpretations, with explicit provenance, evidence grounding, and revision history.

This direction absorbs the strongest part of Karpathy's "LLM Wiki" idea — that good analytical work should become a persistent compounding artifact — while deliberately rejecting the parts that would turn the product into another Obsidian.

---

## Product Framing

## Phase 1

The phase-1 product is:

- a source-grounded reading and analysis system
- a multimodal interpretation engine
- a product that turns raw source material into credible, readable, high-quality analytical outputs

Its core differentiators are:

1. high-quality analysis and summarization
2. multimodal input understanding
3. strong traceability and evidence grounding
4. strong argument quality and synthesis quality
5. premium reading UX

The source-centric library already serves this phase well because it lets users retain high-value source interpretations, revisit them, compare versions, and trust that the system preserves source provenance.

The user is not initially buying a PKM system. The user is buying the ability to understand and consume difficult material faster and better.

## Phase 2

Only after phase 1 works and users value the outputs should the product grow into a stronger knowledge layer.

Phase 2 is not "becoming a note app." It is becoming a stronger system for:

- durable analysis artifacts
- cross-source synthesis
- recurring inquiry
- knowledge maintenance
- better multi-device reading and retrieval

In this framing, knowledge management is an amplifier of the core analysis engine, not the product's original wedge.

---

## What To Absorb From Karpathy

The following ideas are strongly aligned with this product:

### 1. Good analytical work should compound

The most valuable product outputs should not disappear into transient chat history. If a user asks a strong question and receives a high-quality answer, that answer should become a durable object the system can revisit, cite, revise, compare, and build upon.

### 2. There should be a persistent middle layer between raw sources and future reasoning

Karpathy's wiki is one version of this middle layer. In this product, the middle layer should be composed of structured objects designed for analysis and reading rather than freeform note-taking.

### 3. Schema and workflow matter more than one-off prompting

The product's long-term value depends on disciplined object boundaries and maintenance rules:

- what counts as a source
- what counts as an interpretation
- what counts as a report artifact
- how evidence is pinned
- when something is revised versus replaced

This aligns with the project's existing semantics-first approach.

### 4. Query outputs should also become assets

This is the single most important absorbable idea for the current product. The next persistent object should not be another source interpretation; it should be a saved analytical answer to a meaningful question.

### 5. Maintenance should eventually matter

The system should later gain the ability to tell the user when saved knowledge objects are stale, weakly supported, superseded, or ripe for re-synthesis. This should come after the basic report artifact model exists.

---

## What Not To Absorb

The following ideas should not be pulled directly into this product, at least not in the near term:

### 1. Do not turn the product into another Obsidian

The product should not become:

- a generic markdown vault
- a user-authored notes workspace
- a graph-navigation-first tool
- a plugin-driven PKM system
- a general personal writing environment

The main value should still come from the quality of the system's analysis, not from the flexibility of user note organization.

### 2. Do not flatten everything into undifferentiated pages

Karpathy uses a wiki/page metaphor to communicate the pattern. This project does not need to use `page` as its primary abstraction. More disciplined typed objects will serve trust and product clarity better.

### 3. Do not persist chat logs as if they are knowledge

Most chat output is transient exploration. The product should elevate only high-value analytical results into persistent artifacts, and those artifacts should be rewritten into a stable report form rather than stored as raw chat history.

### 4. Do not over-automate invisible mutation

Users should not discover that a previously saved analytical result changed silently because the system rewrote it in the background. Trust requires explicit revision and explicit freshness status, not hidden mutation.

### 5. Do not make global retrieval the first interaction model

Phase 1 of query artifacts should prefer explicit source selection or explicit scope over a vague "chat with your entire knowledge base" experience. Clear scope improves trust and makes saved artifacts legible.

---

## Product Thesis

The product should evolve from:

- a source-centric saved-reading library with strong single-source interpretation

into:

- a source-centric analysis system that can also save high-value cross-source answers as durable report artifacts

The important nuance is that the product does not leave behind the source-centric model. It builds on it.

The source-centric layer stays foundational.
The new report-artifact layer becomes the first major compounding layer above it.

---

## Chosen Persistent Object

The next persistent object should be an **analysis report**.

This is preferred over:

- generic notes
- lightweight Q/A cards
- freeform markdown pages
- dossier-style topic objects as the first expansion

### Why Analysis Report Is The Right First Object

1. it is closest to the current product's strength
2. it preserves the project's emphasis on reading quality
3. it keeps argument quality and synthesis quality visible
4. it is easier to trust than chat output
5. it can later feed a higher-order topic or dossier system

This means the next persistent object should not feel like a note. It should feel like a saved analytical memo, briefing, or research report.

---

## Object Model

## 1. Source

This is the raw captured source material and its canonical identity.

It remains:

- immutable in principle
- the source of truth for provenance
- the stable container for snapshots and metadata

This is already represented by the current source-centric library entry structure.

## 2. Interpretation

An interpretation is the system's best current reading of a single source at a given time.

It should remain:

- the canonical single-source analytical object
- versioned per source
- current by default, with old interpretations recoverable

This matches the current `LibraryEntry` / `LibraryInterpretation` semantics.

## 3. Analysis Report Query Artifact

This should be the next new persistent object.

Definition:

- a durable answer to a specific question
- written in a report form
- grounded in one or more pinned interpretations
- readable on its own later
- revisioned instead of silently overwritten

Suggested user-facing term:

- `Analysis Report`

Suggested internal term:

- `QueryArtifact`
or
- `AnalysisReportArtifact`

Minimum identity requirements:

- a stable artifact id
- the question it answers
- a report title
- a short answer / thesis
- sections for evidence-backed explanation
- a pinned input set
- citations / grounding metadata
- freshness / supersession state
- revision metadata

## 4. Dossier (later)

This should be deferred until after analysis reports are real and trusted.

Definition:

- a higher-order topic container that organizes multiple reports, sources, tensions, and open questions over time

The dossier should not be the first post-library object because it is farther from the current wedge and easier to overbuild.

---

## Query Artifact Design

An analysis report artifact should feel like a saved, high-quality research note rather than a chat answer.

### Required characteristics

It should be:

- question-centered
- report-shaped
- source-grounded
- readable without replaying the original interaction
- explicit about evidence and uncertainty
- revisionable through explicit new revisions only

### Recommended report structure

The exact template can vary by mode, but the default artifact should roughly contain:

1. title
2. explicit question
3. short answer / headline conclusion
4. key findings
5. deeper analytical sections
6. tensions / disagreements / caveats
7. open questions / follow-ups
8. source set summary
9. evidence links / citations

This object should be optimized for later reading, not for reproducing the full exploratory session.

### Recommended default report skeleton

For the default `Analysis Report`, the product should prefer a **question-driven analytical skeleton** instead of mirroring the original source structure.

This is especially important for financial research, industry analysis, strategy analysis, and other "what changed / what matters / what is misunderstood" use cases.

The baseline report should therefore default to a structure closer to:

1. **核心变化 / What changed?**
2. **增量信息 / What is genuinely new here?**
3. **核心论证链 / Why does the answer hold?**
4. **哪里可能被低估、误判或错定价？**
5. **风险、反例与短期扰动是什么？**
6. **一句大白话结论 / Plain-language translation**

This does not mean every report must use these exact headings. It means the product should strongly prefer this underlying logic:

- surface the answer as a change in understanding
- separate true incremental information from background context
- make the reasoning chain legible
- show where the consensus, market, or naive reader may be wrong
- preserve uncertainty and break conditions
- translate the conclusion into plain language

This skeleton is better than a generic summary for the product because it aligns with the product's core wedge:

- not just summarizing material
- but helping the user update their mental model

### Structural rules for the default report

The first version of `Analysis Report` should follow these editorial rules:

1. each section answers a distinct cognitive question, not a source-order chunk
2. each section should begin with a short lead sentence before supporting bullets or paragraphs
3. the report should distinguish background from increment
4. the report should preserve at least one explicit "what could break this view" section
5. the report should include one plain-language translation layer for non-specialist readability

### Mode-specific adaptation

The exact headings can adapt by mode, but the analytical roles should remain recognizable.

Examples:

- **investment / equity research**
  - core change
  - incremental information
  - mispricing / underappreciated point
  - risk / timing / downside
- **strategy / business analysis**
  - what changed
  - what the new evidence implies
  - where the old framing fails
  - execution and adoption risks
- **technical / research synthesis**
  - key update
  - what is newly established
  - strongest supporting mechanism
  - unresolved uncertainty or disconfirming path

The goal is not to copy any one external report's visual style. The goal is to learn from a proven reading pattern: readers absorb analysis best when the report is organized around the update to their understanding.

---

## Query Artifact UX

## The user experience should be:

1. the user saves sources into the source-centric library
2. the user selects one or several sources, or starts from a current result
3. the user asks a meaningful question
4. the system produces a high-quality report-like answer
5. the user can save that answer as an `Analysis Report`
6. the saved report becomes browsable and reusable later

### The product should not present this as “save conversation”

It should present it as:

- `Save as Analysis Report`
- `Create report from this answer`
- `Open saved report`

### Reading UX

Saved reports should inherit the same design philosophy as the result page:

- strong editorial hierarchy
- readable long-form layout
- evidence visible but not visually noisy
- confidence and uncertainty legible
- citations accessible inline or in a quiet side layer

The saved report is a product surface, not a hidden backend record.

---

## Scope Model

Phase 1 should prefer explicit scope.

Recommended query scopes:

- current source only
- selected saved sources
- maybe a small curated scope like recent saved sources, but still user-legible

Avoid in phase 1:

- opaque retrieval across everything
- unconstrained “search all my knowledge” by default

The user should be able to understand what the answer was built from.

---

## Trust and Provenance Constraints

These constraints are central and should be treated as product rules, not polish.

### 1. Pin reports to exact interpretation versions

Reports must point to concrete source interpretations, not just raw source identities.

Why:

- source interpretations can evolve
- old reports need to remain reproducible and historically meaningful

### 2. Preserve source scope visibly

The report should show what it used.

Users should always be able to answer:

- which sources were included
- which interpretations were used
- whether any inputs are now superseded

### 3. No silent rewrites

If a report is updated, it should create a new revision.
Old revisions remain historical objects.

### 4. Distinguish freshness from truth

If a report was generated from older interpretations, it should be labeled as using superseded inputs, not silently treated as current.

### 5. Evidence should remain visible enough to trust the report

The system should not ask the user to trust a polished summary without being able to inspect where the answer came from.

---

## Relationship To The Current Source-Centric Library

The current library remains the foundation.

Recommended layering:

- `Source` = canonical source container
- `Interpretation` = best current single-source reading
- `Analysis Report` = saved answer built from pinned interpretations
- `Dossier` = later multi-report topic object

This means the report artifact does not replace the current library.
It sits above it.

The current library's job remains:

- durable source retention
- image-first detail reading
- interpretation version history
- source-specific recall and restore

The new report layer's job becomes:

- durable multi-source answers
- reusable analysis outputs
- a bridge from one-off query to compounding knowledge

---

## Workflow Model

## Ingest

Bring raw source material into the library and interpret it.

## Interpret

Generate or regenerate a single-source interpretation.

## Query

Ask a question over one or more selected interpretations.

## Save Report

Turn a high-value answer into a durable analysis report artifact.

## Reopen / Reuse

Browse the saved report later, cite it, compare it, or use it as input for a new question.

## Lint / Maintain (later)

Detect:

- stale inputs
- under-supported claims
- conflicting source support
- likely rerun opportunities

This maintenance layer should arrive after the first report artifact model is solid.

---

## Why This Is Better Than Generic Note Persistence

If the product simply saves user queries or chat transcripts, it will drift toward undifferentiated conversational memory. That is not the strongest version of this product.

The stronger pattern is:

- exploratory chat remains ephemeral
- high-value analytical output gets compiled into a stable report
- only the compiled report becomes a persistent artifact

That keeps the product aligned with:

- quality over quantity
- readability over transcript exhaustiveness
- trust over convenience theater

---

## Phase-1 Recommendation

The next knowledge-layer milestone should be:

### `Analysis Report` MVP

Include:

- explicit query over selected saved sources or interpretations
- report-like answer template
- save-as-report action
- pinned source interpretation inputs
- visible citations / source set summary
- basic freshness / supersession status
- reopen and reread report

Do not include yet:

- global graph / wiki browsing
- user-authored freeform note system
- dossier system
- broad autonomous retrieval over the entire library
- giant generalized PKM interface

---

## Phase-2 Recommendation

After report artifacts are established, the next layer can include:

- dossier objects
- report-to-report synthesis
- contradiction tracking
- query rerun against latest interpretations
- query templates for recurring research questions
- better multi-device report reading and browsing

This keeps the product compounding while preserving its differentiated core.

---

## Strategic Position

The long-term direction is not:

- “become a doc tool with some AI features”

It is:

- “start as a superior source-grounded analysis and reading product, then grow a knowledge layer made of durable analytical objects”

In other words:

- phase 1 sells analysis quality and reading quality
- phase 2 compounds that value through persistent report artifacts and later topic-level synthesis

This keeps the product far away from generic note tools while still absorbing the strongest structural insight from Karpathy's idea.

---

## Acceptance Criteria For This Direction

This design direction is correct if the following remain true:

1. the product's primary value proposition is still analysis quality, not note management
2. the first new persistent object after source interpretation is a report artifact, not a generic note
3. saved query artifacts remain visibly grounded in source interpretations
4. the source-centric library remains foundational rather than being replaced
5. the product does not need to become another Obsidian to gain compounding knowledge behavior
