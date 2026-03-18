import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.result_workspace import list_recent_results, load_job_result, load_latest_result


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


if __name__ == "__main__":
    unittest.main()
