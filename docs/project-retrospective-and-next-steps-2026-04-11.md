# Project Retrospective And Next Steps 2026-04-11

This document is meant to be the broadest current project summary.

It records:

- the project state from the point I stepped into this round of work
- the main architecture and product clarifications we made
- the design and brainstorming directions that shaped the work
- what actually shipped in both the Windows GUI and the WSL processing engine
- what we intentionally did **not** do in order to keep scope controlled
- what should happen next across GUI, WSL, and the longer-term product roadmap

It is not just a handoff.
It is the current working retrospective plus forward-looking roadmap checkpoint.

---

## 1. Product Position At This Point

The project is no longer best understood as a simple URL summarizer.

The working product shape is:

- Windows application as the operational shell and reading surface
- WSL processor as the normalization and analysis engine
- shared inbox as the cross-repo transport boundary
- knowledge retention as a first-class product concern rather than an afterthought

The long-term product is moving toward a durable `web viewpoint intelligence` system, not a one-shot page summarizer.

That product idea already existed in earlier roadmap thinking:

- Windows app / future client as capture shell
- WSL as understanding engine
- downstream knowledge system as durable memory layer

What changed during this round is that the product now began to behave more like that system in practice.

---

## 2. The Baseline When This Round Started

When I stepped into this round of work, the broad architecture was already real and useful:

- Windows PySide6 GUI existed
- Windows export into `shared_inbox` existed
- WSL watcher / processor existed
- processed outputs could already be read back in the GUI
- the system already had structured output concepts beyond flat markdown

The most important already-established baseline ideas were:

- Windows should own capture, routing, and user-facing reading surfaces
- WSL should own content understanding and analysis logic
- the Windows-to-WSL handoff contract should stay narrow and stable
- the GUI should not become the place where analysis semantics are invented

Earlier docs had already made several key boundaries explicit:

- the GUI was feature-converged enough to stop broad expansion
- the Windows-to-WSL protocol should stay small and robust
- the WSL processor should aim above generic summary generation and toward structured understanding

That starting point mattered, because this round was not a greenfield build. It was a product-convergence and quality-improvement phase.

---

## 3. The Main Questions We Had To Answer

The most important questions during this round were not low-level implementation questions.
They were product-shape questions.

### 3.1 What is the durable object?

At the beginning of the round, the product still leaned heavily toward job-centric reading.

That was useful for pipeline visibility, but weak for long-term value.

We had to answer:

- is the durable object a processing job?
- or is it a source with evolving interpretations?

This led to the source-centric knowledge library direction.

### 3.2 What should different content types become after processing?

The system already had rich output, but it still risked treating too many inputs as if they were the same kind of argument-heavy content.

That led to deeper alignment with analysis-mode taxonomy thinking:

- `argument`
- `guide`
- `review`
- `narrative`
- `informational`

The point was not to create many disconnected products.
The point was to route content by user need and reading goal.

### 3.3 What actually creates product differentiation?

The answer was not “more GUI surface area.”

The answer became increasingly clear:

- better structure understanding
- better distinction between evidence, interpretation, and implication
- more trustworthy and more readable outputs
- a more durable post-reading loop

That is why later in the round the priority shifted away from broad GUI polishing and toward output quality.

---

## 4. The Architectural Clarifications We Made

Several architecture and boundary decisions became much clearer during this round.

### 4.1 Windows remains the operational shell

Windows is responsible for:

- URL intake
- browser-backed and HTTP capture
- platform routing
- user-facing reading and interaction surfaces
- save / restore library actions
- bridge management into WSL

Windows is **not** the place to invent new analysis semantics.
It should consume and present what WSL emits.

### 4.2 WSL remains the understanding engine

WSL is responsible for:

- normalization
- denoise
- structure understanding
- transcript and media processing
- structured LLM analysis
- presentation-ready analysis contracts for downstream clients

This aligns with the earlier upper-bound WSL design direction:

- structure before summary
- evidence before polish
- local understanding before global synthesis
- presentation-ready artifacts as part of the processor contract

### 4.3 The handoff contract stays narrow

The earlier Windows-WSL handoff contract stayed directionally correct throughout this round.

The important idea is still:

- keep the Windows-to-WSL inbox contract small and stable
- put richer semantics in normalized / structured result outputs, not in a bloated handoff protocol

This discipline prevented the cross-repo boundary from turning into a moving target.

### 4.4 The GUI is temporary, not the final platform

This became an explicit product constraint during the round.

The user clarified that the current GUI is temporary.
The future direction is multi-platform.

That means:

- GUI investment must stay pragmatic
- UI work should serve acceptance, reading quality, and product learning
- the long-term center of gravity should move toward stronger LLM processing and a future client architecture, not endless PySide polish

---

## 5. The Main Brainstorming And Design Directions We Explored

### 5.1 Source-Centric Knowledge Library

One of the strongest product shifts in this round was the move from job-centric history toward source-centric retained knowledge.

The core ideas that were settled were:

- the result page should have a primary `保存进知识库` action
- the durable object is the source entry, not the job
- one source maps to one durable library entry
- the current interpretation is the default reading view
- re-saving the same source should replace the current interpretation and trash the previous current one
- restore should be entry-local, not a global trash feature in v1
- image summary is an interpretation asset, not a top-level library object

This turned the product from “analysis viewer” into the beginning of a durable knowledge loop.

### 5.2 Analysis Mode Taxonomy

The earlier analysis-mode taxonomy work remained important background throughout this round.

Its main value was conceptual clarity:

- not all content should be forced through argument-heavy analysis
- content intent matters more than platform
- shared base output and mode-specific emphasis should coexist

This thinking directly influenced later rendering and output-shape choices, especially the need to keep guide outputs distinct from argument outputs.

### 5.3 Deep Analysis Question-Driven Output

Late in the round, the strongest new direction came from reviewing a paper-summary reference that felt more useful than our current output shape.

The desired qualities were identified as:

- a one-sentence conclusion at the top
- 3-5 explicit question-driven sections
- short, scannable blocks
- a fixed ending that answers `这对我意味着什么？`

This was not framed as copying another product’s visuals.
It was framed as copying a better reading logic.

The resulting design decision was:

- improve prompt / output structure first
- use the existing `structured_result` / `editorial` / `product_view` pipeline where possible
- do not redesign all output modes at once
- start with deep analysis / practical extraction first

This became the basis for the WSL-side `product_view` work and the Windows-side consumption/rendering updates.

---

## 6. What Actually Landed In This Round

### 6.1 Windows-side shipped outcomes

The Windows feature branch ultimately converged into a large but coherent reading-workflow package.

What landed includes:

- source-centric library storage and UI
- save / restore interpretation flows
- result-page and library integration
- improved deep-analysis reading density
- improved guide rendering separation from argument rendering
- improved result rendering for question-driven sections
- improved `insight_brief` adaptation for question-driven `product_view`
- coverage fallback fix for nested `document.evidence_segments`
- bilibili / watchlater routing and browser profile reuse fixes

This work culminated in:

- `e08a222` `feat: complete source-centric reading workflow`

### 6.2 WSL-side shipped outcomes

The WSL work in this round focused on the generation-side contract needed for the new deep-analysis reading shape.

What landed includes:

- `StructuredResult.product_view`
- `argument` mode question-driven `product_view` generation
- hero fields for direct top-level conclusion
- question-block sections for body structure
- final `reader_value` section
- serialization into result artifacts consumed by Windows

This work culminated in:

- `5c64b96` `feat: add question-driven product view output`

### 6.3 Local main acceptance merge and verification

Both repositories were merged locally into dedicated `main` acceptance worktrees and verified there.

Windows main acceptance:

- `211 passed, 1 skipped`

WSL main acceptance:

- `28 passed`

This is important because the final acceptance pass was performed against the merged local `main` worktrees, not only against feature branches.

---

## 7. What We Learned During Implementation

### 7.1 Product-view consumption must be stable across repositories

One recurring theme was that Windows should not infer too much from weak or shifting payloads.

Once WSL emits a meaningful `product_view`, Windows can:

- preserve it
- summarize it
- render it

But if the payload shape is weak, no amount of renderer polish really solves the core problem.

### 7.2 Reading quality beats UI expansion

This round reinforced that the next product leap is not more panels, filters, or settings.
It is stronger reading products.

The best improvements were the ones that made users feel:

- I understand the point faster
- I know what matters
- I know what is evidence-backed
- I know whether this is worth saving

### 7.3 Worktree-local runtime data is operationally significant

The library data issue during acceptance was a good example.

Worktrees are not just code containers in this project.
They also change runtime-local paths like:

- `data/shared_inbox`
- `data/shared_inbox/library`

That means worktree cleanup and runtime data management are product-significant, not just Git hygiene.

---

## 8. What We Deliberately Did Not Do

A lot of restraint in this round was intentional.

### 8.1 We did not keep expanding GUI surface area

We deliberately did not turn the GUI into:

- a settings-heavy application
- a search-heavy workspace
- a queue-management center
- a batch-ops surface
- a feature-rich PKM replacement

This follows the earlier GUI closeout logic: keep the GUI strong enough to operate and read, but stop before it turns into a product distraction.

### 8.2 We did not force all analysis modes into one reading template

The question-driven deep-analysis structure was intentionally limited.

We did **not** try to re-template:

- guide
- review
- narrative
- informational

all at once.

That was a deliberate anti-scope-creep decision.

### 8.3 We did not turn the Windows repo into the intelligence layer

Even when it was tempting to patch around weak outputs in the GUI, the round consistently moved back toward the correct boundary:

- fix generation where generation belongs
- keep presentation on the Windows side

### 8.4 We did not use this round for broad codebase refactoring

There are still large files and architectural rough edges, especially on the GUI side.

Examples include:

- `main_window.py`
- broader GUI state-management complexity
- style duplication and layout density concerns

We consciously avoided turning this round into a large refactor campaign, because that would have expanded risk without directly increasing product usefulness.

### 8.5 We did not finish the longer-term downstream knowledge system

The Obsidian roadmap and the broader knowledge-object model remain strategically relevant.

But we did **not** attempt to ship:

- claim notes
- topic notes
- entity graph
- synthesis boards
- published knowledge products
- cloud sync / collaboration

Instead, we used the source-centric library as a smaller, more immediate product step toward durable knowledge.

---

## 9. What Still Looks Valuable But Was Deferred

There are several things that still look worthwhile, but were intentionally deferred.

### 9.1 Stronger WSL critique / verification layering

Earlier WSL design thinking already pointed toward a stronger critique / verification stage.

That still looks valuable for:

- evidence pressure
- blind-spot detection
- overreach detection
- separation between support and interpretation

It was not finished in this round.

### 9.2 Better multimodal structure understanding

The WSL upper-bound design still points toward richer understanding of:

- image-heavy posts
- video scene transitions
- slide / frame semantics
- visual evidence navigation

This round kept multimodal readiness in view but did not fully expand it.

### 9.3 Stable shared library path strategy

The knowledge library currently lives under worktree-local shared inbox roots.

That is workable for development but not ideal for long-lived user trust.

A future step should decide whether the library should be:

- worktree-local
- repo-root shared
- user-level shared outside the repo

This was not resolved in this round.

### 9.4 Better main-branch integration discipline across two repositories

The project still pays a real coordination cost for having:

- a Windows repo
- a WSL repo
- a shared runtime contract
- worktree-local runtime state

This is manageable but operationally sharp-edged.

It remains worth asking whether future workflow should improve through:

- stronger release checklists
- better shared fixtures / integration smoke tests
- or eventually a more unified operational model

---

## 10. The Current Direction For The Near Future

### 10.1 First priority: improve output quality, not more shell UI

The most important immediate next direction is:

- better deep-analysis usefulness
- better evidence-grounded outputs
- better conclusion quality
- more reliable save-worthy reading artifacts

This means continuing to improve the WSL pipeline and the output contract is likely more valuable than adding more desktop GUI features.

### 10.2 Continue tightening question-driven deep analysis

The new question-driven output shape is only the first step.

It still needs iteration on:

- quality of section questions
- body brevity and discipline
- practical closing strength
- distinction between strong evidence and weaker interpretation
- consistency across real, messy inputs

### 10.3 Keep guide / review / narrative distinct

One likely future direction is not to homogenize all output modes, but to sharpen each one’s value.

For example:

- `guide` should feel more actionable and sequence-oriented
- `review` should feel more judgment / fit / taste aware
- `narrative` should feel event and arc aware
- `argument` should feel thesis / evidence / tension aware

That direction remains valid.

---

## 11. The Medium-Term Direction

The earlier roadmap remains broadly correct.

### 11.1 Multi-platform future

The long-term client direction is not PySide6 forever.

The likely evolution remains:

- Windows GUI as temporary local shell
- future HTTP / API boundary
- future web client or multi-platform client

The desktop GUI is useful now, but it should not be mistaken for the end-state platform.

### 11.2 Service-oriented processing path

The roadmap toward serviceification also still makes sense:

- processor exposed through API boundaries
- remote or persistent task handling
- richer progress / job introspection
- future 24h unattended operation

That direction becomes more meaningful once the quality of the underlying understanding engine is strong enough to justify wider access.

### 11.3 Durable knowledge layer beyond library v1

The Obsidian-facing and broader knowledge-model thinking remains valuable.

The current library is a practical local retention layer.

But the deeper future still points toward:

- source objects
- digest objects
- claim objects
- topic objects
- entity objects
- synthesis objects
- shareable knowledge outputs

That is the larger product horizon beyond the current local reading workflow.

---

## 12. The Long-Term Product Thesis

The strongest long-term thesis that survives all of this work is:

- this project should become a system that helps users understand, retain, compare, and operationalize viewpoints from the open web

Not just:

- collect pages
- summarize pages
- file away markdown exports

The real product gap is created when the system can consistently do all of these together:

- high-quality capture
- trustworthy multimodal understanding
- evidence-aware structure
- useful reading surfaces
- durable retained knowledge
- future cross-source synthesis

That is the best north star for future decisions.

---

## 13. Practical Next-Step Recommendation

If the next builder has limited time, the best next move is not to broaden the shell.

The best next move is:

1. stabilize acceptance `main` promotion and runtime data location
2. keep the current GUI stable
3. improve WSL output quality for deep analysis first
4. then revisit stronger mode-specific output quality
5. only after that, resume broader platform evolution

That ordering is the most likely to increase real product value without reopening unnecessary surface area.

---

## 14. Shortest Honest Summary

The project began this round as a capable but still somewhat job-centric Windows + WSL analysis tool.

It ends this round as a more product-shaped system with:

- a source-centric knowledge loop
- stronger Windows reading surfaces
- a first real question-driven deep-analysis output path
- a cleaner local `main` acceptance state across both repositories

The next product leap is no longer “more GUI.”

It is:

- better understanding
- better evidence use
- better reading products
- and eventually, a stronger long-term knowledge system on top of that foundation.
