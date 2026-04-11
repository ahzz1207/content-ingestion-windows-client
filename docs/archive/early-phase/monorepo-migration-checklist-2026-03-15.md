# Monorepo Migration Checklist

## Scope

This checklist is for moving:

- the current Windows workspace at `H:/demo-win`
- the current WSL workspace at `/home/ahzz1207/codex-demo`

into one GitHub repository with this target shape:

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
    content-ingestion/
```

The goal is to move both applications into one repository without flattening them into one package.

## Phase 0: Freeze and Inventory

- [ ] Confirm both current workspaces are in a known good state.
- [ ] Record the exact test commands that currently pass on Windows.
- [ ] Record the exact test commands that currently pass on WSL.
- [ ] Record the current runtime prerequisites:
  - Python version on Windows
  - Python version on WSL
  - Playwright requirements
  - `yt-dlp`
  - `ffmpeg`
  - Whisper
  - OpenAI SDK / `OPENAI_API_KEY`
- [ ] Record all machine-specific paths and environment variables.

Done means:

- both sides have a documented baseline
- no path assumption is left implicit

## Phase 1: Create the Target Repository Skeleton

- [ ] Create the new GitHub repository.
- [ ] Add the root folders:
  - `apps/windows-client`
  - `apps/content-ingestion`
  - `contracts`
  - `docs`
  - `scripts`
  - `tests/integration`
- [ ] Add a root `.gitignore`.
- [ ] Add a root `README.md`.

Done means:

- the empty monorepo layout exists
- the repository can be cloned without app code yet

## Phase 2: Move the Windows Application

- [ ] Copy the current Windows app into `apps/windows-client`.
- [ ] Keep the current app structure intact on first move:
  - `main.py`
  - `pyproject.toml`
  - `src/windows_client`
  - `tests`
  - app-specific docs if still needed
- [ ] Verify Windows commands still run from `apps/windows-client`.
- [ ] Verify Windows tests still pass from `apps/windows-client`.

Recommended path mapping:

- `H:/demo-win/main.py` -> `apps/windows-client/main.py`
- `H:/demo-win/pyproject.toml` -> `apps/windows-client/pyproject.toml`
- `H:/demo-win/src/windows_client` -> `apps/windows-client/src/windows_client`
- `H:/demo-win/tests` -> `apps/windows-client/tests`

Done means:

- Windows behavior still works after the move
- no cross-app refactor has been mixed into the move step

## Phase 3: Move the WSL Application

- [ ] Copy the current WSL app into `apps/content-ingestion`.
- [ ] Keep the current WSL app structure intact on first move:
  - `main.py`
  - `pyproject.toml`
  - `src/content_ingestion`
  - `tests`
- [ ] Verify WSL commands still run from `apps/content-ingestion`.
- [ ] Verify WSL tests still pass from `apps/content-ingestion`.

Recommended path mapping:

- `/home/ahzz1207/codex-demo/main.py` -> `apps/content-ingestion/main.py`
- `/home/ahzz1207/codex-demo/pyproject.toml` -> `apps/content-ingestion/pyproject.toml`
- `/home/ahzz1207/codex-demo/src/content_ingestion` -> `apps/content-ingestion/src/content_ingestion`
- `/home/ahzz1207/codex-demo/tests` -> `apps/content-ingestion/tests`

Done means:

- WSL behavior still works after the move
- no new processing logic is mixed into the move step

## Phase 4: Extract the Shared Contract

- [ ] Move shared protocol documentation into `contracts/`.
- [ ] Define or update:
  - inbox job structure
  - `metadata.json`
  - `capture_manifest.json`
  - result artifacts
  - attachment role vocabulary
- [ ] Add contract examples or fixtures.
- [ ] Ensure contract changes are no longer hidden inside app-local docs only.

Good candidates to move or mirror:

- Windows/WSL handoff docs
- result vocabulary docs
- attachment role definitions

Done means:

- shared protocol is visible at repo root
- both apps consume the same documented contract

## Phase 5: Remove Hard-Coded Path Assumptions

- [ ] Update the Windows bridge so it no longer assumes `/home/ahzz1207/codex-demo`.
- [ ] Replace any repo-root assumptions with repo-relative configuration.
- [ ] Review scripts, docs, and tests for old paths.
- [ ] Make the new defaults match the monorepo layout.

Done means:

- the same repository layout works on another machine without editing code

## Phase 6: Clean Runtime Artifacts

- [ ] Make sure these are ignored at repo root:
  - `__pycache__/`
  - `.pytest_cache/`
  - `.venv/`
  - `dist/`
  - `build/`
  - `*.egg-info/`
  - browser profiles
  - shared inbox job data
  - processed artifacts
  - logs
- [ ] Remove local runtime artifacts before the first push.
- [ ] Keep only intentional placeholders like `.gitkeep`.

Done means:

- the first GitHub push is clean
- runtime data does not pollute version control

## Phase 7: Add CI and Integration Checks

- [ ] Add a Windows CI job for `apps/windows-client`.
- [ ] Add a Linux CI job for `apps/content-ingestion`.
- [ ] Add a contract validation job.
- [ ] Add at least one end-to-end integration smoke test.

Recommended first integration tests:

- [ ] article smoke
- [ ] Bilibili audio-only smoke
- [ ] Bilibili full-video smoke

Done means:

- both app-local tests and shared integration checks run from one repository

## Phase 8: GitHub Project Management Setup

- [ ] Create labels:
  - `windows-capture`
  - `wsl-processing`
  - `contract-schema`
  - `integration`
  - `infra-ci`
  - `bug`
  - `enhancement`
  - `docs`
- [ ] Create milestones:
  - `Monorepo Setup`
  - `Contract Stabilization`
  - `Media Processing Baseline`
  - `LLM Analysis and Verification`
  - `Platform Depth`
- [ ] Define PR rules in the repository README or contributing guide.

Done means:

- the repository is not only uploadable, but also maintainable

## Phase 9: Cut Over

- [ ] Push the monorepo to GitHub.
- [ ] Confirm both apps still run from the monorepo layout.
- [ ] Confirm at least one Win -> WSL roundtrip still works.
- [ ] Mark the monorepo as the source of truth.
- [ ] Archive or freeze the old separate locations.

Done means:

- development can continue only in the monorepo

## First Push Gate

Do not make the first GitHub push until all of these are true:

- [ ] root layout exists
- [ ] both apps have their own `README.md`
- [ ] both apps still run from their new locations
- [ ] root `.gitignore` is clean
- [ ] contract docs exist
- [ ] CI exists for both apps
- [ ] at least one integration smoke test exists

## Current Recommendation

The next concrete step should be:

1. create the empty monorepo repository
2. move both apps without refactoring them
3. only then fix paths, contracts, and CI

Do not combine file moves, protocol redesign, and new feature work into one migration PR.
