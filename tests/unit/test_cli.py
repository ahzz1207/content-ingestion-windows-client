import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.cli import build_service, main
from windows_client.app.errors import WindowsClientError


class _FakeService:
    def export_url_job(self, **kwargs):
        raise WindowsClientError(
            "http_status_error",
            "http request failed with status 404: https://example.com/missing",
            stage="http_collect",
            details={"source_url": "https://example.com/missing", "status_code": 404},
        )


class _FakeBridge:
    def doctor(self, *, shared_root=None):
        return "project_root=/home/ahzz1207/codex-demo"

    def validate_inbox(self, *, shared_root=None):
        return "[]"

    def watch_once(self, *, shared_root=None):
        return "job_output=/mnt/h/demo-win/data/shared_inbox/processed/job123"

    def start_watch(self, *, shared_root=None, interval_seconds=5.0):
        return SimpleNamespace(
            pid=4321,
            shared_root=str(shared_root or PROJECT_ROOT / "data" / "shared_inbox"),
            interval_seconds=interval_seconds,
            log_path=str(PROJECT_ROOT / "data" / "wsl-watch.log"),
        )

    def watch_status(self):
        return {"running": "True", "pid": "4321"}

    def stop_watch(self):
        return {"stopped": "True", "pid": "4321"}

    def smoke_http(self, *, url, job_id, shared_root=None):
        return {
            "url": url,
            "job_id": job_id,
            "shared_root": str(shared_root or PROJECT_ROOT / "data" / "shared_inbox"),
            "validate_output": "[]",
            "watch_output": "job_output=/mnt/h/demo-win/data/shared_inbox/processed/job123",
            "result_state": "processed",
            "result_dir": str(PROJECT_ROOT / "data" / "shared_inbox" / "processed" / job_id),
        }


class CliTests(unittest.TestCase):
    def test_build_service_uses_env_shared_root_when_cli_does_not_override(self) -> None:
        env_root = PROJECT_ROOT / "env-shared-inbox"

        with patch.dict("os.environ", {"CONTENT_INGESTION_SHARED_INBOX_ROOT": str(env_root)}, clear=False):
            service = build_service()

        self.assertEqual(service.settings.effective_shared_inbox_root, env_root)

    def test_main_prints_structured_error_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("windows_client.app.cli.build_service", return_value=_FakeService()):
            with patch.object(sys, "argv", ["main.py", "export-url-job", "https://example.com/missing"]):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("status=error", stderr.getvalue())
        self.assertIn("operation=export-url-job", stderr.getvalue())
        self.assertIn("error_code=http_status_error", stderr.getvalue())
        self.assertIn("error_stage=http_collect", stderr.getvalue())
        self.assertIn("error_detail.status_code=404", stderr.getvalue())

    def test_main_gui_command_invokes_launcher(self) -> None:
        with patch("windows_client.gui.launch_gui", return_value=0) as launch_gui:
            with patch("windows_client.app.cli._launch_gui_detached", return_value=False):
                with patch.object(sys, "argv", ["main.py", "gui"]):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        launch_gui.assert_called_once_with()

    def test_main_gui_command_detaches_by_default(self) -> None:
        with patch("windows_client.app.cli._launch_gui_detached", return_value=True) as launch_detached:
            with patch.object(sys, "argv", ["main.py", "gui"]):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        launch_detached.assert_called_once_with()

    def test_main_gui_command_debug_console_skips_detach(self) -> None:
        with patch("windows_client.app.cli._launch_gui_detached") as launch_detached:
            with patch("windows_client.gui.launch_gui", return_value=0) as launch_gui:
                with patch.object(sys, "argv", ["main.py", "gui", "--debug-console"]):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        launch_detached.assert_not_called()
        launch_gui.assert_called_once_with()

    def test_main_wsl_doctor_command_prints_bridge_output(self) -> None:
        stdout = io.StringIO()

        with patch("windows_client.app.cli.build_wsl_bridge", return_value=_FakeBridge()):
            with patch.object(sys, "argv", ["main.py", "wsl-doctor"]):
                with redirect_stdout(stdout):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("project_root=/home/ahzz1207/codex-demo", stdout.getvalue())

    def test_main_wsl_start_watch_command_prints_state(self) -> None:
        stdout = io.StringIO()

        with patch("windows_client.app.cli.build_wsl_bridge", return_value=_FakeBridge()):
            with patch.object(sys, "argv", ["main.py", "wsl-start-watch", "--interval-seconds", "2"]):
                with redirect_stdout(stdout):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("status=started", stdout.getvalue())
        self.assertIn("pid=4321", stdout.getvalue())

    def test_main_full_chain_smoke_runs_export_and_bridge(self) -> None:
        stdout = io.StringIO()
        fake_service = unittest.mock.MagicMock()
        fake_service.export_url_job.return_value.job_id = "job123"
        fake_service.export_url_job.return_value.job_dir = PROJECT_ROOT / "data" / "shared_inbox" / "incoming" / "job123"
        fake_service.export_url_job.return_value.payload_path = fake_service.export_url_job.return_value.job_dir / "payload.html"
        fake_service.export_url_job.return_value.metadata_path = fake_service.export_url_job.return_value.job_dir / "metadata.json"
        fake_service.export_url_job.return_value.ready_path = fake_service.export_url_job.return_value.job_dir / "READY"

        with patch("windows_client.app.cli.build_service", return_value=fake_service):
            with patch("windows_client.app.cli.build_wsl_bridge", return_value=_FakeBridge()):
                with patch.object(sys, "argv", ["main.py", "full-chain-smoke", "https://example.com/"]):
                    with redirect_stdout(stdout):
                        exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("job_id=job123", stdout.getvalue())
        self.assertIn("result_state=processed", stdout.getvalue())

    def test_main_export_url_job_forwards_video_download_mode(self) -> None:
        fake_service = unittest.mock.MagicMock()
        fake_service.export_url_job.return_value.job_id = "job123"
        fake_service.export_url_job.return_value.job_dir = PROJECT_ROOT / "data" / "shared_inbox" / "incoming" / "job123"
        fake_service.export_url_job.return_value.payload_path = fake_service.export_url_job.return_value.job_dir / "payload.html"
        fake_service.export_url_job.return_value.metadata_path = fake_service.export_url_job.return_value.job_dir / "metadata.json"
        fake_service.export_url_job.return_value.ready_path = fake_service.export_url_job.return_value.job_dir / "READY"

        with patch("windows_client.app.cli.build_service", return_value=fake_service):
            with patch("windows_client.app.cli.build_wsl_bridge", return_value=_FakeBridge()):
                with patch.object(
                    sys,
                    "argv",
                    ["main.py", "export-url-job", "https://www.bilibili.com/video/BV1demo/", "--video-download-mode", "video"],
                ):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_service.export_url_job.call_args.kwargs["video_download_mode"], "video")


if __name__ == "__main__":
    unittest.main()
