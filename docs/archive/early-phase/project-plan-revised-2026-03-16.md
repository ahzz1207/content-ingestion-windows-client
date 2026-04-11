# Revised Project Plan - 2026-03-16

## 1. Purpose

This document revises the newly added `PROJECT_PLAN.md` into a version that is aligned with the current repository state and safe to execute.

It keeps the strongest parts of the original plan:

- the knowledge-pipeline framing
- Obsidian as a first-class destination
- eventual service and cloud evolution
- richer analysis and transcript ambitions

It corrects the parts that do not match the current code reality.

---

## 2. Product Definition

This project should be treated as:

- a personal viewpoint intelligence system

The system takes fragmented content from multiple sources and turns it into:

- normalized source material
- structured analysis
- reusable knowledge notes
- linked topic context

The product is not only:

- a Windows collector
- a WSL processor
- a GUI wrapper

Those are implementation layers inside a larger knowledge workflow.

---

## 3. Current Architecture Baseline

The currently working path is:

```text
Windows GUI / CLI -> shared_inbox -> WSL processor -> processed results
```

Current verified facts:

- the shared-inbox roundtrip is usable
- Windows capture and export are working
- WSL processing and structured result generation are working
- the Windows GUI can already inspect processed results

Current verified risks:

- LLM requests still need explicit timeout handling
- WSL inbox claiming needs stronger hardening
- Windows still has path portability and observability gaps
- the GUI structure needs refactoring before large visual expansion

Important correction:

- this plan must not treat previously disproven critical bug claims as active blockers

---

## 4. Long-Term Architecture Direction

### v0: Local Paired Workflow

```text
Windows client -> shared inbox -> WSL processor -> processed -> Obsidian export
```

This remains the active transport until internal contracts are stable.

### v1: Service Boundary

```text
Client -> Processor API -> analysis pipeline -> Obsidian writer
```

This should happen only after:

- job contract
- progress contract
- result contract
- Obsidian export contract

are stable enough to survive transport migration.

### v2: Cloud and Multi-Device

```text
Desktop / Web / Mobile -> remote service -> vault sync / publish layers
```

This remains a later direction, not the current implementation center.

---

## 5. Module Structure

### Module A: Capture Surface

Responsible for:

- URL intake
- browser and HTTP collection
- attachment capture
- operator feedback

Current owner:

- Windows client

### Module B: Normalization and Analysis Engine

Responsible for:

- payload parsing
- media preprocessing
- transcript normalization
- structured LLM analysis
- evidence assembly

Current owner:

- WSL processor

### Module C: Obsidian Writer

Responsible for:

- vault output
- note generation
- attachment placement
- frontmatter generation
- wikilink formatting

This is the next major product module to add.

### Module D: Vault Index and Knowledge Linking

Responsible for:

- tag reuse
- related-note suggestions
- lightweight vault index generation
- future topic and entity scaffolding

### Module E: Service Layer

Responsible for:

- transport abstraction
- job submission
- progress updates
- health checks
- future remote execution

This should come after Modules C and D have stabilized.

---

## 6. Obsidian Output Model

The first Obsidian milestone should remain small and dependable.

### First Required Output Types

- one source note
- one digest note
- one asset folder when attachments exist

### Required Vault Directories

```text
Vault/
  Inbox/
  Sources/
  Assets/
```

### Source Note Responsibilities

- preserve the original source in readable markdown form
- keep provenance explicit
- retain source metadata

### Digest Note Responsibilities

- expose the structured summary
- key points
- analysis items
- verification items
- warnings
- synthesis
- tags
- related note suggestions

### Important Rules

- do not modify existing vault notes in the MVP
- do not require an Obsidian plugin in the MVP
- do not add publish automation in the MVP

---

## 7. Transcript and Media Strategy

The original plan's transcription discussion is worth keeping, but it needs a cleaner architectural role.

### Core Decision

The system should standardize on a normalized transcript schema first.

Required transcript fields:

- `segment_id`
- `speaker_id` when available
- `start_ms`
- `end_ms`
- `text`
- `confidence`

### Local Preferred Path

- `WhisperX`

Reason:

- faster transcription
- better diarization support
- stronger timestamp alignment
- less hallucination in silence-heavy input

### Cloud Fallback Path

- `AssemblyAI` or another provider that can produce compatible transcript output

### Rule

Local and cloud transcription should both normalize into the same internal transcript contract before the LLM stage.

This keeps the media pipeline stable even if provider choice changes.

---

## 8. GUI Direction

The GUI should evolve toward:

- a knowledge instrument
- not only a task launcher

However, the implementation path for the next milestone remains:

- `PySide6`

The visual ambition from the newer design work should be adopted through:

- better tokens
- stronger typography
- improved result storytelling
- better knowledge actions

not through:

- an immediate framework rewrite

---

## 9. Phase Order

### Phase 0: Contract and Direction Freeze

Tasks:

- freeze the working build order
- freeze the first Obsidian note schema
- freeze the transcript schema
- record `PySide6` as the next-milestone GUI path

### Phase 1: Stability Cleanup

Tasks:

- add LLM timeout handling
- improve provider failure handling
- fix Windows WSL path portability
- harden WSL inbox claiming
- improve Windows logging
- remove the Windows TOML BOM portability issue
- add CI and type / lint gates

### Phase 2: Obsidian Writer MVP

Tasks:

- implement configurable vault root
- generate source notes
- generate digest notes
- export attachments
- add `Open in Obsidian` or `Reveal in Vault`

### Phase 3: Knowledge Metadata

Tasks:

- add tag generation
- add `related` suggestions
- generate a lightweight vault index
- keep linking one-way from new notes to existing notes

### Phase 4: Transcript Upgrade

Tasks:

- add normalized transcript contract
- evaluate WhisperX
- add fallback provider normalization

### Phase 5: GUI G2 on PySide6

Tasks:

- refactor the GUI structure
- introduce design tokens
- upgrade result presentation
- add knowledge actions and stronger command flow

### Phase 6: Service Boundary

Tasks:

- define internal API contracts
- isolate transport-specific code

### Phase 7: FastAPI Service

Tasks:

- implement service endpoints
- implement progress streaming
- keep the shared-inbox fallback during migration

### Phase 8: Cloud Readiness

Tasks:

- packaging
- authentication
- remote vault strategy
- future platform integrations

---

## 10. Immediate Next Batch

The next implementation batch should be:

1. real stability fixes only
2. Obsidian note schema finalization
3. Obsidian writer MVP
4. GUI refactor groundwork for the next visual pass

That is the shortest path to visible user value without destabilizing the working system.
