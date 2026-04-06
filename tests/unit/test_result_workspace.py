import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.result_workspace import _looks_unreadable_text, list_recent_results, load_job_result, load_latest_result
from windows_client.app.service import ReinterpretRequest, WindowsClientService
from windows_client.config.settings import Settings


class ResultWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.shared_root = Path(self.temp_dir.name) / "shared_inbox"
        (self.shared_root / "processed").mkdir(parents=True)
        (self.shared_root / "failed").mkdir(parents=True)
        (self.shared_root / "incoming").mkdir(parents=True)
        (self.shared_root / "processing").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_processed_job_result(self) -> None:
        job_dir = self.shared_root / "processed" / "job-123"
        job_dir.mkdir()
        (job_dir / "metadata.json").write_text(
            json.dumps({"job_id": "job-123", "source_url": "https://example.com/article"}),
            encoding="utf-8",
        )
        (job_dir / "normalized.json").write_text(
            json.dumps(
                {
                    "job_id": "job-123",
                    "asset": {
                        "source_platform": "generic",
                        "source_url": "https://example.com/article",
                        "canonical_url": "https://example.com/final",
                        "title": "Example title",
                        "author": "Example author",
                        "published_at": "2026-03-14T12:00:00",
                        "result": {
                            "summary": {
                                "headline": "Core takeaway",
                                "short_text": "A concise structured summary.",
                            },
                        }
                    },
                    "metadata": {
                        "llm_processing": {
                            "status": "pass",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "normalized.md").write_text(
            "# Example title\n\n- Platform: generic\n- Source URL: https://example.com/article\n\n---\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-123")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.state, "processed")
        self.assertEqual(result.title, "Example title")
        self.assertEqual(result.author, "Example author")
        self.assertEqual(result.summary, "Core takeaway: A concise structured summary.")
        self.assertEqual(result.preview_text, "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(result.analysis_state, "ready")

    def test_load_processed_job_result_preserves_product_view(self) -> None:
        job_dir = self.shared_root / "processed" / "job-product-view"
        job_dir.mkdir()
        product_view = {
            "hero": {
                "title": "Reader-first title",
                "dek": "Reader dek",
                "bottom_line": "Reader bottom line",
            },
            "sections": [
                {
                    "id": "takeaways",
                    "title": "Takeaways",
                    "kind": "analysis",
                    "priority": 1,
                    "collapsed_by_default": False,
                    "blocks": [
                        {"type": "paragraph", "text": "Render-ready paragraph."},
                    ],
                }
            ],
            "render_hints": {"layout_family": "analysis_brief"},
        }
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-product-view"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps(
                {
                    "job_id": "job-product-view",
                    "asset": {
                        "title": "Legacy title",
                        "result": {
                            "summary": {
                                "headline": "Legacy headline",
                                "short_text": "Legacy summary.",
                            },
                            "product_view": product_view,
                        },
                    },
                    "metadata": {"llm_processing": {"status": "pass"}},
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-product-view")

        self.assertIsNotNone(result)
        assert result is not None
        structured_result = result.details.get("structured_result", {})
        self.assertEqual(structured_result.get("product_view"), product_view)
        self.assertEqual(result.details.get("product_view"), product_view)

    def test_load_processed_job_result_follows_active_version_pointer(self) -> None:
        base_dir = self.shared_root / "processed" / "job-123"
        reinterpret_dir = self.shared_root / "processed" / "job-123--reinterpret-01"
        base_dir.mkdir()
        reinterpret_dir.mkdir()
        (base_dir / "active_version.json").write_text(
            json.dumps(
                {
                    "active_job_id": "job-123--reinterpret-01",
                    "version_ids": ["job-123", "job-123--reinterpret-01"],
                }
            ),
            encoding="utf-8",
        )
        for job_dir, job_id, title in (
            (base_dir, "job-123", "Base title"),
            (reinterpret_dir, "job-123--reinterpret-01", "Reinterpreted title"),
        ):
            (job_dir / "metadata.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
            (job_dir / "normalized.json").write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "asset": {
                            "title": title,
                            "result": {
                                "summary": {
                                    "headline": title,
                                    "short_text": "Summary text.",
                                }
                            },
                        },
                        "metadata": {"llm_processing": {"status": "pass"}},
                    }
                ),
                encoding="utf-8",
            )
            (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-123")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.job_id, "job-123--reinterpret-01")
        self.assertEqual(result.title, "Reinterpreted title")

    def test_reinterpret_result_creates_processed_version_and_updates_active_pointer(self) -> None:
        base_dir = self.shared_root / "processed" / "job-123"
        base_dir.mkdir()
        (base_dir / "metadata.json").write_text(
            json.dumps({"job_id": "job-123", "source_url": "https://example.com/article"}),
            encoding="utf-8",
        )
        (base_dir / "normalized.json").write_text(
            json.dumps(
                {
                    "job_id": "job-123",
                    "asset": {
                        "title": "Example title",
                        "source_url": "https://example.com/article",
                        "result": {
                            "summary": {
                                "headline": "Core takeaway",
                                "short_text": "A concise structured summary.",
                            }
                        },
                    },
                    "metadata": {"llm_processing": {"status": "pass"}},
                }
            ),
            encoding="utf-8",
        )
        (base_dir / "normalized.md").write_text("First paragraph.\n\nSecond paragraph.", encoding="utf-8")
        (base_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        service = WindowsClientService(
            settings=Settings(project_root=Path(self.temp_dir.name) / "project-root"),
            mock_collector=MagicMock(),
            url_collector=MagicMock(),
            browser_collector=MagicMock(),
            exporter=MagicMock(),
        )

        result = service.reinterpret_result(
            ReinterpretRequest(
                job_id="job-123",
                reading_goal="guide",
                domain_template="market-intel",
            ),
            shared_root=self.shared_root,
        )

        reinterpret_dir = self.shared_root / "processed" / "job-123--reinterpret-01"
        self.assertEqual(result.job_id, "job-123--reinterpret-01")
        self.assertTrue(reinterpret_dir.exists())
        self.assertEqual((reinterpret_dir / "normalized.md").read_text(encoding="utf-8"), "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(
            json.loads((base_dir / "active_version.json").read_text(encoding="utf-8")),
            {
                "active_job_id": "job-123--reinterpret-01",
                "version_ids": ["job-123", "job-123--reinterpret-01"],
            },
        )
        normalized = json.loads((reinterpret_dir / "normalized.json").read_text(encoding="utf-8"))
        self.assertEqual(normalized["job_id"], "job-123--reinterpret-01")
        self.assertEqual(normalized["metadata"]["reinterpretation"], {
            "status": "local_clone",
            "source_job_id": "job-123",
            "source_version_job_id": "job-123",
            "requested_reading_goal": "guide",
            "requested_domain_template": "market-intel",
        })
        active_result = load_job_result(self.shared_root, "job-123")
        self.assertIsNotNone(active_result)
        assert active_result is not None
        self.assertEqual(active_result.job_id, "job-123--reinterpret-01")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["status"], "local_clone")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["source_job_id"], "job-123")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["source_version_job_id"], "job-123")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["requested_reading_goal"], "guide")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["requested_domain_template"], "market-intel")
        self.assertEqual(normalized["metadata"]["llm_processing"], {"status": "pass"})
        self.assertNotIn("editorial", normalized["asset"]["result"])

    def test_list_recent_results_prefers_active_processed_version_and_hides_base_pointer_dir(self) -> None:
        base_dir = self.shared_root / "processed" / "job-family"
        active_dir = self.shared_root / "processed" / "job-family--reinterpret-01"
        base_dir.mkdir()
        active_dir.mkdir()
        (base_dir / "active_version.json").write_text(
            json.dumps(
                {
                    "active_job_id": "job-family--reinterpret-01",
                    "version_ids": ["job-family", "job-family--reinterpret-01"],
                }
            ),
            encoding="utf-8",
        )
        for job_dir, job_id, title in (
            (base_dir, "job-family", "Base"),
            (active_dir, "job-family--reinterpret-01", "Active"),
        ):
            (job_dir / "metadata.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
            (job_dir / "normalized.json").write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "asset": {"title": title, "result": {"summary": {"headline": title, "short_text": "summary"}}},
                        "metadata": {"llm_processing": {"status": "pass"}},
                    }
                ),
                encoding="utf-8",
            )
            (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        results = list_recent_results(self.shared_root, limit=10)

        processed_job_ids = [result.job_id for result in results if result.state == "processed"]
        self.assertEqual(processed_job_ids, ["job-family--reinterpret-01"])

    def test_load_latest_result_uses_active_processed_version_timestamp(self) -> None:
        base_dir = self.shared_root / "processed" / "job-family"
        active_dir = self.shared_root / "processed" / "job-family--reinterpret-01"
        failed_dir = self.shared_root / "failed" / "job-failed"
        base_dir.mkdir()
        active_dir.mkdir()
        failed_dir.mkdir()
        (base_dir / "active_version.json").write_text(
            json.dumps(
                {
                    "active_job_id": "job-family--reinterpret-01",
                    "version_ids": ["job-family", "job-family--reinterpret-01"],
                }
            ),
            encoding="utf-8",
        )
        for job_dir, job_id, title in (
            (base_dir, "job-family", "Base"),
            (active_dir, "job-family--reinterpret-01", "Active"),
        ):
            (job_dir / "metadata.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
            (job_dir / "normalized.json").write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "asset": {"title": title, "result": {"summary": {"headline": title, "short_text": "summary"}}},
                        "metadata": {"llm_processing": {"status": "pass"}},
                    }
                ),
                encoding="utf-8",
            )
            (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")
        (failed_dir / "metadata.json").write_text(json.dumps({"job_id": "job-failed"}), encoding="utf-8")
        (failed_dir / "error.json").write_text(json.dumps({"error_message": "failed"}), encoding="utf-8")
        (failed_dir / "status.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

        os = __import__("os")
        os.utime(base_dir, (100, 100))
        os.utime(active_dir, (300, 300))
        os.utime(failed_dir, (200, 200))

        result = load_latest_result(self.shared_root)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.job_id, "job-family--reinterpret-01")

    def test_reinterpret_result_from_selected_version_clones_that_version_not_current_active(self) -> None:
        base_dir = self.shared_root / "processed" / "job-123"
        reinterpret_one_dir = self.shared_root / "processed" / "job-123--reinterpret-01"
        reinterpret_two_dir = self.shared_root / "processed" / "job-123--reinterpret-02"
        base_dir.mkdir()
        reinterpret_one_dir.mkdir()
        reinterpret_two_dir.mkdir()
        (base_dir / "active_version.json").write_text(
            json.dumps(
                {
                    "active_job_id": "job-123--reinterpret-02",
                    "version_ids": ["job-123", "job-123--reinterpret-01", "job-123--reinterpret-02"],
                }
            ),
            encoding="utf-8",
        )
        for job_dir, job_id, title in (
            (base_dir, "job-123", "Base title"),
            (reinterpret_one_dir, "job-123--reinterpret-01", "Version one title"),
            (reinterpret_two_dir, "job-123--reinterpret-02", "Version two title"),
        ):
            (job_dir / "metadata.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
            (job_dir / "normalized.json").write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "asset": {
                            "title": title,
                            "result": {"summary": {"headline": title, "short_text": "summary"}},
                        },
                        "metadata": {"llm_processing": {"status": "pass"}},
                    }
                ),
                encoding="utf-8",
            )
            (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        service = WindowsClientService(
            settings=Settings(project_root=Path(self.temp_dir.name) / "project-root"),
            mock_collector=MagicMock(),
            url_collector=MagicMock(),
            browser_collector=MagicMock(),
            exporter=MagicMock(),
        )

        result = service.reinterpret_result(
            ReinterpretRequest(
                job_id="job-123--reinterpret-01",
                reading_goal="review",
                domain_template="briefing",
            ),
            shared_root=self.shared_root,
        )

        reinterpret_three_dir = self.shared_root / "processed" / "job-123--reinterpret-03"
        normalized = json.loads((reinterpret_three_dir / "normalized.json").read_text(encoding="utf-8"))
        self.assertEqual(result.job_id, "job-123--reinterpret-03")
        self.assertEqual(normalized["asset"]["title"], "Version one title")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["source_job_id"], "job-123")
        self.assertEqual(normalized["metadata"]["reinterpretation"]["source_version_job_id"], "job-123--reinterpret-01")
        self.assertEqual(
            json.loads((base_dir / "active_version.json").read_text(encoding="utf-8"))["active_job_id"],
            "job-123--reinterpret-03",
        )

    def test_load_failed_job_result(self) -> None:
        job_dir = self.shared_root / "failed" / "job-456"
        job_dir.mkdir()
        (job_dir / "metadata.json").write_text(
            json.dumps({"job_id": "job-456", "source_url": "https://example.com/article", "platform": "generic"}),
            encoding="utf-8",
        )
        (job_dir / "error.json").write_text(
            json.dumps({"error_message": "processing failed"}),
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-456")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.state, "failed")
        self.assertEqual(result.summary, "processing failed")
        self.assertIsNotNone(result.error_path)

    def test_load_latest_result_prefers_latest_timestamp(self) -> None:
        old_dir = self.shared_root / "processed" / "job-old"
        new_dir = self.shared_root / "failed" / "job-new"
        old_dir.mkdir()
        new_dir.mkdir()
        (old_dir / "metadata.json").write_text(json.dumps({"job_id": "job-old"}), encoding="utf-8")
        (old_dir / "normalized.json").write_text(json.dumps({"job_id": "job-old", "asset": {}}), encoding="utf-8")
        (old_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")
        (new_dir / "metadata.json").write_text(json.dumps({"job_id": "job-new"}), encoding="utf-8")
        (new_dir / "error.json").write_text(json.dumps({"error_message": "failed"}), encoding="utf-8")
        (new_dir / "status.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

        old_time = old_dir.stat().st_mtime - 10
        new_time = new_dir.stat().st_mtime + 10
        os = __import__("os")
        os.utime(old_dir, (old_time, old_time))
        os.utime(new_dir, (new_time, new_time))

        result = load_latest_result(self.shared_root)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.job_id, "job-new")

    def test_list_recent_results_includes_pending_and_processing(self) -> None:
        incoming_dir = self.shared_root / "incoming" / "job-pending"
        processing_dir = self.shared_root / "processing" / "job-processing"
        incoming_dir.mkdir()
        processing_dir.mkdir()
        (incoming_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "job_id": "job-pending",
                    "source_url": "https://example.com/pending",
                    "platform": "generic",
                    "title_hint": "Pending title",
                }
            ),
            encoding="utf-8",
        )
        (processing_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "job_id": "job-processing",
                    "source_url": "https://example.com/processing",
                    "platform": "wechat",
                    "title_hint": "Processing title",
                }
            ),
            encoding="utf-8",
        )

        results = list_recent_results(self.shared_root, limit=10)

        states_by_job_id = {result.job_id: result.state for result in results}
        self.assertEqual(states_by_job_id["job-pending"], "pending")
        self.assertEqual(states_by_job_id["job-processing"], "processing")

    def test_processed_preview_falls_back_to_none_when_markdown_has_no_body(self) -> None:
        job_dir = self.shared_root / "processed" / "job-empty-preview"
        job_dir.mkdir()
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-empty-preview"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(json.dumps({"job_id": "job-empty-preview", "asset": {}}), encoding="utf-8")
        (job_dir / "normalized.md").write_text("# Only title\n\n- Platform: generic\n\n---", encoding="utf-8")
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-empty-preview")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.preview_text)

    def test_processed_preview_hides_unreadable_text(self) -> None:
        job_dir = self.shared_root / "processed" / "job-bad-preview"
        job_dir.mkdir()
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-bad-preview"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(json.dumps({"job_id": "job-bad-preview", "asset": {}}), encoding="utf-8")
        (job_dir / "normalized.md").write_text(
            "# Bad preview\n\n- Platform: generic\n\n---\n\n\ufffd\x08\x00\x00\x00\x00\x00\x04\x03\ufffd{w\x13G\ufffd7\ufffd\ufffd\ufffd) | unreadable",
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-bad-preview")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNone(result.preview_text)
        self.assertIn("looks unreadable", result.summary)

    def test_processed_result_reports_missing_llm_output(self) -> None:
        job_dir = self.shared_root / "processed" / "job-no-llm"
        job_dir.mkdir()
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-no-llm"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps(
                {
                    "job_id": "job-no-llm",
                    "asset": {
                        "metadata": {
                            "llm_processing": {
                                "status": "skipped",
                                "skip_reason": "missing OPENAI_API_KEY",
                            }
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "normalized.md").write_text(
            "# Title\n\n- Platform: generic\n\n---\n\nThis normalized body is readable and long enough to keep preview extraction stable.",
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-no-llm")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.analysis_state, "skipped")
        self.assertIn("missing OPENAI_API_KEY", result.summary)

    def test_processed_result_prefers_analysis_json_artifact(self) -> None:
        job_dir = self.shared_root / "processed" / "job-analysis-json"
        (job_dir / "analysis" / "llm").mkdir(parents=True)
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-analysis-json"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps(
                {
                    "job_id": "job-analysis-json",
                    "asset": {
                        "metadata": {
                            "llm_processing": {
                                "status": "pass",
                            }
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (job_dir / "status.json").write_text(json.dumps({"status": "success"}), encoding="utf-8")
        analysis_path = job_dir / "analysis" / "llm" / "analysis_result.json"
        analysis_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-analysis-json")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.analysis_json_path, analysis_path)

    def test_llm_image_input_read_when_present(self) -> None:
        job_dir = self.shared_root / "processed" / "job-image-trunc"
        (job_dir / "analysis" / "llm").mkdir(parents=True)
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-image-trunc"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps({"job_id": "job-image-trunc", "asset": {"metadata": {"llm_processing": {"status": "pass"}}}}),
            encoding="utf-8",
        )
        analysis_path = job_dir / "analysis" / "llm" / "analysis_result.json"
        analysis_path.write_text(
            json.dumps({"status": "pass", "image_input_truncated": True, "image_input_count": 8}),
            encoding="utf-8",
        )

        result = load_job_result(self.shared_root, "job-image-trunc")

        self.assertIsNotNone(result)
        assert result is not None
        llm_image = result.details.get("llm_image_input", {})
        self.assertTrue(llm_image.get("image_input_truncated"))
        self.assertEqual(llm_image.get("image_input_count"), 8)

    def test_llm_image_input_empty_when_no_analysis_file(self) -> None:
        job_dir = self.shared_root / "processed" / "job-no-analysis"
        job_dir.mkdir(parents=True)
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-no-analysis"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps({"job_id": "job-no-analysis", "asset": {"metadata": {"llm_processing": {"status": "skipped", "skip_reason": "no key"}}}}),
            encoding="utf-8",
        )

        result = load_job_result(self.shared_root, "job-no-analysis")

        self.assertIsNotNone(result)
        assert result is not None
        llm_image = result.details.get("llm_image_input", {})
        self.assertFalse(llm_image.get("image_input_truncated", False))

    def test_visual_findings_populated_from_analysis_json(self) -> None:
        job_dir = self.shared_root / "processed" / "job-visual"
        (job_dir / "analysis" / "llm").mkdir(parents=True)
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-visual"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps({"job_id": "job-visual", "asset": {"metadata": {"llm_processing": {"status": "pass"}}}}),
            encoding="utf-8",
        )
        analysis_path = job_dir / "analysis" / "llm" / "analysis_result.json"
        analysis_path.write_text(
            json.dumps({
                "status": "pass",
                "visual_findings": [
                    {"id": "vf-1", "frame_timestamp_ms": 12000, "description": "Speaker holds document", "relevance": "high"},
                    {"id": "vf-2", "frame_timestamp_ms": 30000, "description": "Chart shown on screen", "relevance": "medium"},
                ],
            }),
            encoding="utf-8",
        )

        result = load_job_result(self.shared_root, "job-visual")

        self.assertIsNotNone(result)
        assert result is not None
        findings = result.details.get("visual_findings", [])
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["description"], "Speaker holds document")
        self.assertEqual(findings[1]["frame_timestamp_ms"], 30000)

    def test_visual_findings_empty_when_absent(self) -> None:
        job_dir = self.shared_root / "processed" / "job-no-visual"
        (job_dir / "analysis" / "llm").mkdir(parents=True)
        (job_dir / "metadata.json").write_text(json.dumps({"job_id": "job-no-visual"}), encoding="utf-8")
        (job_dir / "normalized.json").write_text(
            json.dumps({"job_id": "job-no-visual", "asset": {"metadata": {"llm_processing": {"status": "pass"}}}}),
            encoding="utf-8",
        )
        analysis_path = job_dir / "analysis" / "llm" / "analysis_result.json"
        analysis_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")

        result = load_job_result(self.shared_root, "job-no-visual")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.details.get("visual_findings"), [])


class LooksUnreadableTextTests(unittest.TestCase):
    def test_binary_garbage_is_unreadable(self) -> None:
        text = "\ufffd\x08\x00\x00\x00\x00\x00\x04\x03\ufffd{w\x13G\ufffd7\ufffd\ufffd\ufffd) | something"
        self.assertTrue(_looks_unreadable_text(text))

    def test_plain_english_is_readable(self) -> None:
        self.assertFalse(_looks_unreadable_text("This is a normal English paragraph."))

    def test_chinese_text_is_readable(self) -> None:
        self.assertFalse(_looks_unreadable_text("这是一段正常的中文内容，用于测试。"))

    def test_japanese_hiragana_is_readable(self) -> None:
        self.assertFalse(_looks_unreadable_text("これはひらがなのテストです。"))

    def test_japanese_katakana_is_readable(self) -> None:
        self.assertFalse(_looks_unreadable_text("コンテンツのテキストサンプルです。"))

    def test_korean_hangul_is_readable(self) -> None:
        self.assertFalse(_looks_unreadable_text("이것은 한국어 테스트 텍스트입니다."))


if __name__ == "__main__":
    unittest.main()
