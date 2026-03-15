import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.collector.html_metadata import detect_platform, extract_html_metadata, focus_platform_payload


WECHAT_HTML = """
<html>
  <head>
    <meta property="og:title" content="直击霍尔木兹&amp;油运">
    <title>直击霍尔木兹&amp;油运</title>
  </head>
  <body>
    <h1 id="activity-name"><span class="js_title_inner">直击霍尔木兹&amp;油运</span></h1>
    <a id="js_name">热点投研</a>
    <em id="publish_time">2026年3月12日 23:56</em>
  </body>
</html>
"""

BILIBILI_HTML = """
<html>
  <head>
    <meta name="description" content="这是一段简洁的视频简介。 视频播放量 123、弹幕量 4、点赞数 5、作者简介 这里不需要">
    <meta name="author" content="某个UP主">
    <meta property="og:title" content="测试视频标题_哔哩哔哩_bilibili">
    <meta property="og:url" content="https://www.bilibili.com/video/BV1abcdEFG23/">
    <meta property="og:image" content="//i0.hdslb.com/test-cover.jpg">
    <link rel="canonical" href="https://www.bilibili.com/video/BV1abcdEFG23/">
    <title>测试视频标题_哔哩哔哩_bilibili</title>
  </head>
  <body>
    <div>这里是整页杂音，不应该进入聚焦版 payload。</div>
  </body>
</html>
"""


class HtmlMetadataTests(unittest.TestCase):
    def test_detect_platform_from_wechat_url(self) -> None:
        self.assertEqual(detect_platform("https://mp.weixin.qq.com/s/test"), "wechat")

    def test_extract_wechat_metadata_hints(self) -> None:
        hints = extract_html_metadata("https://mp.weixin.qq.com/s/test", WECHAT_HTML)

        self.assertEqual(hints.platform, "wechat")
        self.assertEqual(hints.title_hint, "直击霍尔木兹&油运")
        self.assertEqual(hints.author_hint, "热点投研")
        self.assertEqual(hints.published_at_hint, "2026年3月12日 23:56")

    def test_detect_platform_from_bilibili_url(self) -> None:
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV1abcdEFG23/"), "bilibili")

    def test_focus_platform_payload_for_bilibili_keeps_only_video_fields(self) -> None:
        hints = extract_html_metadata("https://www.bilibili.com/video/BV1abcdEFG23/", BILIBILI_HTML)

        focused = focus_platform_payload("https://www.bilibili.com/video/BV1abcdEFG23/", BILIBILI_HTML, hints)

        self.assertEqual(hints.platform, "bilibili")
        self.assertIn("<h2>Video</h2>", focused)
        self.assertIn("测试视频标题_哔哩哔哩_bilibili", focused)
        self.assertIn("某个UP主", focused)
        self.assertIn("这是一段简洁的视频简介。", focused)
        self.assertIn("player.bilibili.com/player.html?bvid=BV1abcdEFG23&amp;page=1", focused)
        self.assertNotIn("这里是整页杂音", focused)
        self.assertNotIn("作者简介 这里不需要", focused)

    def test_detect_generic_platform_for_normal_page(self) -> None:
        self.assertEqual(detect_platform("https://example.com/article", "<html></html>"), "generic")


if __name__ == "__main__":
    unittest.main()
