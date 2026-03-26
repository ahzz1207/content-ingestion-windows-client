from __future__ import annotations

import os
import secrets
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


@dataclass(slots=True)
class ApiConfig:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[3])
    shared_inbox_root: Path | None = field(default_factory=lambda: _read_path_env("CONTENT_INGESTION_SHARED_INBOX_ROOT"))
    host: str = field(default_factory=lambda: _read_env("CONTENT_INGESTION_API_HOST") or "127.0.0.1")
    port: int = field(default_factory=lambda: int(_read_env("CONTENT_INGESTION_API_PORT") or "19527"))
    api_token: str | None = field(default_factory=lambda: _read_env("CONTENT_INGESTION_API_TOKEN"))
    api_token_path: Path = field(default_factory=lambda: Path.home() / ".content-ingestion" / "api_token")

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def effective_shared_inbox_root(self) -> Path:
        if self.shared_inbox_root is not None:
            return self.shared_inbox_root
        return self.data_dir / "shared_inbox"

    def resolve_api_token(self) -> str | None:
        if self.api_token:
            return self.api_token
        if self.api_token_path.exists():
            token = self.api_token_path.read_text(encoding="utf-8").strip()
            return token or None
        return None

    def ensure_api_token(self) -> str:
        token = self.resolve_api_token()
        if token:
            return token
        token = secrets.token_urlsafe(24)
        self.api_token_path.parent.mkdir(parents=True, exist_ok=True)
        self.api_token_path.write_text(token, encoding="utf-8")
        return token
