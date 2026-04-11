# Deep Analysis Question-Driven Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default deep-analysis / practical-extraction result read as a direct conclusion followed by 3-5 question-led sections and a fixed practical closing section.

**Architecture:** Keep the existing `structured_result -> product_view -> insight_brief -> renderer` pipeline. First lock a question-driven `product_view` contract with tests, then adapt summary extraction so API cards and inline previews prefer that contract, and finally update rendering/fixtures so the new shape reads correctly without redesigning unrelated modes.

**Tech Stack:** Python, PySide6 HTML rendering, existing `windows_client` result workspace/api helpers, Python `unittest` + `pytest`

---

## File Map

- Modify: `docs/superpowers/specs/2026-04-10-deep-analysis-question-driven-output-design.md`
  - update status after implementation if needed
- Modify: `tests/unit/test_result_workspace.py`
  - add red tests proving processed results preserve the new deep-analysis `product_view` contract
- Modify: `tests/unit/test_insight_brief.py`
  - add red tests proving briefs prefer question-driven sections and practical closing copy
- Modify: `tests/unit/test_result_renderer.py`
  - add red tests for question-led rendering and closing-section display
- Modify: `src/windows_client/app/result_workspace.py`
  - keep the new question-driven `product_view` available in entry details without degrading existing artifacts
- Modify: `src/windows_client/app/insight_brief.py`
  - prefer question-driven sections and practical closing when present
- Modify: `src/windows_client/gui/result_renderer.py`
  - render the new analysis layout cleanly while preserving existing guide/review/narrative behavior
- Verify: `src/windows_client/app/service.py`
  - trace reinterpret/export handoff to find the real generation-side insertion point if prompt/schema logic is not in the Windows tree
- Verify: `src/windows_client/app/workflow.py`
  - regression only

---

### Task 1: Lock the Question-Driven Result Contract

**Files:**
- Modify: `tests/unit/test_result_workspace.py`
- Modify: `src/windows_client/app/result_workspace.py`

- [ ] **Step 1: Write the failing tests**

Add or update tests around processed results so the new default deep-analysis shape is explicit and durable.

Use a fixture shaped like:

```python
product_view = {
    "hero": {
        "title": "MegaTrain lowers the full-precision training barrier.",
        "dek": "The paper's real contribution is making CPU memory, not GPU memory, the main capacity bottleneck.",
        "bottom_line": "If you care about large-model training on modest GPU setups, this is worth tracking.",
    },
    "sections": [
        {
            "id": "core-idea",
            "title": "MegaTrain的核心思路是什么，它解决了什么问题？",
            "kind": "question_block",
            "priority": 1,
            "blocks": [{"type": "bullet_list", "items": ["要点 A", "要点 B"]}],
        },
        {
            "id": "performance",
            "title": "实际效果如何？",
            "kind": "question_block",
            "priority": 2,
            "blocks": [{"type": "bullet_list", "items": ["结果 A", "结果 B"]}],
        },
        {
            "id": "meaning",
            "title": "这对我意味着什么？",
            "kind": "reader_value",
            "priority": 3,
            "blocks": [{"type": "bullet_list", "items": ["结论 A"]}],
        },
    ],
    "render_hints": {"layout_family": "analysis_brief"},
}
```

Add tests around:

```python
def test_load_processed_job_result_preserves_question_driven_analysis_sections(self) -> None:
    ...

def test_load_processed_job_result_keeps_reader_value_section_in_product_view(self) -> None:
    ...
```

- [ ] **Step 2: Run the focused tests to verify they fail or meaningfully constrain behavior**

Run:

```bash
python -m pytest tests/unit/test_result_workspace.py -k "question_driven_analysis_sections or reader_value_section" -q
```

Expected: if the contract is not yet represented in tests, they fail first; if they pass immediately, keep them as the lock for later tasks.

- [ ] **Step 3: Make the minimal workspace-side adjustments**

In `src/windows_client/app/result_workspace.py`:

- keep `structured_result["product_view"]` and `details["product_view"]` intact for question-driven sections
- avoid any normalization that drops `kind == "question_block"` or `kind == "reader_value"`
- keep this task minimal; do not invent a second deep-analysis payload

The code should continue to look like:

```python
structured_result = _coerce_dict(asset.get("result"))
...
return ResultWorkspaceEntry(
    ...
    details={
        "structured_result": structured_result,
        "product_view": _coerce_dict(structured_result.get("product_view")),
        ...
    },
)
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 2: Make `insight_brief` Prefer the New Skeleton

**Files:**
- Modify: `tests/unit/test_insight_brief.py`
- Modify: `src/windows_client/app/insight_brief.py`

- [ ] **Step 1: Write the failing tests**

Add tests proving the brief now prefers the question-driven deep-analysis structure when present.

Use tests around:

```python
def test_adapt_prefers_product_view_question_blocks_for_quick_takeaways(self) -> None:
    result = {
        "summary": {"headline": "Legacy headline", "short_text": "Legacy summary."},
        "product_view": {
            "hero": {
                "title": "Question-driven title",
                "dek": "Question-driven conclusion.",
                "bottom_line": "This matters because it lowers the barrier.",
            },
            "sections": [
                {
                    "id": "q1",
                    "title": "核心问题是什么？",
                    "kind": "question_block",
                    "priority": 1,
                    "blocks": [{"type": "bullet_list", "items": ["结论 A", "结论 B"]}],
                },
                {
                    "id": "reader-value",
                    "title": "这对我意味着什么？",
                    "kind": "reader_value",
                    "priority": 2,
                    "blocks": [{"type": "bullet_list", "items": ["值得持续关注"]}],
                },
            ],
        },
    }
    ...

def test_adapt_uses_product_view_bottom_line_as_synthesis_conclusion(self) -> None:
    ...
```

Expected assertions:

- `brief.hero.title == "Question-driven title"`
- `brief.hero.one_sentence_take == "Question-driven conclusion."`
- `brief.quick_takeaways` prefers question-block titles or first bullets instead of legacy key-point titles when present
- `brief.synthesis_conclusion == "This matters because it lowers the barrier."`

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_insight_brief.py -k "product_view_question_blocks or product_view_bottom_line" -q
```

Expected: FAIL because `adapt_from_structured_result()` currently prefers editorial and legacy summary/key-point structures.

- [ ] **Step 3: Write the minimal implementation**

In `src/windows_client/app/insight_brief.py` add a small helper before the legacy summary path that adapts deep-analysis `product_view` when it has question-driven sections.

Target shape:

```python
def _adapt_from_product_view(
    result: dict[str, Any],
    product_view: dict[str, Any],
    coverage: CoverageStats | None,
) -> InsightBriefV2 | None:
    hero_payload = _coerce_dict(product_view.get("hero"))
    title = str(hero_payload.get("title") or "").strip()
    dek = str(hero_payload.get("dek") or "").strip()
    bottom_line = str(hero_payload.get("bottom_line") or "").strip()
    if not title and not dek and not bottom_line:
        return None
    ...
```

Implementation rules:

- only use this path for analysis-style product views with at least one `question_block` or `reader_value` section
- `hero.title` should come from `hero.title` first
- `hero.one_sentence_take` should come from `hero.dek` first, then `hero.bottom_line`
- `quick_takeaways` should be derived from the question-block titles, capped to a small set if needed
- `synthesis_conclusion` should prefer `hero.bottom_line`, then the `reader_value` block's first bullet
- keep editorial handling first if it is intentionally richer for other modes

Then wire it in `adapt_from_structured_result()` like:

```python
product_view = result.get("product_view")
if isinstance(product_view, dict):
    adapted = _adapt_from_product_view(result, product_view, coverage)
    if adapted is not None:
        return adapted
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 3: Render Question Blocks As Reader Questions, Not Generic Cards

**Files:**
- Modify: `tests/unit/test_result_renderer.py`
- Modify: `src/windows_client/gui/result_renderer.py`

- [ ] **Step 1: Write the failing tests**

Add renderer tests proving the new analysis shape reads correctly in HTML.

Use tests around:

```python
def test_structured_preview_renders_question_driven_analysis_sections(self) -> None:
    entry = _make_entry(
        details={
            "normalized": {
                "asset": {
                    "result": {
                        "product_view": {
                            "hero": {
                                "title": "单卡GPU训练更可行了",
                                "dek": "核心不是省GPU显存，而是把完整状态放到CPU内存。",
                                "bottom_line": "如果你关注低门槛训练，这篇值得存。",
                            },
                            "sections": [
                                {
                                    "id": "q1",
                                    "title": "它解决了什么问题？",
                                    "kind": "question_block",
                                    "priority": 1,
                                    "blocks": [{"type": "bullet_list", "items": ["问题 A", "问题 B"]}],
                                },
                                {
                                    "id": "reader-value",
                                    "title": "这对我意味着什么？",
                                    "kind": "reader_value",
                                    "priority": 2,
                                    "blocks": [{"type": "bullet_list", "items": ["意义 A"]}],
                                },
                            ],
                            "render_hints": {"layout_family": "analysis_brief"},
                        }
                    }
                },
                "metadata": {"llm_processing": {"status": "pass", "resolved_mode": "argument"}},
            }
        },
    )
    html = _structured_preview_html(entry, resolved_mode="argument")
    assert "它解决了什么问题？" in html
    assert "这对我意味着什么？" in html
```

Also add a more specific renderer assertion that the analysis renderer does not relabel question sections as legacy `核心判断` / `主要论点` buckets when `kind == "question_block"`.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_result_renderer.py -k "question_driven_analysis_sections or reader_value" -q
```

Expected: FAIL because `_analysis_product_view_html()` still treats analysis sections as a generic card grid with legacy labels.

- [ ] **Step 3: Write the minimal renderer changes**

In `src/windows_client/gui/result_renderer.py`:

- keep `_product_view_html()` dispatch logic unchanged unless needed for the new kinds
- update `_analysis_product_view_html()` to preserve section titles literally for `question_block` and `reader_value`
- render these sections in a straightforward reading layout rather than trying to force old argument-card semantics
- keep other layout families unchanged

Preferred shape inside `_analysis_product_view_html()`:

```python
section_kind = str(item.get("kind") or "").strip()
label_html = ""
if section_kind not in {"question_block", "reader_value"} and title:
    label_html = f"<div class='analysis-section-label'>{html.escape(title)}</div>"
elif title:
    label_html = f"<h2>{html.escape(title)}</h2>"
```

Do not add a brand-new layout family unless the existing `analysis_brief` family cannot support the new shape.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 4: Trace And Adjust The Real Generation Insertion Point

**Files:**
- Verify: `src/windows_client/app/service.py`
- Verify: `src/windows_client/app/workflow.py`
- Modify: the actual generation/prompt/schema file once located
- Add or modify: the nearest focused test file for that generator contract

- [ ] **Step 1: Locate the exact generation-side owner of `structured_result` / `product_view`**

Run targeted searches for where the default deep-analysis payload is produced, not just consumed.

Run:

```bash
python -m pytest tests/unit/test_result_workspace.py::ResultWorkspaceTests::test_load_processed_job_result_preserves_product_view -q
```

Then inspect the handoff path rooted at:

- `src/windows_client/app/service.py`
- `src/windows_client/app/result_workspace.py`
- the file named by `llm_processing.output_path` inside real processed jobs

Success condition for this step: identify the concrete file or repository boundary that owns generation of:

- `product_view.hero`
- `product_view.sections`
- any deep-analysis editorial fields reused downstream

- [ ] **Step 2: Write the failing contract test at the real generation boundary**

Once the owner is found, add one focused test that proves the generated deep-analysis payload contains:

- a direct conclusion hero
- 3-5 question-led sections
- a final `reader_value`/equivalent closing section

If the owner is outside this Windows tree, write the nearest contract test in the Windows tree that loads a representative generated payload and asserts the new shape.

- [ ] **Step 3: Implement the smallest prompt/schema change**

Change the generator so the default deep-analysis template emits:

```python
{
    "product_view": {
        "hero": {
            "title": "<direct conclusion>",
            "dek": "<one-sentence explanation>",
            "bottom_line": "<what this means for me>",
        },
        "sections": [
            {"kind": "question_block", "title": "<question>", ...},
            {"kind": "question_block", "title": "<question>", ...},
            {"kind": "reader_value", "title": "这对我意味着什么？", ...},
        ],
        "render_hints": {"layout_family": "analysis_brief"},
    }
}
```

Rules:

- do not force the same shape into guide/review/narrative
- prefer 3-5 sections total
- keep section blocks short, usually bullet lists
- keep evidence grounding available where already supported

- [ ] **Step 4: Run the focused test and inspect one real artifact**

Run the focused generation-side test from Step 2.

Then inspect one produced artifact and confirm it contains:

- direct conclusion hero text
- 3-5 question-led sections
- practical closing section

Expected: PASS plus a real artifact whose structure matches the contract.

---

### Task 5: Regression Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the focused structural suites**

Run:

```bash
python -m pytest tests/unit/test_result_workspace.py tests/unit/test_insight_brief.py tests/unit/test_result_renderer.py -q
```

Expected: PASS.

- [ ] **Step 2: Run adjacent regressions**

Run:

```bash
python -m pytest tests/unit/test_inline_result_view.py tests/unit/test_api/test_job_manager.py tests/unit/test_main_window.py -q
```

Expected: PASS.

- [ ] **Step 3: Manual acceptance on the worktree GUI**

Run:

```bash
python H:\demo-win\.worktrees\domain-aware-reader-v2\main.py gui --debug-console
```

Manual checks:

- top of result states the judgment immediately
- deep-analysis body reads as 3-5 question-led sections
- each section is short enough to scan
- the result ends with a clear `这对我意味着什么？` style landing
- guide/review/narrative outputs are not regressed into the new template

---

## Self-Review

- Spec coverage: this plan covers the approved skeleton, keeps scope limited to deep analysis / practical extraction, and avoids broad GUI redesign.
- Placeholder scan: the only intentionally open variable is the exact generation-side owner; Task 4 makes finding and testing that insertion point an explicit deliverable before code changes there.
- Type consistency: the plan consistently uses `product_view.hero`, `product_view.sections`, `kind == "question_block"`, and `kind == "reader_value"` as the new contract.
