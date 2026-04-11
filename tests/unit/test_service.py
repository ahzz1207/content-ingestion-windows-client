import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.app.service import WindowsClientService
from windows_client.collector.base import CollectedArtifact, CollectedPayload
from windows_client.collector.browser import BrowserLoginOptions
from windows_client.collector.http import HttpCollector
from windows_client.collector.mock import MockCollector
from windows_client.config.settings import Settings
from windows_client.job_exporter.exporter import JobExporter


class WindowsClientServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name) / "project-root"
        settings = Settings(project_root=self.project_root)
        self.service = WindowsClientService(
            settings=settings,
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=settings),
        )
        self.service.browser_collector.is_available.return_value = False
        self.service.browser_collector.availability_reason.return_value = "playwright_not_installed"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_doctor_reports_effective_shared_root(self) -> None:
        lines = list(self.service.doctor())
        self.assertTrue(any(line.startswith("project_root=") for line in lines))
        self.assertIn(f"shared_inbox_root={self.project_root / 'data' / 'shared_inbox'}", lines)
        self.assertIn(f"browser_profiles_dir={self.project_root / 'data' / 'browser-profiles'}", lines)
        self.assertIn("shared_inbox_exists=False", lines)
        self.assertIn("browser_default_headless=True", lines)
        self.assertIn("browser_default_wait_until=domcontentloaded", lines)
        self.assertIn("browser_default_timeout_ms=30000", lines)
        self.assertIn("browser_default_settle_ms=1000", lines)
        self.assertIn("browser_collector_available=False", lines)
        self.assertIn("browser_collector_reason=playwright_not_installed", lines)
        self.assertIn("video_downloader_available=False", lines)
        self.assertIn("video_downloader_reason=not_configured", lines)
        self.assertIn("video_js_runtime=none", lines)
        self.assertTrue(any(line.startswith("wsl_llm_credentials_available=") for line in lines))
        self.assertIn("wsl_whisper_model_override=default", lines)

    def test_export_mock_job_uses_settings_defaults(self) -> None:
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        result = service.export_mock_job(url="https://example.com/article")

        self.assertTrue(result.job_dir.exists())
        self.assertEqual(result.job_dir.parent.parent, self.project_root / "data" / "shared_inbox")
        self.assertEqual(result.payload_path.name, "payload.html")
        metadata = result.metadata_path.read_text(encoding="utf-8")
        self.assertIn('"collection_mode": "mock"', metadata)

    def test_export_mock_job_emits_collect_and_export_progress(self) -> None:
        stages: list[str] = []

        self.service.export_mock_job(
            url="https://example.com/article",
            on_progress=stages.append,
        )

        self.assertEqual(stages, ["collecting", "exporting"])

    def test_settings_can_take_shared_inbox_root_from_env(self) -> None:
        env_root = self.project_root / "external-shared-inbox"
        with patch.dict(os.environ, {"CONTENT_INGESTION_SHARED_INBOX_ROOT": str(env_root)}, clear=False):
            settings = Settings(project_root=self.project_root)
        self.assertEqual(settings.effective_shared_inbox_root, env_root)

    def test_export_browser_job_returns_clear_error_when_runtime_is_unavailable(self) -> None:
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )
        service.browser_collector.is_available.return_value = False
        service.browser_collector.availability_reason.return_value = "playwright_not_installed"
        service.browser_collector.collect.side_effect = WindowsClientError(
            "browser_runtime_unavailable",
            "browser collector unavailable: playwright_not_installed",
            stage="browser_collect",
            details={"reason": "playwright_not_installed"},
        )

        with self.assertRaises(WindowsClientError) as ctx:
            service.export_browser_job(url="https://example.com/article")
        self.assertEqual(ctx.exception.code, "browser_runtime_unavailable")

    def test_browser_login_uses_wechat_default_profile_path(self) -> None:
        mock_collector = MagicMock()
        mock_collector.open_profile_session.return_value = self.project_root / "data" / "browser-profiles" / "wechat"
        mock_collector.default_profile_slug.return_value = "wechat"
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=mock_collector,
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        result = service.browser_login(start_url="https://mp.weixin.qq.com/")

        self.assertEqual(result, self.project_root / "data" / "browser-profiles" / "wechat")
        options = mock_collector.open_profile_session.call_args.args[0]
        self.assertIsInstance(options, BrowserLoginOptions)
        self.assertEqual(options.start_url, "https://mp.weixin.qq.com/")
        self.assertEqual(options.profile_dir, self.project_root / "data" / "browser-profiles" / "wechat")
        self.assertEqual(options.wait_until, "domcontentloaded")
        self.assertEqual(options.timeout_ms, 30000)

    def test_browser_login_passes_completion_waiter_and_progress(self) -> None:
        mock_collector = MagicMock()
        mock_collector.open_profile_session.return_value = self.project_root / "data" / "browser-profiles" / "wechat"
        mock_collector.default_profile_slug.return_value = "wechat"
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=mock_collector,
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )
        completion_waiter = MagicMock()
        stages: list[str] = []

        service.browser_login(
            start_url="https://mp.weixin.qq.com/",
            completion_waiter=completion_waiter,
            on_progress=stages.append,
        )

        self.assertEqual(stages, ["opening_browser", "waiting_for_login"])
        self.assertEqual(
            mock_collector.open_profile_session.call_args.kwargs["completion_waiter"],
            completion_waiter,
        )

    def test_export_browser_job_uses_wechat_profile_and_selector_options_by_default(self) -> None:
        mock_collector = MagicMock()
        mock_collector.collect.return_value = CollectedPayload(
            source_url="https://mp.weixin.qq.com/s/demo",
            content_type="html",
            payload_text="<html><body>demo</body></html>",
            final_url="https://mp.weixin.qq.com/s/final-demo",
            platform="wechat",
            title_hint="Demo",
        )
        mock_collector.default_profile_slug.return_value = "wechat"
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=mock_collector,
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        result = service.export_browser_job(
            url="https://mp.weixin.qq.com/s/demo",
            wait_for_selector="#js_content",
            wait_for_selector_state="attached",
        )

        options = mock_collector.collect.call_args.kwargs["options"]
        self.assertEqual(options.profile_dir, self.project_root / "data" / "browser-profiles" / "wechat")
        self.assertEqual(options.wait_for_selector, "#js_content")
        self.assertEqual(options.wait_for_selector_state, "attached")
        self.assertTrue(result.job_dir.exists())
        metadata = result.metadata_path.read_text(encoding="utf-8")
        self.assertIn('"collection_mode": "browser"', metadata)
        self.assertIn('"profile_slug": "wechat"', metadata)
        self.assertIn('"wait_for_selector": "#js_content"', metadata)
        self.assertIn('"wait_for_selector_state": "attached"', metadata)
        self.assertIn('"final_url": "https://mp.weixin.qq.com/s/final-demo"', metadata)
        mock_collector.default_profile_slug.assert_called_once_with("https://mp.weixin.qq.com/s/demo")

    @patch("windows_client.app.service.build_wechat_article_artifacts")
    def test_export_url_job_attaches_wechat_images_and_markers(self, build_wechat_article_artifacts) -> None:
        build_wechat_article_artifacts.return_value = (
            "<html><body><p>[WeChat image 1] https://cdn.example.com/chart.png</p></body></html>",
            (
                CollectedArtifact(
                    relative_path="attachments/source/wechat-images/chart.png",
                    media_type="image/png",
                    role="image_attachment",
                    content=b"png-bytes",
                ),
            ),
        )
        url_collector = MagicMock()
        url_collector.collect.return_value = CollectedPayload(
            source_url="https://mp.weixin.qq.com/s/demo",
            content_type="html",
            payload_text="<html><body><img src='https://cdn.example.com/chart.png'></body></html>",
            final_url="https://mp.weixin.qq.com/s/demo",
            platform="wechat",
            content_shape="article",
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=url_collector,
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        result = service.export_url_job(url="https://mp.weixin.qq.com/s/demo")

        self.assertIn("[WeChat image 1]", result.payload_path.read_text(encoding="utf-8"))
        self.assertTrue((result.job_dir / "attachments" / "source" / "wechat-images" / "chart.png").exists())
        build_wechat_article_artifacts.assert_called_once()

    def test_export_browser_job_keeps_generic_urls_ephemeral_by_default(self) -> None:
        mock_collector = MagicMock()
        mock_collector.collect.return_value = CollectedPayload(
            source_url="https://example.com/article",
            content_type="html",
            payload_text="<html><body>demo</body></html>",
            platform="generic",
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=mock_collector,
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        service.export_browser_job(url="https://example.com/article")

        options = mock_collector.collect.call_args.kwargs["options"]
        self.assertIsNone(options.profile_dir)
        self.assertIsNone(options.wait_for_selector)
        mock_collector.default_profile_slug.assert_not_called()

    def test_export_url_job_downloads_video_artifacts_for_supported_video_platforms(self) -> None:
        video_source = self.project_root / "downloaded.mp3"
        video_source.parent.mkdir(parents=True, exist_ok=True)
        video_source.write_bytes(b"audio-bytes")
        video_downloader = MagicMock()
        video_downloader.supports.return_value = True
        video_downloader.download.return_value.cleanup_dir = self.project_root / "temp-video-download"
        video_downloader.download.return_value.cleanup_dir.mkdir(parents=True, exist_ok=True)
        video_downloader.download.return_value.artifacts = (
            CollectedArtifact(
                relative_path="attachments/video/video.mp3",
                media_type="audio/mpeg",
                role="audio_file",
                source_path=video_source,
            ),
        )
        video_downloader.download.return_value.title_hint = "Downloaded Video"
        video_downloader.download.return_value.author_hint = "Uploader A"
        video_downloader.download.return_value.published_at_hint = "2026-03-15 17:00:00"
        video_downloader.download.return_value.description_hint = "Short clean description"
        video_downloader.download.return_value.final_url = "https://www.bilibili.com/video/BV1demo/"

        url_collector = MagicMock()
        url_collector.collect.return_value = CollectedPayload(
            source_url="https://www.bilibili.com/video/BV1demo/",
            content_type="html",
            payload_text="<html><body>Video</body></html>",
            platform="bilibili",
            content_shape="video",
            title_hint="Dirty Title_bilibili",
            author_hint="Dirty Uploader",
            artifacts=(
                CollectedArtifact(
                    relative_path="attachments/source/raw.html",
                    media_type="text/html",
                    role="raw_capture",
                    content="<html><body>Raw html</body></html>",
                ),
            ),
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=url_collector,
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
            video_downloader=video_downloader,
        )

        result = service.export_url_job(url="https://www.bilibili.com/video/BV1demo/")

        copied_video = result.job_dir / "attachments" / "video" / "video.mp3"
        self.assertTrue(copied_video.exists())
        self.assertEqual(copied_video.read_bytes(), b"audio-bytes")
        payload_text = result.payload_path.read_text(encoding="utf-8")
        metadata_text = result.metadata_path.read_text(encoding="utf-8")
        self.assertIn("Downloaded Video", payload_text)
        self.assertIn("Uploader A", payload_text)
        self.assertIn("2026-03-15 17:00:00", payload_text)
        self.assertIn("Short clean description", payload_text)
        self.assertIn('"video_download_mode": "audio"', metadata_text)
        video_downloader.download.assert_called_once_with(
            "https://www.bilibili.com/video/BV1demo/",
            platform="bilibili",
            download_mode="audio",
            profile_dir=None,
        )
        self.assertFalse((self.project_root / "temp-video-download").exists())

    def test_export_browser_job_can_request_full_video_download(self) -> None:
        video_source = self.project_root / "downloaded.mp4"
        video_source.parent.mkdir(parents=True, exist_ok=True)
        video_source.write_bytes(b"video-bytes")
        video_downloader = MagicMock()
        video_downloader.supports.return_value = True
        video_downloader.download.return_value.cleanup_dir = None
        video_downloader.download.return_value.artifacts = (
            CollectedArtifact(
                relative_path="attachments/video/video.mp4",
                media_type="video/mp4",
                role="video_file",
                source_path=video_source,
            ),
        )
        video_downloader.download.return_value.title_hint = "Downloaded Video"
        video_downloader.download.return_value.author_hint = "Uploader A"
        video_downloader.download.return_value.published_at_hint = "2026-03-15 17:00:00"
        video_downloader.download.return_value.description_hint = "Short clean description"
        video_downloader.download.return_value.final_url = "https://www.bilibili.com/video/BV1demo/"

        browser_collector = MagicMock()
        browser_collector.collect.return_value = CollectedPayload(
            source_url="https://www.bilibili.com/video/BV1demo/",
            content_type="html",
            payload_text="<html><body>Video</body></html>",
            final_url="https://www.bilibili.com/video/BV1demo/",
            platform="bilibili",
            content_shape="video",
        )
        browser_collector.default_profile_slug.return_value = "bilibili"
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=HttpCollector(timeout_seconds=1.0),
            browser_collector=browser_collector,
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
            video_downloader=video_downloader,
        )

        service.export_browser_job(url="https://www.bilibili.com/video/BV1demo/", video_download_mode="video")

        video_downloader.download.assert_called_once_with(
            "https://www.bilibili.com/video/BV1demo/",
            platform="bilibili",
            download_mode="video",
            profile_dir=self.project_root / "data" / "browser-profiles" / "bilibili",
        )

    def test_export_url_job_uses_existing_bilibili_profile_for_video_download(self) -> None:
        profile_dir = self.project_root / "data" / "browser-profiles" / "bilibili"
        profile_dir.mkdir(parents=True, exist_ok=True)
        video_source = self.project_root / "downloaded.mp3"
        video_source.parent.mkdir(parents=True, exist_ok=True)
        video_source.write_bytes(b"audio-bytes")
        video_downloader = MagicMock()
        video_downloader.supports.return_value = True
        video_downloader.download.return_value.cleanup_dir = None
        video_downloader.download.return_value.artifacts = (
            CollectedArtifact(
                relative_path="attachments/video/video.mp3",
                media_type="audio/mpeg",
                role="audio_file",
                source_path=video_source,
            ),
        )
        video_downloader.download.return_value.title_hint = "Downloaded Video"
        video_downloader.download.return_value.author_hint = "Uploader A"
        video_downloader.download.return_value.published_at_hint = "2026-03-15 17:00:00"
        video_downloader.download.return_value.description_hint = "Short clean description"
        video_downloader.download.return_value.final_url = "https://www.bilibili.com/video/BV1demo/"

        url_collector = MagicMock()
        url_collector.collect.return_value = CollectedPayload(
            source_url="https://www.bilibili.com/video/BV1demo/",
            content_type="html",
            payload_text="<html><body>Video</body></html>",
            final_url="https://www.bilibili.com/video/BV1demo/",
            platform="bilibili",
            content_shape="video",
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=url_collector,
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
            video_downloader=video_downloader,
        )

        service.export_url_job(url="https://www.bilibili.com/video/BV1demo/")

        video_downloader.download.assert_called_once_with(
            "https://www.bilibili.com/video/BV1demo/",
            platform="bilibili",
            download_mode="audio",
            profile_dir=profile_dir,
        )

    def test_export_url_job_skips_video_download_when_mode_is_none(self) -> None:
        video_downloader = MagicMock()
        url_collector = MagicMock()
        url_collector.collect.return_value = CollectedPayload(
            source_url="https://www.bilibili.com/video/BV1demo/",
            content_type="html",
            payload_text="<html><body>Video</body></html>",
            platform="bilibili",
            content_shape="video",
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=url_collector,
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
            video_downloader=video_downloader,
        )

        result = service.export_url_job(
            url="https://www.bilibili.com/video/BV1demo/",
            video_download_mode=None,
        )

        self.assertTrue(result.payload_path.exists())
        video_downloader.download.assert_not_called()

    def test_export_url_job_persists_requested_mode_in_metadata(self) -> None:
        url_collector = MagicMock()
        url_collector.collect.return_value = CollectedPayload(
            source_url="https://example.com/guide",
            content_type="html",
            payload_text="<html><body>Guide</body></html>",
            platform="generic",
            content_shape="article",
        )
        service = WindowsClientService(
            settings=Settings(project_root=self.project_root),
            mock_collector=MockCollector(),
            url_collector=url_collector,
            browser_collector=MagicMock(),
            exporter=JobExporter(settings=Settings(project_root=self.project_root)),
        )

        result = service.export_url_job(url="https://example.com/guide", requested_mode="guide")

        metadata_text = result.metadata_path.read_text(encoding="utf-8")
        self.assertIn('"requested_mode": "guide"', metadata_text)

    def test_save_result_to_library_delegates_to_store(self) -> None:
        entry = MagicMock()
        self.service.library_store = MagicMock()
        self.service.library_store.save_entry.return_value.entry_id = "lib_0001"

        result = self.service.save_result_to_library(entry)

        self.service.library_store.save_entry.assert_called_once_with(entry)
        self.assertEqual(result.entry_id, "lib_0001")

    def test_restore_library_interpretation_delegates_to_store(self) -> None:
        self.service.library_store = MagicMock()
        self.service.library_store.restore_interpretation.return_value.entry_id = "lib_0001"

        result = self.service.restore_library_interpretation("lib_0001", "interp_1")

        self.service.library_store.restore_interpretation.assert_called_once_with(
            entry_id="lib_0001",
            interpretation_id="interp_1",
        )
        self.assertEqual(result.entry_id, "lib_0001")


if __name__ == "__main__":
    unittest.main()
