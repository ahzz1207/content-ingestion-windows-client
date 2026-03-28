# Windows Client for `content-ingestion`

This repository is the Windows-side workspace for the `content-ingestion` project.

The current goal is not to build the final GUI immediately. The active path is:

1. accept a URL
2. collect or mock content on Windows
3. write a valid inbox job into `shared_inbox/incoming/<job_id>/`
4. let the existing WSL processor handle it successfully

The primary alignment documents for this repository are grouped below by purpose.

Architecture and contracts:

- `Content-Ingestion-架构分析.md`
- `docs/architecture-2026-03-22.md`
- `docs/windows-wsl-handoff-contract.md`
- `docs/windows-wsl-roundtrip.md`

Product direction:

- `Content-Ingestion-线1-入口扩展规划.md`
- `docs/roadmap-2026.md`
- `docs/project-plan-revised-2026-03-16.md`
- `docs/obsidian-integration-roadmap-2026-03-16.md`

Current implementation:

- `docs/entry-expansion-checkpoint-2026-03-27.md`
- `docs/changelog-2026-03-22.md`
- `docs/round2-handoff-2026-03-16.md`
- `docs/round2-foundation-2026-03-15.md`
- `docs/result-product-refactor-2026-03-20.md`
- `docs/processing-triage-2026-03-18.md`

GUI and design:

- `docs/gui-vision-2026-03-16.md`
- `docs/gui-direction-editorial-workspace-2026-03-17.md`
- `docs/visual-design-spec-revised-2026-03-16.md`

Engineering:

- `docs/code-review-followup-2026-03-16.md`
- `docs/executable-plan-2026-03-16.md`
- `docs/monorepo-github-plan-2026-03-15.md`

Background and historical reference:

- `docs/cross-review-2026-03-14.md`
- `docs/session-memory-2026-03-20.md`

Current implementation status:

- repository scaffold created
- Windows-side scope and module boundaries documented
- CLI-first structure proposed
- mock job exporter implemented
- default local shared inbox added at `data/shared_inbox`
- `export-url-job` implemented for simple `html/txt/md` pages
- `export-browser-job` implemented with Playwright-backed page capture
- browser export supports `profile-dir`, `browser-channel`, `wait-until`, `timeout-ms`, `settle-ms`, `wait-for-selector`, and `--headed`
- WeChat metadata hints now capture `platform`, `title_hint`, `author_hint`, and `published_at_hint`
- `browser-login` command added for warming and reusing persistent profiles
- WeChat browser export now auto-reuses `data/browser-profiles/wechat` when `--profile-dir` is omitted
- collector/exporter failures now surface structured `error_code`, `error_stage`, and `error_detail.*` output on stderr
- exported metadata now carries `final_url`, `collection_mode`, and browser capture context when available
- unit tests added for exporter, metadata extraction, service defaults, HTTP collection, and browser collector behavior
- mock export, real URL export, browser export, and real WeChat article export have all been validated against the WSL processor
- a first PySide6 GUI shell now exists for URL input, auto routing, login guidance, progress state, and success/failure presentation
- the GUI now includes a first result-workspace entry for browsing recent WSL states from `incoming/`, `processing/`, `processed/`, and `failed/`
- the result workspace now prefers structured WSL output when available, including summary, key points, analysis, verification, and warnings
- the WSL bridge now forwards supported LLM environment variables into watcher and one-shot WSL commands
- a local HTTP API now exists at `python main.py serve`, reusing the same Windows exporter and shared inbox contract
- the local HTTP API now exposes both lightweight job summaries and result-oriented views for completed or failed jobs
- a Chrome extension MVP now exists in `chrome-extension/` as the first HTTP API consumer
- the Chrome and Edge extension popups now render lightweight result cards for queued, processing, completed, and failed jobs
- an Obsidian plugin now exists in `obsidian-plugin/` for URL submission, job review, and importing completed results into Source + Digest notes

Quick commands:

- `python main.py doctor`
- `python main.py serve`
- `python main.py gui`
- `python main.py gui --debug-console`
- `python main.py browser-login --start-url https://mp.weixin.qq.com/`
- `python main.py export-mock-job <url>`
- `python main.py export-url-job <url>`
- `python main.py export-browser-job <url>`
- `python main.py full-chain-smoke https://example.com/`
- `python main.py wsl-doctor`
- `python main.py wsl-validate-inbox`
- `python main.py wsl-watch-once`
- `python main.py wsl-start-watch --interval-seconds 2`
- `python main.py wsl-watch-status`
- `python main.py wsl-stop-watch`
- `python main.py export-browser-job https://mp.weixin.qq.com/s/<id> --wait-for-selector '#js_content'`
- `python main.py export-browser-job <url> --profile-dir <dir> --wait-until domcontentloaded --timeout-ms 5000 --settle-ms 0`

New entry surfaces:

- `chrome-extension/` for the first browser-based HTTP API validation path
- `edge-extension/` for the Edge variant of the same local HTTP API flow
- `obsidian-plugin/` for the first Obsidian command/status-view integration

Local API result surfaces:

- `GET /api/v1/health`
- `POST /api/v1/ingest`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs?view=result_cards`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/result`

Shared inbox configuration:

- prefer `CONTENT_INGESTION_SHARED_INBOX_ROOT` when coordinating with the WSL repo
- an explicit `--shared-root` still overrides the environment variable

Current default behavior:

- if `--shared-root` is omitted and `CONTENT_INGESTION_SHARED_INBOX_ROOT` is set, jobs use that shared inbox root
- if neither `--shared-root` nor `CONTENT_INGESTION_SHARED_INBOX_ROOT` is set, jobs are written to `data/shared_inbox`
- if `--content-type` is omitted, the mock path uses `html`
- if `--content-type` is omitted on `export-url-job`, the collector infers `html/txt/md`
- `export-browser-job` captures `payload.html` through Playwright Chromium
- browser defaults are `headless=True`, `wait_until=networkidle`, `timeout_ms=30000`, `settle_ms=1000`
- if `browser-login` omits `--profile-dir`, a platform-aware or host-aware profile directory under `data/browser-profiles` is chosen automatically
- if `export-browser-job` omits `--profile-dir` for a known platform such as WeChat, the matching profile is reused automatically
- if `--wait-for-selector` is provided, browser export waits for that selector before reading the page HTML
- if `--platform` is omitted, `generic` is used
- failed commands exit with code `1` and print structured error diagnostics to stderr for CLI or future GUI wrappers
- `windows_client.app.workflow` and `windows_client.app.view_models` now provide GUI-facing success/error state adapters on top of the service layer
- `windows_client.app.wsl_bridge` now provides Windows-side operational entry points for WSL doctor, inbox validation, watch lifecycle, and smoke checks
- those GUI-facing modules do not have direct CLI commands; they are intended to be called by the future desktop shell
- `python main.py gui` now detaches from the current terminal on Windows and launches the GUI without keeping the console in front; use `--debug-console` to keep the console attached
- the GUI environment pills now include WSL watcher state so it is easier to spot when results will not arrive automatically
- `GET /api/v1/jobs` defaults to `view=summary` for lightweight polling and badge refresh
- `GET /api/v1/jobs?view=result_cards` returns browser-friendly cards with headline, one-line take, verification signal, warning count, and failure summary
- `GET /api/v1/jobs/{job_id}/result` returns completed or failed result details, but returns `409` while a job is still queued or processing

Recommended validation path for this round:

1. Install the local API dependencies with `pip install -e ".[api]"`
2. Start the local API server with `python main.py serve`
3. Load the Chrome or Edge extension and confirm the popup shows lightweight result cards rather than only raw queue items
4. Submit one ordinary page and one known rich result page, then wait for the jobs to move into `processed/` or `failed/`
5. Open the Obsidian plugin status view and use `Import notes` on a completed job
6. Confirm the vault now contains one note under `01 Sources/` and one note under `02 Digests/` for the same `job_id`

Current milestone status:

- Milestone 0: done
- Milestone 1: done for mock exporter baseline
- Milestone 1 polish: done for defaults, validation, and doctor output
- Milestone 2 slice 1: done for simple HTTP collection and handoff
- Milestone 2 slice 2: done for browser-backed collection and handoff
- Milestone 2 slice 3: done for browser runtime knobs, profile warm-up workflow, WeChat profile reuse, and selector waits
