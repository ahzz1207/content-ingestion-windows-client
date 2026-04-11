# Monorepo GitHub Plan

## Goal

Put the current Windows-side workspace and the current WSL-side workspace into one GitHub repository without collapsing them into one Python package.

The target shape is:

```text
repo/
  README.md
  .gitignore
  docs/
  contracts/
  scripts/
  tests/
    integration/
  apps/
    windows-client/
      README.md
      pyproject.toml
      main.py
      src/windows_client/
      tests/
    content-ingestion/
      README.md
      pyproject.toml
      main.py
      src/content_ingestion/
      tests/
```

## Why This Shape

- Windows and WSL are separate applications with separate runtime assumptions.
- Each side already has its own entrypoint, dependency graph, and test suite.
- The shared contract is important, but the implementations should stay isolated.
- A flat merge at repo root would create avoidable collisions in `main.py`, `pyproject.toml`, tests, docs, and release flow.

## Ownership Model

Treat the repository as three change domains:

1. `apps/windows-client`
2. `apps/content-ingestion`
3. `contracts` plus `tests/integration`

Change policy:

- Windows-only feature work should stay inside `apps/windows-client`.
- WSL-only processing work should stay inside `apps/content-ingestion`.
- Any inbox/handoff/schema change must update both sides and the integration tests in the same PR.

## Repository Layout Rules

### `apps/windows-client`

Owns:

- GUI
- Windows URL/browser capture
- job export
- Windows -> WSL bridge
- platform routing
- `yt-dlp` download behavior on Windows

Should not own:

- content normalization semantics
- transcript analysis logic
- summary / analysis / verification policy

### `apps/content-ingestion`

Owns:

- inbox protocol validation
- normalization
- transcript pipeline
- LLM analysis / verification
- source-grounded evidence construction

Should not own:

- Windows GUI behavior
- Windows browser profile lifecycle
- Windows download UX

### `contracts`

Owns:

- inbox directory protocol
- `metadata.json` schema
- `capture_manifest.json` schema
- attachment role vocabulary
- result file vocabulary

Recommended files:

```text
contracts/
  inbox-job-schema.md
  capture-manifest-schema.md
  result-schema.md
  attachment-roles.md
```

## GitHub Project Management

### Labels

Use a small fixed set:

- `windows-capture`
- `wsl-processing`
- `contract-schema`
- `integration`
- `infra-ci`
- `bug`
- `enhancement`
- `docs`

Optional priority labels:

- `p0`
- `p1`
- `p2`

### Milestones

Recommended milestone sequence:

1. `Monorepo Setup`
2. `Contract Stabilization`
3. `Media Processing Baseline`
4. `LLM Analysis and Verification`
5. `Platform Depth`

### Issue Shape

Each issue should answer:

- which app owns the change
- whether contract changes are required
- how it will be verified
- whether it affects GUI, WSL processing, or both

Good issue examples:

- `windows-capture`: Bilibili browser capture should export transcript-friendly artifacts
- `wsl-processing`: Whisper transcript output should become evidence segments
- `contract-schema`: add `video_download_mode` to metadata and capture manifest
- `integration`: end-to-end test for Bilibili audio-only export

## Branch and PR Rules

Recommended branch naming:

- `codex/windows-...`
- `codex/wsl-...`
- `codex/contract-...`
- `codex/integration-...`

PR rules:

- A PR that changes `contracts/` must also update both affected apps or clearly prove backward compatibility.
- A PR that changes the inbox manifest must include at least one integration test.
- A PR should not mix unrelated Windows UX work with WSL analysis changes.
- Keep PRs single-purpose whenever possible.

## CI Structure

Use separate CI jobs, not one giant environment.

Recommended workflow matrix:

1. `windows-client-tests`
- runner: Windows
- working dir: `apps/windows-client`
- runs unit tests for Windows app

2. `content-ingestion-tests`
- runner: Ubuntu
- working dir: `apps/content-ingestion`
- runs WSL/content-ingestion unit tests

3. `contract-check`
- runner: Ubuntu
- validates schema examples and fixture compatibility

4. `integration-smoke`
- runner: Windows or self-hosted split flow
- validates a minimal exported job and processed result contract

## Ignore Policy

Before upload, the monorepo root `.gitignore` should exclude:

```text
__pycache__/
.pytest_cache/
.venv/
dist/
build/
*.egg-info/

apps/windows-client/data/
apps/content-ingestion/data/

*.log
```

Keep only intentional placeholders like `.gitkeep`.

Do not commit:

- local browser profiles
- shared inbox job data
- processed artifacts
- local session state
- `.venv`
- `UNKNOWN.egg-info`

## Migration Sequence

Do this in phases.

### Phase 1: Prepare

- freeze current Windows repo state
- freeze current WSL repo state
- export a reference list of commands and tests from both sides
- identify all environment variables and machine-specific paths

### Phase 2: Create Target Skeleton

- create the monorepo root
- create `apps/windows-client`
- create `apps/content-ingestion`
- create `contracts`
- create `tests/integration`

### Phase 3: Move Without Refactoring

- copy Windows code into `apps/windows-client`
- copy WSL code into `apps/content-ingestion`
- do not redesign modules during this step
- keep imports and entrypoints working first

### Phase 4: Fix Path Assumptions

- replace hard-coded WSL project root assumptions
- make Windows bridge compute repo-relative app paths
- make docs and scripts reference the new monorepo layout

### Phase 5: Add Integration Tests

- one article smoke
- one audio-only Bilibili smoke
- one full-video Bilibili smoke

### Phase 6: Cut Over

- archive the old separate repo locations
- declare the monorepo as source of truth

## Immediate Refactors Needed After Merge

These are worth planning now:

- Windows `wsl_project_root` must stop defaulting to `/home/ahzz1207/codex-demo`
- shared protocol docs should move out of app-specific docs into `contracts/`
- duplicated docs should be split into:
  - app docs
  - contract docs
  - milestone docs

## Recommended Root README

The root README should describe:

- what the overall system does
- what `apps/windows-client` does
- what `apps/content-ingestion` does
- how the inbox contract connects them
- how to run tests per app

It should not try to document every command inline.

## Recommended First GitHub Deliverables

Before opening the repository publicly or to collaborators, make sure the first commit includes:

- clean monorepo layout
- working READMEs for both apps
- root `.gitignore`
- contract docs
- CI for both apps
- at least one integration smoke test

## Current Recommendation

Do not upload the two current repositories into one GitHub repository as-is.

First create the monorepo skeleton and move both apps into `apps/`.
That gives you:

- clean ownership
- cleaner CI
- safer protocol evolution
- fewer path and dependency conflicts
