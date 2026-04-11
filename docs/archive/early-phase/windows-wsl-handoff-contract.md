# Windows-WSL Handoff Contract v0.2

## Purpose

This document defines the recommended contract for what Windows should hand off to WSL.

It is narrower than a full product spec.
Its goal is to keep the cross-repo boundary stable while still allowing future expansion.

---

## Recommended Model

Treat the handoff as two layers:

1. a small, stable primary contract that WSL must understand
2. optional auxiliary artifacts that WSL may ignore until explicitly supported

This keeps the main processor path simple without blocking richer Windows capture later.

---

## Primary Contract

Each job under `shared_inbox/incoming/<job_id>/` should currently contain:

- one primary payload
- one `metadata.json`
- one `READY`

Current primary payload forms:

- `payload.html`
- `payload.txt`
- `payload.md`

Current rules:

- exactly one primary payload per job
- payload filename remains `payload.<ext>`
- `metadata.json` is required
- `READY` is created last

WSL should continue to treat these three payload types as the only primary content types in the main contract.

---

## Why Keep The Primary Contract Narrow

The primary contract should stay limited to `html`, `txt`, and `md` because:

- WSL parser routing is already built around these types
- validation rules stay simple
- failure modes stay easier to diagnose
- Windows can still collect in richer ways and normalize the result into one of these three forms before handoff

This means browser capture, HTTP capture, and future GUI capture can all converge onto the same processor boundary.

---

## Metadata Tiers

`metadata.json` should be treated as having four tiers.

### 1. Required Protocol Fields

These fields are required for the handoff to be valid:

- `job_id`
- `source_url`
- `collector`
- `collected_at`
- `content_type`

These are protocol-level fields, not business-level hints.

### 2. Core Business Fields

These fields are strongly recommended and should be considered stable cross-repo inputs:

- `platform`
- `final_url`

`final_url` is useful when the browser path resolves redirects or canonical landing pages.

Contract note:

- consumers must accept `final_url` being absent
- consumers must also accept `final_url` being present but identical to `source_url`
- current Windows export writes `final_url` whenever it is known, even if it matches `source_url`

### 3. Hint Fields

These fields are advisory inputs that WSL should prefer before reparsing when they are present:

- `title_hint`
- `author_hint`
- `published_at_hint`

Current recommendation:

- WSL should use these as first-class inputs when present
- WSL should only fall back to reparsing the payload when a specific hint is missing or clearly invalid

Current implementation status:

- WSL now prefers Windows hints for `title`, `author`, and `published_at` when present
- WSL still parses payload content text from the primary payload

### 4. Collection Context Fields

These fields are optional but useful for debugging and future GUI observability:

- `collection_mode`
- `browser_channel`
- `profile_slug`
- `wait_until`
- `wait_for_selector`
- `wait_for_selector_state`

These should not be required for protocol validity.

They are useful for diagnosing why one export succeeded or failed, and for understanding how a payload was captured.

Serialization note:

- optional collection-context fields should be omitted when unknown
- explicit `null` is not required by the contract
- WSL consumers should treat omitted and `null` values equivalently if either appears

Current implementation status:

- Windows export now writes `final_url` when known
- Windows export now writes `collection_mode` for `mock`, `http`, and `browser`
- browser exports now write available capture context such as `browser_channel`, `profile_slug`, `wait_until`, `wait_for_selector`, and `wait_for_selector_state`

---

## Normalized Output Contract

WSL should not mirror the full incoming `metadata.json` into `normalized.json`.

Instead, WSL should expose:

- normalized content fields at the top level of `asset`
- a small, filtered `asset.metadata` object for traceability

Current implementation status:

- `asset.canonical_url` is populated from Windows `final_url` when present
- `asset.metadata.job_id` and `asset.metadata.content_type` remain stable
- WSL now writes a filtered `asset.metadata.handoff` object when collection context exists

Current `asset.metadata.handoff` fields:

- `collector`
- `collected_at`
- `collection_mode`
- `browser_channel`
- `profile_slug`
- `wait_until`
- `wait_for_selector`
- `wait_for_selector_state`

This keeps normalized output useful for debugging and GUI status surfaces without turning it into a raw echo of the inbox protocol file.

---

## Recommended Metadata Example

```json
{
  "job_id": "20260314_130000_ab12cd",
  "source_url": "https://example.com/article",
  "final_url": "https://example.com/article",
  "platform": "generic",
  "collector": "windows-client",
  "collected_at": "2026-03-14T13:00:00+08:00",
  "content_type": "html",
  "title_hint": "Example title",
  "author_hint": "Example author",
  "published_at_hint": "2026-03-14 12:58",
  "collection_mode": "browser",
  "profile_slug": "wechat",
  "wait_until": "domcontentloaded",
  "wait_for_selector": "#js_content",
  "wait_for_selector_state": "visible"
}
```

Not every field above needs to be present today.

In particular:

- `final_url` may be omitted when it is unknown
- optional collection-context fields such as `browser_channel` may be omitted when they are unknown

The important part is the tiering:

- required protocol fields remain minimal
- hints are explicit and cheap to consume
- collection context stays optional

---

## Attachments Strategy

If Windows needs to hand off richer artifacts later, do not expand the primary payload contract first.

Instead, add an auxiliary directory such as:

```text
incoming/<job_id>/
  payload.html
  metadata.json
  READY
  attachments/
    screenshot.png
    page.mhtml
    raw_headers.json
    extra_metadata.json
```

Recommended rule:

- WSL may ignore `attachments/` by default
- support for specific attachment types should be added incrementally and explicitly

This is safer than immediately expanding the primary contract to many new payload types such as `pdf`, `png`, `mhtml`, or arbitrary `json`.

---

## Ownership Boundary

Windows owns:

- URL intake
- browser or HTTP collection
- raw export choice
- metadata hints
- optional auxiliary artifacts

WSL owns:

- protocol validation
- claim and processing flow
- normalization
- processed / failed outputs

Windows should not write:

- `status.json`
- `error.json`
- `pipeline.json`
- `normalized.json`
- `normalized.md`

Those remain WSL-owned outputs.

---

## Current Recommended Direction

The current recommended direction is:

1. keep the primary payload enum limited to `html`, `txt`, and `md`
2. make metadata tiering explicit
3. let WSL prefer Windows hints before reparsing
4. reserve `attachments/` for future richer handoff needs
5. avoid broadening the protocol until a real downstream use case requires it

This preserves the stable MVP boundary while leaving room for future richer capture.

---

## Related Docs

- `docs/windows-client-kickoff.md`
- `docs/windows-wsl-roundtrip.md`
- `docs/cross-review-2026-03-14.md`
- `~/codex-demo/docs/inbox-protocol.md`
- `~/codex-demo/docs/cross-repo-collaboration.md`
