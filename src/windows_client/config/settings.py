import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    return value


def _read_path_env(name: str) -> Path | None:
    value = _read_env(name)
    if not value:
        return None
    return Path(value)


def _resolve_default_project_root() -> Path:
    override = _read_path_env("CONTENT_INGESTION_PROJECT_ROOT")
    if override is not None:
        return override
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: exe lives at {project_root}/dist/<name>.exe
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[3]


@dataclass(slots=True)
class Settings:
    project_root: Path = field(default_factory=_resolve_default_project_root)
    shared_inbox_root: Path | None = field(default_factory=lambda: _read_path_env("CONTENT_INGESTION_SHARED_INBOX_ROOT"))
    wsl_project_root: str = field(
        default_factory=lambda: os.getenv("CONTENT_INGESTION_WSL_PROJECT_ROOT", "/home/ahzz1207/codex-demo")
    )
    wsl_python_executable: str = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_WSL_PYTHON", "python3"))
    yt_dlp_command: str | None = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_YT_DLP_COMMAND"))
    ffmpeg_command: str | None = field(default_factory=lambda: os.getenv("CONTENT_INGESTION_FFMPEG_COMMAND"))
    openai_api_key: str | None = field(default_factory=lambda: _read_env("OPENAI_API_KEY"))
    openai_base_url: str | None = field(default_factory=lambda: _read_env("OPENAI_BASE_URL"))
    zenmux_api_key: str | None = field(default_factory=lambda: _read_env("ZENMUX_API_KEY"))
    zenmux_base_url: str | None = field(default_factory=lambda: _read_env("ZENMUX_BASE_URL"))
    analysis_model_override: str | None = field(default_factory=lambda: _read_env("CONTENT_INGESTION_ANALYSIS_MODEL"))
    multimodal_model_override: str | None = field(default_factory=lambda: _read_env("CONTENT_INGESTION_MULTIMODAL_MODEL"))
    whisper_model_override: str | None = field(default_factory=lambda: _read_env("CONTENT_INGESTION_WHISPER_MODEL"))
    default_content_type: str = "html"
    default_platform: str = "generic"
    browser_headless: bool = True
    browser_wait_until: str = "domcontentloaded"
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

    @property
    def llm_credentials_available(self) -> bool:
        return bool(self.openai_api_key or self.zenmux_api_key)

    @property
    def llm_provider_hint(self) -> str:
        if self.openai_api_key:
            return "openai"
        if self.zenmux_api_key:
            return "zenmux"
        return "missing"
