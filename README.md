# Windows Client for `content-ingestion`

This repository is the Windows-side workspace for the `content-ingestion` project.

The current goal is not to build the final GUI immediately. The active path is:

1. accept a URL
2. collect or mock content on Windows
3. write a valid inbox job into `shared_inbox/incoming/<job_id>/`
4. let the existing WSL processor handle it successfully

The primary alignment document for this repository is:

- `docs/windows-client-kickoff.md`
- `docs/pre-gui-checkpoint-2026-03-14.md`
- `docs/gui-phase1-design-2026-03-14.md`
- `docs/gui-phase1-implementation-2026-03-14.md`
- `docs/gui-convergence-checkpoint-2026-03-14.md`
- `docs/gui-closeout-2026-03-14.md`
- `docs/gui-result-workspace-direction-2026-03-14.md`
- `docs/full-chain-check-2026-03-14.md`
- `docs/phase1-usable-release-2026-03-14.md`
- `docs/phase1-handoff-2026-03-15.md`
- `docs/round2-handoff-2026-03-16.md`
- `docs/code-review-followup-2026-03-16.md`
- `docs/obsidian-integration-roadmap-2026-03-16.md`
- `docs/gui-vision-2026-03-16.md`
- `docs/cross-review-2026-03-14.md` for internal review history and cross-check notes; it is background material, not required reading
- `docs/windows-wsl-handoff-contract.md`
- `docs/windows-wsl-roundtrip.md`
- `docs/monorepo-github-plan-2026-03-15.md`
- `docs/monorepo-migration-checklist-2026-03-15.md`
- `docs/monorepo-root-readme-draft-2026-03-15.md`
- `docs/monorepo-root-gitignore-draft-2026-03-15.txt`
- `docs/monorepo-path-cutover-inventory-2026-03-15.md`

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

Quick commands:

- `python main.py doctor`
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

Current milestone status:

- Milestone 0: done
- Milestone 1: done for mock exporter baseline
- Milestone 1 polish: done for defaults, validation, and doctor output
- Milestone 2 slice 1: done for simple HTTP collection and handoff
- Milestone 2 slice 2: done for browser-backed collection and handoff
- Milestone 2 slice 3: done for browser runtime knobs, profile warm-up workflow, WeChat profile reuse, and selector waits
