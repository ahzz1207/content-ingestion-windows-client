# Phase 1 Usable Release 2026-03-14

## Purpose

This document marks the point where the first round can be treated as usable, not only internally demoable.

Usable here means:

- a Windows operator can submit URLs through CLI or GUI
- WSL processing can be checked and controlled from the Windows repo
- the Win -> WSL path has a repeatable smoke test
- the GUI can surface enough environment state to explain why results may or may not appear

---

## What Is In Scope For The Usable Baseline

The current baseline now includes:

- Windows URL export through HTTP and browser paths
- browser login warm-up for login-bound sites
- structured handoff into `shared_inbox`
- WSL processing into `processed/` or `failed/`
- GUI URL entry plus result workspace browsing
- Windows-side WSL operational commands:
  - `wsl-doctor`
  - `wsl-validate-inbox`
  - `wsl-watch-once`
  - `wsl-start-watch`
  - `wsl-watch-status`
  - `wsl-stop-watch`
  - `full-chain-smoke`

---

## Recommended First-Round Operating Path

For normal use:

1. Start the WSL watcher once from the Windows repo:
   - `python main.py wsl-start-watch --interval-seconds 2`
2. Confirm it is alive:
   - `python main.py wsl-watch-status`
3. Launch the GUI:
   - `python main.py gui`
4. Paste a URL and start processing
5. Use the result workspace after WSL processing completes

For fast regression checks:

- `python main.py full-chain-smoke https://example.com/`

This runs a Windows export, asks WSL to validate the inbox, runs a one-shot WSL consume pass, and confirms that a result directory exists.

---

## Release Signals Confirmed

The following signals were re-confirmed for this usable checkpoint:

- Windows unit tests: `62 passed`
- WSL unit tests: `23 passed`
- `wsl-doctor` works from the Windows repo
- `wsl-start-watch -> wsl-watch-status -> wsl-stop-watch` works from the Windows repo
- `full-chain-smoke` succeeds against the formal shared inbox root
- with `wsl-start-watch` left running, newly exported HTTP jobs are auto-consumed into `processed/` without manual WSL intervention
- real WeChat browser payload replay still produces a valid WSL normalized result

---

## What Makes This Better Than The Prior Baseline

Before this checkpoint, the product was already functionally coherent, but still awkward to operate:

- WSL health checks lived in a different repo context
- inbox validation and one-shot processing required hand-written `wsl.exe` commands
- there was no stable background watcher control path from Windows
- the GUI could not tell you whether the WSL watcher was running

That gap is now closed enough for a first usable release.

---

## Frozen Boundary For Round One

Do not expand these areas further in the first round unless a concrete bug is found:

- GUI information architecture
- result workspace scope
- current text-first reading model
- current WSL operational surface

Do not pull these into Round One:

- richer WSL semantic analysis
- image, table, or video understanding
- queue/history systems
- search/filtering
- real-time WSL event streaming
- cross-job dashboards

---

## Phase 2 Direction

Phase 2 should move away from "make the chain usable" and into "make the processed result richer."

That next round should focus on:

- deeper WSL enrichment
- richer normalized outputs for structured reading
- support for non-text content types such as images, tables, and video
- GUI result surfaces that can render those richer output types cleanly
