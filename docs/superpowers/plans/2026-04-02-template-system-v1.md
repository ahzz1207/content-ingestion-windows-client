# Template System v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce user-selectable analysis templates (Auto / 深度分析 / 实用提炼 / 推荐导览) backed by mode-aware WSL synthesis and a shared editorial contract.

**Architecture:** Reader pass outputs `suggested_mode` signal; `_resolve_mode()` decides final `resolved_mode` (explicit user choice wins, Auto falls back to Reader signal). Synthesizer branches into three mode-specific prompt+schema variants. A new `EditorialResult` sub-object on `StructuredResult` carries shared base + `mode_payload` dict, avoiding flat-field explosion. Windows side propagates `requested_mode` through metadata and shows a mode pill in the result view.

**Tech Stack:** Python 3.12, dataclasses, OpenAI structured output (json_schema strict), PySide6, FastAPI, pytest

**Repos:**
- WSL: `/home/ahzz1207/codex-demo`
- Windows: `H:/demo-win`

**Test commands:**
- WSL: `cd /home/ahzz1207/codex-demo && python3 -m pytest -q`
- Windows: `cd H:/demo-win && python -m pytest tests/unit/ -q`

---

## File Map

### WSL changes
| File | Change |
|------|--------|
| `src/content_ingestion/core/models.py` | Add `EditorialBase`, `EditorialResult` dataclasses; add `editorial` field to `StructuredResult`; add `requested_mode`/`resolved_mode` to `LlmAnalysisResult` |
| `src/content_ingestion/pipeline/llm_pipeline.py` | Add `suggested_mode`+`mode_confidence` to `READER_SCHEMA`; add 3 mode schemas; add `_resolve_mode()`; update `analyze_asset()` signature; add 3 synthesizer instruction functions; update `_build_structured_result()`; update `_serialize_structured_result()` |
| `src/content_ingestion/inbox/processor.py` | Read `requested_mode` from metadata; pass to `analyze_asset()`; write editorial fields to `normalized.json` |
| `tests/unit/test_llm_pipeline.py` | Add mode routing tests, schema tests, editorial serialization tests |
| `tests/unit/test_inbox_processor.py` | Add requested_mode flow test |

### Windows changes
| File | Change |
|------|--------|
| `src/windows_client/job_exporter/models.py` | Add `requested_mode` to `ExportRequest` + `JobMetadata` |
| `src/windows_client/job_exporter/exporter.py` | Pass `requested_mode` through `build_metadata` + `_metadata_to_dict` |
| `src/windows_client/app/service.py` | Add `requested_mode` param to `export_url_job()` |
| `src/windows_client/api/job_manager.py` | Add `requested_mode` param to `submit_url()` |
| `src/windows_client/api/server.py` | Extract `requested_mode` from POST payload |
| `src/windows_client/gui/main_window.py` | Add QComboBox template selector |
| `src/windows_client/app/insight_brief.py` | Mode-aware adaptation (shared base + 1 key section per mode) |
| `src/windows_client/gui/result_renderer.py` | Mode pill + section emphasis |
| `tests/unit/test_job_exporter.py` | requested_mode in metadata |
| `tests/unit/test_api/test_job_manager.py` | submit_url with requested_mode |
| `tests/unit/test_api/test_server.py` | ingest endpoint with requested_mode |
| `tests/unit/test_main_window.py` | Template selector combo box |
| `tests/unit/test_insight_brief.py` | Mode-aware adaptation per mode |
| `tests/unit/test_result_renderer.py` | Mode pill rendering |

---

## Phase 1: WSL

---

### Task 1: Add `suggested_mode` + `mode_confidence` to READER_SCHEMA

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_llm_pipeline.py — add at end of file
def test_reader_schema_has_mode_fields():
    from content_ingestion.pipeline.llm_pipeline import READER_SCHEMA
    props = READER_SCHEMA["properties"]
    assert "suggested_mode" in props
    assert props["suggested_mode"]["type"] == "string"
    assert set(props["suggested_mode"]["enum"]) == {
        "argument", "guide", "review", "informational", "narrative"
    }
    assert "mode_confidence" in props
    assert props["mode_confidence"]["type"] == "number"
    assert "suggested_mode" in READER_SCHEMA["required"]
    assert "mode_confidence" in READER_SCHEMA["required"]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py::test_reader_schema_has_mode_fields -v
```
Expected: FAIL — `AssertionError: assert 'suggested_mode' in ...`

- [ ] **Step 3: Add fields to READER_SCHEMA in llm_pipeline.py**

In `READER_SCHEMA["properties"]`, add after `"content_signals"`:
```python
"suggested_mode": {
    "type": "string",
    "enum": ["argument", "guide", "review", "informational", "narrative"],
},
"mode_confidence": {"type": "number"},
```

In `READER_SCHEMA["required"]`, add `"suggested_mode"` and `"mode_confidence"`.

- [ ] **Step 4: Update `_reader_instructions()` to include mode classification**

At the end of the existing numbered list in `_reader_instructions()`, add:

```python
"""
6. CONTENT MODE — Classify the intended analysis mode for this content.
   Choose the single best fit:
   - argument: commentary, opinion, macro analysis, debate, long-form essay
   - guide: tutorial, walkthrough, how-to, step-by-step advice, travel tips
   - review: album/film/game/product review, exhibition curation, taste recommendation
   - informational: event notice, release note, policy update, factual summary
   - narrative: vlog, experience log, process diary, personal journey recap
   Set mode_confidence between 0.0 and 1.0.
   If the content fits multiple modes, pick the dominant one and lower confidence.
"""
```

- [ ] **Step 5: Run test to verify it passes**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py::test_reader_schema_has_mode_fields -v
```
Expected: PASS

- [ ] **Step 6: Run full test suite**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```
Expected: all 63 tests pass

- [ ] **Step 7: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add suggested_mode + mode_confidence to READER_SCHEMA"
```

---

### Task 2: Add EditorialBase + EditorialResult dataclasses to models.py

**Files:**
- Modify: `src/content_ingestion/core/models.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_llm_pipeline.py — add
def test_editorial_result_dataclass_exists():
    from content_ingestion.core.models import EditorialBase, EditorialResult, StructuredResult
    base = EditorialBase(
        core_summary="test summary",
        bottom_line="test bottom line",
        audience_fit="general readers",
        save_worthy_points=["point 1"],
    )
    editorial = EditorialResult(
        requested_mode="auto",
        resolved_mode="argument",
        mode_confidence=0.85,
        base=base,
        mode_payload={"author_thesis": "test thesis"},
    )
    result = StructuredResult(editorial=editorial)
    assert result.editorial.resolved_mode == "argument"
    assert result.editorial.base.core_summary == "test summary"
    assert result.editorial.mode_payload["author_thesis"] == "test thesis"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py::test_editorial_result_dataclass_exists -v
```
Expected: FAIL — `ImportError: cannot import name 'EditorialBase'`

- [ ] **Step 3: Add dataclasses to models.py**

After the `ChapterEntry` and `ArgumentSkeletonItem` dataclasses, add:

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

In `StructuredResult`, add field at the end:

```python
editorial: EditorialResult | None = None
```

In `LlmAnalysisResult`, add fields after `synthesizer_result_path`:

```python
requested_mode: str = "auto"
resolved_mode: str | None = None
mode_confidence: float | None = None
```

- [ ] **Step 4: Run test to verify it passes**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py::test_editorial_result_dataclass_exists -v
```
Expected: PASS

- [ ] **Step 5: Run full test suite**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```
Expected: all passing

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/core/models.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add EditorialBase + EditorialResult dataclasses to models"
```

---

### Task 3: Add three mode-specific Synthesizer schemas

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_llm_pipeline.py — add
def test_argument_schema_has_required_editorial_fields():
    from content_ingestion.pipeline.llm_pipeline import ARGUMENT_ANALYSIS_SCHEMA
    props = ARGUMENT_ANALYSIS_SCHEMA["properties"]
    for field in ["core_summary", "bottom_line", "audience_fit", "save_worthy_points",
                  "author_thesis", "evidence_backed_points", "interpretive_points",
                  "what_is_new", "tensions", "uncertainties", "verification_items"]:
        assert field in props, f"missing field: {field}"


def test_guide_schema_has_required_editorial_fields():
    from content_ingestion.pipeline.llm_pipeline import GUIDE_ANALYSIS_SCHEMA
    props = GUIDE_ANALYSIS_SCHEMA["properties"]
    for field in ["core_summary", "bottom_line", "audience_fit", "save_worthy_points",
                  "guide_goal", "recommended_steps", "tips", "pitfalls",
                  "prerequisites", "quick_win"]:
        assert field in props, f"missing field: {field}"


def test_review_schema_has_required_editorial_fields():
    from content_ingestion.pipeline.llm_pipeline import REVIEW_ANALYSIS_SCHEMA
    props = REVIEW_ANALYSIS_SCHEMA["properties"]
    for field in ["core_summary", "bottom_line", "audience_fit", "save_worthy_points",
                  "overall_judgment", "highlights", "style_and_mood",
                  "what_stands_out", "who_it_is_for", "reservation_points"]:
        assert field in props, f"missing field: {field}"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "schema_has_required" -v
```
Expected: 3 FAILs — `ImportError: cannot import name 'ARGUMENT_ANALYSIS_SCHEMA'`

- [ ] **Step 3: Add the three schemas to llm_pipeline.py**

After `READER_SCHEMA`, add:

```python
_SHARED_BASE_SCHEMA_PROPS = {
    "core_summary": {"type": "string"},
    "bottom_line": {"type": "string"},
    "content_kind": {"type": "string"},
    "author_stance": {"type": "string"},
    "audience_fit": {"type": "string"},
    "save_worthy_points": {"type": "array", "items": {"type": "string"}},
}
_SHARED_BASE_REQUIRED = ["core_summary", "bottom_line", "content_kind", "author_stance",
                          "audience_fit", "save_worthy_points"]

_VERIFICATION_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "claim": {"type": "string"},
        "status": {"type": "string", "enum": ["supported", "partial", "unsupported", "unclear"]},
        "evidence_segment_ids": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": ["string", "null"]},
        "confidence": {"type": ["number", "null"]},
    },
    "required": ["id", "claim", "status", "evidence_segment_ids", "rationale", "confidence"],
}

ARGUMENT_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **_SHARED_BASE_SCHEMA_PROPS,
        "author_thesis": {"type": "string"},
        "evidence_backed_points": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "details": {"type": "string"},
                    "evidence_segment_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "title", "details", "evidence_segment_ids"],
            },
        },
        "interpretive_points": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                    "kind": {"type": "string", "enum": ["implication", "alternative"]},
                    "evidence_segment_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "statement", "kind", "evidence_segment_ids"],
            },
        },
        "what_is_new": {"type": "string"},
        "tensions": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "verification_items": {"type": "array", "items": _VERIFICATION_ITEM_SCHEMA},
    },
    "required": [
        *_SHARED_BASE_REQUIRED,
        "author_thesis", "evidence_backed_points", "interpretive_points",
        "what_is_new", "tensions", "uncertainties", "verification_items",
    ],
}

GUIDE_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **_SHARED_BASE_SCHEMA_PROPS,
        "guide_goal": {"type": "string"},
        "recommended_steps": {"type": "array", "items": {"type": "string"}},
        "tips": {"type": "array", "items": {"type": "string"}},
        "pitfalls": {"type": "array", "items": {"type": "string"}},
        "prerequisites": {"type": "array", "items": {"type": "string"}},
        "quick_win": {"type": ["string", "null"]},
    },
    "required": [
        *_SHARED_BASE_REQUIRED,
        "guide_goal", "recommended_steps", "tips", "pitfalls", "prerequisites", "quick_win",
    ],
}

REVIEW_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **_SHARED_BASE_SCHEMA_PROPS,
        "overall_judgment": {"type": "string"},
        "highlights": {"type": "array", "items": {"type": "string"}},
        "style_and_mood": {"type": "string"},
        "what_stands_out": {"type": "string"},
        "who_it_is_for": {"type": "string"},
        "reservation_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        *_SHARED_BASE_REQUIRED,
        "overall_judgment", "highlights", "style_and_mood",
        "what_stands_out", "who_it_is_for", "reservation_points",
    ],
}
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "schema_has_required" -v
```
Expected: 3 PASSes

- [ ] **Step 5: Run full test suite**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```
Expected: all passing

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add ARGUMENT/GUIDE/REVIEW_ANALYSIS_SCHEMA for mode-specific synthesis"
```

---

### Task 4: `_resolve_mode()` + `requested_mode` param on `analyze_asset()`

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_resolve_mode_honors_explicit_request():
    from content_ingestion.pipeline.llm_pipeline import _resolve_mode
    mode, conf = _resolve_mode("guide", {"suggested_mode": "argument", "mode_confidence": 0.9})
    assert mode == "guide"
    assert conf == 1.0

def test_resolve_mode_uses_reader_when_auto():
    from content_ingestion.pipeline.llm_pipeline import _resolve_mode
    mode, conf = _resolve_mode("auto", {"suggested_mode": "review", "mode_confidence": 0.75})
    assert mode == "review"
    assert conf == 0.75

def test_resolve_mode_defaults_to_argument_on_missing_signal():
    from content_ingestion.pipeline.llm_pipeline import _resolve_mode
    mode, conf = _resolve_mode("auto", {})
    assert mode == "argument"
    assert conf == 0.5
```

- [ ] **Step 2: Run to verify failure**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "resolve_mode" -v
```
Expected: ImportError — `_resolve_mode` not found

- [ ] **Step 3: Add `_resolve_mode()` after the schema definitions**

```python
_VALID_MODES = {"argument", "guide", "review", "informational", "narrative"}

def _resolve_mode(requested_mode: str, reader_payload: dict) -> tuple[str, float]:
    """Return (resolved_mode, confidence).
    Explicit user choice wins at 1.0. Auto falls back to Reader signal.
    Defaults to ('argument', 0.5) when no signal present.
    """
    if requested_mode in _VALID_MODES:
        return requested_mode, 1.0
    suggested = str(reader_payload.get("suggested_mode") or "").strip()
    confidence = float(reader_payload.get("mode_confidence") or 0.5)
    if suggested in _VALID_MODES:
        return suggested, confidence
    return "argument", 0.5
```

- [ ] **Step 4: Update `analyze_asset()` signature and add routing step**

Change:
```python
def analyze_asset(*, job_dir: Path, asset: ContentAsset, settings: Settings) -> LlmAnalysisResult:
```
To:
```python
def analyze_asset(*, job_dir: Path, asset: ContentAsset, settings: Settings, requested_mode: str = "auto") -> LlmAnalysisResult:
```

After the Reader pass writes `reader_payload`, add:
```python
resolved_mode, mode_confidence = _resolve_mode(requested_mode, reader_payload)
result.requested_mode = requested_mode
result.resolved_mode = resolved_mode
result.mode_confidence = mode_confidence
result.steps.append({"name": "mode_routing", "status": "success",
                      "details": f"{requested_mode} -> {resolved_mode} ({mode_confidence:.2f})"})
```

- [ ] **Step 5: Run to verify all three tests pass**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "resolve_mode" -v
```

- [ ] **Step 6: Full suite**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 7: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): add _resolve_mode() and requested_mode param to analyze_asset"
```

---

### Task 5: Three mode-specific Synthesizer instructions + schema routing

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_synthesizer_instructions_argument_covers_key_fields():
    from content_ingestion.pipeline.llm_pipeline import _synthesizer_instructions_argument
    text = _synthesizer_instructions_argument()
    for kw in ["author_thesis", "evidence_backed_points", "tensions", "what_is_new"]:
        assert kw in text, f"missing: {kw}"

def test_synthesizer_instructions_guide_covers_key_fields():
    from content_ingestion.pipeline.llm_pipeline import _synthesizer_instructions_guide
    text = _synthesizer_instructions_guide()
    for kw in ["guide_goal", "recommended_steps", "pitfalls", "quick_win"]:
        assert kw in text, f"missing: {kw}"

def test_synthesizer_instructions_review_covers_key_fields():
    from content_ingestion.pipeline.llm_pipeline import _synthesizer_instructions_review
    text = _synthesizer_instructions_review()
    for kw in ["overall_judgment", "highlights", "who_it_is_for", "reservation_points"]:
        assert kw in text, f"missing: {kw}"
```

- [ ] **Step 2: Run to verify failure**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "synthesizer_instructions" -v
```

- [ ] **Step 3: Add three instruction functions + routing helper**

```python
def _synthesizer_instructions_argument() -> str:
    return """You are a critical-thinking analyst (argument mode).
Use the Reader's chapter_map and argument_skeleton to focus analysis.

REQUIRED OUTPUT FIELDS:
- core_summary: 1-2 sentences — what this content is and why it matters.
- bottom_line: The single most important judgment the reader should leave with.
- content_kind: article / opinion / analysis / report / interview / thread
- author_stance: objective / advocacy / critical / skeptical / promotional / explanatory / mixed
- audience_fit: Who benefits most from this content.
- save_worthy_points: 3-5 phrases (≤15 words each) worth archiving.
- author_thesis: Core claim in 1-2 sentences, grounded strictly in the text.
- evidence_backed_points: 4-8 key points. Each: title (≤12 words), details (3 dimensions:
  what the argument is / what supports it / how it relates to other points), evidence_segment_ids.
- interpretive_points: 3-5 implications or alternatives. kind = "implication" or "alternative".
- what_is_new: What is genuinely novel vs. common knowledge. Honest if nothing new.
- tensions: Real internal tensions or evidence-judgment gaps. Empty list if none.
- uncertainties: Questionable claims. Label each "text states" or "analyst inference".
- verification_items: id / claim / status (supported|partial|unsupported|unclear) / evidence_segment_ids / rationale / confidence.

RULES: Only use evidence_segment_ids from the provided list. Do not manufacture tensions."""


def _synthesizer_instructions_guide() -> str:
    return """You are an editorial analyst (guide mode).
Use the Reader's chapter_map to understand content structure.

REQUIRED OUTPUT FIELDS:
- core_summary: 1-2 sentences — what this guide covers and for whom.
- bottom_line: Most important practical takeaway.
- content_kind: tutorial / guide / walkthrough / explainer
- author_stance: objective / advisory / promotional / mixed
- audience_fit: Who this is written for and what prior knowledge it assumes.
- save_worthy_points: 3-5 short reminder phrases.
- guide_goal: What the reader is trying to accomplish.
- recommended_steps: Ordered list of concrete actions, each self-contained.
- tips: Shortcuts, best practices, or non-obvious optimisations from the source.
- pitfalls: Common mistakes or failure modes the author mentions.
- prerequisites: What the reader needs before starting.
- quick_win: Fastest path to visible progress. null if not applicable.

RULES: Preserve the original step order. Tips and pitfalls must come from the source text."""


def _synthesizer_instructions_review() -> str:
    return """You are an editorial analyst (review mode).
Use the Reader's structure to identify the evaluative stance.

REQUIRED OUTPUT FIELDS:
- core_summary: 1-2 sentences — what is being reviewed and the overall impression.
- bottom_line: Clearest verdict or recommendation in one sentence.
- content_kind: review / recommendation / curation / critique
- author_stance: advocacy / critical / balanced / promotional / mixed
- audience_fit: Who this review is most useful for.
- save_worthy_points: 3-5 short phrases worth remembering.
- overall_judgment: Author's final assessment. Quote or closely paraphrase.
- highlights: What stands out positively. Short, concrete observations.
- style_and_mood: Tone, atmosphere, or aesthetic quality being conveyed.
- what_stands_out: Single most distinctive or memorable aspect.
- who_it_is_for: Specific description of the ideal audience for the subject.
- reservation_points: Weaknesses, caveats, or "not for everyone" aspects.

RULES: Do not impose argument framing. Highlights and reservation_points must reflect the author's actual assessments."""


def _synthesizer_instructions_for_mode(mode: str) -> str:
    if mode == "guide":
        return _synthesizer_instructions_guide()
    if mode == "review":
        return _synthesizer_instructions_review()
    return _synthesizer_instructions_argument()
```

- [ ] **Step 4: Update the Synthesizer call in `analyze_asset()` to route schema + instructions**

Replace the existing `_call_structured_response(... instructions=_synthesizer_instructions() ...)` with:

```python
_MODE_SCHEMA = {
    "argument": ARGUMENT_ANALYSIS_SCHEMA,
    "guide": GUIDE_ANALYSIS_SCHEMA,
    "review": REVIEW_ANALYSIS_SCHEMA,
}
synthesizer_schema = _MODE_SCHEMA.get(resolved_mode, ARGUMENT_ANALYSIS_SCHEMA)
text_payload = _call_structured_response(
    client=client,
    model=settings.analysis_model,
    instructions=_synthesizer_instructions_for_mode(resolved_mode),
    input_payload=synthesizer_envelope.to_model_input(),
    schema_name="content_analysis",
    schema=synthesizer_schema,
)
```

- [ ] **Step 5: Run to verify 3 tests pass + full suite passes**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "synthesizer_instructions" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 6: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): mode-specific synthesizer instructions and schema routing"
```

---

### Task 6: Mode-aware `_build_structured_result()` + both serialization paths

**Files:**
- Modify: `src/content_ingestion/pipeline/llm_pipeline.py`
- Modify: `src/content_ingestion/inbox/processor.py`
- Test: `tests/unit/test_llm_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
def test_build_structured_result_argument_populates_editorial():
    from content_ingestion.pipeline.llm_pipeline import _build_structured_result
    payload = {
        "core_summary": "summary", "bottom_line": "bottom",
        "content_kind": "opinion", "author_stance": "advocacy",
        "audience_fit": "general", "save_worthy_points": ["p1"],
        "author_thesis": "thesis",
        "evidence_backed_points": [{"id": "kp-1", "title": "T", "details": "D", "evidence_segment_ids": []}],
        "interpretive_points": [{"id": "ip-1", "statement": "S", "kind": "implication", "evidence_segment_ids": []}],
        "what_is_new": "new", "tensions": ["t1"], "uncertainties": [], "verification_items": [],
    }
    result = _build_structured_result(payload, reader_payload={}, resolved_mode="argument")
    assert result.editorial is not None
    assert result.editorial.resolved_mode == "argument"
    assert result.editorial.base.core_summary == "summary"
    assert result.editorial.base.bottom_line == "bottom"
    assert result.editorial.mode_payload["author_thesis"] == "thesis"
    assert len(result.editorial.mode_payload["evidence_backed_points"]) == 1

def test_build_structured_result_guide_populates_editorial():
    from content_ingestion.pipeline.llm_pipeline import _build_structured_result
    payload = {
        "core_summary": "guide summary", "bottom_line": "do X",
        "content_kind": "tutorial", "author_stance": "advisory",
        "audience_fit": "beginners", "save_worthy_points": [],
        "guide_goal": "learn Y", "recommended_steps": ["s1", "s2"],
        "tips": [], "pitfalls": [], "prerequisites": [], "quick_win": None,
    }
    result = _build_structured_result(payload, reader_payload={}, resolved_mode="guide")
    assert result.editorial.resolved_mode == "guide"
    assert result.editorial.mode_payload["guide_goal"] == "learn Y"
    assert result.editorial.mode_payload["recommended_steps"] == ["s1", "s2"]

def test_serialize_structured_result_includes_editorial():
    from content_ingestion.pipeline.llm_pipeline import _build_structured_result, _serialize_structured_result
    payload = {
        "core_summary": "cs", "bottom_line": "bl",
        "content_kind": "review", "author_stance": "balanced",
        "audience_fit": "fans", "save_worthy_points": [],
        "overall_judgment": "great", "highlights": ["h1"],
        "style_and_mood": "warm", "what_stands_out": "vocals",
        "who_it_is_for": "music lovers", "reservation_points": [],
    }
    result = _build_structured_result(payload, reader_payload={}, resolved_mode="review")
    serialized = _serialize_structured_result(result)
    assert serialized["editorial"]["resolved_mode"] == "review"
    assert serialized["editorial"]["base"]["core_summary"] == "cs"
    assert serialized["editorial"]["mode_payload"]["overall_judgment"] == "great"
```

- [ ] **Step 2: Run to verify failure**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "build_structured_result or serialize_structured_result" -v
```

- [ ] **Step 3: Update `_build_structured_result()` signature and add editorial building**

Add `resolved_mode: str = "argument"` param. At the end before `return StructuredResult(...)`, build editorial:

```python
from content_ingestion.core.models import EditorialBase, EditorialResult

_editorial_base = EditorialBase(
    core_summary=str(payload.get("core_summary") or "").strip(),
    bottom_line=str(payload.get("bottom_line") or "").strip(),
    audience_fit=str(payload.get("audience_fit") or "").strip(),
    save_worthy_points=[str(p).strip() for p in payload.get("save_worthy_points", []) if str(p).strip()],
)
if resolved_mode == "argument":
    _mode_payload: dict = {
        "author_thesis": str(payload.get("author_thesis") or "").strip(),
        "evidence_backed_points": list(payload.get("evidence_backed_points", [])),
        "interpretive_points": list(payload.get("interpretive_points", [])),
        "what_is_new": str(payload.get("what_is_new") or "").strip(),
        "tensions": [str(t).strip() for t in payload.get("tensions", []) if str(t).strip()],
        "uncertainties": [str(u).strip() for u in payload.get("uncertainties", []) if str(u).strip()],
    }
elif resolved_mode == "guide":
    _mode_payload = {
        "guide_goal": str(payload.get("guide_goal") or "").strip(),
        "recommended_steps": [str(s).strip() for s in payload.get("recommended_steps", []) if str(s).strip()],
        "tips": [str(t).strip() for t in payload.get("tips", []) if str(t).strip()],
        "pitfalls": [str(p).strip() for p in payload.get("pitfalls", []) if str(p).strip()],
        "prerequisites": [str(p).strip() for p in payload.get("prerequisites", []) if str(p).strip()],
        "quick_win": str(payload.get("quick_win") or "").strip() or None,
    }
elif resolved_mode == "review":
    _mode_payload = {
        "overall_judgment": str(payload.get("overall_judgment") or "").strip(),
        "highlights": [str(h).strip() for h in payload.get("highlights", []) if str(h).strip()],
        "style_and_mood": str(payload.get("style_and_mood") or "").strip(),
        "what_stands_out": str(payload.get("what_stands_out") or "").strip(),
        "who_it_is_for": str(payload.get("who_it_is_for") or "").strip(),
        "reservation_points": [str(r).strip() for r in payload.get("reservation_points", []) if str(r).strip()],
    }
else:
    _mode_payload = {}

_editorial = EditorialResult(
    requested_mode=resolved_mode,
    resolved_mode=resolved_mode,
    mode_confidence=float(payload.get("mode_confidence") or 0.5),
    base=_editorial_base,
    mode_payload=_mode_payload,
)
```

Add `editorial=_editorial` to `StructuredResult(...)`.

Update all callers of `_build_structured_result` inside `analyze_asset()` to pass `resolved_mode=resolved_mode`.

- [ ] **Step 4: Update `_serialize_structured_result()` in llm_pipeline.py to include editorial**

Add to the return dict:
```python
"editorial": None if result.editorial is None else {
    "requested_mode": result.editorial.requested_mode,
    "resolved_mode": result.editorial.resolved_mode,
    "mode_confidence": result.editorial.mode_confidence,
    "base": {
        "core_summary": result.editorial.base.core_summary,
        "bottom_line": result.editorial.base.bottom_line,
        "audience_fit": result.editorial.base.audience_fit,
        "save_worthy_points": result.editorial.base.save_worthy_points,
    },
    "mode_payload": result.editorial.mode_payload,
},
```

Also add to the `analysis_result.json` writeout dict:
```python
"requested_mode": result.requested_mode,
"resolved_mode": result.resolved_mode,
"mode_confidence": result.mode_confidence,
```

- [ ] **Step 5: Update `processor.py` — read `requested_mode` from metadata + write editorial to normalized.json**

In the `_process_job()` method where `analyze_asset()` is called, change:
```python
llm_analysis = analyze_asset(job_dir=target_dir, asset=asset, settings=self.settings)
```
To:
```python
requested_mode = str(metadata.get("requested_mode") or "auto").strip()
llm_analysis = analyze_asset(
    job_dir=target_dir, asset=asset, settings=self.settings,
    requested_mode=requested_mode,
)
```

Add to top-level of `normalized_payload`:
```python
"requested_mode": llm_analysis.requested_mode,
"resolved_mode": llm_analysis.resolved_mode,
"mode_confidence": llm_analysis.mode_confidence,
```

In `processor.py`'s `_serialize_structured_result()`, add at the end of the return dict:
```python
"editorial": None if result.editorial is None else {
    "requested_mode": result.editorial.requested_mode,
    "resolved_mode": result.editorial.resolved_mode,
    "mode_confidence": result.editorial.mode_confidence,
    "base": {
        "core_summary": result.editorial.base.core_summary,
        "bottom_line": result.editorial.base.bottom_line,
        "audience_fit": result.editorial.base.audience_fit,
        "save_worthy_points": result.editorial.base.save_worthy_points,
    },
    "mode_payload": result.editorial.mode_payload,
},
```

- [ ] **Step 6: Run tests to verify they pass**

```
cd /home/ahzz1207/codex-demo && python3 -m pytest tests/unit/test_llm_pipeline.py -k "build_structured or serialize_structured" -v
cd /home/ahzz1207/codex-demo && python3 -m pytest -q
```

- [ ] **Step 7: Commit**

```bash
cd /home/ahzz1207/codex-demo
git add src/content_ingestion/pipeline/llm_pipeline.py src/content_ingestion/inbox/processor.py tests/unit/test_llm_pipeline.py
git commit -m "feat(wsl): mode-aware _build_structured_result, editorial serialization in pipeline + processor"
```

---

## Phase 2: Windows

---

### Task 7: `requested_mode` through ExportRequest → metadata.json

**Files:**
- Modify: `src/windows_client/job_exporter/models.py`
- Modify: `src/windows_client/job_exporter/exporter.py`
- Test: `tests/unit/test_job_exporter.py`

- [ ] **Step 1: Write failing test**

```python
def test_export_writes_requested_mode_to_metadata(tmp_path):
    import json
    from unittest.mock import MagicMock, patch
    from windows_client.job_exporter.exporter import JobExporter
    from windows_client.job_exporter.models import ExportRequest

    request = ExportRequest(source_url="https://x.com", shared_root=tmp_path, requested_mode="guide")
    payload = MagicMock()
    payload.content_type = "html"
    payload.platform = "generic"
    payload.content_shape = "article"
    payload.final_url = None
    payload.payload_text = "<html></html>"

    exporter = JobExporter()
    with patch.object(exporter, "_validate_request"):
        result = exporter.export(request, payload)

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata.get("requested_mode") == "guide"
```

- [ ] **Step 2: Run to verify failure**

```
cd H:/demo-win && python -m pytest tests/unit/test_job_exporter.py::test_export_writes_requested_mode_to_metadata -v
```

- [ ] **Step 3: Add `requested_mode` to `ExportRequest` and `JobMetadata` in models.py**

```python
# ExportRequest — add at end:
requested_mode: str = "auto"

# JobMetadata — add at end:
requested_mode: str = "auto"
```

- [ ] **Step 4: Pass through in exporter.py**

In `build_metadata()`, add `requested_mode=request.requested_mode` to the `JobMetadata(...)` constructor.

In `_metadata_to_dict()`, add:
```python
if metadata.requested_mode and metadata.requested_mode != "auto":
    data["requested_mode"] = metadata.requested_mode
```

- [ ] **Step 5: Run to verify test passes + full suite**

```
cd H:/demo-win && python -m pytest tests/unit/test_job_exporter.py::test_export_writes_requested_mode_to_metadata -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 6: Commit**

```bash
cd H:/demo-win
git add src/windows_client/job_exporter/models.py src/windows_client/job_exporter/exporter.py tests/unit/test_job_exporter.py
git commit -m "feat(win): add requested_mode to ExportRequest/JobMetadata/metadata.json"
```

---

### Task 8: Propagate `requested_mode` through service → job_manager → API server

**Files:**
- Modify: `src/windows_client/app/service.py`
- Modify: `src/windows_client/api/job_manager.py`
- Modify: `src/windows_client/api/server.py`
- Test: `tests/unit/test_api/test_job_manager.py`, `tests/unit/test_api/test_server.py`

- [ ] **Step 1: Write failing tests**

```python
# test_job_manager.py
def test_submit_url_passes_requested_mode_to_service(tmp_path):
    from unittest.mock import MagicMock
    from windows_client.api.job_manager import JobManager
    mock_service = MagicMock()
    mock_result = MagicMock()
    mock_result.job_id = "j1"
    mock_result.job_dir = tmp_path / "j1"
    mock_result.metadata_path = tmp_path / "j1" / "metadata.json"
    (tmp_path / "j1").mkdir()
    mock_result.metadata_path.write_text('{"source_url":"https://x.com","content_type":"html","platform":"generic"}')
    mock_service.export_url_job.return_value = mock_result
    manager = JobManager(service=mock_service, shared_inbox_root=tmp_path)
    manager.submit_url(url="https://x.com", requested_mode="review")
    assert mock_service.export_url_job.call_args.kwargs["requested_mode"] == "review"

# test_server.py
def test_ingest_endpoint_passes_requested_mode(tmp_path):
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient
    from windows_client.api.server import create_app
    from windows_client.api.config import ApiConfig
    mock_manager = MagicMock()
    mock_manager.submit_url.return_value = MagicMock(
        job_id="j1", status="queued", source_url="https://x.com",
        content_type="html", platform="generic", created_at=None,
        job_dir=None, payload_path=None, metadata_path=None, ready_path=None,
    )
    config = ApiConfig(api_token="test-token", shared_inbox_root=tmp_path)
    app = create_app(config=config, manager=mock_manager)
    client = TestClient(app)
    response = client.post("/api/v1/ingest",
        json={"url": "https://x.com", "requested_mode": "guide"},
        headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 201
    assert mock_manager.submit_url.call_args.kwargs.get("requested_mode") == "guide"
```

- [ ] **Step 2: Run to verify failure**

```
cd H:/demo-win && python -m pytest tests/unit/test_api/ -k "requested_mode" -v
```

- [ ] **Step 3: Update service.py — add param to `export_url_job()`**

```python
def export_url_job(self, *, url, shared_root=None, content_type=None, platform=None,
                   video_download_mode="audio", on_progress=None, requested_mode="auto"):
```
Add `requested_mode=requested_mode` to the `ExportRequest(...)` call.

- [ ] **Step 4: Update job_manager.py — add param to `submit_url()`**

```python
def submit_url(self, *, url, content_type=None, platform=None,
               video_download_mode=None, requested_mode="auto"):
```
Pass `requested_mode=requested_mode` to `self.service.export_url_job(...)`.

- [ ] **Step 5: Update server.py — extract from POST body**

In the `ingest()` handler, add:
```python
requested_mode = str(payload.get("requested_mode") or "auto").strip()
```
Pass `requested_mode=requested_mode` to `resolved_manager.submit_url(...)`.

- [ ] **Step 6: Run to verify tests pass + full suite**

```
cd H:/demo-win && python -m pytest tests/unit/test_api/ -k "requested_mode" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 7: Commit**

```bash
cd H:/demo-win
git add src/windows_client/app/service.py src/windows_client/api/job_manager.py src/windows_client/api/server.py tests/unit/test_api/
git commit -m "feat(win): propagate requested_mode through service / job_manager / API server"
```

---

### Task 9: GUI — template selector QComboBox

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing test**

```python
def test_main_window_template_selector_has_four_options(qtbot):
    # Follow the existing window-build pattern in this test file
    window = _build_test_window(qtbot)
    combo = window.template_selector
    assert combo is not None
    labels = [combo.itemText(i) for i in range(combo.count())]
    assert labels == ["Auto", "深度分析", "实用提炼", "推荐/导览"]
    user_data = [combo.itemData(i) for i in range(combo.count())]
    assert user_data == ["auto", "argument", "guide", "review"]
```

- [ ] **Step 2: Run to verify failure**

```
cd H:/demo-win && python -m pytest tests/unit/test_main_window.py::test_main_window_template_selector_has_four_options -v
```

- [ ] **Step 3: Add QComboBox to main_window.py**

In `__init__` (submit card section, near `self.url_input`):
```python
self.template_selector = QComboBox()
self.template_selector.setObjectName("TemplateSelector")
self.template_selector.addItem("Auto", "auto")
self.template_selector.addItem("深度分析", "argument")
self.template_selector.addItem("实用提炼", "guide")
self.template_selector.addItem("推荐/导览", "review")
```
Add to `card_layout` after `self.url_input`.

- [ ] **Step 4: Read `requested_mode` in `_start_from_input()`**

In `_start_from_input()`, before the job submission call:
```python
requested_mode = self.template_selector.currentData() or "auto"
```
Pass `requested_mode=requested_mode` to the `submit_url()` / job manager call.

- [ ] **Step 5: Run to verify passes + full suite**

```
cd H:/demo-win && python -m pytest tests/unit/test_main_window.py::test_main_window_template_selector_has_four_options -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 6: Commit**

```bash
cd H:/demo-win
git add src/windows_client/gui/main_window.py tests/unit/test_main_window.py
git commit -m "feat(win): add template selector QComboBox to GUI submit page"
```

---

### Task 10: insight_brief.py — lightweight mode-aware adaptation

**Files:**
- Modify: `src/windows_client/app/insight_brief.py`
- Test: `tests/unit/test_insight_brief.py`

- [ ] **Step 1: Write failing tests**

```python
def _make_editorial_result(mode, base_override=None, mode_override=None):
    base = {"core_summary": "summary", "bottom_line": "bottom line",
            "audience_fit": "general", "save_worthy_points": ["p1"]}
    base.update(base_override or {})
    payloads = {
        "argument": {"author_thesis": "thesis",
                     "evidence_backed_points": [{"id": "kp-1", "title": "Point A", "details": "D A", "evidence_segment_ids": []}],
                     "interpretive_points": []},
        "guide": {"guide_goal": "learn Y", "recommended_steps": ["Step 1", "Step 2"]},
        "review": {"overall_judgment": "excellent", "highlights": ["Great production"]},
    }
    mp = dict(payloads.get(mode, {}))
    mp.update(mode_override or {})
    return {"editorial": {"resolved_mode": mode, "base": base, "mode_payload": mp},
            "content_kind": "test", "author_stance": "test"}

def test_adapt_argument_uses_evidence_backed_points():
    from windows_client.app.insight_brief import adapt_from_structured_result
    brief = adapt_from_structured_result(_make_editorial_result("argument"), {}, None)
    assert brief.hero.one_sentence_take == "summary"
    assert brief.synthesis_conclusion == "bottom line"
    assert any("Point A" in v.statement for v in brief.viewpoints)

def test_adapt_guide_uses_recommended_steps():
    from windows_client.app.insight_brief import adapt_from_structured_result
    brief = adapt_from_structured_result(_make_editorial_result("guide"), {}, None)
    assert any("Step 1" in v.statement for v in brief.viewpoints)

def test_adapt_review_uses_highlights():
    from windows_client.app.insight_brief import adapt_from_structured_result
    brief = adapt_from_structured_result(_make_editorial_result("review"), {}, None)
    assert any("Great production" in v.statement for v in brief.viewpoints)
```

- [ ] **Step 2: Run to verify failure**

```
cd H:/demo-win && python -m pytest tests/unit/test_insight_brief.py -k "adapt_argument or adapt_guide or adapt_review" -v
```

- [ ] **Step 3: Rewrite `adapt_from_structured_result()` to be mode-aware**

The new function:
1. Check for `result["editorial"]` — use it if present
2. From `editorial.base`: build `hero` (core_summary → one_sentence_take, bottom_line → synthesis_conclusion), `quick_takeaways` from `save_worthy_points`
3. From `editorial.mode_payload` by `resolved_mode`:
   - `argument` → viewpoints from `evidence_backed_points`
   - `guide` → viewpoints from `recommended_steps`
   - `review` → viewpoints from `highlights`
4. Legacy fallback: if no `editorial`, use old `summary`/`key_points`/`synthesis` path (keep existing logic intact)

Full implementation (replace the existing function body):

```python
def adapt_from_structured_result(result, evidence_index, coverage):
    if not result:
        return None

    editorial = result.get("editorial")
    if isinstance(editorial, dict):
        base = editorial.get("base") or {}
        core_summary = str(base.get("core_summary") or "").strip()
        bottom_line = str(base.get("bottom_line") or "").strip()
        if not core_summary:
            return None
        hero = HeroBrief(
            title=core_summary,
            one_sentence_take=core_summary,
            content_kind=str(result.get("content_kind") or "").strip() or None,
            author_stance=str(result.get("author_stance") or "").strip() or None,
        )
        quick_takeaways = [str(p) for p in base.get("save_worthy_points", []) if p]
        resolved_mode = str(editorial.get("resolved_mode") or "argument")
        mode_payload = editorial.get("mode_payload") or {}
        viewpoints: list[ViewpointItem] = []
        if resolved_mode == "argument":
            for item in mode_payload.get("evidence_backed_points", []):
                if not isinstance(item, dict):
                    continue
                stmt = str(item.get("title") or "").strip()
                if stmt:
                    viewpoints.append(ViewpointItem(
                        statement=stmt, kind="key_point",
                        why_it_matters=str(item.get("details") or "").strip() or None,
                        support_level=None,
                        evidence_refs=resolve_evidence_for_item(item, evidence_index),
                    ))
        elif resolved_mode == "guide":
            for step in mode_payload.get("recommended_steps", []):
                s = str(step).strip()
                if s:
                    viewpoints.append(ViewpointItem(statement=s, kind="key_point",
                                                    why_it_matters=None, support_level=None))
        elif resolved_mode == "review":
            for h in mode_payload.get("highlights", []):
                ht = str(h).strip()
                if ht:
                    viewpoints.append(ViewpointItem(statement=ht, kind="key_point",
                                                    why_it_matters=None, support_level=None))
        return InsightBriefV2(
            hero=hero, quick_takeaways=quick_takeaways, viewpoints=viewpoints,
            coverage=coverage, gaps=[], synthesis_conclusion=bottom_line or None,
        )

    # Legacy fallback — existing logic unchanged
    summary = result.get("summary")
    if not isinstance(summary, dict):
        return None
    headline = str(summary.get("headline") or "").strip()
    short_text = str(summary.get("short_text") or "").strip()
    if not headline and not short_text:
        return None
    hero = HeroBrief(title=headline or short_text, one_sentence_take=short_text or headline,
                     content_kind=str(result.get("content_kind") or "").strip() or None,
                     author_stance=str(result.get("author_stance") or "").strip() or None)
    key_points = result.get("key_points") or []
    quick_takeaways = [str(kp.get("title") or "") for kp in key_points
                       if isinstance(kp, dict) and kp.get("title")]
    viewpoints = []
    for item in key_points:
        if not isinstance(item, dict):
            continue
        stmt = str(item.get("title") or "").strip()
        if stmt:
            viewpoints.append(ViewpointItem(statement=stmt, kind="key_point",
                                            why_it_matters=str(item.get("details") or "").strip() or None,
                                            support_level=None,
                                            evidence_refs=resolve_evidence_for_item(item, evidence_index)))
    synthesis = result.get("synthesis")
    gaps, synthesis_conclusion = [], None
    if isinstance(synthesis, dict):
        gaps = [str(q) for q in synthesis.get("open_questions", []) if q]
        synthesis_conclusion = str(synthesis.get("final_answer") or "").strip() or None
    return InsightBriefV2(hero=hero, quick_takeaways=quick_takeaways, viewpoints=viewpoints,
                          coverage=coverage, gaps=gaps, synthesis_conclusion=synthesis_conclusion)
```

- [ ] **Step 4: Run to verify tests pass + full suite**

```
cd H:/demo-win && python -m pytest tests/unit/test_insight_brief.py -k "adapt_argument or adapt_guide or adapt_review" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 5: Commit**

```bash
cd H:/demo-win
git add src/windows_client/app/insight_brief.py tests/unit/test_insight_brief.py
git commit -m "feat(win): mode-aware insight_brief using editorial sub-object"
```

---

### Task 11: result_renderer.py — mode pill

**Files:**
- Modify: `src/windows_client/gui/result_renderer.py`
- Test: `tests/unit/test_result_renderer.py`

- [ ] **Step 1: Write failing test**

```python
def test_result_renderer_mode_pill_shows_correct_label(qtbot):
    # Follow existing renderer build pattern in this test file
    renderer = _build_test_renderer(qtbot)
    from windows_client.app.insight_brief import InsightBriefV2, HeroBrief
    brief = InsightBriefV2(
        hero=HeroBrief(title="T", one_sentence_take="S", content_kind="opinion", author_stance="advocacy"),
        quick_takeaways=[], viewpoints=[], coverage=None, gaps=[], synthesis_conclusion=None,
    )
    renderer.render(brief, resolved_mode="guide")
    assert renderer.mode_pill.isVisible()
    assert "实用提炼" in renderer.mode_pill.text()

def test_result_renderer_mode_pill_hidden_when_no_mode(qtbot):
    renderer = _build_test_renderer(qtbot)
    from windows_client.app.insight_brief import InsightBriefV2, HeroBrief
    brief = InsightBriefV2(
        hero=HeroBrief(title="T", one_sentence_take="S", content_kind=None, author_stance=None),
        quick_takeaways=[], viewpoints=[], coverage=None, gaps=[], synthesis_conclusion=None,
    )
    renderer.render(brief, resolved_mode=None)
    assert not renderer.mode_pill.isVisible()
```

- [ ] **Step 2: Run to verify failure**

```
cd H:/demo-win && python -m pytest tests/unit/test_result_renderer.py -k "mode_pill" -v
```

- [ ] **Step 3: Add mode pill to result_renderer.py**

```python
_MODE_DISPLAY_LABELS = {
    "argument": "深度分析",
    "guide": "实用提炼",
    "review": "推荐/导览",
    "informational": "信息摘要",
    "narrative": "叙事回顾",
}
```

In `__init__` (widget setup):
```python
self.mode_pill = QLabel("")
self.mode_pill.setObjectName("ModePill")
self.mode_pill.hide()
```
Add `mode_pill` to the layout near the title/hero area.

Update `render()` signature to add `resolved_mode: str | None = None`:
```python
if resolved_mode and resolved_mode in _MODE_DISPLAY_LABELS:
    self.mode_pill.setText(_MODE_DISPLAY_LABELS[resolved_mode])
    self.mode_pill.show()
else:
    self.mode_pill.hide()
```

- [ ] **Step 4: Run to verify tests pass + full suite**

```
cd H:/demo-win && python -m pytest tests/unit/test_result_renderer.py -k "mode_pill" -v
cd H:/demo-win && python -m pytest tests/unit/ -q
```

- [ ] **Step 5: Commit**

```bash
cd H:/demo-win
git add src/windows_client/gui/result_renderer.py tests/unit/test_result_renderer.py
git commit -m "feat(win): add mode pill to result renderer"
```

---

## Acceptance Checklist

- [ ] Submit URL without template → `resolved_mode: "argument"` (default), mode pill shows "深度分析"
- [ ] Select "实用提炼" → `metadata.json` has `requested_mode: "guide"` → `normalized.json` has `resolved_mode: "guide"` + `mode_payload.recommended_steps`
- [ ] Select "推荐/导览" → result shows highlights, not argument viewpoints
- [ ] `analysis_result.json` has top-level `requested_mode`, `resolved_mode`, `mode_confidence`
- [ ] `editorial.base.core_summary` and `editorial.base.bottom_line` non-empty for all 3 modes
- [ ] Mode pill visible in result page with correct Chinese label
- [ ] WSL: `python3 -m pytest -q` → all passing
- [ ] Windows: `python -m pytest tests/unit/ -q` → all passing
