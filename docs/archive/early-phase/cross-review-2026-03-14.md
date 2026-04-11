# Cross-Repo Review - 2026-03-14

## 1. Purpose

This note captures:

- the main conclusions from the external `opus` review
- the follow-up cross-check performed locally across both repositories
- the corrected conclusions that should drive the next implementation steps

The two repositories reviewed together are:

- Windows client: `H:\demo-win`
- WSL processor: `~/codex-demo`

This document is meant to be the stable review reference for later alignment and handoff.

---

## 2. Scope Reviewed

The review covered:

- current architecture and repository boundaries
- shared inbox protocol alignment
- Windows collector/exporter implementation status
- WSL processor implementation status
- metadata flow and hint usage
- tests, documentation, and basic engineering hygiene

Key files checked during cross-validation included:

- `H:\demo-win\docs/windows-client-kickoff.md`
- `H:\demo-win\docs/windows-handoff-2026-03-13.md`
- `H:\demo-win\src/windows_client/app/errors.py`
- `H:\demo-win\src/windows_client/config/settings.py`
- `H:\demo-win\src/windows_client/collector/html_metadata.py`
- `~/codex-demo/docs/project-status.md`
- `~/codex-demo/docs/inbox-protocol.md`
- `~/codex-demo/src/content_ingestion/inbox/protocol.py`
- `~/codex-demo/src/content_ingestion/inbox/processor.py`
- `~/codex-demo/src/content_ingestion/raw/html_parser.py`
- `~/codex-demo/src/content_ingestion/raw/text_parser.py`
- `~/codex-demo/src/content_ingestion/app/service.py`
- `~/codex-demo/src/content_ingestion/pipeline/openclaw_adapter.py`

---

## 3. High-Level Assessment

The overall route remains correct:

1. keep Windows responsible for URL intake, page capture, and job export
2. keep WSL responsible for inbox takeover, normalization, and pipeline outputs
3. align both sides through the shared inbox protocol instead of shared runtime code
4. improve coordination and observability before attempting larger refactors

The current system is no longer at the "idea" stage.

Confirmed local state on 2026-03-14:

- Windows client has completed the CLI-first path through Milestone 2 slice 4
- Windows side now has structured CLI error output through `WindowsClientError`
- WSL processor MVP is runnable and its unit tests pass
- `H:\demo-win\data\shared_inbox\processed` currently contains `10` processed jobs
- real WeChat article flow has already been validated end-to-end

---

## 4. Opus Review Cross-Validation

### 4.1 Confirmed

These review points were confirmed as substantially correct:

- the cross-platform architecture is clear and the boundary between Windows and WSL is well chosen
- `~/codex-demo/docs/project-status.md` is outdated and still describes Windows export as not started
- the two repositories do not yet share a single source of truth for shared inbox configuration
- HTML/platform extraction logic is duplicated between the two repositories
- both repositories still use `sys.path.insert(...)` bootstrapping in entrypoints or tests
- the WSL watcher currently handles `KeyboardInterrupt` but has no explicit `SIGTERM` handling
- there is no CI configuration in either repository
- `OpenClawAdapter` in WSL is still a stub
- `sources/` and `session/` in WSL still exist as frozen or overlapping legacy/exploratory code

### 4.2 Partially Correct

These review points were directionally right but needed correction:

- "WSL ignores title/author hints"
  - Not fully correct.
  - WSL already consumes `title_hint` and `author_hint` as fallback or direct input in raw parsers.
  - The real issue is that HTML title extraction is still repeated on the WSL side even though Windows already extracts hints.

- "shared_inbox path is hardcoded on one side"
  - The actual problem is broader.
  - Windows has a default local shared inbox.
  - WSL commands commonly accept `shared_root` explicitly, while also exposing a default inbox concept in `doctor`.
  - The missing piece is a shared configuration source, not just removal of one hardcoded path.

- "codex-demo has no history"
  - Correct that it has no initial commit yet.
  - Important nuance: the working tree already contains substantial code and docs; it is not an empty repo in practical terms.

### 4.3 Incorrect or Outdated

These points did not hold exactly after verification:

- "Windows side has 28 tests"
  - Current verified result is `31` passing tests in `H:\demo-win`.

- "WSL side fully ignores metadata hints"
  - This is not true.
  - Hints are already used in `html_parser.py`, `text_parser.py`, and related flows.

---

## 5. Concrete Findings That Matter Most

### 5.1 Documentation Drift Is the Most Immediate Coordination Risk

The most damaging mismatch today is documentation drift, not code failure.

`~/codex-demo/docs/project-status.md` still says:

- Windows export implementation: not started
- Windows and WSL integration: not started

That is materially false relative to the current Windows repository and can lead to bad prioritization.

### 5.2 Metadata Strategy Is Only Half-Aligned

The current behavior is:

- Windows extracts `platform`, `title_hint`, `author_hint`, and `published_at_hint`
- WSL uses some hints, but still reparses HTML for title and body
- extraction heuristics differ between the two repos

This is acceptable for MVP, but it is now a real maintenance cost and a source of subtle drift.

### 5.3 Shared Inbox Coordination Is Operationally Fragile

The inbox protocol itself is aligned, but configuration is not centrally owned.

Today:

- Windows defaults to `data/shared_inbox`
- WSL commands commonly depend on an explicitly provided `shared_root`
- there is no single environment variable or shared config file both sides consume

That means the protocol is stable, but the deployment and operator story is still manual.

### 5.4 Engineering Hygiene Is Behind Product Progress

The product path has advanced faster than repository hygiene.

Current examples:

- `codex-demo` still has no first commit
- both repos still rely on `sys.path` bootstrapping
- CI is absent
- cross-system integration tests are still manual

None of these block the MVP path immediately, but together they increase coordination cost.

---

## 6. Recommended Execution Order

The recommended order after this review is:

1. fix documentation alignment first
2. define a shared inbox configuration source used by both sides
3. add one automated integration test for Windows export -> WSL processing
4. decide the long-term metadata contract:
   Windows hints as advisory only, or Windows extraction as primary truth
5. only then consider a larger HTML parsing refactor or deduplication effort

More concretely, the next practical batch should be:

1. update `~/codex-demo/docs/project-status.md`
2. add a top-level collaboration document that explains how the two repos fit together
3. unify shared inbox configuration through env var or shared config
4. add a reproducible integration test path

Status after follow-up implementation on 2026-03-14:

- item 1 completed
- item 2 completed
- item 3 started through shared env-var support using `CONTENT_INGESTION_SHARED_INBOX_ROOT`
- item 4 completed through `docs/windows-wsl-roundtrip.md` and `scripts/run_windows_wsl_roundtrip.ps1`
- metadata hint consumption improved in WSL so `title_hint`, `author_hint`, and `published_at_hint` are now preferred when present

---

## 7. Verified Test State

Verified on 2026-03-14:

- Windows client: `31` unit tests passed
- WSL processor: `18` unit tests passed

These numbers should be treated as the current baseline until changed by later work.

---

## 8. Working Conclusion

The current route should continue.

There is no evidence that the architecture or milestone sequence needs to be reset.
The immediate need is coordination cleanup:

- make the docs true
- make shared inbox configuration explicit and shared
- reduce avoidable duplicate metadata work
- raise engineering hygiene enough to support continued iteration

That is the correct follow-on from the current state of both repositories.
