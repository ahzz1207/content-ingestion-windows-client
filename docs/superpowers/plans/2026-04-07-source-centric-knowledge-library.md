# Source-Centric Knowledge Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows-side source-centric knowledge library with result-page save, image-first entry detail, and entry-local restore for replaced interpretations.

**Architecture:** Keep the existing job workspace intact and add a separate local library snapshot store under the shared root. A new library repository/service layer will snapshot source files plus the current interpretation from `ResultWorkspaceEntry`, while the GUI adds a save action in `InlineResultView` and a dedicated library dialog/detail view. The first version reuses `insight_card.png` when it exists, but never blocks save if no image asset is present.

**Tech Stack:** Python 3.10, dataclasses, pathlib, json, shutil, PySide6, pytest, unittest

---

## File Map

### New application files

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/windows_client/app/library_store.py` | File-backed source-centric library repository: source-key resolution, entry save, interpretation trash/current swaps, list/detail loading |
| `src/windows_client/gui/library_panel.py` | Dedicated library dialog UI with source-centric list and image-first detail rendering |

### Modified application files

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/windows_client/app/service.py` | Inject library store and expose save/restore library operations |
| `src/windows_client/app/workflow.py` | Add GUI-facing wrappers for save-to-library and restore-from-trash operations |
| `src/windows_client/app/view_models.py` | Add small snapshot types for library save/restore responses if needed by GUI thread callbacks |
| `src/windows_client/gui/inline_result_view.py` | Add `保存进知识库` and `知识库` actions plus success/failure banner plumbing |
| `src/windows_client/gui/main_window.py` | Wire save-to-library background tasks and open library dialog from ready/result views |
| `src/windows_client/gui/app.py` | No behavior change expected, but keep import paths valid if new GUI module is introduced |

### Existing files reused for data extraction

| File | Responsibility in this plan |
|------|-----------------------------|
| `src/windows_client/app/result_workspace.py` | Existing processed-job snapshot source for save-to-library input |
| `src/windows_client/api/models.py` | Existing serialization patterns to follow for any new view-model dataclasses |
| `src/windows_client/gui/workers.py` | Reuse background task thread pattern for save and restore |

### Test files

| File | Responsibility in this plan |
|------|-----------------------------|
| `tests/unit/test_library_store.py` | New storage/repository tests for save, dedupe, trash, restore, and image-asset behavior |
| `tests/unit/test_service.py` | Verify service delegates to library store and wraps save/restore behavior correctly |
| `tests/unit/test_workflow.py` | Verify GUI-facing workflow wrappers return stable success/failure states for library operations |
| `tests/unit/test_inline_result_view.py` | Verify save/library buttons and save feedback in the result page |
| `tests/unit/test_main_window.py` | Verify save-to-library threading, library dialog entry points, and restore refresh behavior |

---

### Task 1: Build the library storage model with TDD

**Files:**
- Create: `src/windows_client/app/library_store.py`
- Test: `tests/unit/test_library_store.py`

- [ ] **Step 1: Write the failing tests for new-entry save, repeat-save trashing, restore, and missing-image handling**

```python
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.library_store import LibraryStore


class _Entry:
    def __init__(self, *, job_dir: Path, job_id: str, source_url: str, canonical_url: str | None = None) -> None:
        self.job_id = job_id
        self.job_dir = job_dir
        self.source_url = source_url
        self.canonical_url = canonical_url
        self.title = "Macro Note"
        self.author = "Author"
        self.published_at = "2026-04-07"
        self.platform = "wechat"
        self.summary = "Bottom line"
        self.analysis_state = "ready"
        self.state = "processed"
        self.preview_text = None
        self.metadata_path = job_dir / "metadata.json"
        self.analysis_json_path = job_dir / "analysis" / "llm" / "analysis_result.json"
        self.normalized_json_path = job_dir / "normalized.json"
        self.normalized_md_path = job_dir / "normalized.md"
        self.status_path = None
        self.error_path = None
        self.updated_at = 1712487960.0
        self.coverage = None
        self.details = {
            "metadata": {
                "source_url": source_url,
                "final_url": canonical_url or source_url,
                "platform": "wechat",
                "collection_mode": "browser",
                "collected_at": "2026-04-07T18:32:00+08:00",
            },
            "structured_result": {
                "summary": {"headline": "Headline", "short_text": "Short"},
                "product_view": {"layout": "analysis_brief", "title": "Headline", "sections": []},
                "editorial": {"resolved_reading_goal": "argument", "resolved_domain_template": "macro_business", "route_key": "argument.macro_business"},
            },
            "product_view": {"layout": "analysis_brief", "title": "Headline", "sections": []},
            "normalized": {
                "metadata": {
                    "llm_processing": {
                        "resolved_mode": "argument",
                        "resolved_reading_goal": "argument",
                        "resolved_domain_template": "macro_business",
                        "route_key": "argument.macro_business",
                    }
                }
            },
            "insight_card_path": job_dir / "analysis" / "insight_card.png",
        }


class LibraryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.shared_root = Path(self.temp_dir.name) / "shared_inbox"
        self.shared_root.mkdir(parents=True)
        self.store = LibraryStore(shared_root=self.shared_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_entry_creates_new_source_centric_entry(self) -> None:
        entry = self._make_processed_entry("job-1", "https://example.com/a")

        saved = self.store.save_entry(entry)

        self.assertEqual(saved.source.title, "Macro Note")
        self.assertEqual(saved.current_interpretation.route_key, "argument.macro_business")
        self.assertEqual(saved.trashed_interpretations, [])
        self.assertTrue((self.shared_root / "library" / "entries" / saved.entry_id / "entry.json").exists())

    def test_save_same_source_reuses_entry_and_trashes_previous_current_interpretation(self) -> None:
        first = self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))
        second = self.store.save_entry(self._make_processed_entry("job-2", "https://example.com/a"))

        self.assertEqual(first.entry_id, second.entry_id)
        self.assertEqual(len(second.trashed_interpretations), 1)
        self.assertEqual(second.current_interpretation.saved_from_job_id, "job-2")
        self.assertEqual(second.trashed_interpretations[0].saved_from_job_id, "job-1")

    def test_restore_trashed_interpretation_swaps_current_and_trashed(self) -> None:
        self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))
        saved = self.store.save_entry(self._make_processed_entry("job-2", "https://example.com/a"))

        restored = self.store.restore_interpretation(
            entry_id=saved.entry_id,
            interpretation_id=saved.trashed_interpretations[0].interpretation_id,
        )

        self.assertEqual(restored.current_interpretation.saved_from_job_id, "job-1")
        self.assertEqual(len(restored.trashed_interpretations), 1)
        self.assertEqual(restored.trashed_interpretations[0].saved_from_job_id, "job-2")

    def test_save_without_insight_card_still_persists_entry(self) -> None:
        entry = self._make_processed_entry("job-1", "https://example.com/a", with_image=False)

        saved = self.store.save_entry(entry)

        self.assertEqual(saved.current_interpretation.image_summary_asset, None)
        self.assertEqual(saved.current_interpretation.saved_from_job_id, "job-1")

    def _make_processed_entry(self, job_id: str, source_url: str, with_image: bool = True) -> _Entry:
        job_dir = self.shared_root / "processed" / job_id
        (job_dir / "analysis" / "llm").mkdir(parents=True, exist_ok=True)
        (job_dir / "metadata.json").write_text("{}", encoding="utf-8")
        (job_dir / "normalized.json").write_text("{}", encoding="utf-8")
        (job_dir / "normalized.md").write_text("# Headline\n\nBody", encoding="utf-8")
        (job_dir / "analysis" / "llm" / "analysis_result.json").write_text("{}", encoding="utf-8")
        if with_image:
            (job_dir / "analysis" / "insight_card.png").write_bytes(b"png")
        return _Entry(job_dir=job_dir, job_id=job_id, source_url=source_url)
```

- [ ] **Step 2: Run the targeted tests and verify they fail for the expected reason**

Run: `python -m pytest tests/unit/test_library_store.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'windows_client.app.library_store'`

- [ ] **Step 3: Write the minimal file-backed library store implementation**

```python
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from windows_client.app.errors import WindowsClientError
from windows_client.app.result_workspace import ResultWorkspaceEntry


@dataclass(slots=True)
class LibraryAsset:
    kind: str
    path: Path | None


@dataclass(slots=True)
class LibraryInterpretation:
    interpretation_id: str
    state: str
    saved_from_job_id: str
    route_key: str
    saved_at: str
    trashed_at: str | None = None
    trash_reason: str | None = None
    summary_headline: str | None = None
    summary_short_text: str | None = None
    image_summary_asset: LibraryAsset | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LibrarySource:
    title: str | None
    source_url: str | None
    canonical_url: str | None
    platform: str | None
    author: str | None
    published_at: str | None
    captured_at: str | None


@dataclass(slots=True)
class LibraryEntryView:
    entry_id: str
    source_key: str
    source: LibrarySource
    current_interpretation: LibraryInterpretation
    trashed_interpretations: list[LibraryInterpretation]


class LibraryStore:
    def __init__(self, *, shared_root: Path) -> None:
        self.shared_root = shared_root
        self.library_root = shared_root / "library"
        self.entries_root = self.library_root / "entries"

    def save_entry(self, entry: ResultWorkspaceEntry) -> LibraryEntryView:
        self.entries_root.mkdir(parents=True, exist_ok=True)
        source_key = self._source_key(entry)
        entry_dir = self._find_entry_dir(source_key)
        if entry_dir is None:
            entry_id = self._next_entry_id()
            entry_dir = self.entries_root / entry_id
            entry_dir.mkdir(parents=True, exist_ok=True)
            self._copy_source_snapshot(entry, entry_dir)
            manifest = {
                "entry_id": entry_id,
                "source_key": source_key,
                "created_at": self._now_iso(),
                "updated_at": self._now_iso(),
                "source": self._source_payload(entry),
                "current_interpretation_id": None,
                "interpretations": [],
            }
        else:
            manifest = json.loads((entry_dir / "entry.json").read_text(encoding="utf-8"))

        current_id = manifest.get("current_interpretation_id")
        for interpretation in manifest.get("interpretations", []):
            if interpretation.get("interpretation_id") == current_id:
                interpretation["state"] = "trashed"
                interpretation["trashed_at"] = self._now_iso()
                interpretation["trash_reason"] = "replaced_by_new_save"

        new_interpretation = self._interpretation_payload(entry, entry_dir)
        manifest["interpretations"].append(new_interpretation)
        manifest["current_interpretation_id"] = new_interpretation["interpretation_id"]
        manifest["updated_at"] = self._now_iso()
        (entry_dir / "entry.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_index()
        return self.get_entry(manifest["entry_id"])

    def restore_interpretation(self, *, entry_id: str, interpretation_id: str) -> LibraryEntryView:
        entry_dir = self.entries_root / entry_id
        if not entry_dir.exists():
            raise WindowsClientError("library_entry_missing", f"library entry not found: {entry_id}", stage="library")
        manifest = json.loads((entry_dir / "entry.json").read_text(encoding="utf-8"))
        current_id = manifest.get("current_interpretation_id")
        found = False
        for interpretation in manifest.get("interpretations", []):
            if interpretation.get("interpretation_id") == current_id:
                interpretation["state"] = "trashed"
                interpretation["trashed_at"] = self._now_iso()
                interpretation["trash_reason"] = "replaced_by_restore"
            if interpretation.get("interpretation_id") == interpretation_id:
                interpretation["state"] = "current"
                interpretation["trashed_at"] = None
                interpretation["trash_reason"] = None
                found = True
        if not found:
            raise WindowsClientError("library_interpretation_missing", f"interpretation not found: {interpretation_id}", stage="library")
        manifest["current_interpretation_id"] = interpretation_id
        manifest["updated_at"] = self._now_iso()
        (entry_dir / "entry.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_index()
        return self.get_entry(entry_id)

    def get_entry(self, entry_id: str) -> LibraryEntryView:
        manifest = json.loads((self.entries_root / entry_id / "entry.json").read_text(encoding="utf-8"))
        current_id = manifest["current_interpretation_id"]
        interpretations = [self._view_interpretation(item) for item in manifest["interpretations"]]
        current = next(item for item in interpretations if item.interpretation_id == current_id)
        trashed = [item for item in interpretations if item.state == "trashed"]
        source = manifest["source"]
        return LibraryEntryView(
            entry_id=manifest["entry_id"],
            source_key=manifest["source_key"],
            source=LibrarySource(
                title=source.get("title"),
                source_url=source.get("source_url"),
                canonical_url=source.get("canonical_url"),
                platform=source.get("platform"),
                author=source.get("author"),
                published_at=source.get("published_at"),
                captured_at=source.get("captured_at"),
            ),
            current_interpretation=current,
            trashed_interpretations=trashed,
        )

    def list_entries(self) -> list[LibraryEntryView]:
        if not self.entries_root.exists():
            return []
        return [self.get_entry(path.name) for path in sorted(self.entries_root.iterdir()) if path.is_dir()]

    def _find_entry_dir(self, source_key: str) -> Path | None:
        if not self.entries_root.exists():
            return None
        for path in self.entries_root.iterdir():
            entry_file = path / "entry.json"
            if not entry_file.exists():
                continue
            manifest = json.loads(entry_file.read_text(encoding="utf-8"))
            if manifest.get("source_key") == source_key:
                return path
        return None

    def _copy_source_snapshot(self, entry: ResultWorkspaceEntry, entry_dir: Path) -> None:
        source_dir = entry_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        self._copy_if_exists(entry.metadata_path, source_dir / "metadata.json")
        self._copy_if_exists(entry.normalized_json_path, source_dir / "normalized.json")
        self._copy_if_exists(entry.normalized_md_path, source_dir / "normalized.md")

    def _interpretation_payload(self, entry: ResultWorkspaceEntry, entry_dir: Path) -> dict[str, Any]:
        interpretation_id = f"interp_{entry.job_id.replace('-', '_')}"
        destination_dir = entry_dir / "interpretations" / interpretation_id
        assets_dir = destination_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        image_path = None
        raw_image = entry.details.get("insight_card_path")
        if isinstance(raw_image, Path) and raw_image.exists():
            image_path = assets_dir / "insight_card.png"
            shutil.copy2(raw_image, image_path)
        structured = entry.details.get("structured_result") if isinstance(entry.details, dict) else {}
        normalized = entry.details.get("normalized") if isinstance(entry.details, dict) else {}
        llm_processing = normalized.get("metadata", {}).get("llm_processing", {}) if isinstance(normalized, dict) else {}
        payload = {
            "interpretation_id": interpretation_id,
            "state": "current",
            "saved_from_job_id": entry.job_id,
            "saved_at": self._now_iso(),
            "trashed_at": None,
            "trash_reason": None,
            "route_key": llm_processing.get("route_key") or structured.get("editorial", {}).get("route_key") or "argument.generic",
            "summary": structured.get("summary") or {},
            "product_view": entry.details.get("product_view") or structured.get("product_view") or {},
            "editorial": structured.get("editorial") or {},
            "structured_result": structured,
            "assets": [] if image_path is None else [{"kind": "image_summary", "path": str(image_path.relative_to(entry_dir))}],
        }
        (destination_dir / "interpretation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def _source_payload(self, entry: ResultWorkspaceEntry) -> dict[str, Any]:
        metadata = entry.details.get("metadata") if isinstance(entry.details, dict) else {}
        return {
            "title": entry.title,
            "source_url": entry.source_url,
            "canonical_url": entry.canonical_url,
            "platform": entry.platform,
            "author": entry.author,
            "published_at": entry.published_at,
            "captured_at": metadata.get("collected_at") if isinstance(metadata, dict) else None,
        }

    def _source_key(self, entry: ResultWorkspaceEntry) -> str:
        if entry.canonical_url:
            return entry.canonical_url
        if entry.source_url:
            return entry.source_url
        if entry.normalized_md_path is not None and entry.normalized_md_path.exists():
            digest = hashlib.sha1(entry.normalized_md_path.read_bytes()).hexdigest()
            return f"sha1:{digest}"
        return f"job:{entry.job_id}"

    def _view_interpretation(self, payload: dict[str, Any]) -> LibraryInterpretation:
        asset = None
        assets = payload.get("assets") or []
        if assets:
            asset_payload = assets[0]
            asset = LibraryAsset(kind=asset_payload.get("kind", "image_summary"), path=Path(asset_payload["path"]))
        summary = payload.get("summary") or {}
        return LibraryInterpretation(
            interpretation_id=payload["interpretation_id"],
            state=payload["state"],
            saved_from_job_id=payload["saved_from_job_id"],
            route_key=payload["route_key"],
            saved_at=payload["saved_at"],
            trashed_at=payload.get("trashed_at"),
            trash_reason=payload.get("trash_reason"),
            summary_headline=summary.get("headline"),
            summary_short_text=summary.get("short_text"),
            image_summary_asset=asset,
            payload=payload,
        )

    def _write_index(self) -> None:
        self.library_root.mkdir(parents=True, exist_ok=True)
        items = []
        for entry in self.list_entries():
            items.append(
                {
                    "entry_id": entry.entry_id,
                    "source_key": entry.source_key,
                    "title": entry.source.title,
                    "current_route_key": entry.current_interpretation.route_key,
                    "has_image_summary": entry.current_interpretation.image_summary_asset is not None,
                    "trashed_count": len(entry.trashed_interpretations),
                }
            )
        (self.library_root / "index.json").write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _next_entry_id(self) -> str:
        existing = [path.name for path in self.entries_root.iterdir() if path.is_dir()] if self.entries_root.exists() else []
        return f"lib_{len(existing) + 1:04d}"

    def _copy_if_exists(self, src: Path | None, dest: Path) -> None:
        if src is None or not src.exists():
            return
        shutil.copy2(src, dest)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()
```

- [ ] **Step 4: Re-run the storage tests and verify they pass**

Run: `python -m pytest tests/unit/test_library_store.py -q`

Expected: PASS

- [ ] **Step 5: Commit the storage layer**

```bash
git add tests/unit/test_library_store.py src/windows_client/app/library_store.py
git commit -m "feat: add source-centric library storage"
```

### Task 2: Expose library save and restore through service and workflow

**Files:**
- Modify: `src/windows_client/app/service.py`
- Modify: `src/windows_client/app/workflow.py`
- Modify: `src/windows_client/app/view_models.py`
- Test: `tests/unit/test_service.py`
- Test: `tests/unit/test_workflow.py`

- [ ] **Step 1: Write failing service and workflow tests for save-to-library and restore-to-current**

```python
def test_save_result_to_library_delegates_to_store(self) -> None:
    entry = MagicMock()
    self.service.library_store = MagicMock()
    self.service.library_store.save_entry.return_value.entry_id = "lib_0001"

    result = self.service.save_result_to_library(entry)

    self.service.library_store.save_entry.assert_called_once_with(entry)
    self.assertEqual(result.entry_id, "lib_0001")


def test_restore_library_interpretation_delegates_to_store(self) -> None:
    self.service.library_store = MagicMock()
    self.service.library_store.restore_interpretation.return_value.entry_id = "lib_0001"

    result = self.service.restore_library_interpretation("lib_0001", "interp_1")

    self.service.library_store.restore_interpretation.assert_called_once_with(
        entry_id="lib_0001",
        interpretation_id="interp_1",
    )
    self.assertEqual(result.entry_id, "lib_0001")


def test_workflow_save_result_to_library_returns_success_summary(self) -> None:
    self.service.save_result_to_library = MagicMock(return_value=type("Saved", (), {"entry_id": "lib_0001"})())

    state = self.workflow.save_result_to_library(MagicMock())

    self.assertEqual(state.status, "success")
    self.assertIn("lib_0001", state.summary)
```

- [ ] **Step 2: Run the targeted tests and verify they fail for missing methods or fields**

Run: `python -m pytest tests/unit/test_service.py tests/unit/test_workflow.py -k library -q`

Expected: FAIL with `AttributeError` for missing service/workflow methods

- [ ] **Step 3: Implement the minimal service and workflow wrappers**

```python
# in src/windows_client/app/view_models.py
@dataclass(slots=True)
class LibrarySnapshot:
    entry_id: str


@dataclass(slots=True)
class OperationViewState:
    operation: str
    status: str
    summary: str
    doctor: DoctorSnapshot | None = None
    job: JobExportSnapshot | None = None
    browser_session: BrowserSessionSnapshot | None = None
    library: LibrarySnapshot | None = None
    error: GuiErrorState | None = None


# in src/windows_client/app/service.py
from windows_client.app.library_store import LibraryStore, LibraryEntryView


class WindowsClientService:
    def __init__(..., video_downloader: YtDlpVideoDownloader | None = None) -> None:
        ...
        self.library_store = LibraryStore(shared_root=self.settings.effective_shared_inbox_root)

    def save_result_to_library(self, entry) -> LibraryEntryView:
        return self.library_store.save_entry(entry)

    def restore_library_interpretation(self, entry_id: str, interpretation_id: str) -> LibraryEntryView:
        return self.library_store.restore_interpretation(
            entry_id=entry_id,
            interpretation_id=interpretation_id,
        )


# in src/windows_client/app/workflow.py
from windows_client.app.view_models import LibrarySnapshot


class WindowsClientWorkflow:
    def save_result_to_library(self, entry) -> OperationViewState:
        try:
            saved = self.service.save_result_to_library(entry)
            return OperationViewState(
                operation="save-result-to-library",
                status="success",
                summary=f"Saved to library: {saved.entry_id}",
                library=LibrarySnapshot(entry_id=saved.entry_id),
            )
        except WindowsClientError as error:
            return self._failed("save-result-to-library", error)

    def restore_library_interpretation(self, entry_id: str, interpretation_id: str) -> OperationViewState:
        try:
            saved = self.service.restore_library_interpretation(entry_id, interpretation_id)
            return OperationViewState(
                operation="restore-library-interpretation",
                status="success",
                summary=f"Restored library entry: {saved.entry_id}",
                library=LibrarySnapshot(entry_id=saved.entry_id),
            )
        except WindowsClientError as error:
            return self._failed("restore-library-interpretation", error)
```

- [ ] **Step 4: Re-run the targeted service/workflow tests and verify they pass**

Run: `python -m pytest tests/unit/test_service.py tests/unit/test_workflow.py -k library -q`

Expected: PASS

- [ ] **Step 5: Commit the service/workflow plumbing**

```bash
git add src/windows_client/app/service.py src/windows_client/app/workflow.py src/windows_client/app/view_models.py tests/unit/test_service.py tests/unit/test_workflow.py
git commit -m "feat: expose library save and restore operations"
```

### Task 3: Add result-page save affordance in `InlineResultView`

**Files:**
- Modify: `src/windows_client/gui/inline_result_view.py`
- Test: `tests/unit/test_inline_result_view.py`

- [ ] **Step 1: Write failing GUI tests for the new save button, library button, and save banner**

```python
def test_processed_entry_enables_save_to_library_button(self) -> None:
    view = InlineResultView()
    entry = _make_entry()

    view.load_entry(entry, brief=None, resolved_mode="argument")

    self.assertFalse(view.save_to_library_button.isHidden())
    self.assertTrue(view.save_to_library_button.isEnabled())


def test_show_library_save_banner_makes_feedback_visible(self) -> None:
    view = InlineResultView()

    view.show_library_banner("Source 已保存到知识库")

    self.assertFalse(view._library_banner_frame.isHidden())
    self.assertIn("知识库", view._library_banner_label.text())
```

- [ ] **Step 2: Run the targeted GUI tests and verify they fail for missing widgets/methods**

Run: `python -m pytest tests/unit/test_inline_result_view.py -k library -q`

Expected: FAIL with `AttributeError` for missing `save_to_library_button` or banner helpers

- [ ] **Step 3: Implement the minimal result-page library controls and banner**

```python
# in src/windows_client/gui/inline_result_view.py
class InlineResultView(QWidget):
    save_to_library_requested = Signal()
    open_library_requested = Signal()

    def __init__(self, *, parent: QWidget | None = None) -> None:
        ...
        self._save_to_library_btn = QPushButton("保存进知识库")
        self._save_to_library_btn.setObjectName("PrimaryButton")
        self._save_to_library_btn.clicked.connect(self.save_to_library_requested.emit)
        self._open_library_btn = QPushButton("知识库")
        self._open_library_btn.setObjectName("GhostButton")
        self._open_library_btn.clicked.connect(self.open_library_requested.emit)
        top_bar.addWidget(self._save_to_library_btn, 0, Qt.AlignLeft)
        top_bar.addWidget(self._open_library_btn, 0, Qt.AlignLeft)

        self._library_banner_frame = QFrame()
        self._library_banner_frame.setObjectName("CoverageBanner")
        _library_banner_layout = QHBoxLayout(self._library_banner_frame)
        _library_banner_layout.setContentsMargins(18, 12, 18, 12)
        self._library_banner_label = QLabel("")
        self._library_banner_label.setWordWrap(True)
        _library_banner_layout.addWidget(self._library_banner_label)
        self._library_banner_frame.hide()
        content_layout.insertWidget(1, self._library_banner_frame)

    @property
    def save_to_library_button(self) -> QPushButton:
        return self._save_to_library_btn

    @property
    def open_library_button(self) -> QPushButton:
        return self._open_library_btn

    def show_library_banner(self, message: str) -> None:
        text = message.strip()
        if not text:
            self._library_banner_frame.hide()
            return
        self._library_banner_label.setText(text)
        self._library_banner_frame.show()
        QTimer.singleShot(5000, self._library_banner_frame.hide)

    def load_entry(...):
        ...
        self._save_to_library_btn.setEnabled(entry.state == "processed")
        self._save_to_library_btn.setVisible(True)
        self._open_library_btn.setVisible(True)
```

- [ ] **Step 4: Re-run the targeted GUI tests and verify they pass**

Run: `python -m pytest tests/unit/test_inline_result_view.py -k library -q`

Expected: PASS

- [ ] **Step 5: Commit the result-page save affordance**

```bash
git add src/windows_client/gui/inline_result_view.py tests/unit/test_inline_result_view.py
git commit -m "feat: add result page library save actions"
```

### Task 4: Build the dedicated library dialog and image-first detail UI

**Files:**
- Create: `src/windows_client/gui/library_panel.py`
- Modify: `src/windows_client/gui/main_window.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing tests for opening the library dialog from ready/result views**

```python
def test_ready_page_history_button_opens_library_dialog(self) -> None:
    with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
        dialog = dialog_cls.return_value
        dialog.exec.return_value = 0

        self.window._open_library()

    dialog_cls.assert_called_once()


def test_result_page_library_button_opens_library_dialog(self) -> None:
    with patch("windows_client.gui.main_window.LibraryDialog") as dialog_cls:
        dialog = dialog_cls.return_value
        dialog.exec.return_value = 0

        self.window.result_inline.open_library_requested.emit()

    dialog_cls.assert_called_once()
```

- [ ] **Step 2: Run the targeted main-window tests and verify they fail for missing dialog wiring**

Run: `python -m pytest tests/unit/test_main_window.py -k library_dialog -q`

Expected: FAIL with import or attribute errors for missing `LibraryDialog` / `_open_library`

- [ ] **Step 3: Implement the minimal library dialog and main-window entry points**

```python
# in src/windows_client/gui/library_panel.py
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget

from windows_client.app.library_store import LibraryStore, LibraryEntryView


class LibraryDialog(QDialog):
    restore_requested = Signal(str, str)

    def __init__(self, *, parent, shared_root: Path) -> None:
        super().__init__(parent)
        self.store = LibraryStore(shared_root=shared_root)
        self.entries: list[LibraryEntryView] = []
        self.setWindowTitle("知识库")
        self.resize(1180, 760)
        root = QHBoxLayout(self)
        self.list_widget = QListWidget()
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_scroll.setWidget(self.detail_widget)
        root.addWidget(self.list_widget, 0)
        root.addWidget(self.detail_scroll, 1)
        self.list_widget.currentRowChanged.connect(self._render_entry)
        self.reload()

    def reload(self) -> None:
        self.entries = self.store.list_entries()
        self.list_widget.clear()
        for entry in self.entries:
            item = QListWidgetItem(entry.source.title or entry.entry_id)
            self.list_widget.addItem(item)
        if self.entries:
            self.list_widget.setCurrentRow(0)

    def _render_entry(self, row: int) -> None:
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        if row < 0 or row >= len(self.entries):
            return
        entry = self.entries[row]
        self.detail_layout.addWidget(self._build_image_section(entry))
        self.detail_layout.addWidget(self._build_source_section(entry))
        self.detail_layout.addWidget(self._build_interpretation_section(entry))
        self.detail_layout.addWidget(self._build_trash_section(entry))
        self.detail_layout.addStretch(1)

    def _build_image_section(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        title = QLabel("Image Summary")
        layout.addWidget(title)
        asset = entry.current_interpretation.image_summary_asset
        if asset is not None and asset.path is not None:
            image = QLabel()
            pixmap = QPixmap(str((self.store.entries_root / entry.entry_id / asset.path)))
            if not pixmap.isNull() and pixmap.width() > 640:
                pixmap = pixmap.scaledToWidth(640, Qt.SmoothTransformation)
            image.setPixmap(pixmap)
            layout.addWidget(image)
        else:
            layout.addWidget(QLabel("该条目已保存。当前 interpretation 暂无图片摘要，可先查看 source 与完整解读。"))
        return frame

    def _build_source_section(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel(entry.source.title or "Untitled source"))
        layout.addWidget(QLabel(entry.source.source_url or ""))
        layout.addWidget(QLabel(entry.source.platform or ""))
        return frame

    def _build_interpretation_section(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel(entry.current_interpretation.summary_headline or "Current interpretation"))
        layout.addWidget(QLabel(entry.current_interpretation.summary_short_text or ""))
        return frame

    def _build_trash_section(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel("Trashed Interpretations"))
        for interpretation in entry.trashed_interpretations:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.addWidget(QLabel(interpretation.route_key))
            restore_button = QPushButton("恢复为当前")
            restore_button.clicked.connect(lambda _=False, entry_id=entry.entry_id, interpretation_id=interpretation.interpretation_id: self.restore_requested.emit(entry_id, interpretation_id))
            row_layout.addWidget(restore_button)
            layout.addWidget(row)
        return frame


# in src/windows_client/gui/main_window.py
from windows_client.gui.library_panel import LibraryDialog

class MainWindow(QMainWindow):
    def _build_ready_page(self) -> QWidget:
        ...
        self.library_button = QPushButton("知识库")
        self.library_button.setObjectName("GhostButton")
        self.library_button.clicked.connect(self._open_library)
        actions.addWidget(self.library_button)
        ...

    def _build_ui(self) -> None:
        ...
        self.result_inline.open_library_requested.connect(self._open_library)
        self.result_inline.save_to_library_requested.connect(self._save_latest_result_to_library)

    def _open_library(self) -> None:
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        dialog = LibraryDialog(parent=self, shared_root=shared_root)
        dialog.restore_requested.connect(self._restore_library_interpretation)
        dialog.exec()
```

- [ ] **Step 4: Re-run the targeted main-window tests and verify they pass**

Run: `python -m pytest tests/unit/test_main_window.py -k library_dialog -q`

Expected: PASS

- [ ] **Step 5: Commit the library dialog UI**

```bash
git add src/windows_client/gui/library_panel.py src/windows_client/gui/main_window.py tests/unit/test_main_window.py
git commit -m "feat: add source-centric library dialog"
```

### Task 5: Wire save-to-library and restore flows through background tasks

**Files:**
- Modify: `src/windows_client/gui/main_window.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing main-window tests for threaded save and restore behavior**

```python
def test_save_latest_result_to_library_uses_workflow_thread_and_shows_banner(self) -> None:
    entry = _processed_entry("job-123")
    self.window._latest_result_entry = entry
    self.workflow.save_result_to_library = MagicMock(
        return_value=OperationViewState(
            operation="save-result-to-library",
            status="success",
            summary="Saved to library: lib_0001",
            library=type("Library", (), {"entry_id": "lib_0001"})(),
        )
    )

    class _Signal:
        def connect(self, callback):
            self.callback = callback

    class _FakeThread:
        def __init__(self, task):
            self.task = task
            self.progress_changed = _Signal()
            self.completed = _Signal()
            self.crashed = _Signal()

        def start(self):
            self.completed.callback(self.task(lambda _stage: None))

        def isRunning(self):
            return False

    with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread):
        self.window._save_latest_result_to_library()

    self.assertIn("知识库", self.window.result_inline._library_banner_label.text())


def test_restore_library_interpretation_refreshes_dialog_state(self) -> None:
    self.workflow.restore_library_interpretation = MagicMock(
        return_value=OperationViewState(operation="restore-library-interpretation", status="success", summary="restored")
    )

    class _Signal:
        def connect(self, callback):
            self.callback = callback

    class _FakeThread:
        def __init__(self, task):
            self.task = task
            self.progress_changed = _Signal()
            self.completed = _Signal()
            self.crashed = _Signal()

        def start(self):
            self.completed.callback(self.task(lambda _stage: None))

        def isRunning(self):
            return False

    with patch("windows_client.gui.main_window.WorkflowTaskThread", _FakeThread):
        self.window._restore_library_interpretation("lib_0001", "interp_1")

    self.workflow.restore_library_interpretation.assert_called_once_with("lib_0001", "interp_1")
```

- [ ] **Step 2: Run the targeted tests and verify they fail for missing handlers**

Run: `python -m pytest tests/unit/test_main_window.py -k "save_latest_result_to_library or restore_library_interpretation" -q`

Expected: FAIL with `AttributeError` for missing main-window handlers

- [ ] **Step 3: Implement the minimal threaded save and restore handlers**

```python
# in src/windows_client/gui/main_window.py
class MainWindow(QMainWindow):
    def _save_latest_result_to_library(self) -> None:
        entry = self._latest_result_entry
        if entry is None:
            return
        if self._task_thread is not None and self._task_thread.isRunning():
            return
        self.footer_label.setText("Saving to knowledge library...")
        self._task_thread = WorkflowTaskThread(
            lambda progress: self.workflow.save_result_to_library(entry)
        )
        self._task_thread.completed.connect(self._on_save_to_library_completed)
        self._task_thread.crashed.connect(self._on_save_to_library_crashed)
        self._task_thread.start()

    def _on_save_to_library_completed(self, state: OperationViewState) -> None:
        self._task_thread = None
        self.footer_label.setText("Saved to knowledge library.")
        self.result_inline.show_library_banner(
            "Source 已保存到知识库，当前 interpretation 已设为默认阅读视图。旧版本仍可在条目内恢复。"
        )

    def _on_save_to_library_crashed(self, message: str) -> None:
        self._task_thread = None
        self.footer_label.setText("Automatic platform detection and browser guidance are enabled.")
        QMessageBox.warning(self, "Save to library failed", message)

    def _restore_library_interpretation(self, entry_id: str, interpretation_id: str) -> None:
        if self._task_thread is not None and self._task_thread.isRunning():
            return
        self.footer_label.setText("Restoring interpretation...")
        self._task_thread = WorkflowTaskThread(
            lambda progress: self.workflow.restore_library_interpretation(entry_id, interpretation_id)
        )
        self._task_thread.completed.connect(self._on_restore_library_interpretation_completed)
        self._task_thread.crashed.connect(self._on_restore_library_interpretation_crashed)
        self._task_thread.start()

    def _on_restore_library_interpretation_completed(self, state: OperationViewState) -> None:
        self._task_thread = None
        self.footer_label.setText("Interpretation restored.")

    def _on_restore_library_interpretation_crashed(self, message: str) -> None:
        self._task_thread = None
        self.footer_label.setText("Automatic platform detection and browser guidance are enabled.")
        QMessageBox.warning(self, "Restore failed", message)
```

- [ ] **Step 4: Re-run the targeted tests and verify they pass**

Run: `python -m pytest tests/unit/test_main_window.py -k "save_latest_result_to_library or restore_library_interpretation" -q`

Expected: PASS

- [ ] **Step 5: Commit the threaded GUI flow**

```bash
git add src/windows_client/gui/main_window.py tests/unit/test_main_window.py
git commit -m "feat: wire knowledge library save and restore flows"
```

### Task 6: Run the focused verification suites and fix regressions

**Files:**
- Test: `tests/unit/test_library_store.py`
- Test: `tests/unit/test_service.py`
- Test: `tests/unit/test_workflow.py`
- Test: `tests/unit/test_inline_result_view.py`
- Test: `tests/unit/test_main_window.py`

- [ ] **Step 1: Run the new storage tests**

Run: `python -m pytest tests/unit/test_library_store.py -q`

Expected: PASS

- [ ] **Step 2: Run the integration-adjacent unit tests**

Run: `python -m pytest tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`

Expected: PASS

- [ ] **Step 3: If regressions appear, fix the smallest issue and re-run until green**

Run: `python -m pytest tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py -q`

Expected: PASS with no unexpected failures in touched areas

- [ ] **Step 4: Commit the verified vertical slice**

```bash
git add src/windows_client/app/library_store.py src/windows_client/app/service.py src/windows_client/app/workflow.py src/windows_client/app/view_models.py src/windows_client/gui/inline_result_view.py src/windows_client/gui/library_panel.py src/windows_client/gui/main_window.py tests/unit/test_library_store.py tests/unit/test_service.py tests/unit/test_workflow.py tests/unit/test_inline_result_view.py tests/unit/test_main_window.py
git commit -m "feat: add source-centric knowledge library loop"
```

---

## Spec Coverage Check

- Result-page `保存进知识库` action: covered by Task 3 and Task 5.
- Source-centric `LibraryEntry` model: covered by Task 1.
- Repeat save replaces current interpretation and trashes previous current: covered by Task 1.
- Image-first detail: covered by Task 4.
- Entry-local restore: covered by Task 1, Task 4, and Task 5.
- Reuse existing `insight_card.png` when present without blocking save: covered by Task 1 and Task 4.
- Keep job workspace intact: preserved by architecture and file map; no task rewrites result workspace.

## Handoff Notes

- Keep v1 Windows-only. Do not pull API server or WSL generation changes into this pass.
- Prefer one small `library_store.py` file over prematurely splitting repository/models/helpers.
- Do not redesign the whole app shell. A dialog-based library is sufficient for the first closed loop.
- Use snapshot semantics, not symbolic pointers back to processed jobs.
- If restore completes while the library dialog is open, refresh the dialog contents rather than rebuilding the whole main-window stack.
