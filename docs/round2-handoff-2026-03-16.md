# Round 2 Handoff 2026-03-16

This document records the current Windows-side stopping point for Round 2.

## What Landed

- the GUI result preview now prefers structured WSL output when available
- the result workspace now renders:
  - summary
  - key points
  - analysis items
  - verification items
  - warnings
- the task page polling path was tightened so jobs do not stay on stale `still processing` state after the result workspace closes
- the WSL bridge now forwards supported LLM environment variables into:
  - watcher startup
  - one-shot WSL commands
- the current bridge path supports:
  - `OPENAI_*`
  - `ZENMUX_*`
  - analysis and multimodal model overrides

## Current Verified Behavior

- GUI -> Windows export -> shared inbox -> WSL processing is healthy
- WeChat article intake now reaches the WSL processor and produces structured results
- the result page can now show structured result sections instead of only normalized markdown
- watcher status can be refreshed from the GUI path without the earlier stale-state bug

## Current Windows-Side Scope

The Windows client is currently responsible for:

- URL intake
- browser-backed page capture
- platform routing
- non-destructive handoff into the shared inbox
- result preview and workspace browsing
- operational bridge calls into the WSL processor

The Windows client is not the place to implement analysis logic.
That work now sits primarily on the WSL side.

## Current Risks

- content denoise still needs to keep improving before every text + image payload is trustworthy enough for LLM use
- Windows still needs a stricter rule for which article images are meaningful enough to send into the main LLM request path
- the bridge depends on the WSL watcher staying aligned with the latest WSL code and environment

## Next Recommended Build Order

1. keep article capture quality high enough that text + image handoff is trustworthy
2. align Windows image selection with the new WSL `text_image`-first contract
3. keep GUI preview aligned with the structured result contract as WSL output evolves
4. after the Round 2 path is usable end-to-end, revisit monorepo migration
