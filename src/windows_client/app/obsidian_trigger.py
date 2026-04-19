"""Open `obsidian://` URIs to trigger the companion Obsidian plugin.

The plugin already knows how to import a completed job into the user's
vault (`main.ts::importCompletedJob`). We just need to wake it up. A
deep-linking URI is the least invasive integration: Obsidian registers
the scheme on install, Windows hands the URI off via `os.startfile`, and
the plugin's protocol handler runs the import on the vault side.
"""
from __future__ import annotations

import os
import subprocess
import sys
from urllib.parse import quote

from windows_client.app.errors import WindowsClientError


OBSIDIAN_IMPORT_PATH = "content-ingestion-import"


def build_import_uri(job_id: str) -> str:
    if not isinstance(job_id, str) or not job_id.strip():
        raise WindowsClientError(
            "invalid_job_id",
            "job_id is required to build obsidian import URI",
            stage="obsidian_trigger",
            details={"job_id": repr(job_id)},
        )
    return f"obsidian://{OBSIDIAN_IMPORT_PATH}?jobId={quote(job_id, safe='')}"


def trigger_obsidian_import(job_id: str) -> str:
    """Fire the `obsidian://...` URI so the plugin imports the job into the vault.

    Returns the URI that was dispatched. Raises WindowsClientError if the
    OS-level handoff failed — Obsidian not installed, or the URI scheme not
    registered.
    """
    uri = build_import_uri(job_id)
    try:
        if sys.platform == "win32":
            os.startfile(uri)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", uri], check=True)
        else:
            subprocess.run(["xdg-open", uri], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WindowsClientError(
            "obsidian_uri_launch_failed",
            "failed to open obsidian:// URI — is Obsidian installed with the plugin enabled?",
            stage="obsidian_trigger",
            details={"uri": uri, "job_id": job_id},
            cause=exc,
        ) from exc
    return uri
