import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.collector.base import CollectedArtifact, CollectedPayload
from windows_client.config.settings import Settings
from windows_client.job_exporter.exporter import JobExporter
from windows_client.job_exporter.models import ExportRequest


class JobExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.shared_root = Path(self.temp_dir.name) / "shared_inbox"
        self.exporter = JobExporter(settings=Settings(project_root=Path(self.temp_dir.name), shared_inbox_root=self.shared_root))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generate_job_id_matches_expected_format(self) -> None:
        job_id = self.exporter.generate_job_id(self.shared_root)
        self.assertRegex(job_id, r"^\d{8}_\d{6}_[0-9a-f]{6}$")

    def test_export_writes_expected_job_structure(self) -> None:
        request = ExportRequest(
            source_url="https://example.com/article",
            shared_root=self.shared_root,
            content_type="html",
            platform="generic",
            collection_mode="browser",
            browser_channel="msedge",
            profile_slug="wechat",
            wait_until="domcontentloaded",
            wait_for_selector="#js_content",
            wait_for_selector_state="visible",
        )
        payload = CollectedPayload(
            source_url=request.source_url,
            content_type="html",
            payload_text="<html><body><h1>Hello</h1></body></html>",
            final_url="https://example.com/final-article",
            platform="wechat",
            title_hint="Hello",
            author_hint="Tester",
            published_at_hint="2026-03-13 00:00",
            primary_payload_role="focused_capture",
            content_shape="article",
            artifacts=(
                CollectedArtifact(
                    relative_path="attachments/source/raw.html",
                    media_type="text/html",
                    role="raw_capture",
                    content="<html><body><h1>Hello</h1><div>raw</div></body></html>",
                    description="Original HTML before platform-specific focusing.",
                ),
            ),
        )

        result = self.exporter.export(request, payload)
        job_dir = result.job_dir

        self.assertEqual(result.job_id, job_dir.name)
        self.assertEqual(result.payload_path, job_dir / "payload.html")
        self.assertEqual(result.metadata_path, job_dir / "metadata.json")
        self.assertEqual(result.ready_path, job_dir / "READY")
        self.assertEqual(result.capture_manifest_path, job_dir / "capture_manifest.json")
        self.assertEqual(result.attachments_dir, job_dir / "attachments")
        self.assertTrue(job_dir.exists())
        self.assertTrue(result.payload_path.exists())
        self.assertTrue(result.metadata_path.exists())
        self.assertTrue(result.ready_path.exists())
        self.assertTrue(result.capture_manifest_path.exists())
        self.assertTrue((job_dir / "attachments" / "source" / "raw.html").exists())
        self.assertEqual(
            sorted(path.name for path in job_dir.iterdir()),
            ["READY", "attachments", "capture_manifest.json", "metadata.json", "payload.html"],
        )

        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["job_id"], job_dir.name)
        self.assertEqual(metadata["source_url"], request.source_url)
        self.assertEqual(metadata["collector"], "windows-client")
        self.assertEqual(metadata["content_type"], "html")
        self.assertEqual(metadata["platform"], "wechat")
        self.assertEqual(metadata["final_url"], "https://example.com/final-article")
        self.assertEqual(metadata["collection_mode"], "browser")
        self.assertEqual(metadata["browser_channel"], "msedge")
        self.assertEqual(metadata["profile_slug"], "wechat")
        self.assertEqual(metadata["wait_until"], "domcontentloaded")
        self.assertEqual(metadata["wait_for_selector"], "#js_content")
        self.assertEqual(metadata["wait_for_selector_state"], "visible")
        self.assertEqual(metadata["title_hint"], "Hello")
        self.assertEqual(metadata["author_hint"], "Tester")
        self.assertEqual(metadata["published_at_hint"], "2026-03-13 00:00")
        self.assertEqual(metadata["primary_payload_role"], "focused_capture")
        self.assertEqual(metadata["content_shape"], "article")
        self.assertEqual(metadata["capture_manifest_filename"], "capture_manifest.json")
        self.assertIn("collected_at", metadata)

        manifest = json.loads(result.capture_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["job_id"], job_dir.name)
        self.assertEqual(manifest["content_shape"], "article")
        self.assertEqual(manifest["primary_payload"]["path"], "payload.html")
        self.assertEqual(manifest["primary_payload"]["role"], "focused_capture")
        self.assertEqual(manifest["artifacts"][1]["path"], "attachments/source/raw.html")
        self.assertEqual(manifest["artifacts"][1]["role"], "raw_capture")

    def test_export_uses_default_shared_root_when_request_does_not_specify_one(self) -> None:
        project_root = Path(self.temp_dir.name) / "project-root"
        default_root = project_root / "data" / "shared_inbox"
        exporter = JobExporter(settings=Settings(project_root=project_root))
        request = ExportRequest(
            source_url="https://example.com/article",
            content_type="html",
            platform="generic",
        )
        payload = CollectedPayload(
            source_url=request.source_url,
            content_type="html",
            payload_text="<html></html>",
        )

        result = exporter.export(request, payload)

        self.assertTrue(result.job_dir.is_dir())
        self.assertEqual(result.job_dir.parent.parent, default_root)

    def test_export_rejects_mismatched_content_type(self) -> None:
        request = ExportRequest(
            source_url="https://example.com/article",
            shared_root=self.shared_root,
            content_type="html",
            platform="generic",
        )
        payload = CollectedPayload(
            source_url=request.source_url,
            content_type="txt",
            payload_text="hello",
        )

        with self.assertRaises(WindowsClientError) as ctx:
            self.exporter.export(request, payload)
        self.assertEqual(ctx.exception.code, "payload_content_type_mismatch")

    def test_export_rejects_mismatched_source_url(self) -> None:
        request = ExportRequest(
            source_url="https://example.com/article",
            shared_root=self.shared_root,
            content_type="html",
            platform="generic",
        )
        payload = CollectedPayload(
            source_url="https://example.com/other",
            content_type="html",
            payload_text="<html></html>",
        )

        with self.assertRaises(WindowsClientError) as ctx:
            self.exporter.export(request, payload)
        self.assertEqual(ctx.exception.code, "payload_source_url_mismatch")

    def test_export_rejects_invalid_url(self) -> None:
        request = ExportRequest(
            source_url="not-a-url",
            shared_root=self.shared_root,
            content_type="html",
            platform="generic",
        )
        payload = CollectedPayload(
            source_url=request.source_url,
            content_type="html",
            payload_text="<html></html>",
        )

        with self.assertRaises(WindowsClientError) as ctx:
            self.exporter.export(request, payload)
        self.assertEqual(ctx.exception.code, "invalid_source_url")

    def test_export_copies_file_backed_artifacts(self) -> None:
        source_file = Path(self.temp_dir.name) / "video.mp4"
        source_file.write_bytes(b"video-bytes")
        request = ExportRequest(
            source_url="https://www.youtube.com/watch?v=demo123",
            shared_root=self.shared_root,
            content_type="html",
            platform="youtube",
        )
        payload = CollectedPayload(
            source_url=request.source_url,
            content_type="html",
            payload_text="<html><body>Video page</body></html>",
            platform="youtube",
            content_shape="video",
            artifacts=(
                CollectedArtifact(
                    relative_path="attachments/video/video.mp4",
                    media_type="video/mp4",
                    role="video_file",
                    source_path=source_file,
                    description="Primary downloaded video file.",
                ),
            ),
        )

        result = self.exporter.export(request, payload)

        copied_file = result.job_dir / "attachments" / "video" / "video.mp4"
        self.assertTrue(copied_file.exists())
        self.assertEqual(copied_file.read_bytes(), b"video-bytes")


if __name__ == "__main__":
    unittest.main()
