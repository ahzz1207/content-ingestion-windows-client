# Analysis Mode Taxonomy v1

**Date:** 2026-03-29  
**Status:** planning draft  
**Scope:** define content-intent-based analysis modes for the WSL processor so that different kinds of content can receive different LLM treatment, output structure, and card templates

---

## Why This Exists

Not every piece of content should be processed as if it were an argument-heavy article that needs full evidence-pressure analysis.

Some content benefits from deep thesis / evidence / tension extraction:

- macro analysis
- commentary
- long-form opinion
- issue explainers

Other content is valuable for different reasons:

- game guides
- music review and album sharing
- exhibition information
- travel suggestions
- product how-to
- personal experience logs

If every input is forced through the same research-style analysis flow, the system will often:

- over-analyze practical or lifestyle content
- flatten different content intents into one generic digest
- waste interface space on sections the user did not actually need
- produce repetitive cards and summaries

The processor therefore needs an explicit taxonomy that routes content into the right analysis mode.

---

## Product Goal

The taxonomy should let the system answer the right question for the right type of content.

Examples:

- For commentary: what is the author really arguing, and how well is it supported?
- For a guide: what should I do, in what order, and what should I avoid?
- For a review: what stands out, what is the overall judgment, and who is it for?
- For an informational post: what changed, who is affected, and what do I need to know?
- For narrative content: what happened, what were the key moments, and what is the takeaway?

The goal is not to create many disconnected pipelines.

The goal is to create a small set of content-intent-aware modes that share a common base contract while enabling different downstream outputs.

---

## Design Principles

- Intent over platform: route by content purpose, not by source platform.
- Shared base contract: all modes should emit a common minimum output.
- Selective depth: only some modes require strong evidence / critique structure.
- User goal alignment: the result should reflect what a user wants from that content type.
- Auto route first: default mode is inferred automatically.
- Lightweight override: users may override the reading goal, but should not be forced to choose a technical template every time.

---

## Shared Base Output

Every analysis mode should emit a minimum shared layer so that Windows clients, Obsidian, and future card builders have a stable baseline.

Suggested shared fields:

- `analysis_mode`
- `mode_confidence`
- `core_summary`
- `core_takeaways`
- `content_kind`
- `author_stance`
- `audience_fit`
- `save_worthy_points`
- `card_template_hint`

These fields are not enough for a full result, but they give every mode a common editorial spine.

---

## Mode A: `argument`

### Best For

- commentary
- macro analysis
- issue explainers
- long-form opinion
- debate-style video or article

### User Need

- what is the core thesis?
- what evidence supports it?
- what is interpretation versus support?
- where are the tensions or blind spots?

### Priority Sections

- `author_thesis`
- `argument_map`
- `evidence_backed_points`
- `interpretive_points`
- `tensions`
- `uncertainties`
- `bottom_line`

### De-emphasized Sections

- `recommended_steps`
- `practical_checklist`
- `audience_fit_as_purchase_decision`

### Wrong Fit Symptoms

If this mode is applied to the wrong content, the output tends to become:

- too heavy
- too skeptical
- too abstract
- less useful for immediate action

---

## Mode B: `guide`

### Best For

- game guides
- tutorials
- practical explainers
- tool usage walkthroughs
- travel or planning advice

### User Need

- what is the goal?
- what are the recommended steps?
- what shortcuts or best practices matter?
- what are the main pitfalls?

### Priority Sections

- `goal`
- `recommended_steps`
- `tips`
- `pitfalls`
- `prerequisites`
- `quick_win`
- `bottom_line`

### De-emphasized Sections

- `tensions`
- `critique`
- `argument_map`

### Wrong Fit Symptoms

If this mode is not used when it should be, the result often:

- sounds like a book report
- misses practical value
- hides the action sequence
- over-focuses on rhetoric instead of execution

---

## Mode C: `review`

### Best For

- music album sharing
- film / game / exhibition review
- product recommendation
- style or taste curation

### User Need

- what is the overall judgment?
- what stands out?
- what is the tone, style, or atmosphere?
- who is this for?

### Priority Sections

- `overall_judgment`
- `highlights`
- `style_and_mood`
- `what_stands_out`
- `who_it_is_for`
- `reservation_points`
- `bottom_line`

### De-emphasized Sections

- `formal_verification`
- `evidence_pressure`
- `argument_map`

### Wrong Fit Symptoms

If this mode is forced into argument-style analysis, the output often:

- feels too prosecutorial
- overweights proof instead of taste or appraisal
- loses the subjective but useful evaluation layer

---

## Mode D: `informational`

### Best For

- exhibition information
- event announcements
- release notes
- update notices
- policy or rule change summaries

### User Need

- what happened?
- what changed?
- who is affected?
- what should I do with this information?

### Priority Sections

- `key_info`
- `what_changed`
- `who_is_affected`
- `time_location_conditions`
- `action_needed`
- `bottom_line`

### De-emphasized Sections

- `author_stance`
- `style_and_mood`
- `deep critique`

### Wrong Fit Symptoms

If this mode is not used, the result often:

- adds unnecessary interpretation
- hides factual details inside prose
- becomes less actionable

---

## Mode E: `narrative`

### Best For

- vlog
- experience sharing
- process log
- documentary-style personal record
- journey or visit recap

### User Need

- what happened?
- what were the key moments?
- what was the emotional tone?
- what is the takeaway?

### Priority Sections

- `story_arc`
- `key_moments`
- `emotional_tone`
- `memorable_details`
- `takeaway`
- `bottom_line`

### De-emphasized Sections

- `strict_argument_map`
- `formal_verification`
- `recommended_steps`

### Wrong Fit Symptoms

If this mode is over-analyzed as commentary, the output often:

- sounds unnatural
- imposes argument structure where none exists
- loses narrative rhythm

---

## Auto Routing

The system should default to automatic mode selection.

Suggested classifier output:

```json
{
  "analysis_mode": "argument|guide|review|informational|narrative",
  "confidence": 0.82,
  "signals": [
    "contains numbered instruction sequence",
    "uses recommendation language",
    "weak evidence-pressure demand"
  ]
}
```

### Candidate Signals

- title patterns
- section structure
- imperative verbs
- recommendation language
- event metadata
- review vocabulary
- rhetorical density
- how-to sequencing
- timeline structure
- media and visual cues

This classifier does not need to be perfect.

It only needs to provide a strong default route that can later be overridden.

---

## User Override

Users should not need to choose an internal technical mode.

Instead, the product can expose reading goals such as:

- `Deep analysis`
- `Practical extraction`
- `Recommendation view`
- `Info summary`
- `Narrative recap`

Suggested mapping:

- `Deep analysis` -> `argument`
- `Practical extraction` -> `guide`
- `Recommendation view` -> `review`
- `Info summary` -> `informational`
- `Narrative recap` -> `narrative`

This keeps the front-end simple while preserving taxonomic control.

---

## Relation To Insight Cards

Each mode should map to a different default card template.

Suggested initial mapping:

- `argument` -> `Thesis + Argument + Tensions`
- `guide` -> `Goal + Steps + Pitfalls`
- `review` -> `Verdict + Highlights + Audience Fit`
- `informational` -> `Key Info + What Changed + Action`
- `narrative` -> `Story Arc + Key Moments + Takeaway`

This does not mean one hardcoded layout per mode forever.

It means each mode should have a default editorial pattern that downstream card rendering can start from.

---

## Shared Schema Strategy

The system should not create five fully disconnected result schemas.

Instead:

- one shared base schema exists across all modes
- each mode activates a different subset of sections
- some sections are mode-specific extensions

This keeps:

- clients simpler
- evolution safer
- contracts easier to version

---

## Suggested v1 Scope

To keep rollout manageable, v1 should validate only three modes first:

- `argument`
- `guide`
- `review`

Why these three first:

- they are easy for users to distinguish
- they cover a large share of real-world content
- they create clearly different output expectations
- they are enough to prove whether taxonomy-based routing materially improves quality

`informational` and `narrative` can remain defined in taxonomy v1 but be activated in a later implementation batch.

---

## What v1 Does Not Attempt

- a large ontology of content modes
- claim / topic / entity graph extraction
- per-platform mode trees
- forcing users to manually choose an analysis mode every time
- fully separate pipelines per mode

---

## Open Questions

- Which mode should be the fallback when classification confidence is low?
- Should users override the mode before processing, after processing, or both?
- Should one piece of content support secondary views in another mode without rerunning the full pipeline?
- Is `review` distinct enough from `argument` in all cases, or should there be hybrid handling for some long-form criticism?
- Should `narrative` treat emotional tone as a primary section or a side-band annotation?

---

## Provisional Conclusion

The WSL processor should not treat all content as if it requires the same deep evidence-pressure workflow.

Instead, it should:

1. infer the content intent
2. route into the appropriate analysis mode
3. emit a shared editorial base plus mode-specific sections
4. let downstream clients and insight cards render from that structured result

This taxonomy is the first step toward intent-aware analysis and more differentiated downstream outputs.
