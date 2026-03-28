import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.api.job_manager import JobManager
from windows_client.job_exporter.models import ExportResult


class _FakeService:
    def __init__(self, *, shared_root: Path) -> None:
        self.shared_root = shared_root
        self.calls: list[dict[str, object]] = []

    def export_url_job(
        self,
        *,
        url: str,
        shared_root: Path | None = None,
        content_type: str | None = None,
        platform: str | None = None,
        video_download_mode: str | None = None,
    ) -> ExportResult:
        self.calls.append(
            {
                "url": url,
                "shared_root": shared_root,
                "content_type": content_type,
                "platform": platform,
                "video_download_mode": video_download_mode,
            }
        )
        job_dir = (shared_root or self.shared_root) / "incoming" / "job123"
        job_dir.mkdir(parents=True, exist_ok=True)
        payload_path = job_dir / f"payload.{content_type or 'html'}"
        payload_path.write_text("<html><body>demo</body></html>", encoding="utf-8")
        metadata_path = job_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "job_id": "job123",
                    "source_url": url,
                    "platform": platform or "generic",
                    "content_type": content_type or "html",
                    "collected_at": "2026-03-26T12:00:00+08:00",
                }
            ),
            encoding="utf-8",
        )
        ready_path = job_dir / "READY"
        ready_path.write_text("", encoding="utf-8")
        return ExportResult(
            job_id="job123",
            job_dir=job_dir,
            payload_path=payload_path,
            metadata_path=metadata_path,
            ready_path=ready_path,
        )


class JobManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.shared_root = Path(self.temp_dir.name) / "shared_inbox"
        self.service = _FakeService(shared_root=self.shared_root)
        self.manager = JobManager(service=self.service, shared_inbox_root=self.shared_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_submit_url_delegates_to_service_export_and_returns_payload_paths(self) -> None:
        result = self.manager.submit_url(
            url="https://example.com/article",
            platform="generic",
            video_download_mode="audio",
        )

        self.assertEqual(result.job_id, "job123")
        self.assertEqual(result.status, "queued")
        self.assertTrue(result.payload_path.exists())
        self.assertTrue(result.metadata_path.exists())
        self.assertTrue(result.ready_path.exists())
        self.assertEqual(self.service.calls[0]["shared_root"], self.shared_root)
        self.assertEqual(self.service.calls[0]["url"], "https://example.com/article")

    def test_submit_url_defaults_video_download_mode_to_audio(self) -> None:
        self.manager.submit_url(url="https://example.com/video")

        self.assertEqual(self.service.calls[0]["video_download_mode"], "audio")

    def test_list_jobs_filters_multiple_statuses(self) -> None:
        self._write_job("incoming", "job-queued", source_url="https://example.com/queued")
        self._write_job("processing", "job-processing", source_url="https://example.com/processing")
        self._write_processed_job("job-completed")
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="boom")

        result = self.manager.list_jobs(statuses=["queued", "processing"], limit=10)

        found = {(item.job_id, item.status) for item in result.items}
        self.assertEqual(result.total, 2)
        self.assertEqual(found, {("job-queued", "queued"), ("job-processing", "processing")})

    def test_list_result_cards_exposes_completed_and_failed_cards(self) -> None:
        self._write_processed_job("job-completed")
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="processor exploded")

        result = self.manager.list_result_cards(statuses=["completed", "failed"], limit=10)

        self.assertEqual(result.total, 2)
        completed = next(item for item in result.items if item.job_id == "job-completed")
        failed = next(item for item in result.items if item.job_id == "job-failed")
        assert completed.result_card is not None
        assert failed.failure_card is not None
        self.assertEqual(completed.result_card["headline"], "Structured headline")
        self.assertEqual(completed.result_card["verification_signal"], "supported")
        self.assertIsNotNone(completed.result_card["coverage_warning"])
        self.assertEqual(failed.failure_card["error"], "processor exploded")

    def test_get_job_result_returns_completed_payload(self) -> None:
        self._write_processed_job("job-completed")

        result = self.manager.get_job_result("job-completed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.source_metadata["content_shape"], "article")
        self.assertIn("Structured headline", result.normalized_markdown or "")
        self.assertEqual(result.insight_brief["hero"]["title"], "Structured headline")

    def test_get_job_result_returns_processing_status_for_unready_jobs(self) -> None:
        self._write_job("processing", "job-processing", source_url="https://example.com/processing")

        result = self.manager.get_job_result("job-processing")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "processing")
        self.assertFalse(result.structured_result)

    def test_list_result_cards_treats_incomplete_processed_jobs_as_processing(self) -> None:
        self._write_incomplete_processed_job("job-half-baked")

        result = self.manager.list_result_cards(statuses=["completed"], limit=10)

        self.assertEqual(result.total, 1)
        card = result.items[0]
        self.assertEqual(card.job_id, "job-half-baked")
        self.assertEqual(card.status, "processing")
        self.assertEqual(card.analysis_state, "processing")
        self.assertIsNone(card.result_card)

    def test_archive_job_moves_job_to_archived_directory(self) -> None:
        self._write_processed_job("job-completed")

        result = self.manager.archive_job("job-completed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "completed")
        self.assertFalse((self.shared_root / "processed" / "job-completed").exists())
        self.assertTrue((self.shared_root / "archived" / "job-completed").exists())

    def test_archive_job_returns_none_for_unknown_job(self) -> None:
        result = self.manager.archive_job("missing-job")

        self.assertIsNone(result)

    def test_archive_job_is_idempotent_for_already_archived_job(self) -> None:
        self._write_processed_job("job-completed")
        self.manager.archive_job("job-completed")

        result = self.manager.archive_job("job-completed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "archived")
        self.assertTrue((self.shared_root / "archived" / "job-completed").exists())

    def test_archived_jobs_excluded_from_default_list(self) -> None:
        self._write_processed_job("job-completed")
        self.manager.archive_job("job-completed")

        result = self.manager.list_jobs()

        self.assertEqual(result.total, 0)

    def test_archived_jobs_retrievable_with_explicit_status_filter(self) -> None:
        self._write_processed_job("job-completed")
        self.manager.archive_job("job-completed")

        result = self.manager.list_jobs(statuses=["archived"])

        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].status, "archived")

    def test_archived_completed_job_result_is_readable(self) -> None:
        self._write_processed_job("job-completed")
        self.manager.archive_job("job-completed")

        result = self.manager.get_job_result("job-completed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "archived")
        self.assertEqual(result.insight_brief["hero"]["title"], "Structured headline")

    def test_archived_completed_job_result_card_is_populated(self) -> None:
        self._write_processed_job("job-completed")
        self.manager.archive_job("job-completed")

        result = self.manager.list_result_cards(statuses=["archived"], limit=10)

        self.assertEqual(result.total, 1)
        card = result.items[0]
        self.assertEqual(card.status, "archived")
        self.assertIsNotNone(card.result_card)
        assert card.result_card is not None
        self.assertEqual(card.result_card["headline"], "Structured headline")

    def test_archived_failed_job_result_card_preserves_error(self) -> None:
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="boom")
        self.manager.archive_job("job-failed")

        result = self.manager.list_result_cards(statuses=["archived"], limit=10)

        self.assertEqual(result.total, 1)
        card = result.items[0]
        self.assertEqual(card.status, "archived")
        self.assertIsNone(card.result_card)
        self.assertIsNotNone(card.failure_card)
        assert card.failure_card is not None
        self.assertEqual(card.failure_card["error"], "boom")

    def test_archived_failed_job_result_detail_preserves_error(self) -> None:
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="boom")
        self.manager.archive_job("job-failed")

        result = self.manager.get_job_result("job-failed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "archived")
        self.assertEqual(result.error, "boom")

    def test_get_job_result_returns_processing_for_incomplete_processed_jobs(self) -> None:
        self._write_incomplete_processed_job("job-half-baked")

        result = self.manager.get_job_result("job-half-baked")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "processing")
        self.assertEqual(result.analysis_state, "processing")
        self.assertFalse(result.structured_result)

    def test_get_job_result_includes_capture_artifacts_from_capture_manifest_fallback(self) -> None:
        self._write_processed_job_without_normalized_capture("job-with-thumbnail")

        result = self.manager.get_job_result("job-with-thumbnail")

        self.assertIsNotNone(result)
        assert result is not None
        kinds = {item["kind"] for item in result.available_artifacts}
        self.assertIn("capture_manifest", kinds)
        self.assertIn("thumbnail", kinds)

    def test_sample_processed_job_builds_result_card_from_real_fixture(self) -> None:
        fixture_root = PROJECT_ROOT / "data" / "shared_inbox"
        fixture_job_id = "20260327_001844_af7078"
        fixture_job_dir = fixture_root / "processed" / fixture_job_id
        if not fixture_job_dir.exists():
            self.skipTest("sample processed job fixture is unavailable")

        fixture_manager = JobManager(service=self.service, shared_inbox_root=fixture_root)
        result = fixture_manager.list_result_cards(statuses=["completed"], limit=20)

        fixture_card = next((item for item in result.items if item.job_id == fixture_job_id), None)
        self.assertIsNotNone(fixture_card)
        assert fixture_card is not None
        assert fixture_card.result_card is not None
        self.assertTrue(fixture_card.result_card["headline"])
        self.assertLessEqual(len(fixture_card.result_card["quick_takeaways"]), 3)

    def _write_job(self, dirname: str, job_id: str, *, source_url: str, error: str | None = None) -> None:
        job_dir = self.shared_root / dirname / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        if dirname in {"incoming", "processing"}:
            (job_dir / "payload.html").write_text("<html></html>", encoding="utf-8")
        metadata = {
            "job_id": job_id,
            "source_url": source_url,
            "final_url": source_url,
            "platform": "generic",
            "content_type": "html",
            "collection_mode": "http",
            "collected_at": "2026-03-26T12:00:00+08:00",
            "title_hint": f"title-{job_id}",
            "author_hint": "Author",
            "published_at_hint": "2026-03-25",
        }
        (job_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        if dirname == "failed" and error:
            (job_dir / "error.json").write_text(json.dumps({"message": error}), encoding="utf-8")

    def _write_processed_job(self, job_id: str) -> None:
        job_dir = self.shared_root / "processed" / job_id
        (job_dir / "analysis" / "llm").mkdir(parents=True, exist_ok=True)
        (job_dir / "analysis" / "transcript").mkdir(parents=True, exist_ok=True)
        metadata = {
            "job_id": job_id,
            "source_url": "https://example.com/completed",
            "final_url": "https://example.com/completed",
            "platform": "generic",
            "content_type": "md",
            "collection_mode": "http",
            "collected_at": "2026-03-26T12:00:00+08:00",
        }
        (job_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (job_dir / "status.json").write_text(json.dumps({"stage": "completed"}), encoding="utf-8")
        (job_dir / "normalized.md").write_text("# Structured headline\n\nA readable markdown body.", encoding="utf-8")
        structured_result = {
            "summary": {
                "headline": "Structured headline",
                "short_text": "A concise one-line take.",
            },
            "key_points": [
                {"title": "Point one", "details": "Why point one matters."},
                {"title": "Point two", "details": "Why point two matters."},
                {"title": "Point three", "details": "Why point three matters."},
                {"title": "Point four", "details": "Why point four matters."},
            ],
            "analysis_items": [
                {
                    "kind": "interpretation",
                    "statement": "Interpretation",
                }
            ],
            "verification_items": [
                {
                    "claim": "Claim one",
                    "status": "supported",
                    "rationale": "Evidence lines up.",
                    "evidence_segment_ids": ["seg-1"],
                }
            ],
            "synthesis": {
                "final_answer": "Bottom line for the digest.",
                "open_questions": ["Open question"],
                "next_steps": ["Next step"],
            },
            "warnings": [{"message": "Structured warning"}],
        }
        normalized = {
            "job_id": job_id,
            "status": "success",
            "content_type": "md",
            "asset": {
                "source_platform": "generic",
                "source_url": "https://example.com/completed",
                "canonical_url": "https://example.com/completed",
                "content_shape": "article",
                "title": "Structured headline",
                "author": "Author",
                "published_at": "2026-03-25T12:00:00",
                "result": structured_result,
            },
            "metadata": {
                "handoff": {
                    "content_shape": "article",
                    "collection_mode": "http",
                },
                "capture": {
                    "artifacts": [
                        {
                            "path": "attachments/source/raw.html",
                            "role": "raw_capture",
                            "media_type": "text/html",
                            "description": "Original capture",
                        }
                    ]
                },
                "media_processing": {
                    "warnings": ["Media warning"],
                },
                "llm_processing": {
                    "status": "pass",
                    "warnings": ["LLM warning"],
                },
            },
        }
        (job_dir / "normalized.json").write_text(json.dumps(normalized), encoding="utf-8")
        (job_dir / "analysis" / "llm" / "text_request.json").write_text(
            json.dumps(
                {
                    "evidence_segments": [
                        {"id": "seg-1", "kind": "transcript", "text": "Evidence one", "end_ms": 1000},
                        {"id": "seg-2", "kind": "transcript", "text": "Evidence two", "end_ms": 2000},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "analysis" / "transcript" / "transcript.json").write_text(
            json.dumps(
                {
                    "segments": [
                        {"end": 1},
                        {"end": 2},
                        {"end": 3},
                        {"end": 4},
                    ]
                }
            ),
            encoding="utf-8",
        )

    def _write_processed_job_without_normalized_capture(self, job_id: str) -> None:
        job_dir = self.shared_root / "processed" / job_id
        (job_dir / "analysis" / "llm").mkdir(parents=True, exist_ok=True)
        (job_dir / "attachments" / "video").mkdir(parents=True, exist_ok=True)
        metadata = {
            "job_id": job_id,
            "source_url": "https://example.com/video",
            "final_url": "https://example.com/video",
            "platform": "bilibili",
            "content_type": "html",
            "collection_mode": "http",
            "collected_at": "2026-03-26T12:00:00+08:00",
        }
        (job_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (job_dir / "status.json").write_text(json.dumps({"stage": "completed"}), encoding="utf-8")
        (job_dir / "normalized.md").write_text("# Headline\n\nBody.", encoding="utf-8")
        normalized = {
            "job_id": job_id,
            "status": "success",
            "content_type": "html",
            "asset": {
                "source_platform": "bilibili",
                "source_url": "https://example.com/video",
                "canonical_url": "https://example.com/video",
                "content_shape": "video",
                "title": "Headline",
                "author": "Author",
                "published_at": "2026-03-25T12:00:00",
                "result": {
                    "summary": {
                        "headline": "Headline",
                        "short_text": "Short text",
                    }
                },
            },
            "metadata": {
                "llm_processing": {
                    "status": "pass",
                }
            },
        }
        (job_dir / "normalized.json").write_text(json.dumps(normalized), encoding="utf-8")
        (job_dir / "analysis" / "llm" / "analysis_result.json").write_text(json.dumps({"status": "pass"}), encoding="utf-8")
        (job_dir / "attachments" / "video" / "video.jpg").write_bytes(b"jpg")
        (job_dir / "capture_manifest.json").write_text(
            json.dumps(
                {
                    "artifacts": [
                        {
                            "path": "attachments/video/video.jpg",
                            "role": "thumbnail",
                            "media_type": "image/jpeg",
                            "description": "Video thumbnail",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def _write_incomplete_processed_job(self, job_id: str) -> None:
        job_dir = self.shared_root / "processed" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "job_id": job_id,
            "source_url": "https://example.com/incomplete",
            "final_url": "https://example.com/incomplete",
            "platform": "generic",
            "content_type": "html",
            "collection_mode": "http",
            "collected_at": "2026-03-26T12:00:00+08:00",
            "title_hint": "Incomplete title",
            "author_hint": "Author",
            "published_at_hint": "2026-03-25",
        }
        (job_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
