# Preview 1.0 Boundary Repair Plan

## Purpose

This document defines the repair plan after the local HTTP API, browser entry surfaces, and Obsidian plugin upgrades.

It is intentionally anchored to the project state that was accepted as `Preview 1.0`, then extended only by the latest Windows-side local API work.

The goal is not to redesign the system again.

The goal is to:

- restore a clear Windows / WSL repository boundary
- prevent another data-loss or "which inbox is real" incident
- keep the local HTTP API as a thin, stable entry layer
- keep browser extensions and Obsidian aligned with that same entry layer

## Accepted Baseline

The accepted baseline for this repair plan is:

- `docs/entry-expansion-checkpoint-2026-03-27.md`
- `docs/round2-handoff-2026-03-16.md`
- `docs/windows-wsl-handoff-contract.md`

That baseline implies the following architecture:

```text
Windows entry surface
  -> Windows collector / exporter
  -> shared_inbox/incoming/<job_id>/
  -> WSL watcher / processor
  -> processed/failed result artifacts
  -> Windows result readers (GUI / API / extensions / Obsidian)
```

The local HTTP API is an entry adapter and result reader.
It is not a second processing pipeline.

## Canonical Boundary

### Windows Repository Responsibilities

The Windows repository owns:

- URL intake
- browser-backed and HTTP-backed capture
- metadata hints
- writing protocol-valid inbox jobs
- WSL watcher launch and operational status
- local HTTP API
- GUI, Chrome, Edge, and Obsidian user entry surfaces
- result-oriented read models over WSL outputs
- user-facing archive / cleanup policy

The Windows repository does not own:

- normalization logic
- media processing logic
- LLM analysis, verification, or synthesis logic
- WSL-native result generation

### WSL Repository Responsibilities

The WSL repository owns:

- shared inbox validation
- claiming jobs from `incoming/`
- raw parsing
- normalization
- media processing
- structured analysis, verification, and synthesis
- writing `processed/` and `failed/` outputs
- writing analysis artifacts used by result readers

The WSL repository does not own:

- browser extension behavior
- Obsidian integration behavior
- local HTTP API behavior
- user-facing deletion policy
- new external entry protocols

### Local HTTP API Responsibilities

The local HTTP API is a Windows-side adapter that:

- accepts external client submissions
- reuses the existing Windows exporter path
- reads WSL-generated result artifacts
- exposes stable polling and result endpoints

It must not:

- invent a second handoff protocol
- reimplement WSL analysis logic
- silently mutate WSL-owned result semantics

## Current Problems To Repair

The system drifted away from the accepted boundary in several ways:

1. runtime data inside repo worktrees is too easy to destroy during repo operations
2. the active shared inbox path is not visible enough to operators
3. `processed/` currently behaves like "result assembly in progress" instead of "completed"
4. user-facing delete actions currently risk destroying shared processing history
5. WSL documentation still partially describes an older or more ambiguous ownership model
6. attachments, capture manifests, and analysis artifacts are real runtime contracts now, but are not documented as such
7. browser / Obsidian clients are at risk of compensating for upstream gaps with the wrong product semantics

## Repair Principles

All repair work in this document follows these rules:

1. keep the Preview 1.0 architecture intact
2. do not add a database
3. do not add a new network protocol
4. do not move analysis logic into Windows
5. do not move browser / Obsidian concerns into WSL
6. do not treat repo-local `data/` as a safe long-term runtime store
7. do not add convenience fallbacks that change semantic meaning

## Target End State

After the repair work, the system should look like this:

```text
Windows clients
  -> local HTTP API
  -> Windows exporter
  -> active shared inbox
  -> WSL processing pipeline
  -> completed result artifacts
  -> Windows read models
  -> browser result cards / GUI / Obsidian knowledge import
```

With these guarantees:

- every entry surface can show the active shared root it is using
- deleting a job from a client does not physically destroy shared history by default
- `processed/` means completed, not half-written
- WSL runtime data is outside the repo worktree
- WSL docs describe the processor boundary accurately
- Obsidian only imports real result artifacts and does not fabricate result semantics

## Workstreams

### Workstream A: Data Safety and Storage Boundary

Objective:

- separate source code worktrees from valuable runtime data

Required changes:

- move WSL runtime data out of `~/codex-demo/data/`
- define an explicit WSL runtime root outside the repo worktree
- document the difference between:
  - active shared inbox
  - local WSL runtime data
  - repo source tree
- keep Windows active shared inbox explicit and operator-visible

Recommended WSL runtime layout:

```text
~/.content-ingestion-wsl/
  shared_inbox_local/
  cache/
  profiles/
  sessions/
```

Expected outcome:

- a repo reset, reclone, or replacement no longer threatens runtime assets

### Workstream B: Shared Inbox Truth and Operator Visibility

Objective:

- remove ambiguity about which inbox is real at any moment

Required changes:

- show the active shared root in:
  - Windows GUI
  - local HTTP API diagnostics
  - browser extension settings or status surface
  - Obsidian status view
- make watcher status always include:
  - running state
  - shared root
  - launcher PID
  - log path

Expected outcome:

- operators stop confusing a local repo inbox with the active cross-repo inbox

### Workstream C: WSL Processing State Semantics

Objective:

- make `processed/` mean "completed" again

Current problem:

- the WSL processor currently moves a job into `processed/` before all result files are written

Required changes:

- introduce an explicit finalization stage before `processed/`, or
- otherwise change the implementation so `processed/` is only reached after all required outputs exist

Preferred state model:

```text
incoming -> processing -> finalizing -> processed
incoming -> processing -> failed
```

Required guarantees for `processed/<job_id>/`:

- `normalized.json` exists
- `normalized.md` exists
- `pipeline.json` exists
- `status.json` exists
- any declared result artifacts are either fully present or intentionally absent

Expected outcome:

- Windows readers no longer need to guess whether a `processed/` job is still incomplete

### Workstream D: Archive Instead of Hard Delete

Objective:

- make user cleanup safe

Required changes:

- replace hard delete with archive semantics in:
  - local HTTP API
  - browser extensions
  - Obsidian plugin
- define a shared archive location or shared archive flag model
- keep imported Obsidian notes separate from pipeline job lifecycle

Required behavior:

- deleting from a client removes the job from active lists
- deleting does not physically destroy evidence by default
- GUI history and API history remain reviewable

Expected outcome:

- user cleanup becomes a reversible product action instead of a destructive filesystem action

### Workstream E: WSL Boundary Cleanup

Objective:

- make WSL read as a processor repo again

Required changes:

- rewrite WSL top-level docs around the accepted processor role
- clearly mark `sources/` and `session/` as legacy or non-primary
- stop documenting direct WSL-side fetch/login as if it were the recommended mainline path
- document the real processor contract:
  - inbox input
  - capture manifest
  - attachments
  - media processing
  - LLM outputs
  - processed/failed result artifacts

Expected outcome:

- new contributors no longer confuse the WSL repo with the user-facing entry layer

### Workstream F: API and Client Product Semantics

Objective:

- keep clients honest to WSL result meaning

Required changes:

- document the API as a Windows-side read model over WSL outputs
- keep browser extensions lightweight:
  - submit
  - poll
  - view result cards
  - archive
- keep Obsidian focused on consuming completed results as Source + Digest notes
- do not let clients fabricate meaning that WSL did not produce

Explicit rule for result visuals:

- a Digest may embed `insight_card` when it truly exists
- a client must not substitute unrelated visuals such as a generic video thumbnail and present it as the result card

Expected outcome:

- clients stay aligned with the processor instead of drifting into separate semantics

### Workstream G: WSL Processing Contract Recovery

Objective:

- explicitly preserve the accepted WSL processing and LLM contract instead of letting it disappear behind boundary-only repair work

Why this is needed:

- Preview 1.0 accepted the WSL side as the main processing and result-generation engine
- the current repair plan would be incomplete if it only repaired entry boundaries and storage safety
- the current processing contract already includes media handling, structured analysis, verification, synthesis, and result presentation hints
- that processing work exists today, but it is spread across multiple WSL documents and code paths rather than restated as part of the repaired baseline

The accepted WSL processing baseline to preserve is:

- raw payload parsing
- metadata hint consumption
- capture manifest validation
- attachment-aware asset construction
- media processing for audio and video when attachments exist
- LLM structured analysis
- evidence-grounded verification
- synthesis output
- analysis artifacts such as `analysis/llm/analysis_result.json`
- frontend-facing result metadata such as structured result display hints

Primary references for this processing baseline:

- WSL `docs/round2-wsl-processing-plan-2026-03-15.md`
- WSL `docs/llm-interaction-contract-2026-03-16.md`
- WSL `docs/round2-llm-handoff-2026-03-16.md`

Required changes:

- add one current WSL processing contract document that summarizes the real accepted processor behavior
- explicitly describe the current stages:
  - parse
  - normalize
  - media processing
  - LLM analysis
  - verification
  - synthesis
  - artifact writing
- document which result artifacts are now part of the practical contract:
  - `normalized.json`
  - `normalized.md`
  - `pipeline.json`
  - `status.json`
  - `analysis/llm/analysis_result.json`
  - media and transcript artifacts when available
- document which LLM interaction behaviors are intentionally preserved:
  - structured JSON-schema output
  - evidence references
  - one repair pass for broken evidence references
  - text-first plus optional multimodal verification

Prompt / contract boundary rules:

- prompt evolution remains a WSL concern
- Windows clients must not invent or fork prompt logic
- Windows may render WSL results, but may not redefine analysis semantics
- if the WSL prompt contract changes, the source of truth must be updated in WSL docs and only then reflected in Windows read models

Expected outcome:

- the repair plan protects the accepted WSL intelligence layer instead of accidentally shrinking it out of the documented architecture

### Workstream H: Documentation Realignment

Objective:

- make the accepted architecture readable again

Required changes:

- repair or replace WSL docs with encoding issues
- update both repo READMEs
- update cross-repo collaboration docs
- update the handoff contract to reflect real attachment and analysis artifacts
- add one current "source of truth" architecture document for the post-Preview 1.0 state

Documentation layers after cleanup:

1. Primary docs
   - Windows README
   - WSL README
   - cross-repo collaboration
   - handoff contract
   - Preview 1.0 checkpoint
2. Current implementation docs
   - API contract
   - WSL processing contract
   - Obsidian integration
   - browser extension docs
3. Historical docs
   - earlier plans and snapshots kept as reference only

Expected outcome:

- the written architecture matches the code and operator reality

## Execution Order

The repair plan should be executed in this order:

1. stop destructive delete behavior
2. expose the active shared root everywhere
3. redesign runtime data locations outside repo worktrees
4. repair WSL processing state semantics
5. realign WSL boundary docs
6. recover and restate the WSL processing contract
7. realign API and client semantics
8. finish the cross-repo documentation cleanup

## Deliverables

### Phase 0 Deliverables

- archive replaces hard delete
- active shared root is visible in all entry surfaces
- watcher status is explicit and inspectable

### Phase 1 Deliverables

- WSL runtime root moved outside repo
- migration notes written
- operator docs updated

### Phase 2 Deliverables

- corrected WSL processing state machine
- `processed/` restored to completed-only meaning
- Windows result readers simplified accordingly

### Phase 3 Deliverables

- rewritten WSL README
- rewritten or repaired WSL protocol docs
- cross-repo responsibilities clarified

### Phase 4 Deliverables

- current WSL processing contract document added
- LLM contract inheritance clarified
- result artifact contract documented

### Phase 5 Deliverables

- API contract document aligned with read-model responsibilities
- browser and Obsidian docs aligned with non-destructive client roles

## Acceptance Criteria

The repair work is complete only when all of the following are true:

- a repo sync or reset can no longer erase valuable runtime data by default
- operators can identify the active shared root without inspecting code
- `processed/` no longer exposes half-written jobs
- archive actions no longer erase shared history
- WSL docs describe processor responsibilities only
- Windows docs describe the local API as an adapter over the shared inbox contract
- browser and Obsidian clients only consume real result semantics

## Non-Goals

This repair plan explicitly does not include:

- introducing a database
- introducing a cloud sync layer
- moving analysis into Windows
- giving WSL a new external HTTP API
- turning browser extensions into a heavy workstation
- turning Obsidian into a background sync engine
- broadening the project into claim/topic/entity knowledge graph generation

## Final Definition

The repaired post-Preview 1.0 architecture is:

```text
Windows owns every external client surface and the local HTTP API.
WSL owns every processing, analysis, and result-generation step after inbox handoff.
The shared inbox remains the stable cross-boundary contract.
Runtime data must not depend on the safety of a repo worktree.
```

This is the boundary that all follow-up implementation work should preserve.
