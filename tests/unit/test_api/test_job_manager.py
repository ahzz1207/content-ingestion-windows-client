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

    def test_list_jobs_filters_multiple_statuses(self) -> None:
        self._write_job("incoming", "job-queued", source_url="https://example.com/queued")
        self._write_job("processing", "job-processing", source_url="https://example.com/processing")
        self._write_job("processed", "job-completed", source_url="https://example.com/completed")
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="boom")

        result = self.manager.list_jobs(statuses=["queued", "processing"], limit=10)

        found = {(item.job_id, item.status) for item in result.items}
        self.assertEqual(result.total, 2)
        self.assertEqual(found, {("job-queued", "queued"), ("job-processing", "processing")})

    def test_get_job_reads_failed_error_payload(self) -> None:
        self._write_job("failed", "job-failed", source_url="https://example.com/failed", error="processor exploded")

        result = self.manager.get_job("job-failed")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "processor exploded")

    def _write_job(self, dirname: str, job_id: str, *, source_url: str, error: str | None = None) -> None:
        job_dir = self.shared_root / dirname / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        if dirname in {"incoming", "processing"}:
            (job_dir / "payload.html").write_text("<html></html>", encoding="utf-8")
        metadata = {
            "job_id": job_id,
            "source_url": source_url,
            "platform": "generic",
            "content_type": "html",
            "collection_mode": "http",
            "collected_at": "2026-03-26T12:00:00+08:00",
        }
        (job_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        if dirname == "failed" and error:
            (job_dir / "error.json").write_text(json.dumps({"message": error}), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
