import sys
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.collector.browser import BrowserCollectOptions, BrowserCollector, BrowserLoginOptions


class _BrowserFixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = "<html><head><title>Browser Test</title></head><body><h1>Browser Test</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class BrowserCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _BrowserFixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/article.html"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        self.collector = BrowserCollector(timeout_ms=5000)

    def test_availability_reason_matches_runtime_state(self) -> None:
        expected = "ok" if self.collector.is_available() else "playwright_not_installed"
        self.assertEqual(self.collector.availability_reason(), expected)

    def test_default_profile_slug_prefers_platform_then_hostname(self) -> None:
        self.assertEqual(self.collector.default_profile_slug("https://mp.weixin.qq.com/"), "wechat")
        self.assertEqual(self.collector.default_profile_slug("https://sub.example.com/path"), "sub-example-com")
        self.assertEqual(self.collector.default_profile_slug("https://example.com/"), "example-com")

    def test_rejects_non_html_output_request(self) -> None:
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.collect("https://example.com/article", content_type="txt", platform="generic")
        self.assertEqual(ctx.exception.code, "unsupported_content_type")

    def test_rejects_invalid_wait_until(self) -> None:
        options = BrowserCollectOptions(wait_until="bad-state")
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.collect("https://example.com/article", content_type="html", platform="generic", options=options)
        self.assertEqual(ctx.exception.code, "invalid_wait_until")

    def test_rejects_invalid_wait_for_selector_state(self) -> None:
        options = BrowserCollectOptions(wait_for_selector="#app", wait_for_selector_state="bad-state")
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.collect("https://example.com/article", content_type="html", platform="generic", options=options)
        self.assertEqual(ctx.exception.code, "invalid_wait_for_selector_state")

    def test_rejects_negative_settle_ms(self) -> None:
        options = BrowserCollectOptions(settle_ms=-1)
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.collect("https://example.com/article", content_type="html", platform="generic", options=options)
        self.assertEqual(ctx.exception.code, "invalid_settle_ms")

    def test_login_rejects_invalid_start_url(self) -> None:
        with self.assertRaises(WindowsClientError) as ctx:
            self.collector.open_profile_session(BrowserLoginOptions(profile_dir=Path("x"), start_url="not-a-url"))
        self.assertEqual(ctx.exception.code, "invalid_start_url")

    def test_fails_cleanly_when_runtime_is_forced_unavailable(self) -> None:
        with patch.object(self.collector, "is_available", return_value=False):
            with self.assertRaises(WindowsClientError) as ctx:
                self.collector.collect("https://example.com/article", content_type="html", platform="generic")
            self.assertEqual(ctx.exception.code, "browser_runtime_unavailable")
            self.assertEqual(ctx.exception.stage, "browser_collect")

    def test_login_fails_cleanly_when_runtime_is_forced_unavailable(self) -> None:
        with patch.object(self.collector, "is_available", return_value=False):
            with self.assertRaises(WindowsClientError) as ctx:
                self.collector.open_profile_session(BrowserLoginOptions(profile_dir=Path("x"), start_url="https://example.com/"))
            self.assertEqual(ctx.exception.code, "browser_runtime_unavailable")
            self.assertEqual(ctx.exception.stage, "browser_login")

    def test_collects_page_when_runtime_is_available(self) -> None:
        if not self.collector.is_available():
            self.skipTest("Playwright runtime is not available in this environment")

        payload = self.collector.collect(
            self.base_url,
            content_type="html",
            platform="generic",
            options=BrowserCollectOptions(timeout_ms=5000, settle_ms=0, wait_for_selector="h1"),
        )

        self.assertEqual(payload.content_type, "html")
        self.assertEqual(payload.final_url, self.base_url)
        self.assertEqual(payload.title_hint, "Browser Test")
        self.assertIn("Browser Test", payload.payload_text)

    def test_collects_page_with_persistent_profile_when_runtime_is_available(self) -> None:
        if not self.collector.is_available():
            self.skipTest("Playwright runtime is not available in this environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir) / "profile"
            payload = self.collector.collect(
                self.base_url,
                content_type="html",
                platform="generic",
                options=BrowserCollectOptions(timeout_ms=5000, settle_ms=0, profile_dir=profile_dir, wait_for_selector="h1"),
            )
            self.assertTrue(profile_dir.exists())
            self.assertIn("Browser Test", payload.payload_text)


if __name__ == "__main__":
    unittest.main()
