# Full Chain Check 2026-03-14

## Purpose

This document records the Win -> WSL validation pass that followed the current GUI closeout.

The focus of this pass was not new GUI work. It was to confirm that WSL can still consume Windows-exported jobs correctly, quickly, and in a way that matches the GUI result-reading assumptions.

---

## GUI Status At Time Of Check

The Windows GUI was treated as closed for feature growth during this pass:

- URL-first entry flow
- result workspace enabled
- recent result browsing enabled
- reading-surface preview enabled

Reference:

- `docs/gui-closeout-2026-03-14.md`

---

## Validation Baseline

Windows-side verification run:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `55 passed`
- note: one existing `ResourceWarning` still appears during the suite, but it does not fail the run

WSL-side verification run:

- `python3 -m pytest -q tests/unit`
- result: `23 passed`

WSL doctor snapshot:

- `project_root=/home/ahzz1207/codex-demo`
- `shared_inbox_exists=True`
- `registered_connectors=wechat`
- `playwright=ok`

Observed note:

- `wsl.exe` currently prints a localized localhost / WSL NAT warning on this machine
- it did not block validation, `watch-inbox`, or processor output generation during this pass

---

## Stable Roundtrip Check

Stable roundtrip command used:

- `powershell -ExecutionPolicy Bypass -File scripts/run_windows_wsl_roundtrip.ps1`

Result:

- export mode: `mock`
- job id: `20260314_225646_51e325`
- inbox validation: success
- `watch-inbox --once`: success
- processed output created successfully
- contract assertions between exported `metadata.json` and WSL `normalized.json` passed

This confirms that the current Windows-side handoff contract still matches the WSL processor.

---

## Fresh Shared-Root HTTP Check

The formal Windows shared inbox root was re-checked with a fresh URL export instead of relying on old directory counts.

Command sequence:

- `python main.py export-url-job https://example.com/`
- `wsl.exe ... python3 main.py validate-inbox`
- `wsl.exe ... python3 main.py watch-inbox --once`

Observed result:

- job id: `20260314_233659_9e67ae`
- exported into `data/shared_inbox/incoming/`
- WSL validation succeeded
- WSL `watch-inbox --once` consumed the job from the Windows-mounted root
- end-to-end WSL processing time for the `watch-inbox --once` step was about `0.37s`
- processed output was written to `data/shared_inbox/processed/20260314_233659_9e67ae/`

This invalidated an earlier suspicion that WSL was silently failing to consume Windows-mounted inbox jobs. The real issue was that the earlier `incoming=6` observation was stale; by the time the re-check happened, those jobs had already been processed.

---

## Real Browser Payload Re-Check

One real WeChat browser-exported job was replayed through a temporary shared inbox to verify result quality against actual Windows-collected HTML.

Replay source:

- original processed job: `20260314_225504_9ff6ec`
- source URL: `https://mp.weixin.qq.com/s/l3for3iHUfD5_Fe_tSYDPg`

Replay result:

- temporary inbox validation: success
- WSL `watch-inbox --once` processing time was about `0.46s`
- `normalized.json` preserved correct Chinese title and body text when read as `utf-8`
- `published_at` now resolves to `2026-03-13T13:30:00`

Important note:

- PowerShell / WSL terminal output on this machine can display Chinese text as mojibake
- direct `utf-8` file reads show that the actual `metadata.json` and `normalized.json` contents are correct
- the terminal display issue should not be mistaken for a processor corruption bug

---

## Parsing Fix Landed During This Check

WSL parsing was tightened for localized numeric timestamps coming from Windows hints.

Change made:

- `published_at_hint` values such as `2026年3月13日 13:30` are now parsed by the WSL raw layer

Verification:

- unit coverage added for localized timestamp parsing
- WSL unit suite moved from `22` to `23` passing tests
- the real WeChat replay above confirms the fix in processor output, not only in unit tests

---

## Current Shared Inbox Snapshot

At the end of this pass, the Windows-side shared inbox contained:

- `processed`: `17`
- `incoming`: `0`
- `processing`: `0`
- `failed`: `0`

This means the GUI result workspace is currently reading against a real, non-empty dataset that includes both synthetic verification output and previously processed browser jobs.

---

## Conclusion

The current cross-repo baseline is healthy enough to move forward from:

- GUI can stay in closeout / bugfix-only mode
- WSL consumes Windows-exported jobs correctly from the formal shared inbox root
- WSL processor turnaround for current single-job checks is sub-second once `watch-inbox --once` is invoked
- current result files match the GUI reading model closely enough for continued result-workspace iteration

The remaining work should now focus on:

- targeted real-URL browser-route verification, especially around login-bound platforms
- operational questions such as how often WSL should scan and how GUI should reflect WSL latency
