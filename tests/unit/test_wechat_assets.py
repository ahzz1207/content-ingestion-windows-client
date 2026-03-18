import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.collector.wechat_assets import build_wechat_article_artifacts


class _FakeHeaders:
    def __init__(self, media_type: str) -> None:
        self.media_type = media_type

    def get_content_type(self) -> str:
        return self.media_type


class _FakeResponse:
    def __init__(self, *, media_type: str, content: bytes) -> None:
        self._headers = _FakeHeaders(media_type)
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def info(self) -> _FakeHeaders:
        return self._headers

    def read(self, _limit: int | None = None) -> bytes:
        return self._content


class WechatAssetsTests(unittest.TestCase):
    @patch("windows_client.collector.wechat_assets.urlopen")
    def test_build_wechat_article_artifacts_downloads_images_and_inserts_markers(self, urlopen) -> None:
        urlopen.return_value = _FakeResponse(media_type="image/png", content=b"png-bytes")

        annotated_html, artifacts = build_wechat_article_artifacts(
            """
            <html>
              <body>
                <div id="js_content">
                  <p>Lead paragraph.</p>
                  <img data-src="https://cdn.example.com/chart.png" alt="chart">
                </div>
              </body>
            </html>
            """,
            base_url="https://mp.weixin.qq.com/s/demo",
        )

        self.assertIn("[WeChat image 1]", annotated_html)
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(artifacts[0].role, "image_attachment")
        self.assertEqual(artifacts[0].media_type, "image/png")
        self.assertEqual(artifacts[1].role, "image_manifest")
        self.assertIn('"status": "downloaded"', artifacts[1].content or "")

    @patch("windows_client.collector.wechat_assets.urlopen")
    def test_build_wechat_article_artifacts_generates_unique_paths_for_duplicate_wechat_basenames(self, urlopen) -> None:
        urlopen.return_value = _FakeResponse(media_type="image/png", content=b"png-bytes")

        _, artifacts = build_wechat_article_artifacts(
            """
            <html>
              <body>
                <div id="js_content">
                  <img src="https://mmbiz.qpic.cn/sz_mmbiz_png/demo-a/640?wx_fmt=png">
                  <img src="https://mmbiz.qpic.cn/sz_mmbiz_png/demo-b/640?wx_fmt=png">
                  <img src="https://mmbiz.qpic.cn/sz_mmbiz_png/demo-c/640?wx_fmt=png">
                </div>
              </body>
            </html>
            """,
            base_url="https://mp.weixin.qq.com/s/demo",
        )

        image_artifacts = [artifact for artifact in artifacts if artifact.role == "image_attachment"]
        self.assertEqual(len(image_artifacts), 3)
        self.assertEqual(len({artifact.relative_path for artifact in image_artifacts}), 3)
        self.assertTrue(
            all(artifact.relative_path.startswith("attachments/source/wechat-images/image-640-") for artifact in image_artifacts)
        )

        manifest_artifact = next(artifact for artifact in artifacts if artifact.role == "image_manifest")
        manifest = json.loads(manifest_artifact.content or "{}")
        downloaded_paths = [entry["path"] for entry in manifest["images"] if entry.get("status") == "downloaded"]
        self.assertEqual(len(downloaded_paths), 3)
        self.assertEqual(len(set(downloaded_paths)), 3)


if __name__ == "__main__":
    unittest.main()
