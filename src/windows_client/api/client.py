from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from windows_client.app.errors import WindowsClientError


class ContentIngestionClient:
    def __init__(self, *, base_url: str, api_token: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def submit_url(
        self,
        url: str,
        *,
        content_type: str | None = None,
        platform: str | None = None,
        video_download_mode: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
        }
        if content_type:
            payload["content_type"] = content_type
        if platform:
            payload["platform"] = platform
        if video_download_mode:
            payload["video_download_mode"] = video_download_mode
        return self._request("POST", "/ingest", body=payload)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/jobs/{job_id}")

    def delete_job(self, job_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/jobs/{job_id}")

    def get_job_result(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/jobs/{job_id}/result")

    def list_jobs(self, *, status: str | None = None, limit: int = 20, view: str | None = None) -> dict[str, Any]:
        query = {"limit": limit}
        if status:
            query["status"] = status
        if view:
            query["view"] = view
        return self._request("GET", f"/jobs?{urlencode(query)}")

    def _request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
        }
        data = None
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        request = Request(f"{self.base_url}{path}", method=method, headers=headers, data=data)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise WindowsClientError(
                "api_http_error",
                f"api request failed with status {exc.code}: {detail}",
                stage="api_client",
                details={"status_code": exc.code, "path": path},
                cause=exc,
            ) from exc
        except URLError as exc:
            raise WindowsClientError(
                "api_connection_error",
                f"failed to connect to api server: {self.base_url}",
                stage="api_client",
                details={"path": path},
                cause=exc,
            ) from exc
