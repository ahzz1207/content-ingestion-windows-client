import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.config.settings import Settings
from windows_client.gui.platform_router import resolve_platform_route


class PlatformRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name) / "project-root"
        self.settings = Settings(project_root=self.project_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_wechat_route_uses_browser_profile(self) -> None:
        route = resolve_platform_route("https://mp.weixin.qq.com/s/demo")

        self.assertEqual(route.platform, "wechat")
        self.assertEqual(route.strategy, "browser")
        self.assertEqual(route.start_url, "https://mp.weixin.qq.com/")
        self.assertEqual(route.profile_slug, "wechat")
        self.assertEqual(route.wait_for_selector, "#js_content")
        self.assertEqual(route.profile_dir(self.settings), self.settings.browser_profiles_dir / "wechat")

    def test_generic_route_uses_http(self) -> None:
        route = resolve_platform_route("https://example.com/article")

        self.assertEqual(route.platform, "generic")
        self.assertEqual(route.strategy, "http")
        self.assertIsNone(route.profile_slug)
        self.assertIsNone(route.profile_dir(self.settings))

    def test_bilibili_route_uses_http_with_specific_platform(self) -> None:
        route = resolve_platform_route("https://www.bilibili.com/video/BV1abcdEFG23/")

        self.assertEqual(route.platform, "bilibili")
        self.assertEqual(route.display_name, "Bilibili Video")
        self.assertEqual(route.strategy, "http")
        self.assertIsNone(route.profile_slug)

    def test_youtube_route_uses_browser_profile(self) -> None:
        route = resolve_platform_route("https://www.youtube.com/watch?v=demo123")

        self.assertEqual(route.platform, "youtube")
        self.assertEqual(route.strategy, "browser")
        self.assertEqual(route.profile_slug, "youtube")


if __name__ == "__main__":
    unittest.main()
