import argparse
import os
import subprocess
import sys
from pathlib import Path

from windows_client.app.errors import WindowsClientError
from windows_client.app.service import WindowsClientService
from windows_client.app.wsl_bridge import WslBridge
from windows_client.collector.browser import (
    BrowserCollector,
    SUPPORTED_WAIT_FOR_SELECTOR_STATES,
    SUPPORTED_WAIT_UNTIL,
)
from windows_client.collector.http import HttpCollector
from windows_client.collector.mock import MockCollector
from windows_client.config.settings import Settings
from windows_client.job_exporter.exporter import JobExporter
from windows_client.video_downloader import YtDlpVideoDownloader

_GUI_DETACHED_ENV = "WINDOWS_CLIENT_GUI_DETACHED"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="windows-client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--shared-root", type=Path)

    login = subparsers.add_parser("browser-login")
    login.add_argument("--start-url")
    login.add_argument("--profile-dir", type=Path)
    login.add_argument("--browser-channel")
    login.add_argument("--wait-until", choices=tuple(sorted(SUPPORTED_WAIT_UNTIL)))
    login.add_argument("--timeout-ms", type=int)

    export_mock = subparsers.add_parser("export-mock-job")
    export_mock.add_argument("url")
    export_mock.add_argument("--shared-root", type=Path)
    export_mock.add_argument("--content-type", choices=("html", "txt", "md"))
    export_mock.add_argument("--platform")

    export_url = subparsers.add_parser("export-url-job")
    export_url.add_argument("url")
    export_url.add_argument("--shared-root", type=Path)
    export_url.add_argument("--content-type", choices=("html", "txt", "md"))
    export_url.add_argument("--platform")
    export_url.add_argument("--video-download-mode", choices=("audio", "video"), default="audio")

    export_browser = subparsers.add_parser("export-browser-job")
    export_browser.add_argument("url")
    export_browser.add_argument("--shared-root", type=Path)
    export_browser.add_argument("--platform")
    export_browser.add_argument("--video-download-mode", choices=("audio", "video"), default="audio")
    export_browser.add_argument("--profile-dir", type=Path)
    export_browser.add_argument("--browser-channel")
    export_browser.add_argument("--wait-until", choices=tuple(sorted(SUPPORTED_WAIT_UNTIL)))
    export_browser.add_argument("--timeout-ms", type=int)
    export_browser.add_argument("--settle-ms", type=int)
    export_browser.add_argument("--wait-for-selector")
    export_browser.add_argument("--wait-for-selector-state", choices=tuple(sorted(SUPPORTED_WAIT_FOR_SELECTOR_STATES)))
    export_browser.add_argument("--headed", action="store_true")

    gui = subparsers.add_parser("gui")
    gui.add_argument("--debug-console", action="store_true")

    wsl_doctor = subparsers.add_parser("wsl-doctor")
    wsl_doctor.add_argument("--shared-root", type=Path)

    wsl_validate = subparsers.add_parser("wsl-validate-inbox")
    wsl_validate.add_argument("--shared-root", type=Path)

    wsl_watch_once = subparsers.add_parser("wsl-watch-once")
    wsl_watch_once.add_argument("--shared-root", type=Path)

    wsl_start_watch = subparsers.add_parser("wsl-start-watch")
    wsl_start_watch.add_argument("--shared-root", type=Path)
    wsl_start_watch.add_argument("--interval-seconds", type=float, default=2.0)

    subparsers.add_parser("wsl-watch-status")
    subparsers.add_parser("wsl-stop-watch")

    full_chain_smoke = subparsers.add_parser("full-chain-smoke")
    full_chain_smoke.add_argument("url")
    full_chain_smoke.add_argument("--shared-root", type=Path)
    full_chain_smoke.add_argument("--content-type", choices=("html", "txt", "md"))
    full_chain_smoke.add_argument("--platform")
    full_chain_smoke.add_argument("--video-download-mode", choices=("audio", "video"), default="audio")

    return parser


def build_service(shared_root: Path | None = None) -> WindowsClientService:
    settings_kwargs = {"shared_inbox_root": shared_root} if shared_root is not None else {}
    settings = Settings(**settings_kwargs)
    exporter = JobExporter(settings=settings)
    mock_collector = MockCollector()
    url_collector = HttpCollector()
    browser_collector = BrowserCollector(timeout_ms=settings.browser_timeout_ms)
    video_downloader = YtDlpVideoDownloader(
        python_executable=sys.executable,
        command_override=settings.yt_dlp_command,
        ffmpeg_command=settings.ffmpeg_command,
    )
    return WindowsClientService(
        settings=settings,
        mock_collector=mock_collector,
        url_collector=url_collector,
        browser_collector=browser_collector,
        exporter=exporter,
        video_downloader=video_downloader,
    )


def build_wsl_bridge(shared_root: Path | None = None) -> WslBridge:
    settings_kwargs = {"shared_inbox_root": shared_root} if shared_root is not None else {}
    settings = Settings(**settings_kwargs)
    return WslBridge(settings=settings)


def _print_export_result(result) -> None:
    print(f"job_id={result.job_id}")
    print(f"job_dir={result.job_dir}")
    print(f"payload_path={result.payload_path}")
    print(f"metadata_path={result.metadata_path}")
    if getattr(result, "capture_manifest_path", None) is not None:
        print(f"capture_manifest_path={result.capture_manifest_path}")
    if getattr(result, "attachments_dir", None) is not None:
        print(f"attachments_dir={result.attachments_dir}")
    print(f"ready_path={result.ready_path}")


def _print_error(error: WindowsClientError, *, operation: str) -> None:
    print("status=error", file=sys.stderr)
    print(f"operation={operation}", file=sys.stderr)
    print(f"error_code={error.code}", file=sys.stderr)
    print(f"error_stage={error.stage}", file=sys.stderr)
    print(f"error_message={error.message}", file=sys.stderr)
    for key in sorted(error.details):
        print(f"error_detail.{key}={error.details[key]}", file=sys.stderr)
    if error.__cause__ is not None:
        print(f"error_cause_type={type(error.__cause__).__name__}", file=sys.stderr)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _launch_gui_detached() -> bool:
    if sys.platform != "win32":
        return False
    if os.environ.get(_GUI_DETACHED_ENV) == "1":
        return False

    env = dict(os.environ)
    env[_GUI_DETACHED_ENV] = "1"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        [sys.executable, str(_project_root() / "main.py"), "gui"],
        cwd=str(_project_root()),
        env=env,
        close_fds=True,
        creationflags=creationflags,
    )
    return True


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        if args.command == "gui":
            if not args.debug_console and _launch_gui_detached():
                return 0
            from windows_client.gui import launch_gui

            return launch_gui()

        if args.command in {
            "wsl-doctor",
            "wsl-validate-inbox",
            "wsl-watch-once",
            "wsl-start-watch",
            "wsl-watch-status",
            "wsl-stop-watch",
        }:
            bridge = build_wsl_bridge(getattr(args, "shared_root", None))
            if args.command == "wsl-doctor":
                output = bridge.doctor(shared_root=args.shared_root)
                if output:
                    print(output)
                return 0
            if args.command == "wsl-validate-inbox":
                output = bridge.validate_inbox(shared_root=args.shared_root)
                if output:
                    print(output)
                return 0
            if args.command == "wsl-watch-once":
                output = bridge.watch_once(shared_root=args.shared_root)
                if output:
                    print(output)
                return 0
            if args.command == "wsl-start-watch":
                state = bridge.start_watch(
                    shared_root=args.shared_root,
                    interval_seconds=args.interval_seconds,
                )
                print(f"status=started")
                print(f"pid={state.pid}")
                print(f"shared_root={state.shared_root}")
                print(f"interval_seconds={state.interval_seconds:g}")
                print(f"log_path={state.log_path}")
                return 0
            if args.command == "wsl-watch-status":
                status = bridge.watch_status()
                if status is None:
                    print("running=False")
                    print("reason=not_started")
                else:
                    for key, value in status.items():
                        print(f"{key}={value}")
                return 0
            if args.command == "wsl-stop-watch":
                status = bridge.stop_watch()
                for key, value in status.items():
                    print(f"{key}={value}")
                return 0

        service = build_service(getattr(args, "shared_root", None))
        bridge = build_wsl_bridge(getattr(args, "shared_root", None))

        if args.command == "doctor":
            for line in service.doctor():
                print(line)
            return 0

        if args.command == "browser-login":
            profile_dir = service.browser_login(
                start_url=args.start_url,
                profile_dir=args.profile_dir,
                browser_channel=args.browser_channel,
                wait_until=args.wait_until,
                timeout_ms=args.timeout_ms,
            )
            print(f"profile_dir={profile_dir}")
            return 0

        if args.command == "export-mock-job":
            _print_export_result(
                service.export_mock_job(
                    url=args.url,
                    shared_root=args.shared_root,
                    content_type=args.content_type,
                    platform=args.platform,
                )
            )
            return 0

        if args.command == "export-url-job":
            _print_export_result(
                service.export_url_job(
                    url=args.url,
                    shared_root=args.shared_root,
                    content_type=args.content_type,
                    platform=args.platform,
                    video_download_mode=args.video_download_mode,
                )
            )
            return 0

        if args.command == "export-browser-job":
            _print_export_result(
                service.export_browser_job(
                    url=args.url,
                    shared_root=args.shared_root,
                    platform=args.platform,
                    video_download_mode=args.video_download_mode,
                    profile_dir=args.profile_dir,
                    browser_channel=args.browser_channel,
                    headless=not args.headed,
                    wait_until=args.wait_until,
                    timeout_ms=args.timeout_ms,
                    settle_ms=args.settle_ms,
                    wait_for_selector=args.wait_for_selector,
                    wait_for_selector_state=args.wait_for_selector_state,
                )
            )
            return 0

        if args.command == "full-chain-smoke":
            export_result = service.export_url_job(
                url=args.url,
                shared_root=args.shared_root,
                content_type=args.content_type,
                platform=args.platform,
                video_download_mode=args.video_download_mode,
            )
            smoke = bridge.smoke_http(
                url=args.url,
                job_id=export_result.job_id,
                shared_root=args.shared_root,
            )
            _print_export_result(export_result)
            print(f"result_state={smoke['result_state']}")
            if smoke["result_dir"]:
                print(f"result_dir={smoke['result_dir']}")
            print(f"validate_output={smoke['validate_output']}")
            if smoke["watch_output"]:
                print(f"watch_output={smoke['watch_output']}")
            return 0

        parser.error(f"unknown command: {args.command}")
    except WindowsClientError as exc:
        _print_error(exc, operation=args.command)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        _print_error(
            WindowsClientError(
                "unexpected_error",
                str(exc) or type(exc).__name__,
                stage="cli",
                cause=exc,
            ),
            operation=args.command,
        )
        return 1

    return 1
