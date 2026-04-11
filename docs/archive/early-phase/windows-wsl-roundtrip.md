# Windows-WSL Roundtrip

## Purpose

This is the repeatable cross-repo verification path for:

1. Windows job export
2. shared inbox alignment
3. WSL inbox validation
4. WSL processing output generation

It is intended to verify the real handoff contract, not just unit tests inside one repo.

---

## Script

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_windows_wsl_roundtrip.ps1
```

Default mode is `mock`.

The script will:

1. create a temporary shared inbox
2. set `CONTENT_INGESTION_SHARED_INBOX_ROOT`
3. run Windows `export-mock-job`
4. run WSL `validate-inbox`
5. run WSL `watch-inbox --once`
6. verify the expected `processed/<job_id>/` outputs exist
7. verify key `metadata.json -> normalized.json` fields survived the handoff correctly

By default it removes the temporary artifacts after success.

To keep the artifacts for inspection:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_windows_wsl_roundtrip.ps1 -KeepArtifacts
```

---

## What It Verifies

This roundtrip intentionally exercises the shared configuration contract:

- Windows side uses `CONTENT_INGESTION_SHARED_INBOX_ROOT` without requiring `--shared-root`
- WSL side uses the same env var without requiring a positional `shared_root`
- both repositories point at the same shared inbox root

For the current mock path it also verifies that:

- Windows writes expanded handoff metadata such as `final_url` and `collection_mode`
- WSL accepts and preserves the expanded metadata without breaking processing
- `normalized.asset.canonical_url` matches the exported `final_url` when present
- `normalized.asset.metadata.job_id` and `content_type` stay aligned with the processed `metadata.json`
- filtered handoff fields under `normalized.asset.metadata.handoff` match the exported metadata when those fields are present

Expected processed output files:

- `metadata.json`
- `normalized.json`
- `normalized.md`
- `pipeline.json`
- `status.json`

---

## Parameters

Optional script parameters:

- `-WindowsPython`
- `-WslRepo`
- `-SourceUrl`
- `-ExportMode` with `mock`, `http`, or `browser`
- `-SharedRoot`
- `-ContentType`
- `-Platform`
- `-ProfileDir`
- `-BrowserChannel`
- `-WaitUntil`
- `-TimeoutMs`
- `-SettleMs`
- `-WaitForSelector`
- `-WaitForSelectorState`
- `-Headed`
- `-KeepArtifacts`

Defaults assume:

- Windows repo is the current working tree at `H:\demo-win`
- WSL repo is `~/codex-demo`
- Windows Python is `C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe`

Environment note:

- the default `-WindowsPython` value is specific to the current development machine
- if your Python interpreter lives elsewhere, pass `-WindowsPython <path>` explicitly

Exit behavior:

- success returns exit code `0`
- failures surface as a PowerShell error and return a non-zero exit code

Example browser-mode run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_windows_wsl_roundtrip.ps1 `
  -ExportMode browser `
  -SourceUrl https://mp.weixin.qq.com/s/example `
  -ProfileDir H:\demo-win\data\browser_profiles\wechat `
  -WaitForSelector "#js_content" `
  -WaitForSelectorState visible
```

Use browser mode only when the local browser/profile prerequisites are already prepared. `mock` remains the stable default regression path.

---

## Related Docs

- `docs/cross-review-2026-03-14.md` for internal review history and cross-check notes
- `docs/windows-client-kickoff.md`
- `docs/windows-wsl-handoff-contract.md`
- `~/codex-demo/docs/cross-repo-collaboration.md`
