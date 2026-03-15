import json
import gzip
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.collector.http import HttpCollector


class _TestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/article":
            body = "<html><head><title>Example Article</title></head><body><h1>Hi</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/plain":
            body = "hello from text"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/notes.md":
            body = "# Notes\n\nBody"
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        if self.path == "/gzip":
            body = "<html><head><title>Compressed</title></head><body><h1>Compressed page</h1></body></html>"
            payload = gzip.compress(body.encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/bilibili":
            body = (
                "<html><head>"
                "<title>Video Demo</title>"
                '<meta property="og:url" content="https://www.bilibili.com/video/BV1xx411c7mD/">'
                '<meta property="og:title" content="Video Demo">'
                '<meta name="author" content="Uploader A">'
                '<meta name="description" content="Short bilibili description">'
                "</head><body><script>window.__INITIAL_STATE__={};</script><div>raw source</div></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class HttpCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        self.collector = HttpCollector(timeout_seconds=5.0)

    def test_collect_infers_html_and_extracts_title(self) -> None:
        payload = self.collector.collect(f"{self.base_url}/article", content_type=None, platform="generic")

        self.assertEqual(payload.content_type, "html")
        self.assertEqual(payload.final_url, f"{self.base_url}/article")
        self.assertEqual(payload.title_hint, "Example Article")
        self.assertIn("<h1>Hi</h1>", payload.payload_text)
        artifact_paths = {artifact.relative_path for artifact in payload.artifacts}
        self.assertIn("attachments/derived/primary_visible_text.txt", artifact_paths)
        self.assertIn("attachments/derived/capture_validation.json", artifact_paths)
        validation_artifact = next(
            artifact for artifact in payload.artifacts if artifact.relative_path == "attachments/derived/capture_validation.json"
        )
        validation = json.loads(validation_artifact.content)
        self.assertIn(validation["summary"]["status"], {"pass", "warn"})
        self.assertGreater(validation["metrics"]["primary_visible_text_chars"], 0)

    def test_collect_infers_text_plain(self) -> None:
        payload = self.collector.collect(f"{self.base_url}/plain", content_type=None, platform="generic")

        self.assertEqual(payload.content_type, "txt")
        self.assertEqual(payload.payload_text, "hello from text")

    def test_collect_infers_markdown(self) -> None:
        payload = self.collector.collect(f"{self.base_url}/notes.md", content_type=None, platform="generic")

        self.assertEqual(payload.content_type, "md")
        self.assertIn("# Notes", payload.payload_text)

    def test_collect_decodes_gzip_encoded_html(self) -> None:
        payload = self.collector.collect(f"{self.base_url}/gzip", content_type=None, platform="generic")

        self.assertEqual(payload.content_type, "html")
        self.assertEqual(payload.title_hint, "Compressed")
        self.assertIn("Compressed page", payload.payload_text)

    def test_collect_preserves_raw_html_as_attachment_when_platform_focuses_payload(self) -> None:
        payload = self.collector.collect(f"{self.base_url}/bilibili", content_type=None, platform="generic")

        self.assertEqual(payload.platform, "bilibili")
        self.assertEqual(payload.content_shape, "video")
        self.assertEqual(payload.primary_payload_role, "focused_capture")
        artifact_paths = {artifact.relative_path for artifact in payload.artifacts}
        self.assertIn("attachments/source/raw.html", artifact_paths)
        self.assertIn("attachments/derived/raw_visible_text.txt", artifact_paths)
        self.assertIn("attachments/derived/primary_visible_text.txt", artifact_paths)
        self.assertIn("attachments/derived/capture_validation.json", artifact_paths)
        self.assertIn("Video Demo", payload.payload_text)
        raw_artifact = next(artifact for artifact in payload.artifacts if artifact.relative_path == "attachments/source/raw.html")
        self.assertIn("raw source", raw_artifact.content)
        validation_artifact = next(
            artifact for artifact in payload.artifacts if artifact.relative_path == "attachments/derived/capture_validation.json"
        )
        validation = json.loads(validation_artifact.content)
        self.assertEqual(validation["platform"], "bilibili")
        self.assertEqual(validation["summary"]["failed"], 0)

    def test_collect_rejects_http_error(self) -> None:
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.collect(f"{self.base_url}/missing", content_type=None, platform="generic")
        self.assertEqual(ctx.exception.code, "http_status_error")
        self.assertEqual(ctx.exception.stage, "http_collect")
        self.assertEqual(ctx.exception.details["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
