# Round 2 Foundation 2026-03-15

This document records the first implementation step of Round 2.

## What Landed

- Windows export is now non-destructive.
- `payload.*` remains the Phase 1 compatible primary payload.
- richer capture context is exported into `capture_manifest.json`
- auxiliary artifacts are stored under `attachments/`
- HTML capture now exports derived correctness artifacts such as visible text, media manifest, and capture validation
- Windows now has a first-class `yt-dlp` video download path for Bilibili and YouTube
- WSL validates `capture_manifest.json` when present
- WSL surfaces capture manifest context into `normalized.json`, `pipeline.json`, and `status.json`
- WSL surfaces capture validation summary into processed outputs

## Contract Shape

Current exported job shape:

```text
incoming/<job_id>/
  payload.html | payload.txt | payload.md
  metadata.json
  capture_manifest.json
  READY
  attachments/
    ...
```

Current rule:

- WSL still processes the primary payload as the main parsing input
- `attachments/` and `capture_manifest.json` are additive
- Phase 1 jobs without these files remain valid

## Why This Matters

This unblocks two Round 2 tracks:

- Windows can preserve raw source material without breaking the current GUI and normalized output
- WSL can start using richer evidence for summary, analysis, verification, and synthesis
- video pages can hand off actual downloadable assets instead of only page HTML

## Current Video Notes

- `yt-dlp` is now the downloader path for supported video platforms
- current supported targets are `bilibili` and `youtube`
- YouTube success rate still depends on environment prerequisites such as a JS runtime and, for some videos, browser cookies
- browser-profile based video export is the intended higher-success YouTube path

## Next Build Order

1. Windows: add more capture artifacts by content shape
2. WSL: introduce a richer intermediate document model instead of collapsing directly to plain text
3. WSL: split processing into explicit summarize / analyze / verify / synthesize stages
4. Platform depth: article, WeChat, and Bilibili as the first three Round 2 adapters
