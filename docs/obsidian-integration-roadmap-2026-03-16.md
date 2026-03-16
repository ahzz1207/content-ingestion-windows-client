# Obsidian Integration Roadmap 2026-03-16

## 1. Purpose

This document proposes how the current Windows + WSL content-ingestion workflow can evolve into a fuller product:

- ingest content from the open web
- normalize and analyze it with the existing pipeline
- turn the output into reusable knowledge objects
- curate, compare, summarize, and share those objects through Obsidian

The target product direction is:

- a durable `web viewpoint intelligence` system
- not just a URL collector
- not just a one-shot summarizer

In product terms, this is the path toward:

- an `all-web viewpoint synthesis application`

---

## 2. High-Level Product Position

The current repositories already do two important things well:

- collect and normalize source material
- produce structured LLM output that is richer than plain markdown

Obsidian should not replace that pipeline.
It should become the downstream knowledge workspace where processed results are:

- organized
- linked
- compared
- refined by the user
- prepared for internal or public sharing

Recommended positioning:

- Windows app = capture and operational shell
- WSL processor = normalization and analysis engine
- Obsidian vault = knowledge operating system
- Obsidian Publish or vault-to-site export = sharing layer

This separation keeps the ingestion pipeline stable while giving the product a much stronger knowledge surface.

---

## 3. Why Obsidian Fits

Obsidian is a strong fit because its current product model already supports the exact downstream behavior this project needs:

- local markdown files as durable knowledge objects
- Properties for structured metadata
- Bases for database-like browsing over note metadata
- Canvas for spatial relationship maps and argument boards
- URI actions for deep-linking from the Windows client into specific notes or vault locations
- CLI and headless entry points for automation
- Web Clipper templates for capture-side consistency
- Publish for digital-garden or report-style sharing

This matters because our output is not only text.
It is:

- sources
- summaries
- claims
- evidence references
- topics
- entities
- contradictions
- synthesis notes

Obsidian is much better as a long-lived container for these objects than a flat export folder.

---

## 4. Current Obsidian Capabilities That Matter Most

The most relevant current official capabilities are:

- Properties: structured note metadata that can be used for filtering and downstream views
- Bases: table / board / calendar style views over notes with matching properties
- Canvas: an open JSON-based spatial whiteboard format
- URI scheme: open vaults, notes, commands, and plugin commands from external apps
- CLI and headless mode: useful for scripted vault actions and future automation paths
- Publish: hosted site sharing with custom domain, CSS, JS, graph view, and search
- Plugin API: enough surface area to build a focused companion plugin later

Important constraint:

- community plugins are powerful but not sandboxed

That means the safest first phase is file-based integration plus URI deep-links, not an immediate heavy plugin dependency.

---

## 5. Product Thesis

The product should not stop at:

- "Here is a summary of one URL."

It should mature into:

- "Here is how multiple sources, claims, and viewpoints relate to one another across time, topic, and source type."

That means the core product object is not a page capture.
The core product object becomes:

- a viewpoint graph

Where each processed source can produce or enrich:

- source notes
- digest notes
- claim notes
- topic notes
- entity notes
- debate / contradiction boards
- shareable briefings

---

## 6. Recommended Knowledge Model

The current WSL output is already rich enough to begin a stronger knowledge model.

Recommended first-class objects:

### 6.1 Source

Represents a single processed URL or media asset.

Suggested fields:

- `source_id`
- `job_id`
- `source_url`
- `canonical_url`
- `platform`
- `content_shape`
- `title`
- `author`
- `published_at`
- `captured_at`
- `language`
- `ingestion_status`
- `llm_processing_status`
- `confidence`
- `topics`
- `entities`

### 6.2 Digest

Represents the best structured summary of one source.

Suggested fields:

- `digest_id`
- `source_id`
- `headline`
- `short_summary`
- `key_points`
- `analysis_items`
- `verification_items`
- `warnings`
- `takeaway`
- `stance_tags`

### 6.3 Claim

Represents one normalized claim extracted from a source or synthesis.

Suggested fields:

- `claim_id`
- `claim_text`
- `topic`
- `entity_refs`
- `source_refs`
- `evidence_refs`
- `stance`
- `confidence`
- `claim_type`
- `time_scope`

### 6.4 Topic

Represents a durable subject area across many sources.

Suggested fields:

- `topic_id`
- `topic_name`
- `aliases`
- `active_claims`
- `related_entities`
- `open_questions`
- `recurring_frames`
- `contradictions`

### 6.5 Entity

Represents a person, organization, product, country, or concept that recurs across sources.

Suggested fields:

- `entity_id`
- `entity_name`
- `entity_type`
- `aliases`
- `topic_refs`
- `claim_refs`
- `source_refs`

### 6.6 Synthesis

Represents a cross-source note created by the system or user.

Suggested fields:

- `synthesis_id`
- `scope`
- `source_refs`
- `claim_refs`
- `agreements`
- `disagreements`
- `open_questions`
- `draft_for_share`

---

## 7. Recommended Vault Structure

Recommended vault layout:

```text
Vault/
  00 Inbox/
  01 Sources/
  02 Digests/
  03 Claims/
  04 Topics/
  05 Entities/
  06 Syntheses/
  07 Boards/
  08 Publish/
  Assets/
  Templates/
  Bases/
```

Suggested usage:

- `00 Inbox/`: raw imported notes awaiting curation
- `01 Sources/`: one source note per processed job
- `02 Digests/`: one digest note per processed source
- `03 Claims/`: extracted and normalized claims
- `04 Topics/`: durable topical hubs
- `05 Entities/`: recurring actors and concepts
- `06 Syntheses/`: comparative notes and briefs
- `07 Boards/`: `.canvas` files for debate maps and relationship maps
- `08 Publish/`: curated public-facing notes
- `Assets/`: screenshots, images, thumbnails, captured files
- `Templates/`: note templates
- `Bases/`: saved Bases definitions once the vault model stabilizes

This structure maps well to how the current pipeline already separates:

- payload
- normalized content
- structured result
- evidence

---

## 8. Integration Modes

There are several ways to integrate with Obsidian.
They should not all be attempted at once.

### 8.1 Mode A: Vault Export on Disk

The pipeline writes markdown notes and attachments directly into a chosen vault folder.

Benefits:

- simplest
- robust
- easy to debug
- no plugin dependency
- preserves user ownership of files

This should be the first implementation.

### 8.2 Mode B: URI Deep-Linking

The Windows app opens Obsidian to:

- a vault
- a newly created source note
- a daily review note
- a plugin command later

Benefits:

- excellent handoff from capture app to knowledge workspace
- very low implementation cost

This should land very early.

### 8.3 Mode C: Companion Obsidian Plugin

A small plugin can later add:

- command palette actions for imported notes
- vault-side re-clustering
- note promotion workflows
- one-click canvas generation
- share/export helpers

Benefits:

- much better vault ergonomics

Risks:

- more maintenance
- plugin lifecycle cost
- community-plugin trust and security expectations

This should come after the file-based model is stable.

### 8.4 Mode D: Publish Layer

Curated notes can be copied or promoted into a Publish-ready folder.

Benefits:

- fast route to a knowledge garden
- strong fit for viewpoint synthesis, topic dossiers, and public briefs

This should be a later but important product layer.

---

## 9. Recommended Phase Order

### Phase O1: Stable Vault Export

Goal:

- every processed job can be exported as stable Obsidian-friendly markdown plus attachments

Deliverables:

- vault path configuration
- source note template
- digest note template
- attachment export layout
- `Open in Obsidian` action from the Windows GUI

Key decision:

- markdown + Properties become the canonical interchange format

### Phase O2: Metadata-First Vault

Goal:

- notes become queryable and browsable as structured knowledge objects

Deliverables:

- normalized frontmatter schema
- saved Bases for sources, digests, claims, and topics
- backlinks and cross-note references
- consistent note naming strategy

### Phase O3: Viewpoint Graph

Goal:

- move from source summaries to cross-source viewpoint intelligence

Deliverables:

- claim extraction normalization
- topic hubs
- entity hubs
- contradiction markers
- generated `.canvas` debate maps

### Phase O4: Companion Plugin

Goal:

- reduce friction inside the vault

Deliverables:

- promote digest -> synthesis
- merge claims
- generate topic canvas
- mark note as publish-ready

### Phase O5: Publish and Share

Goal:

- turn internal knowledge into shareable products

Deliverables:

- publish-ready note templates
- topic landing pages
- weekly or event-based brief packs
- internal / public sharing playbooks

---

## 10. Recommended Note Templates

### 10.1 Source Note

Should contain:

- metadata properties
- source link
- compact capture context
- normalized markdown body
- evidence section
- outbound links to digest, claims, topics, and entities

### 10.2 Digest Note

Should contain:

- one-line headline
- short summary
- key points
- analysis
- verification
- warnings
- synthesis takeaway
- human curation block

### 10.3 Topic Note

Should contain:

- topic definition
- recurring viewpoints
- recurring entities
- supporting sources
- conflicting claims
- open questions
- link to relevant canvas

### 10.4 Synthesis Note

Should contain:

- scope of comparison
- compared sources
- agreement zones
- disagreement zones
- strongest evidence
- weakest evidence
- what remains unresolved
- publish draft section

---

## 11. Suggested Metadata Schema

Recommended core Properties for most generated notes:

- `type`
- `source_id`
- `job_id`
- `status`
- `platform`
- `content_shape`
- `title`
- `author`
- `published_at`
- `captured_at`
- `topic_refs`
- `entity_refs`
- `claim_refs`
- `source_refs`
- `confidence`
- `share_status`
- `review_status`

Important rule:

- keep metadata narrow and stable
- do not push large LLM payloads into Properties
- keep large machine output in note body or linked JSON artifacts

---

## 12. What the Windows GUI Should Add for Obsidian

Once the vault export path exists, the Windows GUI should expose a few direct actions:

- `Open in Obsidian`
- `Reveal in Vault`
- `Promote to Topic`
- `Create Comparison Brief`
- `Mark for Publish`

These actions make the GUI feel like the operational front door, while Obsidian becomes the deeper workspace.

Recommended boundary:

- the Windows app triggers and routes
- Obsidian handles long-form knowledge curation

---

## 13. What the WSL Processor Should Add Later

To make the Obsidian product truly strong, the WSL side should gradually produce cleaner machine-readable knowledge outputs:

- stable claim objects
- stable entity references
- topic suggestions
- contradiction candidates
- more explicit confidence fields
- better evidence anchoring

This is the bridge from `summary app` to `viewpoint intelligence app`.

---

## 14. Publish Strategy

There are two good publish directions:

### Internal Knowledge Garden

Use Obsidian as the working vault and publish selected notes for internal review.

Use cases:

- weekly briefings
- market narratives
- policy watch
- company research
- event dossiers

### Public Viewpoint Product

Curate selected notes into a public knowledge product.

Use cases:

- topic explainers
- source-grounded issue maps
- public research collections
- contradiction dashboards built from curated notes

Important rule:

- public sharing must always keep provenance visible
- every synthesized view must link back to source notes

---

## 15. Recommended Technical Sequence

The practical implementation order should be:

1. define a stable vault export schema
2. generate source and digest markdown notes from current processed results
3. add GUI deep-links into Obsidian through the URI scheme
4. add vault-ready Properties and saved Bases
5. add topic / entity / claim note generation
6. add `.canvas` generation for topic and contradiction maps
7. add a companion plugin only after the file model is stable
8. add Publish-ready curation and sharing flows

This order keeps the integration incremental and avoids coupling the ingestion engine to Obsidian too early.

---

## 16. Working Recommendation

The best near-term move is not a complex plugin.
It is:

1. treat Obsidian as the durable downstream knowledge workspace
2. export processed results into a clean vault structure
3. use Properties, Bases, Canvas, and URI deep-links before adding heavier custom code
4. grow from source notes into topic, claim, and synthesis notes
5. use Publish only after curation rules are stable

That is the most realistic path from the current ingestion pipeline to a genuine all-web viewpoint synthesis application.

---

## 17. References

Official references reviewed during this planning pass:

- [Obsidian Help: URI actions](https://help.obsidian.md/Extending+Obsidian/Obsidian+URI)
- [Obsidian Help: Command line interface](https://help.obsidian.md/Extending+Obsidian/Command+line+interface)
- [Obsidian Help: Headless mode](https://help.obsidian.md/Extending+Obsidian/Headless+mode)
- [Obsidian Help: Properties](https://help.obsidian.md/properties)
- [Obsidian Help: Bases](https://help.obsidian.md/bases)
- [Obsidian Help: Canvas](https://help.obsidian.md/canvas)
- [JSON Canvas](https://jsoncanvas.org/)
- [Obsidian Help: Web Clipper](https://help.obsidian.md/web-clipper)
- [Obsidian Help: Publish](https://help.obsidian.md/Obsidian+Publish)
- [Obsidian Help: Plugin security](https://help.obsidian.md/Extending+Obsidian/Plugin+security)
- [Obsidian Developer Docs: Build a plugin](https://docs.obsidian.md/Plugins/Getting+started/Build+a+plugin)
- [Obsidian Developer Docs: Vault](https://docs.obsidian.md/Plugins/Vault)
- [Obsidian Developer Docs: Build a Bases view](https://docs.obsidian.md/Bases/Build+a+Bases+view)
