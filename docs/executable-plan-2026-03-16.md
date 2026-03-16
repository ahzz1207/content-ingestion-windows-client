# Executable Plan - 2026-03-16

## 1. Purpose

This document replaces a speculative roadmap with a build order that matches the current code reality across:

- Windows client: `H:\demo-win`
- WSL processor: `~/codex-demo`

It is designed to be executable rather than aspirational.
The main goals are:

- preserve the working Windows -> WSL roundtrip
- add Obsidian value without destabilizing the pipeline
- improve the GUI in a controlled way
- prepare for later service and cloud evolution without forcing an early rewrite

---

## 2. Current Baseline

The current system already has a usable end-to-end path:

- Windows GUI and CLI can capture and export jobs
- the shared inbox contract works
- the WSL processor can normalize and analyze jobs
- structured result preview already shows up in the Windows GUI

Current confirmed constraints:

- the shared inbox path is still the production transport
- the Windows GUI is implemented in `PySide6`
- the WSL side is not currently in a syntax-broken state
- some earlier review findings are outdated and should not drive Phase 1 work

Current priority risks that still matter:

- LLM requests lack explicit timeout control
- WSL inbox claiming needs stronger hardening
- the Windows default WSL project root is non-portable
- Windows observability remains weak
- the GUI file structure needs refactoring before large design expansion

This plan assumes those facts and does not re-open already disproven bug claims.

---

## 3. Product Direction

The system should evolve toward:

- a capture surface on Windows
- a normalization and analysis engine in WSL or service form
- a downstream knowledge workspace in Obsidian
- a later publish and sharing layer

The product should be treated as:

- a viewpoint intelligence workflow

not merely:

- a URL collector
- a file handoff demo
- a one-shot summarizer

---

## 4. Key Decisions

### 4.1 Obsidian Is a Downstream Knowledge Workspace

Obsidian should not replace the ingestion pipeline.
It should be the first durable destination for processed knowledge artifacts.

### 4.2 PySide6 Remains the Mainline GUI Path

The current repository should continue on `PySide6`.

Reasoning:

- the app already has a working GUI shell
- the workflow layer is already integrated with Python desktop code
- a Tauri rewrite now would add major delivery risk before the product model stabilizes

Implication:

- the current visual spec can guide aesthetics and interaction design
- it should not be treated as a mandatory immediate framework migration

### 4.3 Service Boundaries Should Be Designed Before Transport Migration

FastAPI remains the right long-term direction, but the first step is not immediate cutover.

The first step is:

- define stable internal job, progress, result, and Obsidian-export contracts

After those contracts are stable, moving from shared inbox to HTTP becomes much lower risk.

### 4.4 Audio and Video Should Move to a Unified Transcript Contract

If transcription quality is expanded, the system should standardize on one internal transcript schema:

- segment id
- speaker id if available
- start and end timestamps
- text
- confidence

This matters more than the specific transcription provider.

---

## 5. Tracks

Work should proceed in five tracks, but with one mainline ordering.

### Track A: Stability and Operability

Focus:

- timeouts
- path portability
- inbox hardening
- logging
- CI

### Track B: Obsidian Output

Focus:

- note schema
- vault export
- source and digest notes
- topic and relation scaffolding

### Track C: Knowledge Model

Focus:

- tags
- related note suggestions
- claim extraction
- topic and entity objects

### Track D: GUI Evolution

Focus:

- refactor current PySide6 structure
- apply stronger design language
- make results and knowledge actions first-class

### Track E: Service Boundary

Focus:

- internal contracts first
- FastAPI transport second
- cloud-readiness third

---

## 6. Recommended Phase Order

### Phase 0: Alignment and Contract Freeze

Goal:

- lock the next implementation direction before large code changes

Tasks:

- adopt this executable plan as the working build order
- adopt the review follow-up instead of outdated critical bug claims
- define the first Obsidian export schema
- define the first transcript schema for audio and video
- decide that `PySide6` remains the mainline GUI path for the next milestone

Acceptance:

- one approved note schema for Obsidian source and digest files
- one approved transcript schema
- one explicit GUI technology decision recorded in docs

### Phase 1: Stability Cleanup

Goal:

- harden the existing Windows -> WSL workflow without changing its architecture

Tasks:

- add explicit timeout handling around WSL LLM requests
- add retry boundaries or failure policy around provider calls where appropriate
- replace the non-portable Windows default WSL project root with discovery or required configuration
- harden WSL inbox claim behavior for multi-watcher and cross-filesystem edge cases
- improve Windows logging beyond CLI `print(...)`
- remove Windows TOML BOM portability issue
- add CI for unit tests and lint / type gates

Acceptance:

- roundtrip still works end-to-end
- CI passes on both repositories
- LLM failures fail predictably instead of hanging indefinitely

### Phase 2: Obsidian Writer MVP

Goal:

- close the loop from processed job to useful vault artifact

Tasks:

- implement `ObsidianWriter`
- add configurable vault root
- export one source note per processed job
- export one digest note per processed job
- export attachments into a stable vault asset path
- generate frontmatter from current normalized output
- add a Windows GUI action for `Open in Obsidian` or `Reveal in Vault`

Non-goals:

- no plugin dependency
- no vault mutation of existing notes
- no publish automation yet

Acceptance:

- a processed WeChat article produces a readable source note and digest note inside a vault
- file naming and frontmatter are stable enough for repeated use

### Phase 3: Knowledge Metadata and Linking

Goal:

- make exported notes useful as a growing knowledge base rather than isolated files

Tasks:

- define stable tag taxonomy guidance
- generate `tags` and `related` fields from structured analysis
- build a lightweight vault index from frontmatter
- recommend related notes without modifying existing notes
- add topic, entity, or claim references only where confidence is high enough

Acceptance:

- new exported notes include stable tags
- notes can reference related existing notes using wikilinks
- vault index generation can be rerun without corruption

### Phase 4: Transcript and Media Upgrade

Goal:

- improve audio and video quality without entangling it with unrelated architecture work

Tasks:

- define unified transcript schema
- evaluate `WhisperX` as the local preferred transcription path
- define a cloud fallback contract such as `AssemblyAI`
- normalize both outputs into the same internal structure
- update media preprocessing to consume the normalized transcript contract

Important rule:

- do not couple this phase to FastAPI migration

Acceptance:

- a media job produces standardized transcript segments
- downstream LLM analysis can consume both local and fallback transcript outputs identically

### Phase 5: PySide6 GUI G2

Goal:

- make the current GUI feel materially more modern without a full stack rewrite

Tasks:

- split `main_window.py` into screen and component modules
- introduce design tokens for color, spacing, radius, typography, and motion
- add a command-ribbon style input surface
- make processed result presentation more editorial and less utilitarian
- add knowledge actions near the result
- preserve keyboard-driven workflows and accessibility basics

Acceptance:

- the app still runs on the existing Python desktop path
- the interface feels meaningfully more polished and result-first
- new visual work is achieved without re-implementing the application in web tech

### Phase 6: Internal Service Boundary

Goal:

- prepare the system for transport migration without immediately abandoning the inbox path

Tasks:

- formalize internal job submission model
- formalize progress event model
- formalize processed result model
- formalize Obsidian export request and result model
- isolate current transport-specific logic behind stable interfaces

Acceptance:

- the system can support both inbox transport and a future HTTP transport behind the same higher-level calls

### Phase 7: FastAPI Service

Goal:

- move the processor into a service form once contracts are stable

Tasks:

- add FastAPI entry points
- implement job submission and status endpoints
- implement progress streaming
- retain shared-inbox fallback transport while service mode is being proven
- introduce client-side API abstraction that can replace direct `wsl.exe` calls incrementally

Acceptance:

- the same job can be submitted through HTTP and processed to the same result shape as inbox mode

### Phase 8: Cloud Readiness

Goal:

- prepare for remote or multi-device usage after the local product is stable

Tasks:

- package the processor service
- add authentication
- define vault sync strategy
- reserve clean adapter boundaries for future OpenClaw integration

Acceptance:

- the service can run outside the local Windows + WSL pairing without re-architecting the knowledge model

---

## 7. Obsidian MVP Schema

The first Obsidian export should stay deliberately small.

Required generated note types:

- source note
- digest note

Required source note fields:

- `title`
- `source_url`
- `canonical_url`
- `platform`
- `content_shape`
- `author`
- `published_at`
- `collected_at`
- `job_id`

Required digest note fields:

- `title`
- `source_ref`
- `summary`
- `key_points`
- `analysis_items`
- `verification_items`
- `warnings`
- `synthesis`
- `tags`
- `related`

Required output directories:

- `Inbox/`
- `Sources/`
- `Assets/`

Do not add topic maps, canvas generation, or publish folders to the first shipping milestone.

---

## 8. GUI Path Decision

The project now has two distinct GUI ideas:

- a real current path: `PySide6`
- a future visual language proposal: `Tauri + React + Tailwind`

The practical decision is:

- keep shipping on `PySide6`
- allow the visual spec to influence layout, typography, color, and interaction
- revisit a Tauri exploration only after Phase 5 or after the service boundary is stable

This avoids replacing working software with an unproven shell at the exact moment the product model is still shifting.

---

## 9. Explicit Non-Goals For The Next Milestone

The next milestone should not attempt:

- a full GUI framework rewrite
- public publishing workflows
- automatic editing of existing vault notes
- deep cloud deployment work
- simultaneous parser rewrite, service cutover, and GUI rewrite

Those combinations would raise delivery risk sharply.

---

## 10. Immediate Next Batch

The next batch should be:

1. patch the remaining real stability issues
2. define the Obsidian note schema in code and docs
3. implement the Obsidian writer MVP
4. refactor the GUI shell enough to support the next visual pass cleanly

That is the shortest credible route from the current prototype to a usable knowledge product.
