# Phase 0 Boundary Repair — Work Log

**Date:** 2026-03-28
**Ref plan:** `docs/preview1-boundary-repair-plan-2026-03-27.md`
**Scope:** Phase 0 deliverables only — archive semantics, shared root visibility, watcher status

---

## Objective

Phase 0 targets the three highest-priority safety and visibility items before any structural changes:

1. Replace hard delete with archive across all entry surfaces
2. Expose active shared root in all entry surfaces
3. Make watcher status inspectable via the API and clients

---

## Pre-work: Review Findings (2026-03-28)

**Archive (current state):**
- `job_manager.py:83` — `shutil.rmtree(record.job_dir)` — physical destroy
- `server.py:108-117` — DELETE endpoint, responds `{"deleted": true}`
- Chrome `popup.js:68-78` — confirm dialog → hard delete
- Obsidian `main.ts:204-223` — confirm dialog → hard delete

**Shared root visibility (current state):**
- `/health` already returns `shared_inbox_root` ✓
- Obsidian `StatusView` only shows `"API: ok"` — shared root not surfaced
- Obsidian `types.ts` `ApiHealth` interface missing `shared_inbox_root` field
- Chrome popup has no health/shared root display at all

**Watcher status (current state):**
- `/health` returns `{status, version, shared_inbox_root, statuses}` — no watcher info
- `wsl_bridge.get_watch_status()` exists and can be called
- Chrome background has a `health` message handler — popup never uses it

---

## Task Breakdown

### Task A — Archive semantics (backend + API)

**Files:** `src/windows_client/api/job_manager.py`, `src/windows_client/api/server.py`

- [ ] A1: Add `"archived"` to `STATUS_TO_DIR` → `"archived"`
- [ ] A2: Rename `delete_job()` to `archive_job()` — move job dir to `archived/<job_id>/` instead of `shutil.rmtree`
- [ ] A3: Update `get_job()` to scan `archived/` dir as well (so archived jobs remain retrievable)
- [ ] A4: Update DELETE endpoint — call `archive_job()`, respond `{"archived": true, "job_id": ..., "previous_status": ...}`
- [ ] A5: Update `list_jobs()` and `list_result_cards()` — exclude `archived` from default status list (archived jobs should not appear in normal listings unless explicitly requested)
- [ ] A6: Update tests

### Task B — Shared root visibility (API health)

**Files:** `src/windows_client/api/server.py`, `src/windows_client/api/config.py` (read only)

- [ ] B1: Add watcher status to `/health` response — call `wsl_bridge.get_watch_status()`, include `watcher: {running, pid, shared_root, log_path}`
- [ ] B2: Confirm `shared_inbox_root` is already present in health response ✓ (already done)

### Task C — Shared root + watcher visibility (Obsidian)

**Files:** `obsidian-plugin/types.ts`, `obsidian-plugin/main.ts`

- [ ] C1: Add `shared_inbox_root?: string` and `watcher?: { running: boolean; pid?: number; shared_root?: string }` to `ApiHealth` in `types.ts`
- [ ] C2: Update `StatusView.render()` — show shared root path and watcher running/stopped below the "API: ok" line
- [ ] C3: Rebuild `main.js` from TypeScript

### Task D — Shared root + watcher visibility (Chrome + Edge)

**Files:** `chrome-extension/popup.html`, `chrome-extension/popup.js`, `chrome-extension/background.js` (+ Edge mirrors)

- [ ] D1: Add a small status bar to popup that calls `health` message and shows inbox path + watcher state
- [ ] D2: Update popup UI label for delete → archive

### Task F — Remove Obsidian thumbnail fallback

**Files:** `obsidian-plugin/importer.ts`

- [ ] F1: Remove `|| findArtifact(..., "thumbnail")` fallback in `importInsightCard()`
- [ ] F2: If no `insight_card` artifact exists, return `null` — no embed at all
- [ ] F3: Rebuild `main.js`

---

### Task E — Client label + UX update (archive language)

**Files:** `chrome-extension/popup.js`, `obsidian-plugin/main.ts`

- [ ] E1: Chrome popup — "Delete" button → "Archive"; confirm dialog text updated
- [ ] E2: Obsidian — "Delete" button → "Archive"; confirm dialog text updated; `deleteJob()` → `archiveJob()` in plugin and api-client

---

## Execution Order

```
A1 → A2 → A3 → A4 → A5 → A6   (backend archive, self-contained)
B1                               (API health + watcher, depends on A stable)
F1 → F2 → F3                    (Obsidian thumbnail fix, independent)
C1 → C2 → C3                    (Obsidian types + StatusView, depends on B1)
D1 → D2                         (Chrome/Edge health display, depends on B1)
E1 → E2                         (archive label rename, alongside D/C)
```

---

## Progress

| Task | Status | Notes |
|------|--------|-------|
| A1 — `STATUS_TO_DIR` add archived | done | |
| A2 — `archive_job()` move instead of rmtree | done | |
| A3 — `get_job()` scan archived dir | done | found missing during test run, fixed |
| A4 — DELETE endpoint → archive response | done | |
| A5 — exclude archived from default list | done | `_DEFAULT_LIST_STATUSES` constant |
| A6 — update tests | done | +3 new archive tests, 183 passed |
| B1 — watcher status in `/health` | done | `_get_watcher_status()` helper, fail-safe |
| C1 — `ApiHealth` type fields | done | `shared_inbox_root`, `watcher` block |
| C2 — StatusView show root + watcher | done | inline health text |
| C3 — rebuild main.js | done | build passed |
| D1 — Chrome popup health/inbox display | done | `inbox-status` bar + `refreshInboxStatus()` |
| D2 — Chrome popup archive label | done | mirrored to Edge |
| E1 — Chrome "Archive" label + confirm text | done | background.js `archive-job` message |
| E2 — Obsidian "Archive" label + api-client rename | done | `archiveJob()` throughout |
| F1/F2 — Remove thumbnail fallback in importer.ts | done | only `insight_card` accepted |
| F3 — Rebuild main.js | done | combined with C3 |

---

## Codex Review Additions (2026-03-28)

Codex 全局 review 补充了以下信息，已吸收进本计划：

| 项目 | 优先级 | 处理方式 |
|------|--------|---------|
| WSL `processed/` 先移目录再写文件（`processor.py:53-61`） | P0 | **不在本批** — WSL 仓库，下一批单独处理；Windows 侧已有 `incomplete_result` 兜底 |
| Obsidian thumbnail 兜底需撤掉（`importer.ts:45-55`） | P1 | **加入本批** — Task F，纯 Windows 侧改动 |
| WSL runtime data 在 repo worktree（`config.py:56,58`） | P1 | **不在本批** — Phase 1，WSL 仓库 |
| WSL 3 个 processing blocker（llm_pipeline / media_pipeline / cli） | P1 | **不在本批** — Phase 1+，WSL 仓库 |

决策原则：**不跨仓库并行，保持模块解耦**。本批只动 Windows 仓库。

测试基线（Codex 核验）：Windows 180 passed，WSL 41 passed，Obsidian build OK，browser syntax OK。

---

## Decisions & Notes

- `archived/` dir sits alongside `incoming/`, `processing/`, `processed/`, `failed/` inside `shared_inbox_root`
- Archived jobs are excluded from default `list_jobs()` — clients must pass `status=archived` to retrieve them
- `get_job(job_id)` will scan `archived/` so individual job lookup still works
- Watcher status in `/health` uses best-effort: if `wsl_bridge` call fails, return `{"running": false, "error": "..."}` rather than crashing health check
- Chrome/Edge are mirror repos — all changes applied to both simultaneously
- Obsidian TypeScript must be rebuilt to `main.js` after every `.ts` change

---

## Codex Round-2 Review Fixes (2026-03-28)

Codex 对第一轮改动做了 review，发现 3 个收口问题，已全部修复：

| # | 问题 | 修复位置 | 状态 |
|---|------|---------|------|
| R1 | 归档 job 从 GUI 历史消失 | `result_workspace.py` — `list_recent_results()` 加入 `archived/` glob；新增 `_load_archived_result()` | done |
| R2 | API result 面半接通（result_card 空壳，/result 404） | `result_workspace.py` — `load_job_result()` 加 archived 路径；`job_manager.py` — `_build_result_card()` archived 分支；`RESULT_STATE_TO_STATUS` 加 archived；`_load_job_record` result_dir 含 archived | done |
| R3 | `/health` watcher 异常吞掉，只返回固定字符串 | `server.py` — `_get_watcher_status()` 改为 `str(exc)` | done |

测试：185 passed（+2 archived 结果读取测试）

---

## Acceptance Check (Phase 0 complete when)

- [ ] `DELETE /api/v1/jobs/{job_id}` moves the job dir to `archived/`, does not destroy it
- [ ] `GET /api/v1/health` returns `watcher` block and `shared_inbox_root`
- [ ] Obsidian StatusView shows shared root path and watcher running/stopped
- [ ] Chrome popup shows active inbox path
- [ ] All delete buttons across clients say "Archive" not "Delete"
- [ ] Existing tests pass; new archive tests added

---

## Post-Phase-0 GUI Follow-up (2026-03-29)

While validating fresh jobs after the WSL upgrade work, one UX issue became
clear in the Windows GUI:

- a completed job should automatically switch from the `Current Run` task view
  into the inline result page
- but if `load_job_result(...)` raised during a poll cycle, the exception was
  silently swallowed and the window stayed on the task page

This made the experience feel like:

- processing had finished
- but the GUI "did not jump" to the result page

### Follow-up Fix

Updated in:

- `src/windows_client/gui/main_window.py`
- `tests/unit/test_main_window.py`

Behavior change:

- `_refresh_current_job_result()` now logs the exception instead of silently
  swallowing it
- the task page now shows an explicit retry message:
  - "Result is being prepared, but the GUI could not load it yet. Retrying automatically..."
- automatic polling continues, so the UI can still switch to the inline result
  view once the result becomes readable

### Verification

- `python -m pytest tests\\unit\\test_main_window.py -q` -> `18 passed`

### Scope Note

This follow-up does not change the intended navigation model.

The intended behavior remains:

- when a `processed` result can be loaded successfully, the GUI should switch
  directly to the inline result page
- this patch only removes the silent-failure case that made the task page look
  "stuck"
