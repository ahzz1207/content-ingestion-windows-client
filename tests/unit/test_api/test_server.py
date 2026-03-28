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
from windows_client.api.models import (
    IngestedJob,
    JobListResult,
    JobRecord,
    JobResultCard,
    JobResultCardListResult,
    JobResultDetail,
)
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

    def test_cors_preflight_is_allowed_for_health(self) -> None:
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": "app://obsidian.md",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_list_jobs_supports_comma_separated_status_filter(self) -> None:
        response = self.client.get(
            "/api/v1/jobs",
            params={"status": "queued,processing", "limit": 5},
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.manager.last_statuses, ["queued", "processing"])
        self.assertEqual(response.json()["total"], 2)

    def test_list_jobs_supports_result_cards_view(self) -> None:
        response = self.client.get(
            "/api/v1/jobs",
            params={"view": "result_cards", "limit": 5},
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.manager.last_list_view, "result_cards")
        self.assertEqual(response.json()["items"][0]["result_card"]["headline"], "Structured headline")

    def test_job_result_returns_conflict_for_processing_job(self) -> None:
        response = self.client.get(
            "/api/v1/jobs/job-processing/result",
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("processing", response.json()["detail"])

    def test_job_result_returns_completed_payload(self) -> None:
        response = self.client.get(
            "/api/v1/jobs/job-completed/result",
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], "job-completed")
        self.assertEqual(response.json()["structured_result"]["summary"]["headline"], "Structured headline")

    def test_delete_job_returns_archived_payload(self) -> None:
        response = self.client.delete(
            "/api/v1/jobs/job-completed",
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], "job-completed")
        self.assertTrue(response.json()["archived"])
        self.assertNotIn("deleted", response.json())
        self.assertEqual(response.json()["previous_status"], "completed")

    def test_delete_job_returns_not_found_for_missing_job(self) -> None:
        response = self.client.delete(
            "/api/v1/jobs/job-missing",
            headers={"Authorization": "Bearer demo-token"},
        )

        self.assertEqual(response.status_code, 404)

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
        self.last_list_view = "summary"

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
        self.last_list_view = "summary"
        return JobListResult(
            items=[
                JobRecord(job_id="job1", status="queued"),
                JobRecord(job_id="job2", status="processing"),
            ],
            total=2,
            limit=limit,
            statuses=statuses or [],
        )

    def list_result_cards(self, *, statuses: list[str] | None = None, limit: int = 20) -> JobResultCardListResult:
        self.last_statuses = statuses
        self.last_list_view = "result_cards"
        return JobResultCardListResult(
            items=[
                JobResultCard(
                    job_id="job-completed",
                    status="completed",
                    title="Demo",
                    result_card={
                        "headline": "Structured headline",
                        "one_sentence_take": "One line",
                        "quick_takeaways": ["A"],
                        "conclusion": "Bottom line",
                        "verification_signal": "supported",
                        "warning_count": 0,
                        "coverage_warning": None,
                    },
                )
            ],
            total=1,
            limit=limit,
            statuses=statuses or [],
        )

    def get_job(self, job_id: str) -> JobRecord | None:
        return JobRecord(job_id=job_id, status="queued")

    def archive_job(self, job_id: str) -> JobRecord | None:
        if job_id == "job-completed":
            return JobRecord(job_id=job_id, status="completed")
        return None

    def get_job_result(self, job_id: str) -> JobResultDetail | None:
        if job_id == "job-processing":
            return JobResultDetail(job_id=job_id, status="processing")
        if job_id == "job-completed":
            return JobResultDetail(
                job_id=job_id,
                status="completed",
                structured_result={"summary": {"headline": "Structured headline"}},
            )
        return None


if __name__ == "__main__":
    unittest.main()
