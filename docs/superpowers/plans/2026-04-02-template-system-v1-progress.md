# Template System v1 Progress

Date: 2026-04-02
Branch: `codex/template-system-v1`

## Completed in this slice

- Windows-side `requested_mode` plumbing is now connected from:
  - `JobExporter` metadata
  - `WindowsClientService`
  - `WindowsClientWorkflow`
  - `JobManager`
  - `POST /api/v1/ingest`
  - GUI URL submit flow
- GUI submit page now exposes a lightweight analysis template selector:
  - `Auto`
  - `深度分析`
  - `实用提炼`
  - `推荐导览`
- GUI resets the selector to `Auto` when returning to `New URL`.
- API ingest responses now echo `requested_mode`.
- `InsightBriefV2` now has a lightweight editorial-aware adaptation path:
  - `argument` reads `evidence_backed_points` / `interpretive_points` / `uncertainties`
  - `guide` reads `recommended_steps` / `tips` / `pitfalls`
  - `review` reads `highlights` / `reservation_points`
- Result preview now renders a lightweight mode pill from an explicitly threaded `resolved_mode`.
- Main window now explicitly passes `resolved_mode` into the inline result view call chain instead of relying on renderer-side implicit lookup only.

## Deliberately kept lightweight

- `insight_brief.py` is only lightly mode-aware in this slice.
- Result rendering adds a mode signal but does not yet fully reorganize the entire layout by mode.
- Browser extension and Obsidian submit pickers remain out of scope for this batch.

## Verification

- Targeted Windows tests:
  - `tests/unit/test_job_exporter.py`
  - `tests/unit/test_service.py`
  - `tests/unit/test_api/test_job_manager.py`
  - `tests/unit/test_api/test_server.py`
  - `tests/unit/test_main_window.py`
  - `tests/unit/test_insight_brief.py`
  - `tests/unit/test_result_renderer.py`
  - Result: `102 passed`
- Full Windows suite:
  - `python -m pytest -q`
  - Result: `196 passed`

## Next likely step

- Run code review and end-to-end user testing on the new template selector + mode-aware result path.
- If review is clean, the next implementation step should move from contract plumbing into richer presentation:
  - stronger mode-specific section emphasis
  - template-aware insight card selection
  - browser extension / Obsidian submit-time template choice in a later batch
