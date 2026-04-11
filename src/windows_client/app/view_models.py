from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from windows_client.app.errors import WindowsClientError
from windows_client.job_exporter.models import ExportResult


@dataclass(slots=True)
class GuiErrorState:
    code: str
    stage: str
    message: str
    details: dict[str, object] = field(default_factory=dict)
    cause_type: str | None = None


@dataclass(slots=True)
class DoctorSnapshot:
    lines: list[str]
    values: dict[str, str]


@dataclass(slots=True)
class JobExportSnapshot:
    job_id: str
    job_dir: Path
    payload_path: Path
    metadata_path: Path
    ready_path: Path


@dataclass(slots=True)
class BrowserSessionSnapshot:
    profile_dir: Path


@dataclass(slots=True)
class LibrarySnapshot:
    entry_id: str
    trashed_interpretation_count: int = 0


@dataclass(slots=True)
class OperationViewState:
    operation: str
    status: str
    summary: str
    doctor: DoctorSnapshot | None = None
    job: JobExportSnapshot | None = None
    browser_session: BrowserSessionSnapshot | None = None
    library: LibrarySnapshot | None = None
    error: GuiErrorState | None = None


def doctor_snapshot(lines: list[str]) -> DoctorSnapshot:
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return DoctorSnapshot(lines=lines, values=values)


def job_export_snapshot(result: ExportResult) -> JobExportSnapshot:
    return JobExportSnapshot(
        job_id=result.job_id,
        job_dir=result.job_dir,
        payload_path=result.payload_path,
        metadata_path=result.metadata_path,
        ready_path=result.ready_path,
    )


def error_state(error: WindowsClientError) -> GuiErrorState:
    return GuiErrorState(
        code=error.code,
        stage=error.stage,
        message=error.message,
        details=dict(error.details),
        cause_type=type(error.__cause__).__name__ if error.__cause__ is not None else None,
    )
