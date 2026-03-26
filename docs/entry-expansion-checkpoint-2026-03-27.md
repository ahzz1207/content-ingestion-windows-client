# Entry Expansion Checkpoint - 2026-03-27

This checkpoint records the first implementation pass for the "line 1" direction in the latest planning documents:

- `Content-Ingestion-架构分析.md`
- `Content-Ingestion-线1-入口扩展规划.md`

The goal of this round was not to replace the existing Windows -> WSL file handoff, but to put a stable local HTTP entry layer in front of it and validate that layer with the first external clients.

## What changed

### 1. Local HTTP API on the Windows side

A new local API module now exists under `src/windows_client/api/`.

Current endpoints:

- `GET /api/v1/health`
- `POST /api/v1/ingest`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`

Important implementation constraint:

- the API does not invent a new handoff format
- `POST /api/v1/ingest` reuses the existing Windows exporter/service path
- jobs are still written as standard inbox directories with `payload.*`, `metadata.json`, and `READY`

This keeps the API as a thin adapter over the existing `shared_inbox` contract rather than a competing pipeline.

### 2. CLI entry for the API server

The Windows CLI now exposes:

- `python main.py serve`

This starts the local API server on `127.0.0.1:19527` by default and uses the same shared inbox root as the rest of the Windows client.

### 3. Chrome extension MVP

A first browser entry now exists in `chrome-extension/`.

Current scope:

- submit current tab
- submit a pasted URL
- show recent jobs
- update badge count from queued + processing jobs
- store local API URL and API token in extension storage

During validation, a practical issue appeared for Bilibili URLs:

- synchronous submission could feel stuck while waiting for video-related work

That was corrected by changing the extension/API submission path so browser entry submission defaults to fast queueing instead of synchronous video download behavior.

### 4. Edge extension MVP

An Edge variant now exists in `edge-extension/`.

It mirrors the Chrome extension flow and is intended to validate the same local HTTP API behavior inside Microsoft Edge.

### 5. Obsidian plugin MVP

A first Obsidian plugin now exists in `obsidian-plugin/`.

Current scope:

- command palette URL submission
- status side view for recent jobs
- settings for API base URL and token

Important correction:

- settings persistence uses whole-object `loadData()` / `saveData()`
- it does not misuse those APIs as key-value storage

The plugin was built successfully and `main.js` is present for installation.

### 6. WSL watcher auto-start from entry points

A real usability gap appeared during browser validation:

- the API could queue work successfully
- but jobs would remain in `incoming/` if the WSL watcher had not been started manually

This was fixed by making both entry points ensure the watcher is running:

- `python main.py serve`
- `python main.py gui`

Current behavior:

- if the watcher is already running, the existing watcher is reused
- if it is not running, it is started automatically

This makes the browser/API path behave like a usable end-to-end product instead of a half-manual demo.

## Validation results

Validation completed in this round:

- local API server starts successfully
- Chrome extension was manually validated against a real Bilibili page
- queued job was confirmed to move into `processed/` once watcher auto-start was corrected
- Edge extension package was prepared
- Obsidian plugin dependencies installed and build completed

Automated checks at the end of the round:

- Python test suite: `165 passed`
- Obsidian plugin build: `npm run build`

## Current direction after this checkpoint

The next priority should remain aligned with the two planning documents:

1. keep the local HTTP API as the single entry surface for external clients
2. deepen browser-based validation and result inspection rather than adding many new protocols
3. move Obsidian from "submit URL" toward "consume processed result as knowledge artifact"

The architecture direction is still:

- Windows local clients and extensions submit through a single local HTTP surface
- the stable cross-boundary contract remains the file-based shared inbox
- WSL remains the processor and result generator

This round establishes the first usable version of that model.
