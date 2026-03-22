import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.wsl_bridge import WslBridge, WslWatchState
from windows_client.config.settings import Settings


class WslBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name) / "project-root"
        self.settings = Settings(project_root=self.project_root)
        self.bridge = WslBridge(settings=self.settings)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_to_wsl_path_converts_windows_drive_path(self) -> None:
        converted = self.bridge._to_wsl_path(Path(r"H:\demo-win\data\shared_inbox"))

        self.assertEqual(converted, "/mnt/h/demo-win/data/shared_inbox")

    def test_watch_status_reads_running_process_output(self) -> None:
        self.settings.wsl_watch_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.wsl_watch_state_path.write_text(
            json.dumps(
                {
                    "pid": 4321,
                    "shared_root": str(self.project_root / "data" / "shared_inbox"),
                    "interval_seconds": 5.0,
                    "log_path": str(self.project_root / "data" / "wsl-watch.log"),
                    "started_at": "2026-03-14T16:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "windows_client.app.wsl_bridge.subprocess.run",
            return_value=unittest.mock.Mock(returncode=0, stdout=b'"wsl.exe","4321","Console","1","12,000 K"\n', stderr=""),
        ):
            status = self.bridge.watch_status()

        self.assertIsNotNone(status)
        self.assertEqual(status["running"], "True")
        self.assertEqual(status["pid"], "4321")
        self.assertEqual(status["launcher"], "wsl.exe")

    def test_stop_watch_without_state_returns_not_started(self) -> None:
        result = self.bridge.stop_watch()

        self.assertEqual(result["stopped"], "False")
        self.assertEqual(result["reason"], "not_started")

    def test_write_and_read_watch_state_round_trip(self) -> None:
        state = WslWatchState(
            pid=1234,
            shared_root=str(self.project_root / "data" / "shared_inbox"),
            interval_seconds=3.0,
            log_path=str(self.project_root / "data" / "wsl-watch.log"),
            started_at="2026-03-14T16:00:00+00:00",
        )

        self.bridge._write_watch_state(state)
        loaded = self.bridge._read_watch_state()

        self.assertEqual(loaded, state)

    def test_build_exports_includes_llm_env_when_present(self) -> None:
        shared_root = self.project_root / "data" / "shared_inbox"
        with patch.dict(
            os.environ,
            {
                "ZENMUX_API_KEY": "secret-key",
                "ZENMUX_BASE_URL": "https://zenmux.ai/api/v1",
                "CONTENT_INGESTION_ANALYSIS_MODEL": "openai/gpt-5",
                "CONTENT_INGESTION_WHISPER_MODEL": "large-v3",
            },
            clear=False,
        ):
            exports = self.bridge._build_exports(shared_root=shared_root)

        self.assertTrue(any("CONTENT_INGESTION_SHARED_INBOX_ROOT" in item for item in exports))
        self.assertTrue(any("ZENMUX_API_KEY" in item for item in exports))
        self.assertTrue(any("ZENMUX_BASE_URL" in item for item in exports))
        self.assertTrue(any("CONTENT_INGESTION_ANALYSIS_MODEL" in item for item in exports))
        self.assertTrue(any("CONTENT_INGESTION_WHISPER_MODEL" in item for item in exports))
