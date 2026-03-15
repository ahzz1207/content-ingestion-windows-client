# content-ingestion Monorepo

This repository contains the end-to-end content ingestion system across two applications:

- a Windows-side capture and export application
- a processing application that runs in WSL/Linux

The system is designed around a shared inbox-style contract:

1. the Windows app captures content from URLs, pages, or media platforms
2. it exports a structured job into the shared inbox
3. the processing app ingests that job
4. the processing app normalizes, analyzes, verifies, and synthesizes the result

## Repository Layout

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

## Applications

### `apps/windows-client`

Owns:

- GUI
- Windows-side URL and browser capture
- job export
- Windows -> WSL bridge
- platform routing
- optional `yt-dlp` download behavior for supported video sites

Does not own:

- content normalization policy
- transcript analysis logic
- summary / analysis / verification semantics

### `apps/content-ingestion`

Owns:

- inbox protocol validation
- normalization
- transcript pipeline
- evidence construction
- summary / analysis / verification
- source-grounded synthesis

Does not own:

- Windows GUI behavior
- Windows browser-profile lifecycle
- Windows-side capture UX

## Shared Contract

The two apps communicate through a shared handoff contract.

See:

- `contracts/inbox-job-schema.md`
- `contracts/capture-manifest-schema.md`
- `contracts/result-schema.md`
- `contracts/attachment-roles.md`

Any change to the handoff contract should update:

- the contract docs
- the Windows exporter
- the WSL reader
- integration tests

## Development Model

This repository is managed as a monorepo with separate app ownership.

Rules:

- Windows-only work stays in `apps/windows-client`
- WSL-only work stays in `apps/content-ingestion`
- contract changes require cross-app validation
- integration tests protect the Win -> WSL roundtrip

## Running Tests

Run tests per application instead of treating the repository as one Python environment.

### Windows client

```powershell
cd apps/windows-client
python -m unittest discover -s tests -p "test_*.py"
```

### Content ingestion

```bash
cd apps/content-ingestion
pytest -q
```

### Integration

Integration tests should live under `tests/integration`.

The initial integration scope should include:

- article smoke
- Bilibili audio-only smoke
- Bilibili full-video smoke

## Runtime Notes

Typical local dependencies across the two apps include:

- Python
- Playwright
- `yt-dlp`
- `ffmpeg`
- Whisper
- OpenAI SDK

Not every dependency is required in both apps.

## Current Focus

The current architecture focus is:

- stable Windows capture for text, audio, and video content
- richer WSL processing for normalization, transcript handling, analysis, verification, and synthesis
- clearer contract ownership between capture and processing

## Related Docs

See the planning docs in `docs/` for repository migration and ownership:

- `docs/monorepo-github-plan-2026-03-15.md`
- `docs/monorepo-migration-checklist-2026-03-15.md`
