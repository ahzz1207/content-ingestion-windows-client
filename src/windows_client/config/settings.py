import os
from dataclasses import dataclass, field
from pathlib import Path


def _read_path_env(name: str) -> Path | None:
    value = os.getenv(name)
    if not value:
        return None
    return Path(value)


@dataclass(slots=True)
class Settings:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[3])
    shared_inbox_root: Path | None = field(default_factory=lambda: _read_path_env("CONTENT_INGESTION_SHARED_INBOX_ROOT"))
    wsl_project_root: str = field(
        default_factory=lambda: os.getenv("CONTENT_INGESTION_WSL_PROJECT_ROOT", "/home/ahzz1207/codex-demo")
    )
    wsl_python_executable: str = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_WSL_PYTHON", "python3"))
    yt_dlp_command: str | None = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_YT_DLP_COMMAND"))
    ffmpeg_command: str | None = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_FFMPEG_COMMAND"))
    default_content_type: str = "html"
    default_platform: str = "generic"
    browser_headless: bool = True
    browser_wait_until: str = "networkidle"
    browser_timeout_ms: int = 30000
    browser_settle_ms: int = 1000

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def effective_shared_inbox_root(self) -> Path:
        if self.shared_inbox_root is not None:
            return self.shared_inbox_root
        return self.data_dir / "shared_inbox"

    @property
    def browser_profiles_dir(self) -> Path:
        return self.data_dir / "browser-profiles"

    @property
    def wsl_watch_state_path(self) -> Path:
        return self.data_dir / "wsl-watch-state.json"

    @property
    def wsl_watch_log_path(self) -> Path:
        return self.data_dir / "wsl-watch.log"
