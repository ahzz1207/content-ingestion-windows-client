import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None

if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient

from windows_client.api.config import ApiConfig
from windows_client.api.models import IngestedJob, JobListResult, JobRecord
from windows_client.api.server import create_app


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi test dependencies are not installed")
class ApiServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp_dir.name) / "api_token"
        self.manager = _FakeManager()
        self.app = create_app(
            config=ApiConfig(api_token="demo-token", api_token_path=self.token_path),
            manager=self.manager,
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_endpoint_is_public(self) -> None:
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_list_jobs_supports_comma_separated_status_filter(self) -> None:
        response = self.client.get(
            "/api/v1/jobs",
            params={"status": "queued,processing", "limit": 5},
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.manager.last_statuses, ["queued", "processing"])
        self.assertEqual(response.json()["total"], 2)

    def test_ingest_requires_authorization(self) -> None:
        response = self.client.post("/api/v1/ingest", json={"url": "https://example.com/article"})

        self.assertEqual(response.status_code, 401)

    def test_ingest_returns_queued_job(self) -> None:
        response = self.client.post(
            "/api/v1/ingest",
            json={"url": "https://example.com/article"},
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["job_id"], "job123")
        self.assertEqual(self.manager.last_submit_url, "https://example.com/article")
        self.assertIsNone(self.manager.last_video_download_mode)


class _FakeManager:
    def __init__(self) -> None:
        self.last_statuses: list[str] | None = None
        self.last_submit_url: str | None = None
        self.last_video_download_mode: str | None = None

    def submit_url(
        self,
        *,
        url: str,
        content_type: str | None = None,
        platform: str | None = None,
        video_download_mode: str | None = None,
    ) -> IngestedJob:
        self.last_submit_url = url
        self.last_video_download_mode = video_download_mode
        return IngestedJob(
            job_id="job123",
            status="queued",
            source_url=url,
            content_type=content_type or "html",
            platform=platform or "generic",
            created_at="2026-03-26T12:00:00+08:00",
        )

    def list_jobs(self, *, statuses: list[str] | None = None, limit: int = 20) -> JobListResult:
        self.last_statuses = statuses
        return JobListResult(
            items=[
                JobRecord(job_id="job1", status="queued"),
                JobRecord(job_id="job2", status="processing"),
            ],
            total=2,
            limit=limit,
            statuses=statuses or [],
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        return JobRecord(job_id=job_id, status="queued")


if __name__ == "__main__":
    unittest.main()
