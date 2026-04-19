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
    collection_mode: str | None
    content_type: str | None
    job_snapshot: "LibraryJobSnapshot"


@dataclass(slots=True)
class LibraryJobSnapshot:
    saved_from_job_id: str
    normalized_markdown_path: Path | None
    normalized_json_path: Path | None
    metadata_path: Path | None


@dataclass(slots=True)
class SourceSnapshotPaths:
    normalized_markdown_path: Path | None
    normalized_json_path: Path | None
    metadata_path: Path | None


@dataclass(slots=True)
class LibraryEntryView:
    entry_id: str
    source_key: str
    updated_at: str
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
            try:
                entry_dir.mkdir(parents=True, exist_ok=True)
                source_snapshot = self._copy_source_snapshot(entry, entry_dir)
            except Exception as exc:
                shutil.rmtree(entry_dir, ignore_errors=True)
                raise WindowsClientError(
                    "library_source_snapshot_failed",
                    f"failed to create source snapshot for {entry.job_id}",
                    stage="library",
                    details={"job_id": entry.job_id},
                    cause=exc,
                ) from exc
            manifest = {
                "entry_id": entry_id,
                "source_key": source_key,
                "created_at": self._now_iso(),
                "updated_at": self._now_iso(),
                "source": self._source_payload(entry, source_snapshot),
                "current_interpretation_id": None,
                "interpretations": [],
            }
        else:
            manifest = self._read_manifest(entry_dir)

        manifest = json.loads(json.dumps(manifest))
        current_id = manifest.get("current_interpretation_id")
        now = self._now_iso()
        for interpretation in manifest.get("interpretations", []):
            if interpretation.get("interpretation_id") == current_id:
                interpretation["state"] = "trashed"
                interpretation["trashed_at"] = now
                interpretation["trash_reason"] = "replaced_by_new_save"

        try:
            new_interpretation = self._interpretation_payload(entry, entry_dir, manifest)
        except Exception as exc:
            raise WindowsClientError(
                "library_interpretation_snapshot_failed",
                f"failed to create interpretation snapshot for {entry.job_id}",
                stage="library",
                details={"job_id": entry.job_id},
                cause=exc,
            ) from exc

        manifest["interpretations"].append(new_interpretation)
        manifest["current_interpretation_id"] = new_interpretation["interpretation_id"]
        manifest["updated_at"] = now
        self._write_manifest(entry_dir, manifest)
        self._write_index()
        return self.get_entry(manifest["entry_id"])

    def restore_interpretation(self, *, entry_id: str, interpretation_id: str) -> LibraryEntryView:
        entry_dir = self.entries_root / entry_id
        if not entry_dir.exists():
            raise WindowsClientError(
                "library_entry_missing",
                f"library entry not found: {entry_id}",
                stage="library",
                details={"entry_id": entry_id},
            )

        manifest = self._read_manifest(entry_dir)
        current_id = manifest.get("current_interpretation_id")
        now = self._now_iso()
        found = False
        target_is_trashed = False

        for interpretation in manifest.get("interpretations", []):
            if interpretation.get("interpretation_id") == interpretation_id:
                found = True
                target_is_trashed = interpretation.get("state") == "trashed"

        if not found:
            raise WindowsClientError(
                "library_interpretation_missing",
                f"interpretation not found: {interpretation_id}",
                stage="library",
                details={"entry_id": entry_id, "interpretation_id": interpretation_id},
            )

        if not target_is_trashed:
            raise WindowsClientError(
                "library_interpretation_not_trashed",
                f"interpretation is not trashed: {interpretation_id}",
                stage="library",
                details={"entry_id": entry_id, "interpretation_id": interpretation_id},
            )

        for interpretation in manifest.get("interpretations", []):
            if interpretation.get("interpretation_id") == current_id:
                interpretation["state"] = "trashed"
                interpretation["trashed_at"] = now
                interpretation["trash_reason"] = "replaced_by_restore"
            if interpretation.get("interpretation_id") == interpretation_id:
                interpretation["state"] = "current"
                interpretation["trashed_at"] = None
                interpretation["trash_reason"] = None

        manifest["current_interpretation_id"] = interpretation_id
        manifest["updated_at"] = now
        self._write_manifest(entry_dir, manifest)
        self._write_index()
        return self.get_entry(entry_id)

    def get_entry(self, entry_id: str) -> LibraryEntryView:
        manifest = self._read_manifest(self.entries_root / entry_id)
        current_id = manifest.get("current_interpretation_id")
        interpretations = [self._view_interpretation(item) for item in manifest.get("interpretations", [])]
        current = next((item for item in interpretations if item.interpretation_id == current_id), None)
        if current is None:
            raise WindowsClientError(
                "library_current_interpretation_missing",
                f"current interpretation not found for entry: {entry_id}",
                stage="library",
                details={"entry_id": entry_id},
            )
        source = manifest.get("source") or {}
        return LibraryEntryView(
            entry_id=manifest["entry_id"],
            source_key=manifest["source_key"],
            updated_at=str(manifest.get("updated_at") or ""),
            source=LibrarySource(
                title=source.get("title"),
                source_url=source.get("source_url"),
                canonical_url=source.get("canonical_url"),
                platform=source.get("platform"),
                author=source.get("author"),
                published_at=source.get("published_at"),
                captured_at=source.get("captured_at"),
                collection_mode=source.get("collection_mode"),
                content_type=source.get("content_type"),
                job_snapshot=self._view_job_snapshot(source.get("job_snapshot")),
            ),
            current_interpretation=current,
            trashed_interpretations=[item for item in interpretations if item.state == "trashed"],
        )

    def list_entries(self) -> list[LibraryEntryView]:
        if not self.entries_root.exists():
            return []
        entries: list[LibraryEntryView] = []
        for path in sorted(self.entries_root.iterdir()):
            if not path.is_dir() or not (path / "entry.json").exists():
                continue
            try:
                entries.append(self.get_entry(path.name))
            except Exception:
                continue
        return entries

    def _find_entry_dir(self, source_key: str) -> Path | None:
        if not self.entries_root.exists():
            return None
        for path in self.entries_root.iterdir():
            if not path.is_dir():
                continue
            entry_file = path / "entry.json"
            if not entry_file.exists():
                continue
            try:
                manifest = self._read_manifest(path)
            except Exception:
                continue
            if manifest.get("source_key") == source_key:
                return path
        return None

    def _copy_source_snapshot(self, entry: ResultWorkspaceEntry, entry_dir: Path) -> SourceSnapshotPaths:
        source_dir = entry_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = self._copy_if_exists(entry.metadata_path, source_dir / "metadata.json")
        normalized_json_path = self._copy_if_exists(entry.normalized_json_path, source_dir / "normalized.json")
        normalized_markdown_path = self._copy_if_exists(entry.normalized_md_path, source_dir / "normalized.md")
        return SourceSnapshotPaths(
            normalized_markdown_path=normalized_markdown_path.relative_to(entry_dir)
            if normalized_markdown_path is not None
            else None,
            normalized_json_path=normalized_json_path.relative_to(entry_dir)
            if normalized_json_path is not None
            else None,
            metadata_path=metadata_path.relative_to(entry_dir) if metadata_path is not None else None,
        )

    def _interpretation_payload(
        self,
        entry: ResultWorkspaceEntry,
        entry_dir: Path,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        interpretation_id = self._next_interpretation_id(entry, manifest)
        destination_dir = entry_dir / "interpretations" / interpretation_id
        assets_dir = destination_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        image_path = None
        raw_image = entry.details.get("insight_card_path") if isinstance(entry.details, dict) else None
        if isinstance(raw_image, Path) and raw_image.exists():
            image_path = assets_dir / "insight_card.png"
            shutil.copy2(raw_image, image_path)

        details = entry.details if isinstance(entry.details, dict) else {}
        normalized = details.get("normalized") if isinstance(details.get("normalized"), dict) else {}
        normalized_asset = normalized.get("asset") if isinstance(normalized.get("asset"), dict) else {}
        normalized_result = normalized_asset.get("result") if isinstance(normalized_asset.get("result"), dict) else {}
        structured = details.get("structured_result") if isinstance(details.get("structured_result"), dict) else {}
        if not structured and normalized_result:
            structured = normalized_result
        editorial = structured.get("editorial") if isinstance(structured.get("editorial"), dict) else {}
        summary = structured.get("summary") if isinstance(structured.get("summary"), dict) else {}
        product_view = details.get("product_view") if isinstance(details.get("product_view"), dict) else {}
        normalized_metadata = normalized.get("metadata") if isinstance(normalized.get("metadata"), dict) else {}
        llm_processing = normalized_metadata.get("llm_processing") if isinstance(normalized_metadata.get("llm_processing"), dict) else {}

        payload = {
            "interpretation_id": interpretation_id,
            "state": "current",
            "saved_from_job_id": entry.job_id,
            "saved_at": self._now_iso(),
            "trashed_at": None,
            "trash_reason": None,
            "route_key": llm_processing.get("route_key") or editorial.get("route_key") or "argument.generic",
            "summary": summary,
            "product_view": product_view or structured.get("product_view") or {},
            "editorial": editorial,
            "structured_result": structured,
            "assets": [],
        }
        if image_path is not None:
            payload["assets"].append(
                {
                    "kind": "image_summary",
                    "path": str(image_path.relative_to(entry_dir)),
                }
            )

        (destination_dir / "interpretation.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def _source_payload(self, entry: ResultWorkspaceEntry, snapshot_paths: SourceSnapshotPaths) -> dict[str, Any]:
        metadata = entry.details.get("metadata") if isinstance(entry.details, dict) else {}
        return {
            "title": entry.title,
            "source_url": entry.source_url,
            "canonical_url": entry.canonical_url,
            "platform": entry.platform,
            "author": entry.author,
            "published_at": entry.published_at,
            "captured_at": metadata.get("collected_at") if isinstance(metadata, dict) else None,
            "collection_mode": metadata.get("collection_mode") if isinstance(metadata, dict) else None,
            "content_type": metadata.get("content_type") if isinstance(metadata, dict) else None,
            "job_snapshot": {
                "saved_from_job_id": entry.job_id,
                "normalized_markdown_path": str(snapshot_paths.normalized_markdown_path)
                if snapshot_paths.normalized_markdown_path is not None
                else None,
                "normalized_json_path": str(snapshot_paths.normalized_json_path)
                if snapshot_paths.normalized_json_path is not None
                else None,
                "metadata_path": str(snapshot_paths.metadata_path) if snapshot_paths.metadata_path is not None else None,
            },
        }

    def _source_key(self, entry: ResultWorkspaceEntry) -> str:
        if entry.canonical_url:
            return entry.canonical_url
        if entry.source_url:
            return entry.source_url
        if entry.normalized_md_path is not None and entry.normalized_md_path.exists():
            normalized_text = entry.normalized_md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            digest = hashlib.sha1(normalized_text.encode("utf-8")).hexdigest()
            return f"sha1:{digest}"
        return f"job:{entry.job_id}"

    def _view_interpretation(self, payload: dict[str, Any]) -> LibraryInterpretation:
        asset = None
        assets = payload.get("assets") or []
        if assets:
            asset_payload = assets[0]
            asset = LibraryAsset(
                kind=asset_payload.get("kind", "image_summary"),
                path=Path(asset_payload["path"]),
            )
        summary = payload.get("summary") or {}
        product_view = payload.get("product_view") if isinstance(payload.get("product_view"), dict) else {}
        product_hero = product_view.get("hero") if isinstance(product_view.get("hero"), dict) else {}
        product_title = str(product_hero.get("title") or "").strip() or None
        product_dek = str(product_hero.get("dek") or "").strip() or None
        return LibraryInterpretation(
            interpretation_id=payload["interpretation_id"],
            state=payload["state"],
            saved_from_job_id=payload["saved_from_job_id"],
            route_key=payload["route_key"],
            saved_at=payload["saved_at"],
            trashed_at=payload.get("trashed_at"),
            trash_reason=payload.get("trash_reason"),
            summary_headline=product_title or summary.get("headline"),
            summary_short_text=product_dek or summary.get("short_text"),
            image_summary_asset=asset,
            payload=payload,
        )

    def _view_job_snapshot(self, payload: Any) -> LibraryJobSnapshot:
        if not isinstance(payload, dict):
            return LibraryJobSnapshot(
                saved_from_job_id="",
                normalized_markdown_path=None,
                normalized_json_path=None,
                metadata_path=None,
            )
        return LibraryJobSnapshot(
            saved_from_job_id=str(payload.get("saved_from_job_id") or ""),
            normalized_markdown_path=Path(payload["normalized_markdown_path"])
            if payload.get("normalized_markdown_path")
            else None,
            normalized_json_path=Path(payload["normalized_json_path"])
            if payload.get("normalized_json_path")
            else None,
            metadata_path=Path(payload["metadata_path"]) if payload.get("metadata_path") else None,
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
        (self.library_root / "index.json").write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _next_entry_id(self) -> str:
        existing_numbers: set[int] = set()
        if self.entries_root.exists():
            for path in self.entries_root.iterdir():
                if not path.is_dir():
                    continue
                prefix, separator, suffix = path.name.partition("_")
                if prefix != "lib" or separator != "_" or not suffix.isdigit():
                    continue
                existing_numbers.add(int(suffix))

        next_number = 1
        while next_number in existing_numbers or (self.entries_root / f"lib_{next_number:04d}").exists():
            next_number += 1
        return f"lib_{next_number:04d}"

    def _next_interpretation_id(self, entry: ResultWorkspaceEntry, manifest: dict[str, Any]) -> str:
        existing = manifest.get("interpretations", [])
        return f"interp_{len(existing) + 1:04d}_{entry.job_id.replace('-', '_')}"

    def _copy_if_exists(self, src: Path | None, dest: Path) -> Path | None:
        if src is None or not src.exists():
            return None
        shutil.copy2(src, dest)
        return dest

    def _read_manifest(self, entry_dir: Path) -> dict[str, Any]:
        entry_file = entry_dir / "entry.json"
        if not entry_file.exists():
            raise WindowsClientError(
                "library_manifest_missing",
                f"library manifest not found: {entry_dir.name}",
                stage="library",
                details={"entry_id": entry_dir.name},
            )
        return json.loads(entry_file.read_text(encoding="utf-8"))

    def _write_manifest(self, entry_dir: Path, manifest: dict[str, Any]) -> None:
        (entry_dir / "entry.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()
