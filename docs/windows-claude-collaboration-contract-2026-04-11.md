# Windows-Claude Collaboration Contract 2026-04-11

This document records the recommended collaboration model when Claude is responsible for WSL/backend development and I am responsible for the Windows frontend / GUI / reading experience work.

It is meant to prevent duplicate work, schema drift, and the common failure mode where frontend and backend both try to solve the same product problem in different layers.

---

## 1. Core Principle

The core principle is:

- WSL output is the contract
- Windows consumes and presents that contract
- Windows does not invent backend semantics
- WSL does not patch frontend rendering problems by reshaping output blindly

In short:

- Claude owns `what the result means`
- I own `how the result is read and experienced`

The most important shared contract right now is:

- `product_view`

That means:

- WSL is responsible for generating `product_view`
- Windows is responsible for rendering `product_view`

---

## 2. High-Level Division Of Responsibility

### Claude owns the WSL side

Claude is responsible for:

- `src/content_ingestion/**`
- prompt logic
- schema design
- normalization and processor behavior
- `StructuredResult` / `editorial` / `product_view` generation
- WSL-side fixtures and backend tests
- deciding the meaning of fields and section kinds

### I own the Windows side

I am responsible for:

- `src/windows_client/**`
- GUI layout
- result reading surfaces
- `insight_brief` adaptation
- `result_renderer` and `inline_result_view`
- library / history / result-page interaction behavior
- Windows-side tests
- mode-aware rendering and fallback behavior

### User owns product direction and final acceptance

The user remains the final decision-maker for:

- product priorities
- quality bar
- whether a backend contract is good enough
- whether a frontend reading experience is good enough
- final acceptance before merge

---

## 3. Boundary Rules

### Claude should not touch

Claude should not modify Windows rendering code such as:

- `result_renderer.py`
- `inline_result_view.py`
- `main_window.py`
- other GUI layout or style files

Claude should also not attempt to fix a weak output by describing the ideal frontend behavior instead of stabilizing the emitted contract.

### I should not touch

I should not modify WSL backend code such as:

- `llm_pipeline.py`
- `processor.py`
- `models.py`
- prompt / schema generation code

I should also not invent output semantics in Windows that are missing on the WSL side.

### Shared rule

If a field is unclear, the answer is not to guess.
The answer is to update the contract and make the semantics explicit.

---

## 4. The Contract-First Workflow

Before Claude implements a new mode or changes an existing mode's output structure, Claude should first publish a short contract update describing:

- which mode is changing
- what the `product_view` shape is
- which hero fields exist
- which section `kind` values exist
- what `render_hints.layout_family` should be
- whether the change is backward-compatible or not

This should happen before asking Windows to adapt the frontend.

The purpose is simple:

- frontend work should start from an explicit payload contract
- not from live watcher output exploration or reverse engineering after the fact

This allows both sides to work in parallel without blocking on runtime integration.

---

## 5. Fixture-Driven Frontend Work

The preferred collaboration pattern is:

- backend produces fixtures
- frontend consumes fixtures

Claude should create a fixture whenever a new `product_view` shape is ready, for example:

- `tests/fixtures/product_view_argument_sample.json`
- `tests/fixtures/product_view_guide_sample.json`
- `tests/fixtures/product_view_review_sample.json`

These fixtures should be realistic enough to drive frontend rendering tests.

This avoids requiring Windows frontend work to wait for:

- watcher startup
- cross-repo local environment alignment
- live job processing
- transient runtime state

Runtime end-to-end testing still matters, but it should come after fixture-based frontend adaptation.

---

## 6. Required Handoff From Claude To Me

Whenever Claude finishes a backend-facing deliverable that affects Windows, Claude should provide three things.

### 1. Contract update

A short statement of what changed in the backend contract.

Minimum required information:

- scope
- affected modes
- fields added / removed / reinterpreted
- section kinds added / changed
- `render_hints.layout_family` value

### 2. Fixture JSON

A minimal but representative sample payload that Windows can use directly in tests.

### 3. Short implementation note

A concise summary answering:

- what changed
- what Windows needs to do
- whether the new structure is additive or breaking

---

## 7. Required Handoff From Me To Claude

Whenever Windows discovers ambiguity or a missing field, I should not silently work around it.

Instead, I should hand back a short contract request containing:

- which field is missing or unclear
- where Windows expected to consume it
- whether it is required or optional
- what fallback behavior currently exists
- whether the fix belongs in schema, payload generation, or semantics clarification

This keeps backend and frontend discussion focused on the contract rather than on symptoms.

---

## 8. Recommended Handoff Templates

### Claude -> Windows

```md
## WSL Change
- Scope:
- Affected modes:
- Output contract change:
- Example payload:
- Backward compatibility:
- Tests:
```

### Windows -> Claude

```md
## Windows Change
- Scope:
- Fields consumed:
- Required vs optional:
- Fallback behavior:
- Tests:
```

These templates are intentionally small.
The goal is clarity, not ceremony.

---

## 9. Parallel Work Pattern

The preferred rhythm is:

1. user defines a small target
2. Claude updates the WSL contract and fixture for that target
3. I adapt the Windows reading surface against the fixture
4. user runs acceptance
5. feedback returns either to backend semantics or frontend reading experience

This means the two sides can work in parallel on different branches without repeatedly waiting on live integration.

### Example

If the current goal is:

- make `guide` mode more useful

Then:

- Claude should define the `guide` `product_view`
- Claude should ship a guide fixture
- I should render that fixture well in Windows
- the user should validate whether the output is actually readable and useful

Not every cycle needs a live watcher run until the integration checkpoint.

---

## 10. Current Priority Interpretation

The current product direction suggests this order of work:

### Claude should prioritize

- deep-analysis output quality
- evidence / interpretation separation
- stronger `product_view` for additional modes such as `guide` and `review`
- better prompt / schema discipline
- clearer mode-specific artifacts

### I should prioritize

- reading layout quality
- mode-specific visual presentation
- stronger library reading flows
- robust fallback behavior when optional fields are absent
- fixture-driven rendering tests

This aligns with the broader project principle that the next major gains are more likely to come from better output quality than from more shell UI expansion.

---

## 11. Shared Quality Standard

The collaboration should be judged by the following standards:

- backend contracts are explicit
- frontend rendering does not guess semantics
- fixtures are sufficient for offline frontend work
- end-to-end runs confirm the fixture assumptions
- mode-specific outputs remain distinct instead of collapsing into one generic template
- changes improve real reading usefulness, not just structural neatness

---

## 12. What Success Looks Like

This collaboration model is working if:

- Claude can ship a new mode contract without waiting on GUI integration first
- I can build and test the Windows experience using fixtures before runtime integration
- the user only needs live integration checks at milestone points
- frontend and backend do not fight over who owns meaning
- product quality improves without expanding scope uncontrollably

---

## 13. Shortest Summary

The shortest correct version of this collaboration contract is:

- Claude owns WSL output semantics
- I own Windows reading and presentation
- `product_view` is the contract
- fixtures are the shared currency
- unclear fields must be resolved in the contract, not guessed in the GUI

That is the working rule set for future collaboration.
