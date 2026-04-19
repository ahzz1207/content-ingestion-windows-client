import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.app.library_store import LibraryStore


class _Entry:
    def __init__(
        self,
        *,
        job_dir: Path,
        job_id: str,
        source_url: str | None,
        canonical_url: str | None = None,
    ) -> None:
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
                "content_type": "html",
                "collected_at": "2026-04-07T18:32:00+08:00",
            },
            "structured_result": {
                "summary": {"headline": "Headline", "short_text": "Short"},
                "product_view": {"layout": "analysis_brief", "title": "Headline", "sections": []},
                "editorial": {
                    "resolved_reading_goal": "argument",
                    "resolved_domain_template": "macro_business",
                    "route_key": "argument.macro_business",
                },
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
        self.assertEqual(saved.source.collection_mode, "browser")
        self.assertEqual(saved.source.content_type, "html")
        self.assertEqual(saved.source.job_snapshot.saved_from_job_id, "job-1")
        self.assertEqual(saved.source.job_snapshot.normalized_markdown_path, Path("source/normalized.md"))
        self.assertEqual(saved.source.job_snapshot.normalized_json_path, Path("source/normalized.json"))
        self.assertEqual(saved.source.job_snapshot.metadata_path, Path("source/metadata.json"))
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
        self.assertGreaterEqual(restored.updated_at, saved.updated_at)

    def test_restore_rejects_interpretation_that_is_not_trashed(self) -> None:
        saved = self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))

        with self.assertRaises(WindowsClientError) as ctx:
            self.store.restore_interpretation(
                entry_id=saved.entry_id,
                interpretation_id=saved.current_interpretation.interpretation_id,
            )

        self.assertEqual(ctx.exception.code, "library_interpretation_not_trashed")

    def test_save_without_insight_card_still_persists_entry(self) -> None:
        entry = self._make_processed_entry("job-1", "https://example.com/a", with_image=False)

        saved = self.store.save_entry(entry)

        self.assertEqual(saved.current_interpretation.image_summary_asset, None)
        self.assertEqual(saved.current_interpretation.saved_from_job_id, "job-1")

    def test_save_entry_preserves_normalized_only_interpretation_payload(self) -> None:
        entry = self._make_processed_entry("job-1", "https://example.com/a")
        entry.details.pop("structured_result", None)
        entry.details.pop("product_view", None)
        entry.details["normalized"]["asset"] = {
            "result": {
                "summary": {"headline": "Normalized headline", "short_text": "Normalized short text"},
                "product_view": {
                    "layout": "analysis_brief",
                    "hero": {"title": "Normalized hero", "dek": "Normalized dek"},
                    "sections": [
                        {
                            "id": "section-1",
                            "title": "Normalized section",
                            "priority": 1,
                            "blocks": [{"type": "paragraph", "text": "Normalized paragraph."}],
                        }
                    ],
                },
            }
        }

        saved = self.store.save_entry(entry)

        # summary_headline/short_text now prefer the new product_view.hero
        # fields (short label + mode-specific dek) over the legacy
        # summary.headline/short_text. The legacy fields remain available
        # in the raw payload as a fallback for callers that need them.
        self.assertEqual(saved.current_interpretation.summary_headline, "Normalized hero")
        self.assertEqual(saved.current_interpretation.summary_short_text, "Normalized dek")
        self.assertEqual(saved.current_interpretation.payload["product_view"]["hero"]["title"], "Normalized hero")
        self.assertEqual(saved.current_interpretation.payload["structured_result"]["summary"]["headline"], "Normalized headline")

    def test_source_key_prefers_canonical_url_over_source_url(self) -> None:
        saved = self.store.save_entry(
            self._make_processed_entry(
                "job-1",
                "https://example.com/source",
                canonical_url="https://example.com/canonical",
            )
        )

        self.assertEqual(saved.source_key, "https://example.com/canonical")

    def test_source_key_uses_source_url_when_canonical_url_missing(self) -> None:
        saved = self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/source"))

        self.assertEqual(saved.source_key, "https://example.com/source")

    def test_source_key_falls_back_to_normalized_markdown_hash_when_urls_missing(self) -> None:
        saved = self.store.save_entry(
            self._make_processed_entry(
                "job-1",
                source_url=None,
                canonical_url=None,
            )
        )

        self.assertTrue(saved.source_key.startswith("sha1:"))

    def test_source_key_falls_back_to_job_id_when_urls_and_markdown_missing(self) -> None:
        saved = self.store.save_entry(
            self._make_processed_entry(
                "job-1",
                source_url=None,
                canonical_url=None,
                with_markdown=False,
            )
        )

        self.assertEqual(saved.source_key, "job:job-1")
        self.assertEqual(saved.source.job_snapshot.normalized_markdown_path, None)

    def test_new_entry_id_skips_existing_numbering_gaps_and_collisions(self) -> None:
        library_entries = self.shared_root / "library" / "entries"
        (library_entries / "lib_0001").mkdir(parents=True)
        (library_entries / "lib_0003").mkdir(parents=True)

        saved = self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))

        self.assertEqual(saved.entry_id, "lib_0002")

    def test_list_entries_skips_corrupt_entry_manifest(self) -> None:
        saved = self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))
        corrupt_dir = self.shared_root / "library" / "entries" / "lib_9999"
        corrupt_dir.mkdir(parents=True)
        (corrupt_dir / "entry.json").write_text("{not-json", encoding="utf-8")

        entries = self.store.list_entries()

        self.assertEqual([entry.entry_id for entry in entries], [saved.entry_id])

    def test_save_entry_succeeds_when_unrelated_entry_manifest_is_corrupt(self) -> None:
        self.store.save_entry(self._make_processed_entry("job-1", "https://example.com/a"))
        corrupt_dir = self.shared_root / "library" / "entries" / "lib_9999"
        corrupt_dir.mkdir(parents=True)
        (corrupt_dir / "entry.json").write_text("{not-json", encoding="utf-8")

        saved = self.store.save_entry(self._make_processed_entry("job-2", "https://example.com/b"))

        self.assertEqual(saved.source_key, "https://example.com/b")

    def _make_processed_entry(
        self,
        job_id: str,
        source_url: str | None,
        canonical_url: str | None = None,
        with_image: bool = True,
        with_markdown: bool = True,
    ) -> _Entry:
        job_dir = self.shared_root / "processed" / job_id
        (job_dir / "analysis" / "llm").mkdir(parents=True, exist_ok=True)
        (job_dir / "metadata.json").write_text("{}", encoding="utf-8")
        (job_dir / "normalized.json").write_text("{}", encoding="utf-8")
        if with_markdown:
            (job_dir / "normalized.md").write_text("# Headline\n\nBody", encoding="utf-8")
        (job_dir / "analysis" / "llm" / "analysis_result.json").write_text("{}", encoding="utf-8")
        if with_image:
            (job_dir / "analysis" / "insight_card.png").write_bytes(b"png")
        return _Entry(
            job_dir=job_dir,
            job_id=job_id,
            source_url=source_url,
            canonical_url=canonical_url,
        )
