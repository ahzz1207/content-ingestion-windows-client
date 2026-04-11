# Template System v1 Revised Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a small user-selectable template system for URL submission that produces mode-aware editorial results across WSL processing and Windows result surfaces.

**Architecture:** Keep one shared Reader pass, resolve the final mode in code, and branch only the Synthesizer pass for the three implemented v1 modes: `argument`, `guide`, and `review`. Add an `editorial` sub-object to `StructuredResult`, serialize explicit `requested_mode` / `resolved_mode` / `mode_confidence`, and attach a minimal `display` contract to new editorial sections. Phase 2 is intentionally limited to GUI + API + result view; browser extension and Obsidian template selection are deferred until the WSL contract stabilizes.

**Tech Stack:** Python 3.10/3.12, dataclasses, OpenAI structured output, PySide6, FastAPI, pytest

---

## Why This Revision Exists

This plan supersedes the earlier detailed draft in one important way: it closes the contract and scope gaps that would otherwise force mid-implementation rewrites.

The original draft was directionally right, but still had five practical risks:

1. `requested_mode` was at risk of being overwritten or inferred too late.
2. `Auto` could resolve to modes that v1 does not actually synthesize.
3. New editorial fields did not yet have a display contract.
4. Phase 2 scope still implicitly mixed GUI/API work with browser-extension and Obsidian entry points.
5. Result rendering changes did not explicitly include the call-site wiring needed to pass `resolved_mode`.

This revised plan fixes those issues before implementation begins.

---

## Explicit v1 Decisions

### Decision 1: v1 implements exactly three resolved modes

The taxonomy document defines five conceptual modes, but Template System v1 implements only:

- `argument`
- `guide`
- `review`

`Auto` must resolve only into one of these three values in v1.

The Reader may still observe broader content signals, but the resolver must clamp final output to the implemented set.

### Decision 2: routing values are explicit data, not serializer guesses

The WSL pipeline must compute:

- `requested_mode`
- `resolved_mode`
- `mode_confidence`

inside `analyze_asset()` immediately after the Reader pass.

These values must then be passed explicitly into editorial construction and serialization. No serializer may infer or overwrite them later.

### Decision 3: editorial data and display data are different layers

The new `editorial` sub-object stores raw editorial meaning.

The new `display` payload v1 stores lightweight presentation hints:

- `kind`
- `priority`
- `tone`
- `compact_text`

This is a semantic display layer, not a layout engine.

### Decision 4: Phase 2 scope is intentionally narrow

Phase 2 covers:

- Windows exporter/service/API propagation
- GUI submit-page template selector
- GUI result view mode pill
- lightweight mode-aware `insight_brief`

Phase 2 does **not** yet cover:

- browser extension template selector
- Obsidian manual submit template selector

Those are follow-up tasks after the WSL editorial contract is stable.

---

## File Map

### WSL files

| File | Responsibility in this plan |
|------|-----------------------------|
| `/home/ahzz1207/codex-demo/src/content_ingestion/core/models.py` | Add `EditorialBase`, `EditorialResult`; add `editorial` to `StructuredResult`; add routing fields to `LlmAnalysisResult` |
| `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py` | Add v1 Reader suggestion fields; add v1 mode resolver; add three Synthesizer schemas/instructions; build `editorial`; serialize `analysis_result.json` |
| `/home/ahzz1207/codex-demo/src/content_ingestion/inbox/processor.py` | Read `requested_mode` from metadata; pass to `analyze_asset()`; serialize editorial + display payload into `normalized.json` |
| `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py` | Routing, schema, editorial construction, analysis artifact serialization |
| `/home/ahzz1207/codex-demo/tests/unit/test_processor.py` | `requested_mode` flow and normalized serialization |

### Windows files

| File | Responsibility in this plan |
|------|-----------------------------|
| `H:/demo-win/src/windows_client/job_exporter/models.py` | Add `requested_mode` to `ExportRequest` and `JobMetadata` |
| `H:/demo-win/src/windows_client/job_exporter/exporter.py` | Write `requested_mode` into `metadata.json` |
| `H:/demo-win/src/windows_client/app/service.py` | Propagate `requested_mode` to exporter |
| `H:/demo-win/src/windows_client/app/workflow.py` | Propagate `requested_mode` through GUI-facing export methods |
| `H:/demo-win/src/windows_client/api/job_manager.py` | Accept and pass `requested_mode` |
| `H:/demo-win/src/windows_client/api/server.py` | Read `requested_mode` from POST payload |
| `H:/demo-win/src/windows_client/gui/main_window.py` | Add template selector and pass selected mode into GUI exports |
| `H:/demo-win/src/windows_client/app/insight_brief.py` | Lightweight mode-aware adaptation from the new `editorial` contract |
| `H:/demo-win/src/windows_client/gui/result_renderer.py` | Add mode pill and accept `resolved_mode` |
| `H:/demo-win/tests/unit/test_job_exporter.py` | Metadata propagation tests |
| `H:/demo-win/tests/unit/test_api/test_job_manager.py` | API propagation tests |
| `H:/demo-win/tests/unit/test_api/test_server.py` | Ingest endpoint propagation tests |
| `H:/demo-win/tests/unit/test_main_window.py` | GUI selector tests and submit-path propagation tests |
| `H:/demo-win/tests/unit/test_insight_brief.py` | Mode-aware adaptation tests |
| `H:/demo-win/tests/unit/test_result_renderer.py` | Mode pill tests |

---

## Phase 1: WSL Contract and Mode-Aware Synthesis

### Task 1: Lock v1 routing to implemented modes only

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write failing routing tests**

Add tests that lock these exact behaviors:

- `requested_mode="guide"` overrides Reader suggestion and returns `("guide", 1.0)`
- `requested_mode="auto"` uses Reader suggestion when it is one of `argument|guide|review`
- `requested_mode="auto"` falls back to `("argument", 0.5)` when the Reader suggestion is missing or invalid
- `READER_SCHEMA["suggested_mode"]` enum contains only `argument`, `guide`, `review`

- [ ] **Step 2: Run the targeted tests and confirm failure**

Run:

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "suggested_mode or resolve_mode" -v
```

Expected: failure because the fields or helper do not yet exist in the revised form.

- [ ] **Step 3: Implement the routing contract**

In `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`:

- add `suggested_mode` and `mode_confidence` to `READER_SCHEMA`
- keep the enum limited to `argument`, `guide`, `review`
- add `_VALID_V1_MODES = {"argument", "guide", "review"}`
- implement:

```python
def _resolve_mode(requested_mode: str, reader_payload: dict[str, object]) -> tuple[str, float]:
    if requested_mode in _VALID_V1_MODES:
        return requested_mode, 1.0
    suggested = str(reader_payload.get("suggested_mode") or "").strip()
    confidence = float(reader_payload.get("mode_confidence") or 0.5)
    if suggested in _VALID_V1_MODES:
        return suggested, confidence
    return "argument", 0.5
```

- [ ] **Step 4: Run the targeted tests and confirm pass**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "suggested_mode or resolve_mode" -v
```

- [ ] **Step 5: Run the full WSL suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): lock template routing to v1 modes"
```

### Task 2: Add the editorial sub-object and explicit routing fields

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/core/models.py`
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write failing model tests**

Add tests that assert:

- `StructuredResult(editorial=...)` is constructible
- `EditorialResult` stores `requested_mode`, `resolved_mode`, `mode_confidence`, `base`, and `mode_payload`
- `LlmAnalysisResult` includes top-level `requested_mode`, `resolved_mode`, and `mode_confidence`

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "editorial_result_dataclass" -v
```

- [ ] **Step 3: Implement the dataclasses**

In `/home/ahzz1207/codex-demo/src/content_ingestion/core/models.py`, add:

```python
@dataclass(slots=True)
class EditorialBase:
    core_summary: str
    bottom_line: str
    audience_fit: str
    save_worthy_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EditorialResult:
    requested_mode: str
    resolved_mode: str
    mode_confidence: float
    base: EditorialBase
    mode_payload: dict[str, Any] = field(default_factory=dict)
```

Then:

- add `editorial: EditorialResult | None = None` to `StructuredResult`
- add `requested_mode: str = "auto"`, `resolved_mode: str | None = None`, and `mode_confidence: float | None = None` to `LlmAnalysisResult`

- [ ] **Step 4: Update `analyze_asset()` to set routing fields immediately after the Reader pass**

In `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`:

- change `analyze_asset()` signature to accept `requested_mode: str = "auto"`
- compute:

```python
resolved_mode, mode_confidence = _resolve_mode(requested_mode, reader_payload)
result.requested_mode = requested_mode
result.resolved_mode = resolved_mode
result.mode_confidence = mode_confidence
```

Do this before any Synthesizer call.

- [ ] **Step 5: Run targeted tests, then full suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "editorial_result_dataclass or resolve_mode" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/core/models.py src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add editorial result model and explicit routing fields"
```

### Task 3: Add the three v1 Synthesizer schemas and prompt variants

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write failing schema and prompt tests**

Add tests that assert:

- `ARGUMENT_ANALYSIS_SCHEMA` contains `core_summary`, `bottom_line`, `author_thesis`, `evidence_backed_points`, `what_is_new`, `tensions`
- `GUIDE_ANALYSIS_SCHEMA` contains `core_summary`, `bottom_line`, `guide_goal`, `recommended_steps`, `tips`, `pitfalls`
- `REVIEW_ANALYSIS_SCHEMA` contains `core_summary`, `bottom_line`, `overall_judgment`, `highlights`, `style_and_mood`, `who_it_is_for`
- `_synthesizer_instructions_for_mode("argument")`, `("guide")`, and `("review")` return different strings and mention their own required fields

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "schema_has_required or synthesizer_instructions" -v
```

- [ ] **Step 3: Implement the three schemas and prompt functions**

In `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`:

- add `_SHARED_EDITORIAL_SCHEMA_PROPS`
- define:
  - `ARGUMENT_ANALYSIS_SCHEMA`
  - `GUIDE_ANALYSIS_SCHEMA`
  - `REVIEW_ANALYSIS_SCHEMA`
- add:
  - `_synthesizer_instructions_argument()`
  - `_synthesizer_instructions_guide()`
  - `_synthesizer_instructions_review()`
  - `_synthesizer_instructions_for_mode(resolved_mode: str) -> str`
- add a `_MODE_SCHEMA` map keyed by the three v1 modes

- [ ] **Step 4: Route the Synthesizer pass by `resolved_mode`**

In `analyze_asset()`:

- after `resolved_mode` is known, select:

```python
synthesizer_schema = _MODE_SCHEMA.get(resolved_mode, ARGUMENT_ANALYSIS_SCHEMA)
instructions = _synthesizer_instructions_for_mode(resolved_mode)
```

- then call the structured response with those values

- [ ] **Step 5: Run targeted tests, then full suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "schema_has_required or synthesizer_instructions" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add mode-specific synthesizer schemas and prompts"
```

### Task 4: Build `StructuredResult.editorial` from explicit routing inputs

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write failing structured-result tests**

Add tests that assert:

- `_build_structured_result(..., requested_mode="auto", resolved_mode="argument", mode_confidence=0.72)` writes those exact values into `result.editorial`
- `argument` mode stores `author_thesis`, `evidence_backed_points`, `interpretive_points`, `what_is_new`, `tensions`, `uncertainties`
- `guide` mode stores `guide_goal`, `recommended_steps`, `tips`, `pitfalls`, `prerequisites`, `quick_win`
- `review` mode stores `overall_judgment`, `highlights`, `style_and_mood`, `what_stands_out`, `who_it_is_for`, `reservation_points`

- [ ] **Step 2: Run targeted tests and confirm failure**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "build_structured_result_mode" -v
```

- [ ] **Step 3: Update the helper signature and construction flow**

Change `_build_structured_result()` to accept:

```python
def _build_structured_result(
    payload: dict[str, object],
    *,
    reader_payload: dict[str, object],
    requested_mode: str,
    resolved_mode: str,
    mode_confidence: float,
) -> StructuredResult:
```

At the end of the helper:

- create `EditorialBase` from `core_summary`, `bottom_line`, `audience_fit`, `save_worthy_points`
- create a mode-specific `mode_payload`
- attach:

```python
editorial = EditorialResult(
    requested_mode=requested_mode,
    resolved_mode=resolved_mode,
    mode_confidence=mode_confidence,
    base=base,
    mode_payload=mode_payload,
)
```

Then return `StructuredResult(..., editorial=editorial)`.

- [ ] **Step 4: Update every caller**

In `analyze_asset()`, pass all three explicit routing values into both the main build path and the repair path.

- [ ] **Step 5: Run targeted tests, then full suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "build_structured_result_mode" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): build editorial result from explicit mode routing"
```

### Task 5: Add display payload v1 to editorial serialization

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/inbox/processor.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_llm_pipeline.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_processor.py`

- [ ] **Step 1: Write failing serialization tests**

Add tests that assert `analysis_result.json` and `normalized.json` both include:

- top-level `requested_mode`, `resolved_mode`, `mode_confidence`
- `result.editorial.base`
- `result.editorial.mode_payload`
- minimal `display` payloads on:
  - `core_summary`
  - `bottom_line`
  - `save_worthy_points`
  - `argument.author_thesis`
  - `guide.recommended_steps`
  - `review.highlights`

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py tests/unit/test_processor.py -k "editorial and display" -v
```

- [ ] **Step 3: Add serializer helpers**

In `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`, add helpers like:

```python
def _display_payload(*, kind: str, priority: int, tone: str, compact_text: str) -> dict[str, object]:
    return {
        "kind": kind,
        "priority": priority,
        "tone": tone,
        "compact_text": compact_text,
    }
```

Then add editorial-specific helpers that map fields to v1 defaults:

- `core_summary` -> `summary`, priority `0`, tone `hero`
- `bottom_line` -> `bottom_line`, priority `30`, tone `hero`
- `save_worthy_points[*]` -> `key_point`, priority `110`, tone `accent`
- `author_thesis` -> `thesis`, priority `10`, tone `hero`
- `recommended_steps[*]` -> `step`, priority `100`, tone `accent`
- `highlights[*]` -> `highlight`, priority `110`, tone `accent`

- [ ] **Step 4: Serialize editorial + display in both artifacts**

Update both serializer paths:

- `/home/ahzz1207/codex-demo/src/content_ingestion/pipeline/llm_pipeline.py`
- `/home/ahzz1207/codex-demo/src/content_ingestion/inbox/processor.py`

The serialized `editorial` shape should look like:

```json
{
  "requested_mode": "auto",
  "resolved_mode": "guide",
  "mode_confidence": 0.84,
  "base": {
    "core_summary": "...",
    "bottom_line": "...",
    "audience_fit": "...",
    "save_worthy_points": ["..."],
    "display": {
      "core_summary": {...},
      "bottom_line": {...},
      "save_worthy_points": [{...}]
    }
  },
  "mode_payload": {
    "...": "...",
    "display": {
      "...": {...}
    }
  }
}
```

Do not invent layout or card-grid metadata in v1. Only add `kind`, `priority`, `tone`, and `compact_text`.

- [ ] **Step 5: Run targeted tests, then full suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py tests/unit/test_processor.py -k "editorial and display" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py src/content_ingestion/inbox/processor.py tests/unit/test_llm_pipeline.py tests/unit/test_processor.py
git commit -m "feat(wsl): serialize editorial display payload v1"
```

### Task 6: Read `requested_mode` from handoff metadata and thread it through processing

**Files:**
- Modify: `/home/ahzz1207/codex-demo/src/content_ingestion/inbox/processor.py`
- Test: `/home/ahzz1207/codex-demo/tests/unit/test_processor.py`

- [ ] **Step 1: Write failing processor tests**

Add tests that assert:

- when `metadata.json` contains `"requested_mode": "guide"`, `analyze_asset(..., requested_mode="guide")` is called
- `normalized.json` preserves both `requested_mode` and `resolved_mode`

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_processor.py -k "requested_mode" -v
```

- [ ] **Step 3: Implement metadata threading**

In `/home/ahzz1207/codex-demo/src/content_ingestion/inbox/processor.py`:

- read:

```python
requested_mode = str(metadata.get("requested_mode") or "auto").strip()
```

- pass it into:

```python
llm_analysis = analyze_asset(
    job_dir=target_dir,
    asset=asset,
    settings=self.settings,
    requested_mode=requested_mode,
)
```

- [ ] **Step 4: Run targeted tests, then full suite**

```bash
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_processor.py -k "requested_mode" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 5: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/inbox/processor.py tests/unit/test_processor.py
git commit -m "feat(wsl): thread requested_mode from metadata into llm analysis"
```

---

## Phase 2: Windows Entry and Lightweight Result Surface

### Task 7: Propagate `requested_mode` through exporter, service, workflow, API

**Files:**
- Modify: `H:/demo-win/src/windows_client/job_exporter/models.py`
- Modify: `H:/demo-win/src/windows_client/job_exporter/exporter.py`
- Modify: `H:/demo-win/src/windows_client/app/service.py`
- Modify: `H:/demo-win/src/windows_client/app/workflow.py`
- Modify: `H:/demo-win/src/windows_client/api/job_manager.py`
- Modify: `H:/demo-win/src/windows_client/api/server.py`
- Test: `H:/demo-win/tests/unit/test_job_exporter.py`
- Test: `H:/demo-win/tests/unit/test_api/test_job_manager.py`
- Test: `H:/demo-win/tests/unit/test_api/test_server.py`

- [ ] **Step 1: Write failing propagation tests**

Add tests that assert:

- `ExportRequest` and `JobMetadata` accept `requested_mode`
- `metadata.json` writes `requested_mode`
- `service.export_url_job()` and `service.export_browser_job()` pass `requested_mode` into `ExportRequest`
- `workflow.export_url_job()` and `workflow.export_browser_job()` accept and forward `requested_mode`
- API `/api/v1/ingest` forwards `requested_mode` into `job_manager.submit_url()`

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_job_exporter.py tests/unit/test_api/test_job_manager.py tests/unit/test_api/test_server.py -k "requested_mode" -v
```

- [ ] **Step 3: Implement the propagation path**

Make these exact signature updates:

```python
# job_exporter/models.py
requested_mode: str = "auto"

# app/service.py
def export_url_job(..., requested_mode: str = "auto", ...):
def export_browser_job(..., requested_mode: str = "auto", ...):

# app/workflow.py
def export_url_job(..., requested_mode: str = "auto", ...):
def export_browser_job(..., requested_mode: str = "auto", ...):

# api/job_manager.py
def submit_url(..., requested_mode: str = "auto", ...):
```

In `server.py`, read:

```python
requested_mode = str(payload.get("requested_mode") or "auto").strip()
```

- [ ] **Step 4: Run targeted tests, then Windows unit suite**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_job_exporter.py tests/unit/test_api/test_job_manager.py tests/unit/test_api/test_server.py -k "requested_mode" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 5: Commit**

```bash
cd H:/demo-win
git add src/windows_client/job_exporter/models.py src/windows_client/job_exporter/exporter.py src/windows_client/app/service.py src/windows_client/app/workflow.py src/windows_client/api/job_manager.py src/windows_client/api/server.py tests/unit/test_job_exporter.py tests/unit/test_api/test_job_manager.py tests/unit/test_api/test_server.py
git commit -m "feat(win): propagate requested_mode through export and api paths"
```

### Task 8: Add GUI template selector and thread it into both HTTP and browser exports

**Files:**
- Modify: `H:/demo-win/src/windows_client/gui/main_window.py`
- Test: `H:/demo-win/tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing GUI tests**

Add tests that assert:

- `template_selector` exists with exactly four choices
- item data values are `auto`, `argument`, `guide`, `review`
- `_start_from_input()` and `_run_export()` propagate the selected value into `workflow.export_url_job()` or `workflow.export_browser_job()`

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_main_window.py -k "template_selector or requested_mode" -v
```

- [ ] **Step 3: Implement the selector**

In `H:/demo-win/src/windows_client/gui/main_window.py`:

- import `QComboBox`
- add `self.template_selector = QComboBox()`
- populate item data with `auto`, `argument`, `guide`, `review`
- place it near the URL field on the submit card
- in `_start_from_input()` read:

```python
requested_mode = self.template_selector.currentData() or "auto"
```

- pass `requested_mode` through `_run_export()`
- extend `_run_export()` to pass `requested_mode` into both `workflow.export_url_job()` and `workflow.export_browser_job()`

- [ ] **Step 4: Run targeted tests, then Windows unit suite**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_main_window.py -k "template_selector or requested_mode" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 5: Commit**

```bash
cd H:/demo-win
git add src/windows_client/gui/main_window.py tests/unit/test_main_window.py
git commit -m "feat(win): add GUI template selector for template system v1"
```

### Task 9: Make `insight_brief` and result rendering lightly mode-aware

**Files:**
- Modify: `H:/demo-win/src/windows_client/app/insight_brief.py`
- Modify: `H:/demo-win/src/windows_client/gui/result_renderer.py`
- Modify: `H:/demo-win/src/windows_client/gui/main_window.py`
- Test: `H:/demo-win/tests/unit/test_insight_brief.py`
- Test: `H:/demo-win/tests/unit/test_result_renderer.py`
- Test: `H:/demo-win/tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing result-surface tests**

Add tests that assert:

- `adapt_from_structured_result()` can read `editorial.base` plus one mode-specific section:
  - `argument` -> `evidence_backed_points`
  - `guide` -> `recommended_steps`
  - `review` -> `highlights`
- `result_renderer.render(..., resolved_mode="guide")` shows a mode pill
- the main-window render path passes `resolved_mode` into the renderer / inline result view call chain

- [ ] **Step 2: Run the targeted tests and confirm failure**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_insight_brief.py tests/unit/test_result_renderer.py tests/unit/test_main_window.py -k "editorial or mode_pill or resolved_mode" -v
```

- [ ] **Step 3: Implement lightweight adaptation**

In `H:/demo-win/src/windows_client/app/insight_brief.py`:

- if `result["editorial"]` exists:
  - build `hero` from `editorial.base.core_summary`
  - build `synthesis_conclusion` from `editorial.base.bottom_line`
  - build `quick_takeaways` from `editorial.base.save_worthy_points`
  - branch lightly by `resolved_mode`
- keep the current legacy fallback intact when `editorial` is absent

Do **not** attempt full per-mode rendering logic in v1.

- [ ] **Step 4: Implement mode pill and wire the call site**

In `H:/demo-win/src/windows_client/gui/result_renderer.py`:

- add `_MODE_DISPLAY_LABELS`
- add `self.mode_pill`
- extend `render()` to accept `resolved_mode: str | None = None`

In `H:/demo-win/src/windows_client/gui/main_window.py`:

- update the render call path so the resolved mode from the current result is passed into the renderer or inline result view
- do not rely on renderer defaults; pass it explicitly

- [ ] **Step 5: Run targeted tests, then Windows unit suite**

```bash
cd H:/demo-win && python -m pytest tests/unit/test_insight_brief.py tests/unit/test_result_renderer.py tests/unit/test_main_window.py -k "editorial or mode_pill or resolved_mode" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 6: Commit**

```bash
cd H:/demo-win
git add src/windows_client/app/insight_brief.py src/windows_client/gui/result_renderer.py src/windows_client/gui/main_window.py tests/unit/test_insight_brief.py tests/unit/test_result_renderer.py tests/unit/test_main_window.py
git commit -m "feat(win): add lightweight mode-aware result rendering"
```

---

## Deferred Work

These items are intentionally out of scope for this revised v1 plan:

- browser extension submit-time template selector
- Obsidian manual submit template selector
- `informational` and `narrative` synthesizer variants
- card-layout-specific metadata beyond `display payload v1`
- full mode-aware result renderer layout branching

They should be planned only after this v1 contract is green in both repos.

---

## Acceptance Checklist

- [ ] GUI submit page exposes exactly four choices: `auto`, `argument`, `guide`, `review`
- [ ] GUI submit path passes the selected mode into both direct URL export and browser export
- [ ] `metadata.json` preserves `requested_mode`
- [ ] WSL `analysis_result.json` preserves top-level `requested_mode`, `resolved_mode`, `mode_confidence`
- [ ] WSL `normalized.json` preserves the same three fields
- [ ] `StructuredResult.editorial.base.core_summary` and `bottom_line` are non-empty for all three modes
- [ ] `argument`, `guide`, and `review` differ structurally in `mode_payload`, not just wording
- [ ] `editorial.display` exists for the minimum v1 fields
- [ ] GUI result view can display a mode pill from `resolved_mode`
- [ ] WSL: `cd /home/ahzz1207/codex-demo && python3 -m pytest -q` passes
- [ ] Windows: `cd H:/demo-win && python -m pytest tests/unit/ -q` passes

---

## Recommended Execution Order

Implement in this order and do not start Phase 2 until Phase 1 is fully green:

1. Task 1 - lock v1 routing
2. Task 2 - add editorial result model
3. Task 3 - add three synthesizer schemas/prompts
4. Task 4 - build editorial from explicit routing inputs
5. Task 5 - add display payload v1
6. Task 6 - thread `requested_mode` through processor
7. Task 7 - propagate through Windows export and API paths
8. Task 8 - add GUI selector
9. Task 9 - add lightweight mode-aware result rendering

This keeps the contract stable before any UI depends on it.
