from __future__ import annotations

from typing import Any

from windows_client import __version__
from windows_client.api.auth import verify_api_token
from windows_client.api.config import ApiConfig
from windows_client.api.job_manager import JobManager, STATUS_TO_DIR
from windows_client.app.cli import build_service
from windows_client.app.wsl_bridge import WslBridge
from windows_client.config.settings import Settings

_FASTAPI_IMPORT_ERROR: Exception | None = None

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
    from fastapi.middleware.cors import CORSMiddleware
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    _FASTAPI_IMPORT_ERROR = exc
    CORSMiddleware = Depends = FastAPI = Header = HTTPException = Query = status = None  # type: ignore[assignment]


def fastapi_available() -> bool:
    return _FASTAPI_IMPORT_ERROR is None


def create_app(*, config: ApiConfig | None = None, manager: JobManager | None = None):
    if _FASTAPI_IMPORT_ERROR is not None:  # pragma: no cover - exercised in CLI/tests by import guard
        raise ModuleNotFoundError("fastapi is required for the local API server") from _FASTAPI_IMPORT_ERROR

    resolved_config = config or ApiConfig()
    resolved_config.ensure_api_token()
    resolved_manager = manager or JobManager(
        service=build_service(resolved_config.effective_shared_inbox_root),
        shared_inbox_root=resolved_config.effective_shared_inbox_root,
    )
    app = FastAPI(title="Content Ingestion API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
        if not verify_api_token(provided_token=token, expected_token=resolved_config.resolve_api_token()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid api token",
            )

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        watcher = _get_watcher_status(resolved_config.effective_shared_inbox_root)
        return {
            "status": "ok",
            "version": __version__,
            "shared_inbox_root": str(resolved_config.effective_shared_inbox_root),
            "watcher": watcher,
            "statuses": dict(STATUS_TO_DIR),
        }

    @app.post("/api/v1/ingest", status_code=status.HTTP_201_CREATED)
    def ingest(
        payload: dict[str, Any],
        _: None = Depends(require_auth),
    ) -> dict[str, Any]:
        url = str(payload.get("url") or "").strip()
        if not url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="url is required",
            )
        job = resolved_manager.submit_url(
            url=url,
            content_type=_optional_text(payload.get("content_type")),
            platform=_optional_text(payload.get("platform")),
            video_download_mode=_optional_text(payload.get("video_download_mode")),
        )
        return job.to_dict()

    @app.get("/api/v1/jobs")
    def list_jobs(
        status_filter: str | None = Query(default=None, alias="status"),
        view: str = Query(default="summary"),
        limit: int = Query(default=20, ge=1, le=200),
        _: None = Depends(require_auth),
    ) -> dict[str, Any]:
        statuses = _parse_status_filter(status_filter)
        if view == "summary":
            result = resolved_manager.list_jobs(statuses=statuses, limit=limit)
        elif view == "result_cards":
            result = resolved_manager.list_result_cards(statuses=statuses, limit=limit)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="view must be one of: summary, result_cards",
            )
        return result.to_dict()

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str, _: None = Depends(require_auth)) -> dict[str, Any]:
        result = resolved_manager.get_job(job_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return result.to_dict()

    @app.delete("/api/v1/jobs/{job_id}")
    def delete_job(job_id: str, _: None = Depends(require_auth)) -> dict[str, Any]:
        result = resolved_manager.archive_job(job_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return {
            "job_id": result.job_id,
            "archived": True,
            "previous_status": result.status,
        }

    @app.get("/api/v1/jobs/{job_id}/result")
    def get_job_result(job_id: str, _: None = Depends(require_auth)) -> dict[str, Any]:
        result = resolved_manager.get_job_result(job_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        if result.status in {"queued", "processing"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"result is not available while job is {result.status}",
            )
        return result.to_dict()

    return app


def run_server(*, config: ApiConfig | None = None) -> None:
    if _FASTAPI_IMPORT_ERROR is not None:  # pragma: no cover - environment dependent
        raise ModuleNotFoundError("fastapi is required for the local API server") from _FASTAPI_IMPORT_ERROR

    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise ModuleNotFoundError("uvicorn is required for the local API server") from exc

    resolved_config = config or ApiConfig()
    app = create_app(config=resolved_config)
    uvicorn.run(app, host=resolved_config.host, port=resolved_config.port)


def _parse_status_filter(status_filter: str | None) -> list[str] | None:
    if not status_filter:
        return None
    items = [item.strip() for item in status_filter.split(",")]
    return [item for item in items if item in STATUS_TO_DIR]


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get_watcher_status(shared_inbox_root: object) -> dict[str, Any]:
    try:
        from pathlib import Path
        bridge = WslBridge(Settings(shared_inbox_root=Path(str(shared_inbox_root))))
        raw = bridge.watch_status()
        if raw is None:
            return {"running": False}
        return {
            "running": raw.get("running") == "True",
            "pid": raw.get("pid"),
            "shared_root": raw.get("shared_root"),
            "log_path": raw.get("log_path"),
            "started_at": raw.get("started_at"),
        }
    except Exception as exc:
        return {"running": False, "error": str(exc) or "status unavailable"}
