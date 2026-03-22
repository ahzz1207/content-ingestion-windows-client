from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from windows_client.app.errors import WindowsClientError
from windows_client.collector.base import CollectedArtifact

SUPPORTED_VIDEO_PLATFORMS = {"bilibili", "youtube"}
SUPPORTED_DOWNLOAD_MODES = {"audio", "video"}
TEXT_SUFFIXES = {".json", ".description", ".vtt", ".srt", ".ass", ".lrc", ".txt"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_JS_RUNTIMES = ("deno", "node", "bun", "qjs", "qjs-ng", "quickjs")
BILIBILI_REQUEST_HEADERS = (
    "Referer:https://www.bilibili.com",
    "Origin:https://www.bilibili.com",
)


@dataclass(slots=True)
class VideoDownloadResult:
    artifacts: tuple[CollectedArtifact, ...]
    download_mode: str
    title_hint: str | None = None
    author_hint: str | None = None
    published_at_hint: str | None = None
    description_hint: str | None = None
    final_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cleanup_dir: Path | None = None


class YtDlpVideoDownloader:
    def __init__(
        self,
        *,
        python_executable: str | None = None,
        command_override: str | None = None,
        ffmpeg_command: str | None = None,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.command_override = command_override
        self.ffmpeg_command = ffmpeg_command

    def is_available(self) -> bool:
        return self._resolve_command_base() is not None

    def availability_reason(self) -> str:
        if self._resolve_command_base() is None:
            return "yt_dlp_not_installed"
        return "ok"

    def ffmpeg_available(self) -> bool:
        return self._resolve_ffmpeg_path() is not None

    def js_runtime(self) -> str | None:
        for runtime in SUPPORTED_JS_RUNTIMES:
            if shutil.which(runtime):
                return runtime
        return None

    def supports(self, *, url: str, platform: str) -> bool:
        if platform in SUPPORTED_VIDEO_PLATFORMS:
            return True
        host = urlparse(url).netloc.lower()
        return "bilibili.com" in host or "b23.tv" in host or "youtube.com" in host or "youtu.be" in host

    def download(
        self,
        url: str,
        *,
        platform: str,
        download_mode: str = "audio",
        profile_dir: Path | None = None,
    ) -> VideoDownloadResult:
        if platform not in SUPPORTED_VIDEO_PLATFORMS:
            raise WindowsClientError(
                "unsupported_video_platform",
                f"video download is not supported for platform: {platform}",
                stage="video_download",
                details={"platform": platform, "source_url": url},
            )
        if download_mode not in SUPPORTED_DOWNLOAD_MODES:
            raise WindowsClientError(
                "unsupported_video_download_mode",
                f"unsupported video download mode: {download_mode}",
                stage="video_download",
                details={"platform": platform, "source_url": url, "download_mode": download_mode},
            )
        if self._resolve_ffmpeg_path() is None:
            raise WindowsClientError(
                "video_download_requires_ffmpeg",
                "ffmpeg is required for video and audio extraction",
                stage="video_download",
                details={"platform": platform, "source_url": url, "download_mode": download_mode},
            )

        command_base = self._resolve_command_base()
        if command_base is None:
            raise WindowsClientError(
                "video_downloader_unavailable",
                "yt-dlp is required for video downloads but is not installed",
                stage="video_download",
                details={"platform": platform, "source_url": url},
            )

        temp_dir = Path(tempfile.mkdtemp(prefix="content-ingestion-video-"))
        output_template = temp_dir / "video.%(ext)s"
        command = self._build_command(
            command_base,
            url=url,
            output_template=output_template,
            platform=platform,
            download_mode=download_mode,
            profile_dir=profile_dir,
        )
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise WindowsClientError(
                "video_download_failed",
                f"yt-dlp failed to download video: {url}",
                stage="video_download",
                details={
                    "download_mode": download_mode,
                    "platform": platform,
                    "source_url": url,
                    "returncode": completed.returncode,
                    "stderr": completed.stderr.strip(),
                    "js_runtime": self.js_runtime() or "none",
                    "cookies_profile_dir": str(profile_dir) if profile_dir else "",
                },
            )

        try:
            info_payload = self._load_info_payload(temp_dir)
            artifacts = self._build_artifacts(
                temp_dir=temp_dir,
                platform=platform,
                source_url=url,
                download_mode=download_mode,
                info_payload=info_payload,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
            return VideoDownloadResult(
                artifacts=artifacts,
                download_mode=download_mode,
                title_hint=_optional_str(info_payload.get("title")),
                author_hint=_optional_str(info_payload.get("uploader")) or _optional_str(info_payload.get("channel")),
                published_at_hint=_normalize_publish_hint(info_payload),
                description_hint=_optional_str(info_payload.get("description")),
                final_url=_optional_str(info_payload.get("webpage_url")) or _optional_str(info_payload.get("original_url")),
                metadata={
                    "video_id": _optional_str(info_payload.get("id")),
                    "extractor": _optional_str(info_payload.get("extractor_key")) or _optional_str(info_payload.get("extractor")),
                    "ffmpeg_available": self.ffmpeg_available(),
                    "js_runtime": self.js_runtime() or "none",
                },
                cleanup_dir=temp_dir,
            )
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _resolve_command_base(self) -> list[str] | None:
        if self.command_override:
            return [self.command_override]
        if importlib.util.find_spec("yt_dlp") is not None:
            return [self.python_executable, "-m", "yt_dlp"]
        binary = shutil.which("yt-dlp")
        if binary:
            return [binary]
        return None

    def _build_command(
        self,
        command_base: list[str],
        *,
        url: str,
        output_template: Path,
        platform: str,
        download_mode: str,
        profile_dir: Path | None,
    ) -> list[str]:
        command = [*command_base]
        ffmpeg_path = self._resolve_ffmpeg_path()
        if ffmpeg_path:
            command.extend(["--ffmpeg-location", str(ffmpeg_path)])
        js_runtime = self.js_runtime()
        if platform == "youtube" and js_runtime:
            command.extend(["--js-runtimes", js_runtime])
        if profile_dir is not None and profile_dir.exists():
            command.extend(["--cookies-from-browser", f"chromium:{profile_dir}"])
        if platform == "bilibili":
            command.extend(["--extractor-retries", "3", "--retries", "3", "--sleep-requests", "1"])
            for header in BILIBILI_REQUEST_HEADERS:
                command.extend(["--add-headers", header])
        command.extend(
            [
                "--no-playlist",
                "--write-info-json",
                "--write-thumbnail",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                "all,-live_chat",
                "--output",
                str(output_template),
            ]
        )
        if download_mode == "audio":
            command.extend(
                [
                    "--extract-audio",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "0",
                ]
            )
        command.extend(["--format", self._format_selector(download_mode), url])
        return command

    def _format_selector(self, download_mode: str) -> str:
        if download_mode == "audio":
            return "ba/bestaudio/best"
        if self.ffmpeg_available():
            return "bv*+ba/b"
        return "best*[vcodec!=none][acodec!=none]/best"

    def _resolve_ffmpeg_path(self) -> str | None:
        if self.ffmpeg_command:
            resolved = shutil.which(self.ffmpeg_command)
            if resolved:
                return resolved
            if Path(self.ffmpeg_command).exists():
                return self.ffmpeg_command
        resolved = shutil.which("ffmpeg")
        if resolved:
            return resolved
        for candidate in _winget_ffmpeg_candidates():
            if candidate.exists():
                return str(candidate)
        return None

    def _load_info_payload(self, temp_dir: Path) -> dict[str, Any]:
        info_path = temp_dir / "video.info.json"
        if not info_path.exists():
            raise WindowsClientError(
                "video_info_missing",
                "yt-dlp did not produce video.info.json",
                stage="video_download",
                details={"expected_path": str(info_path)},
            )
        return json.loads(info_path.read_text(encoding="utf-8"))

    def _build_artifacts(
        self,
        *,
        temp_dir: Path,
        platform: str,
        source_url: str,
        download_mode: str,
        info_payload: dict[str, Any],
        stdout: str,
        stderr: str,
    ) -> tuple[CollectedArtifact, ...]:
        artifacts: list[CollectedArtifact] = []
        downloaded_files = sorted(path for path in temp_dir.iterdir() if path.is_file())
        primary_media = next(
            (path for path in downloaded_files if path.stem == "video" and _is_primary_media_file(path)),
            None,
        )
        if primary_media is None:
            raise WindowsClientError(
                "video_file_missing",
                "yt-dlp completed without producing a primary media file",
                stage="video_download",
                details={"platform": platform, "source_url": source_url, "download_mode": download_mode},
            )

        primary_role = "audio_file" if download_mode == "audio" else "video_file"
        artifacts.append(
            CollectedArtifact(
                relative_path=f"attachments/video/{primary_media.name}",
                media_type=_media_type_for_path(primary_media),
                role=primary_role,
                source_path=primary_media,
                description="Primary downloaded media file.",
            )
        )

        for path in downloaded_files:
            if path == primary_media:
                continue
            suffix = path.suffix.lower()
            if path.name == "video.info.json":
                role = "video_metadata"
            elif suffix in IMAGE_SUFFIXES:
                role = "thumbnail"
            elif suffix in TEXT_SUFFIXES:
                role = "subtitle" if ".vtt" in path.name or ".srt" in path.name or ".ass" in path.name or ".lrc" in path.name else "video_metadata"
            else:
                role = "video_auxiliary"
            artifacts.append(
                CollectedArtifact(
                    relative_path=f"attachments/video/{path.name}",
                    media_type=_media_type_for_path(path),
                    role=role,
                    source_path=path,
                    description=f"Video downloader artifact: {path.name}",
                )
            )

        report = {
            "downloader": "yt-dlp",
            "download_mode": download_mode,
            "platform": platform,
            "source_url": source_url,
            "video_id": _optional_str(info_payload.get("id")),
            "title": _optional_str(info_payload.get("title")),
            "uploader": _optional_str(info_payload.get("uploader")) or _optional_str(info_payload.get("channel")),
            "webpage_url": _optional_str(info_payload.get("webpage_url")),
            "extractor": _optional_str(info_payload.get("extractor_key")) or _optional_str(info_payload.get("extractor")),
            "format_id": _optional_str(info_payload.get("format_id")),
            "ext": _optional_str(info_payload.get("ext")),
            "ffmpeg_available": self.ffmpeg_available(),
            "js_runtime": self.js_runtime() or "none",
            "downloaded_files": [path.name for path in downloaded_files],
            "stdout_tail": stdout.strip().splitlines()[-10:],
            "stderr_tail": stderr.strip().splitlines()[-10:],
        }
        artifacts.append(
            CollectedArtifact(
                relative_path="attachments/video/download_report.json",
                media_type="application/json",
                role="video_download_report",
                content=json.dumps(report, ensure_ascii=False, indent=2),
                description="Summary of the yt-dlp video download run.",
            )
        )
        return tuple(artifacts)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _media_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".m4v": "video/x-m4v",
        ".json": "application/json",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".vtt": "text/vtt",
        ".srt": "application/x-subrip",
        ".ass": "text/x-ass",
        ".lrc": "text/plain",
    }.get(suffix, "application/octet-stream")


def _is_primary_media_file(path: Path) -> bool:
    return path.suffix.lower() not in TEXT_SUFFIXES | IMAGE_SUFFIXES


def _winget_ffmpeg_candidates() -> tuple[Path, ...]:
    local_appdata = Path.home() / "AppData" / "Local"
    packages_root = local_appdata / "Microsoft" / "WinGet" / "Packages"
    if not packages_root.exists():
        return ()
    return tuple(
        sorted(
            packages_root.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"),
            reverse=True,
        )
    )


def _normalize_publish_hint(info_payload: dict[str, Any]) -> str | None:
    timestamp = info_payload.get("timestamp")
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    upload_date = _optional_str(info_payload.get("upload_date"))
    if upload_date and len(upload_date) == 8 and upload_date.isdigit():
        return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return upload_date
