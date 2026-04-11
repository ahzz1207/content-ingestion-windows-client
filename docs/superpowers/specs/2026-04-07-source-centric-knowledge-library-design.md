# Source-Centric Knowledge Library Design

## Summary

This design turns the current result reader into a stronger product loop: after reading a result, the user can save the source into a knowledge library instead of leaving the result page with no durable outcome.

The library is source-centric, not job-centric. Each library entry represents one source snapshot and stores one current interpretation as the default reading view. When the user saves the same source again after producing a better reinterpretation, the new interpretation replaces the current one and the old one is moved into an entry-local trash area that supports restore.

The detail page is image-first: show the image summary first, then the source, then the long interpretation. The image summary remains an asset of the selected interpretation, not a separate top-level object.

Reference mockup:

- `H:\demo-win\.worktrees\domain-aware-reader-v2\.superpowers\brainstorm\session-20260407-product-gap\content\knowledge-library-v2.html`

## Problem

The current product has a strong input-to-analysis-to-reading path, but it still behaves like a result workspace more than a durable knowledge product.

Today the user can:

- ingest a source
- process it into a structured result
- read the result in a richer mode-aware UI
- reinterpret the same source into a different reading mode

What is still missing is the product loop after reading:

- there is no first-class "save this into my long-term knowledge space" action
- history is job-centric, so it reflects processing state more than durable reading objects
- the product does not distinguish between transient processing records and retained knowledge entries
- the result page can feel complete for one reading session, but not complete as a keepable artifact

This design closes that gap with the smallest coherent product surface.

## Goals

- Add a clear primary action on the result page: `保存进知识库`
- Create a source-centric knowledge library that is separate from job history
- Save the current interpretation as the default reading view for that source
- Support repeated saves for the same source by replacing the current interpretation and trashing the previous current interpretation
- Make library detail image-first, then source, then long interpretation
- Preserve older replaced interpretations inside the entry and allow restore
- Reuse existing result data and assets where possible so the first version does not depend on a brand-new generation pipeline

## Non-Goals

- Replacing or removing the existing job history / result workspace
- Designing a global multi-entry trash can in the first version
- Building a brand-new WSL image-summary generation pipeline as a prerequisite for the first library milestone
- Solving team/shared library sync or cloud sync
- Building tagging, folders, search ranking, or recommendation systems beyond a minimal browse/search surface

## Product Principles

### 1. Library objects are knowledge entries, not processing records

Jobs remain useful for ingestion, pipeline visibility, retries, and technical history. The library is a separate object model for retained sources.

### 2. One source maps to one library entry

The entry is the durable object. Interpretations can change over time, but the entry remains the same source-centered container.

### 3. The current interpretation is the default reading view, not the only truth

The library should feel decisive without pretending that alternative interpretations never existed.

### 4. Replaced interpretations should disappear from the main path without being destroyed

The user explicitly prefers replacement semantics for re-save behavior because new reinterpretations usually mean dissatisfaction with the old one. The old interpretation should leave the main reading path and move into an entry-local trash area that allows restore.

### 5. Image summary is an interpretation asset

The image summary is not the primary library object. It belongs to the current interpretation and acts as the first reading surface in library detail.

## User Experience

## Result Page Save Flow

When the user finishes reading a result, the primary action on the page is `保存进知识库`.

Pressing save performs these product actions:

1. Resolve the source identity for the current result.
2. Create a new library entry if this source has never been saved.
3. If the source already exists in the library, keep the existing entry instead of creating a duplicate.
4. Create a new interpretation snapshot from the current result.
5. Mark the previous current interpretation as trashed.
6. Promote the new interpretation to current.
7. Keep the entry card stable in the library list rather than creating a duplicate list item.

After save succeeds, the result page shows a success confirmation with:

- `打开条目`
- `查看知识库`

The message should explain the semantic result, not implementation details. Example:

`Source 已保存到知识库，当前 interpretation 已设为默认阅读视图。旧版本仍可在条目内恢复。`

## Knowledge Library List

The list page is a browseable set of retained source entries.

Each card represents one `LibraryEntry` and should emphasize:

- source title
- source/platform identity
- current interpretation mode / route
- whether an image summary asset exists
- how many interpretations exist
- whether the entry contains trashed interpretations
- last updated time

The list should not foreground job ids, processor states, or technical artifacts.

The first version list needs only lightweight filtering:

- all entries
- recently saved
- entries with image summary
- entries with trashed interpretations

It is acceptable for search to be basic string matching over title, source URL, and current interpretation metadata.

## Library Detail

The detail page must establish a clear reading order:

1. image summary first
2. source second
3. long interpretation last

The page has two conceptual columns:

- main column: image summary, source, long interpretation
- side column: current interpretation metadata, restoreable trashed interpretations, lightweight behavioral context

### Image Summary Section

This is the hero of the page.

It should show:

- the current interpretation's image asset when available
- route/mode context
- a concise title/dek relationship that makes the entry immediately legible

If no image summary asset exists, the section still renders in the same place with a polished empty state rather than collapsing the layout. The empty state should indicate that the entry is saved and readable even without a visual summary.

### Source Section

This section establishes that the entry is anchored to real source material.

It should include:

- source title
- source URL / canonical URL when available
- platform
- captured time
- source snapshot references such as normalized markdown and source artifacts

The source section should feel like a trustworthy anchor, not a dump of raw JSON.

### Long Interpretation Section

This is where the user reads the current default interpretation in full.

It should render the same current interpretation content already available from the saved result, including the mode-aware reading payload that best maps to the selected interpretation.

### Trashed Interpretations Section

The first version uses entry-local trash, not a global trash view.

Each trashed interpretation row shows:

- interpretation mode / route
- why or when it left the current slot
- when it was trashed
- `恢复为当前`

Restore is a local entry action:

- the selected trashed interpretation becomes current
- the previously current interpretation moves into trash
- the entry itself stays stable
- the library list card updates to reflect the restored current interpretation

## Information Model

## Core Object: `LibraryEntry`

The library should introduce a new source-centric model on the Windows side.

Recommended shape for the first version:

```json
{
  "entry_id": "lib_20260407_001",
  "source_key": "https://mp.weixin.qq.com/s/example-macro-weekly",
  "created_at": "2026-04-07T19:06:00+08:00",
  "updated_at": "2026-04-07T19:06:00+08:00",
  "source": {
    "title": "中信建投策略周报解读稿",
    "source_url": "https://mp.weixin.qq.com/s/example-macro-weekly",
    "canonical_url": "https://mp.weixin.qq.com/s/example-macro-weekly",
    "platform": "wechat",
    "author": "中信建投策略",
    "published_at": null,
    "captured_at": "2026-04-07T18:32:00+08:00",
    "content_type": "html",
    "collection_mode": "browser",
    "job_snapshot": {
      "saved_from_job_id": "wechat-20260407-1832",
      "normalized_markdown_path": "source/normalized.md",
      "normalized_json_path": "source/normalized.json",
      "metadata_path": "source/metadata.json"
    }
  },
  "current_interpretation_id": "interp_20260407_1906",
  "interpretations": [
    {
      "interpretation_id": "interp_20260407_1906",
      "state": "current",
      "saved_at": "2026-04-07T19:06:00+08:00",
      "saved_from_job_id": "wechat-20260407-1832--reinterpret-01",
      "requested_reading_goal": "argument",
      "resolved_reading_goal": "argument",
      "resolved_domain_template": "macro_business",
      "route_key": "argument.macro_business",
      "summary": {
        "headline": "真正该盯的不是降息，而是盈利预期何时补跌",
        "short_text": "..."
      },
      "product_view": {},
      "editorial": {},
      "structured_result": {},
      "assets": [
        {
          "asset_id": "asset_20260407_1906_img",
          "kind": "image_summary",
          "label": "Insight card",
          "path": "interpretations/interp_20260407_1906/assets/insight_card.png",
          "media_type": "image/png"
        }
      ],
      "trashed_at": null,
      "trash_reason": null
    }
  ]
}
```

## Interpretation States

Use a minimal state model:

- `current`
- `trashed`

Only one interpretation may be `current` at a time.

The entry stores all interpretations in one list. This keeps the model simple, keeps restore local to the entry, and avoids introducing a second parallel container for trash.

## Source Identity and Deduplication

The product needs deterministic same-source behavior when the user saves again.

For the first version, compute `source_key` with a simple precedence order:

1. `canonical_url` if present
2. else `source_url` if present
3. else stable hash of normalized markdown text
4. else saved-from job id as last-resort fallback

This keeps URL-backed sources stable while still allowing non-URL sources to be saved.

The fallback to job id is not ideal for long-term dedupe, but it is acceptable in the first milestone because most real user saves are URL-backed. The design does not require a more complex identity system yet.

For the first version, repeated saves for the same `source_key` do not replace the stored source snapshot. They only add a new interpretation snapshot and update which interpretation is current. This keeps the entry stable and avoids introducing source-revision management in the same milestone.

## Persistence Layout

Store the knowledge library under the same shared root as results, but as its own top-level product space.

Recommended layout:

```text
<shared_root>/library/
  index.json
  entries/
    <entry_id>/
      entry.json
      source/
        metadata.json
        normalized.json
        normalized.md
        attachments/... 
      interpretations/
        <interpretation_id>/
          interpretation.json
          assets/
            insight_card.png
```

Why this layout:

- keeps library data separate from transient job folders
- supports snapshot semantics instead of pointer semantics
- allows a library entry to survive archive, reinterpretation, or job cleanup operations
- makes restore and current interpretation switching a metadata change inside the entry rather than a dependency on active job version state

The first version should treat the library as a snapshot store, not as a set of symbolic pointers back into processed jobs.

## Data Flow

## Save to Library

When the user saves from the result page:

1. Load the current `ResultWorkspaceEntry`.
2. Resolve source identity and look up an existing library entry.
3. Copy source snapshot files into the library if this is a new entry.
4. If this is an existing entry, preserve the existing source snapshot in place for the first version.
5. Build a new interpretation snapshot from the current result payload.
6. Copy reusable assets for that interpretation into the interpretation assets directory.
7. If an existing current interpretation exists, mark it `trashed` and set `trashed_at` plus a human-readable reason such as `replaced_by_new_save`.
8. Mark the new interpretation as `current`.
9. Update the entry manifest and list index.

## Restore From Trash

When the user restores a trashed interpretation:

1. Load the target entry.
2. Find the current interpretation.
3. Find the selected trashed interpretation.
4. Move the current interpretation to `trashed`.
5. Move the selected interpretation to `current`.
6. Update `current_interpretation_id`.
7. Update entry timestamps and derived list-card metadata.

No new source snapshot is created during restore.

## Image Summary Strategy

The desired long-term behavior is for text and image summary to be generated together from the same source material.

However, the first library milestone should not block on a brand-new image generation pipeline.

For the first version:

- treat the existing `insight_card.png` artifact as the initial image-summary asset when it exists
- copy it into the saved interpretation asset folder during save
- render it as the hero image in library detail
- if it does not exist, render a polished empty state in the same hero position

This preserves the intended product hierarchy without delaying the library feature on new generation work.

Later, a dedicated image-summary pipeline can replace the source of this asset without changing the library object model.

## Architecture Impact

This design implies a new product layer in the Windows client.

### Keep Existing Job Workspace

The existing result workspace remains responsible for:

- loading processed job results
- showing job history
- supporting reinterpretation
- exposing raw artifacts and technical diagnostics

### Add Library Service / Repository

The library should have its own small storage boundary responsible for:

- resolving source identity
- reading and writing library entries
- creating interpretation snapshots
- moving interpretations between `current` and `trashed`
- listing entry cards for the UI

### Add Library UI Surface

The UI should expose:

- save action from the result page
- open knowledge library from the main window / result success flow
- library list screen or dialog
- library detail screen or dialog

This is a product layer addition, not a rewrite of the current result renderer.

## Error Handling and Empty States

### Save Failures

If save fails, the result page should show a concise failure message such as:

`保存到知识库失败，请重试。`

The detailed exception can still be logged, but the user-facing copy should stay product-level.

### Missing Image Summary

The absence of an image summary must not block save.

The detail page should render an empty-state hero like:

`该条目已保存。当前 interpretation 暂无图片摘要，可先查看 source 与完整解读。`

### Missing Older Assets

If an older trashed interpretation is missing a non-critical asset, restore should still succeed. The current interpretation should simply render without that asset.

### Broken Source Snapshot

If the source snapshot copy fails for a new entry, abort the save rather than creating a partial entry.

### Broken Interpretation Snapshot

If interpretation copy fails, do not update the existing entry's current interpretation. Save should behave transactionally at the entry level as much as practical.

## Testing Strategy

The first implementation should verify behavior at three levels.

### Storage / Repository Tests

- create new entry from a result snapshot
- save same source twice and confirm one entry remains with one current interpretation and one trashed interpretation
- restore trashed interpretation and confirm current/trash swap
- save without image asset and confirm entry still persists
- source identity precedence: canonical URL, source URL, markdown hash, job id fallback

### API / View-Model Tests

- list cards reflect current interpretation metadata
- detail payload orders the data around image summary, source, and long interpretation
- trashed interpretations are exposed in entry detail but not promoted to list-card defaults

### GUI Tests

- result page save action appears in the correct state
- success banner exposes `打开条目` and/or `查看知识库`
- library list opens and shows source-centric cards
- entry detail renders image-first and includes restore actions for trashed interpretations

## Rollout Shape

The smallest coherent implementation should be delivered in this order:

1. library storage model and save semantics
2. result-page `保存进知识库` action and success feedback
3. library list UI
4. library detail UI with image-first layout
5. entry-local trash restore

This produces a complete retention loop without requiring the full long-term asset generation roadmap.

## Why This Direction

This design matches the product decisions already made in the session:

- the first missing product loop is post-reading retention
- the right retained object is source-centric
- the current best interpretation should become the default reading view
- repeated saves should feel decisive and replace the current interpretation
- older interpretations should remain recoverable inside the entry rather than cluttering the main list
- image summary should lead the detail experience but remain subordinate to the interpretation

The result is a cleaner separation of roles:

- job history = processing workspace
- knowledge library = durable reading product

That separation is what gives the next version of the app a more finished product shape instead of a better-looking processor.
