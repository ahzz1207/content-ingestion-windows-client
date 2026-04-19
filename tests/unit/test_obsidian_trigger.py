import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.errors import WindowsClientError
from windows_client.app.obsidian_trigger import build_import_uri, trigger_obsidian_import


class BuildImportUriTests(unittest.TestCase):
    def test_encodes_job_id(self) -> None:
        self.assertEqual(
            build_import_uri("20260412_140643_d1f07c"),
            "obsidian://content-ingestion-import?jobId=20260412_140643_d1f07c",
        )

    def test_escapes_unsafe_chars(self) -> None:
        self.assertEqual(
            build_import_uri("job with spaces&=?"),
            "obsidian://content-ingestion-import?jobId=job%20with%20spaces%26%3D%3F",
        )

    def test_rejects_empty_or_whitespace(self) -> None:
        for bad in ("", "   ", "\n"):
            with self.subTest(job_id=bad):
                with self.assertRaises(WindowsClientError) as ctx:
                    build_import_uri(bad)
                self.assertEqual(ctx.exception.code, "invalid_job_id")


class TriggerObsidianImportTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows-only os.startfile path")
    def test_windows_uses_os_startfile(self) -> None:
        with patch("windows_client.app.obsidian_trigger.os.startfile", create=True) as mocked:
            uri = trigger_obsidian_import("job-abc")
        mocked.assert_called_once_with("obsidian://content-ingestion-import?jobId=job-abc")
        self.assertEqual(uri, "obsidian://content-ingestion-import?jobId=job-abc")

    @unittest.skipUnless(sys.platform == "win32", "Windows-only os.startfile path")
    def test_launch_failure_wraps_os_error(self) -> None:
        def _raiser(uri):
            raise OSError("no handler registered for obsidian://")

        with patch("windows_client.app.obsidian_trigger.os.startfile", side_effect=_raiser, create=True):
            with self.assertRaises(WindowsClientError) as ctx:
                trigger_obsidian_import("job-abc")
        self.assertEqual(ctx.exception.code, "obsidian_uri_launch_failed")


if __name__ == "__main__":
    unittest.main()
