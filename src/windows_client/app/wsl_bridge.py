import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from windows_client.app.errors import WindowsClientError
from windows_client.config.settings import Settings


@dataclass(slots=True)
class WslWatchState:
    pid: int
    shared_root: str
    interval_seconds: float
    log_path: str
    started_at: str


class WslBridge:
    _ENV_PASSTHROUGH_KEYS = (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "ZENMUX_API_KEY",
        "ZENMUX_BASE_URL",
        "CONTENT_INGESTION_ANALYSIS_MODEL",
        "CONTENT_INGESTION_MULTIMODAL_MODEL",
        "CONTENT_INGESTION_WHISPER_MODEL",
        "CONTENT_INGESTION_IMAGE_CARD_MODEL",
        "CONTENT_INGESTION_IMAGE_CARD_API_KEY",
        "CONTENT_INGESTION_IMAGE_CARD_BASE_URL",
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def doctor(self, *, shared_root: Path | None = None) -> str:
        resolved = shared_root or self.settings.effective_shared_inbox_root
        return self._run_app_command("doctor", shared_root=resolved).stdout.strip()

    def validate_inbox(self, *, shared_root: Path | None = None) -> str:
        resolved = shared_root or self.settings.effective_shared_inbox_root
        return self._run_app_command("validate-inbox", shared_root=resolved).stdout.strip()

    def watch_once(self, *, shared_root: Path | None = None) -> str:
        resolved = shared_root or self.settings.effective_shared_inbox_root
        wsl_path = self._to_wsl_path(resolved)
        return self._run_app_command(
            f"watch-inbox {self._shell_quote(wsl_path)} --once", shared_root=resolved
        ).stdout.strip()

    def start_watch(
        self,
        *,
        shared_root: Path | None = None,
        interval_seconds: float = 2.0,
    ) -> WslWatchState:
        if interval_seconds <= 0:
            raise WindowsClientError(
                "invalid_interval_seconds",
                f"interval_seconds must be positive: {interval_seconds}",
                stage="wsl_watch",
                details={"interval_seconds": interval_seconds},
            )
        current = self.watch_status()
        if current is not None and current.get("running") == "True":
            raise WindowsClientError(
                "wsl_watch_already_running",
                "WSL watcher is already running",
                stage="wsl_watch",
                details={"pid": current["pid"], "log_path": current["log_path"]},
            )

        shared_root_path = shared_root or self.settings.effective_shared_inbox_root
        shared_root_path.mkdir(parents=True, exist_ok=True)
        self.settings.wsl_watch_log_path.parent.mkdir(parents=True, exist_ok=True)
        wsl_shared_root = self._to_wsl_path(shared_root_path)
        wsl_log_path = self._to_wsl_path(self.settings.wsl_watch_log_path)
        interval_value = f"{interval_seconds:g}"
        exports = self._build_exports(shared_root=shared_root_path)
        exports.extend(
            [
                f"cd {self._shell_quote(self.settings.wsl_project_root)}",
                (
                    f"{self.settings.wsl_python_executable} main.py watch-inbox "
                    f"{self._shell_quote(wsl_shared_root)} "
                    f"--interval-seconds {interval_value} > {self._shell_quote(wsl_log_path)} 2>&1"
                ),
            ]
        )
        script = "; ".join(exports)
        detach_flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        process = subprocess.Popen(
            ["wsl.exe", "-e", "bash", "-lc", script],
            close_fds=True,
            creationflags=detach_flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        state = WslWatchState(
            pid=process.pid,
            shared_root=str(shared_root_path),
            interval_seconds=interval_seconds,
            log_path=str(self.settings.wsl_watch_log_path),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._write_watch_state(state)
        return state

    def ensure_watch_running(
        self,
        *,
        shared_root: Path | None = None,
        interval_seconds: float = 2.0,
    ) -> dict[str, str]:
        current = self.watch_status()
        if current is not None and current.get("running") == "True":
            result = dict(current)
            result["status"] = "already_running"
            return result

        state = self.start_watch(shared_root=shared_root, interval_seconds=interval_seconds)
        return {
            "status": "started",
            "running": "True",
            "pid": str(state.pid),
            "shared_root": state.shared_root,
            "interval_seconds": f"{state.interval_seconds:g}",
            "log_path": state.log_path,
            "started_at": state.started_at,
            "launcher": "wsl.exe",
        }

    def watch_status(self) -> dict[str, str] | None:
        state = self._read_watch_state()
        if state is None:
            return None
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {state.pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # tasklist output may be GBK on Chinese Windows; decode with both
        stdout_raw = result.stdout
        stdout = stdout_raw.decode("gbk", errors="replace").strip()
        if not stdout:
            stdout = stdout_raw.decode("utf-8", errors="replace").strip()
        # Process not found: returncode non-zero, empty output, or the CSV
        # output does not quote the image name (meaning no matching row).
        # We detect "process found" by checking whether the output contains
        # a quoted CSV token — tasklist /FO CSV /NH emits lines like
        # "wsl.exe","75920",... only when a match exists.
        process_found = result.returncode == 0 and '"' in stdout
        if not process_found:
            return {
                "running": "False",
                "pid": str(state.pid),
                "shared_root": state.shared_root,
                "interval_seconds": f"{state.interval_seconds:g}",
                "log_path": state.log_path,
                "started_at": state.started_at,
            }
        return {
            "running": "True",
            "pid": str(state.pid),
            "shared_root": state.shared_root,
            "interval_seconds": f"{state.interval_seconds:g}",
            "log_path": state.log_path,
            "started_at": state.started_at,
            "launcher": "wsl.exe",
        }

    def stop_watch(self) -> dict[str, str]:
        state = self._read_watch_state()
        if state is None:
            return {"stopped": "False", "reason": "not_started"}
        result = subprocess.run(
            ["taskkill", "/PID", str(state.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stopped = result.returncode == 0
        if stopped and self.settings.wsl_watch_state_path.exists():
            self.settings.wsl_watch_state_path.unlink()
        return {
            "stopped": "True" if stopped else "False",
            "pid": str(state.pid),
            "log_path": state.log_path,
            "shared_root": state.shared_root,
        }

    def smoke_http(self, *, url: str, job_id: str, shared_root: Path | None = None) -> dict[str, str]:
        shared_root_path = shared_root or self.settings.effective_shared_inbox_root
        validate_output = self.validate_inbox(shared_root=shared_root_path)
        watch_output = self.watch_once(shared_root=shared_root_path)
        processed_dir = shared_root_path / "processed" / job_id
        failed_dir = shared_root_path / "failed" / job_id
        state = "processed" if processed_dir.exists() else "failed" if failed_dir.exists() else "missing"
        output_dir = processed_dir if processed_dir.exists() else failed_dir
        return {
            "url": url,
            "job_id": job_id,
            "shared_root": str(shared_root_path),
            "validate_output": validate_output,
            "watch_output": watch_output,
            "result_state": state,
            "result_dir": str(output_dir) if output_dir.exists() else "",
        }

    def _read_watch_state(self) -> WslWatchState | None:
        path = self.settings.wsl_watch_state_path
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return WslWatchState(**payload)

    def _write_watch_state(self, state: WslWatchState) -> None:
        path = self.settings.wsl_watch_state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")

    def _run_command(
        self,
        command: str,
        *,
        shared_root: Path | None = None,
        check: bool = True,
        capture_label: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        exports = self._build_exports(shared_root=shared_root)
        exports.append(f"cd {self._shell_quote(self.settings.wsl_project_root)}")
        exports.append(command)
        script = "; ".join(exports)
        result = subprocess.run(
            ["wsl.exe", "-e", "bash", "-lc", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if check and result.returncode != 0:
            raise WindowsClientError(
                "wsl_command_failed",
                f"WSL command failed: {capture_label or command}",
                stage="wsl_bridge",
                details={
                    "command": capture_label or command,
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                },
            )
        return result

    def _run_app_command(
        self,
        command: str,
        *,
        shared_root: Path | None = None,
        check: bool = True,
        capture_label: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self._run_command(
            f"{self.settings.wsl_python_executable} main.py {command}",
            shared_root=shared_root,
            check=check,
            capture_label=capture_label or command,
        )

    def _to_wsl_path(self, path: Path) -> str:
        raw = str(path)
        if raw.startswith("/"):
            return raw
        windows = PureWindowsPath(raw)
        if windows.drive:
            drive = windows.drive.rstrip(":").lower()
            parts = [part for part in windows.parts[1:] if part not in ("\\", "/")]
            suffix = "/".join(parts)
            return f"/mnt/{drive}/{suffix}" if suffix else f"/mnt/{drive}"
        return raw.replace("\\", "/")

    def _shell_quote(self, value: str) -> str:
        return "'" + value.replace("'", "'\"'\"'") + "'"

    def _build_exports(self, *, shared_root: Path | None) -> list[str]:
        exports: list[str] = []
        if shared_root is not None:
            exports.append(
                f"export CONTENT_INGESTION_SHARED_INBOX_ROOT={self._shell_quote(self._to_wsl_path(shared_root))}"
            )
        for key in self._ENV_PASSTHROUGH_KEYS:
            value = os.environ.get(key)
            if value:
                exports.append(f"export {key}={self._shell_quote(value)}")
        return exports
