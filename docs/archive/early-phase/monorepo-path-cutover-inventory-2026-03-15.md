# Monorepo Path Cutover Inventory

## Goal

This document lists the concrete path, entrypoint, and repository-root assumptions that will need to change when:

- the current Windows repo at `H:/demo-win`
- the current WSL repo at `/home/ahzz1207/codex-demo`

are moved into one GitHub monorepo.

Target layout:

```text
repo/
  apps/
    windows-client/
    content-ingestion/
```

This is not a migration checklist. It is the inventory of what will break or need updating during cutover.

## Priority Summary

### P0: Must change during cutover

- Windows default WSL repo path
- Windows WSL bridge `cd` target
- Windows detached GUI launcher root assumption
- docs that still name `H:/demo-win` and `~/codex-demo` as the canonical repo paths

### P1: Should change in the same migration window

- tests that assert the old WSL repo path
- docs that still show root-level `main.py`
- app READMEs that still describe a two-repo layout

### P2: Can change after the initial move

- historical review docs
- older phase handoff notes
- background material that is no longer the primary operating guide

## Windows Code Path Assumptions

### 1. Default WSL project root is hard-coded

File:

- [settings.py](H:/demo-win/src/windows_client/config/settings.py#L17)

Current behavior:

- `CONTENT_INGESTION_WSL_PROJECT_ROOT` falls back to `/home/ahzz1207/codex-demo`

Why it breaks:

- after monorepo migration, the WSL app should live under something like `/home/<user>/<repo>/apps/content-ingestion`

Cutover action:

- change the default from a hard-coded legacy repo path to a monorepo-aware path
- ideally compute it from a shared monorepo root instead of storing a second fixed repo root

### 2. Windows WSL bridge explicitly `cd`s into the old WSL repo

Files:

- [wsl_bridge.py](H:/demo-win/src/windows_client/app/wsl_bridge.py#L64)
- [wsl_bridge.py](H:/demo-win/src/windows_client/app/wsl_bridge.py#L183)

Current behavior:

- watcher start and all WSL bridge commands run:
  - `cd <wsl_project_root>`
  - `python3 main.py ...`

Why it breaks:

- `main.py` will no longer live at the old standalone WSL repo root

Cutover action:

- point `cd` to the monorepo app directory
- keep the app-local entrypoint model:
  - `apps/content-ingestion/main.py`

### 3. Detached GUI launch assumes current repo root owns `main.py`

File:

- [cli.py](H:/demo-win/src/windows_client/app/cli.py#L146)

Current behavior:

- `_project_root()` resolves to the current repo root
- detached GUI launch uses:
  - `<project_root>/main.py`

Why it breaks:

- after migration, Windows app root becomes `apps/windows-client`

Cutover action:

- keep `_project_root()` aligned with the Windows app root after the move
- verify detached GUI launch still invokes:
  - `apps/windows-client/main.py`

### 4. Windows default runtime data root depends on current repo root

File:

- [settings.py](H:/demo-win/src/windows_client/config/settings.py#L31)

Current behavior:

- runtime data defaults to:
  - `<project_root>/data`

Impact:

- this is not inherently wrong in a monorepo
- but it changes the actual location to:
  - `apps/windows-client/data`

Cutover action:

- keep this behavior for app isolation
- update docs and ignore rules to match the new app-local data location

## WSL Code Path Assumptions

### 5. WSL root entrypoint assumes a standalone repo root

File:

- [main.py](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/main.py#L4)

Current behavior:

- `PROJECT_ROOT = Path(__file__).resolve().parent`
- `SRC_DIR = PROJECT_ROOT / "src"`

Why it matters:

- this is fine if `main.py` moves together with `src/`
- it only breaks if the file move is incomplete or if the new app layout is changed during migration

Cutover action:

- move `main.py` and `src/` together into `apps/content-ingestion`
- do not redesign this entrypoint in the same PR

### 6. WSL settings default to app-local `data/`

File:

- [config.py](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/src/content_ingestion/core/config.py#L38)

Current behavior:

- runtime paths default under:
  - `<project_root>/data`

Impact:

- after migration this becomes:
  - `apps/content-ingestion/data`

Cutover action:

- keep this behavior
- update root `.gitignore` and app docs accordingly

### 7. Shared inbox env var remains valid and should not be renamed

Files:

- [settings.py](H:/demo-win/src/windows_client/config/settings.py#L16)
- [config.py](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/src/content_ingestion/core/config.py#L41)

Current behavior:

- both apps already align on:
  - `CONTENT_INGESTION_SHARED_INBOX_ROOT`

Cutover action:

- keep this environment variable unchanged
- do not rename it during monorepo migration

This is one of the few cross-repo contracts that is already stable.

## Test Assumptions That Must Be Updated

### 8. Windows tests assert the old WSL repo path

File:

- [test_cli.py](H:/demo-win/tests/unit/test_cli.py#L30)

Current behavior:

- tests expect:
  - `/home/ahzz1207/codex-demo`

Why it matters:

- these tests will fail immediately after path cutover

Cutover action:

- update expected values to the new monorepo app path
- prefer deriving expected paths from test settings instead of hard-coding the old repo name again

### 9. Windows tests assume current repo-relative shared inbox paths

Files:

- [test_wsl_bridge.py](H:/demo-win/tests/unit/test_wsl_bridge.py#L28)
- [test_service.py](H:/demo-win/tests/unit/test_service.py#L44)

Current behavior:

- tests assert current Windows repo-relative paths like:
  - `H:/demo-win/data/shared_inbox`

Impact:

- these should become app-local monorepo paths after the move

Cutover action:

- update fixture expectations to:
  - `<monorepo>/apps/windows-client/data/shared_inbox`

### 10. WSL tests mostly look safe

Files:

- [config.py](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/src/content_ingestion/core/config.py#L41)
- WSL tests mainly assert env-var behavior and app-local path behavior

Impact:

- most WSL tests should survive as long as `main.py`, `src/`, and `data/` move together

Cutover action:

- re-run all WSL tests after the move
- only patch tests that reference old documentation or explicit standalone repo names

## Command Cutover Map

### Windows app

Before:

```powershell
cd H:\demo-win
python main.py gui
python main.py export-url-job <url>
python main.py wsl-doctor
```

After:

```powershell
cd <repo>\apps\windows-client
python main.py gui
python main.py export-url-job <url>
python main.py wsl-doctor
```

### WSL app

Before:

```bash
cd /home/ahzz1207/codex-demo
python3 main.py doctor
python3 main.py watch-inbox --once
```

After:

```bash
cd /home/<user>/<repo>/apps/content-ingestion
python3 main.py doctor
python3 main.py watch-inbox --once
```

### Important rule

Do not try to replace app-local `main.py` commands with a new root command layer during the same migration.

Keep command semantics stable first.

## Documentation Cutover Targets

### Must update early

- [README.md](H:/demo-win/README.md)
- [README.md](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/README.md#L3)
- [windows-wsl-roundtrip.md](H:/demo-win/docs/windows-wsl-roundtrip.md)
- [windows-wsl-handoff-contract.md](H:/demo-win/docs/windows-wsl-handoff-contract.md)
- [cross-repo-collaboration.md](\\wsl.localhost/Ubuntu-22.04/home/ahzz1207/codex-demo/docs/cross-repo-collaboration.md)

Why:

- these are operational docs, not just history

### Safe to leave for later

- [cross-review-2026-03-14.md](H:/demo-win/docs/cross-review-2026-03-14.md)
- older phase handoff docs
- older review snapshots

Why:

- they are historical records, not primary operating instructions

## Recommended Cutover Order

1. Create the monorepo skeleton.
2. Move Windows app into `apps/windows-client` without refactoring.
3. Move WSL app into `apps/content-ingestion` without refactoring.
4. Update Windows WSL bridge default repo path.
5. Re-run Windows tests and patch path assertions.
6. Re-run WSL tests and patch any repo-name assumptions.
7. Update the two app READMEs and operational docs.
8. Only after that, add root CI and integration wiring.

## Recommended Post-Cutover Validation

Minimum validation after the move:

### Windows

```powershell
cd <repo>\apps\windows-client
python -m unittest discover -s tests -p "test_*.py"
python main.py wsl-doctor
python main.py wsl-watch-status
python main.py gui
```

### WSL

```bash
cd /home/<user>/<repo>/apps/content-ingestion
pytest -q
python3 main.py doctor
```

### End-to-end

```powershell
cd <repo>\apps\windows-client
python main.py full-chain-smoke https://example.com/
```

## Current Recommendation

The first code change to plan for after the directory move is:

- make the Windows `wsl_project_root` monorepo-aware

That is the most direct technical blocker for a healthy post-migration Win -> WSL roundtrip.
