import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.video_downloader import YtDlpVideoDownloader


class YtDlpVideoDownloaderTests(unittest.TestCase):
    def test_availability_reason_reports_missing_command(self) -> None:
        downloader = YtDlpVideoDownloader(command_override=None)
        with patch("windows_client.video_downloader.yt_dlp_downloader.importlib.util.find_spec", return_value=None):
            with patch("windows_client.video_downloader.yt_dlp_downloader.shutil.which", return_value=None):
                self.assertFalse(downloader.is_available())
                self.assertEqual(downloader.availability_reason(), "yt_dlp_not_installed")

    def test_download_collects_video_info_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name) / "download-run"

            def _fake_run(command, capture_output, text, encoding, errors):
                output_template = Path(command[command.index("--output") + 1])
                temp_dir.mkdir(parents=True, exist_ok=True)
                (temp_dir / "video.mp3").write_bytes(b"audio-bytes")
                (temp_dir / "video.info.json").write_text(
                    json.dumps(
                        {
                            "id": "demo123",
                            "title": "Demo Video",
                            "uploader": "Uploader A",
                            "webpage_url": "https://www.youtube.com/watch?v=demo123",
                            "extractor_key": "Youtube",
                            "format_id": "18",
                            "ext": "mp4",
                        }
                    ),
                    encoding="utf-8",
                )
                (temp_dir / "video.en.vtt").write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nhello", encoding="utf-8")
                (temp_dir / "video.webp").write_bytes(b"image-bytes")

                class _Completed:
                    returncode = 0
                    stdout = "[download] 100%"
                    stderr = ""

                self.assertEqual(output_template.parent, temp_dir)
                return _Completed()

            downloader = YtDlpVideoDownloader(command_override="yt-dlp")
            with patch("windows_client.video_downloader.yt_dlp_downloader.tempfile.mkdtemp", return_value=str(temp_dir)):
                with patch("windows_client.video_downloader.yt_dlp_downloader.subprocess.run", side_effect=_fake_run):
                    result = downloader.download("https://www.youtube.com/watch?v=demo123", platform="youtube")

            artifact_paths = {artifact.relative_path for artifact in result.artifacts}
            self.assertIn("attachments/video/video.mp3", artifact_paths)
            self.assertIn("attachments/video/video.info.json", artifact_paths)
            self.assertIn("attachments/video/video.en.vtt", artifact_paths)
            self.assertIn("attachments/video/video.webp", artifact_paths)
            self.assertIn("attachments/video/download_report.json", artifact_paths)
            self.assertEqual(result.title_hint, "Demo Video")
            self.assertEqual(result.author_hint, "Uploader A")
            self.assertEqual(result.final_url, "https://www.youtube.com/watch?v=demo123")
            self.assertEqual(result.cleanup_dir, temp_dir)
            self.assertEqual(result.download_mode, "audio")

    def test_download_requires_ffmpeg_for_bilibili(self) -> None:
        downloader = YtDlpVideoDownloader(command_override="yt-dlp")
        with patch.object(downloader, "_resolve_ffmpeg_path", return_value=None):
            with self.assertRaises(WindowsClientError) as ctx:
                downloader.download("https://www.bilibili.com/video/BV1demo/", platform="bilibili")
        self.assertEqual(ctx.exception.code, "video_download_requires_ffmpeg")

    def test_build_command_adds_bilibili_retry_headers_and_ffmpeg_location(self) -> None:
        downloader = YtDlpVideoDownloader(command_override="yt-dlp")
        with patch.object(downloader, "_resolve_ffmpeg_path", return_value="C:\\ffmpeg\\bin\\ffmpeg.exe"):
            command = downloader._build_command(
                ["yt-dlp"],
                url="https://www.bilibili.com/video/BV1demo/",
                output_template=Path("C:/temp/video.%(ext)s"),
                platform="bilibili",
                download_mode="video",
                profile_dir=None,
            )
        self.assertIn("--ffmpeg-location", command)
        self.assertIn("C:\\ffmpeg\\bin\\ffmpeg.exe", command)
        self.assertIn("--extractor-retries", command)
        self.assertIn("--retries", command)
        self.assertIn("--sleep-requests", command)
        self.assertIn("Referer:https://www.bilibili.com", command)
        self.assertIn("Origin:https://www.bilibili.com", command)

    def test_build_command_uses_audio_extraction_by_default(self) -> None:
        downloader = YtDlpVideoDownloader(command_override="yt-dlp")
        with patch.object(downloader, "_resolve_ffmpeg_path", return_value="C:\\ffmpeg\\bin\\ffmpeg.exe"):
            command = downloader._build_command(
                ["yt-dlp"],
                url="https://www.bilibili.com/video/BV1demo/",
                output_template=Path("C:/temp/video.%(ext)s"),
                platform="bilibili",
                download_mode="audio",
                profile_dir=None,
            )
        self.assertIn("--extract-audio", command)
        self.assertIn("--audio-format", command)
        self.assertIn("mp3", command)
        self.assertIn("ba/bestaudio/best", command)

    def test_ffmpeg_available_discovers_winget_installation(self) -> None:
        downloader = YtDlpVideoDownloader(command_override="yt-dlp")
        with tempfile.TemporaryDirectory() as temp_dir_name:
            ffmpeg_path = Path(temp_dir_name) / "ffmpeg.exe"
            ffmpeg_path.write_bytes(b"")
            with patch("windows_client.video_downloader.yt_dlp_downloader.shutil.which", return_value=None):
                with patch(
                    "windows_client.video_downloader.yt_dlp_downloader._winget_ffmpeg_candidates",
                    return_value=(ffmpeg_path,),
                ):
                    self.assertTrue(downloader.ffmpeg_available())

    def test_download_raises_clear_error_when_info_json_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name) / "download-run"

            def _fake_run(command, capture_output, text, encoding, errors):
                temp_dir.mkdir(parents=True, exist_ok=True)
                (temp_dir / "video.mp4").write_bytes(b"video-bytes")

                class _Completed:
                    returncode = 0
                    stdout = ""
                    stderr = ""

                return _Completed()

            downloader = YtDlpVideoDownloader(command_override="yt-dlp")
            with patch("windows_client.video_downloader.yt_dlp_downloader.tempfile.mkdtemp", return_value=str(temp_dir)):
                with patch("windows_client.video_downloader.yt_dlp_downloader.subprocess.run", side_effect=_fake_run):
                    with self.assertRaises(WindowsClientError) as ctx:
                        downloader.download("https://www.youtube.com/watch?v=demo123", platform="youtube")
            self.assertEqual(ctx.exception.code, "video_info_missing")


if __name__ == "__main__":
    unittest.main()
