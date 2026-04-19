import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.browser_preflight import (
    INSTALL_COMMAND,
    check_chromium_available,
    resolve_browsers_dir,
)


class ResolveBrowsersDirTests(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": "Z:/custom/ms-playwright"}, clear=False):
            self.assertEqual(resolve_browsers_dir(), Path("Z:/custom/ms-playwright"))

    def test_falls_back_to_localappdata(self) -> None:
        env = {"LOCALAPPDATA": "D:/fake/AppData/Local"}
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(resolve_browsers_dir(), Path("D:/fake/AppData/Local/ms-playwright"))


class CheckChromiumAvailableTests(unittest.TestCase):
    def test_missing_dir_returns_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "ms-playwright-doesnt-exist"
            with patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": str(missing)}, clear=False):
                result = check_chromium_available()
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "browsers_dir_missing")
        self.assertIn(INSTALL_COMMAND, result.hint)

    def test_dir_without_binary_returns_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "ffmpeg-1011").mkdir()
            with patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": temp_dir}, clear=False):
                result = check_chromium_available()
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "chromium_binary_missing")
        self.assertIn(INSTALL_COMMAND, result.hint)

    @unittest.skipUnless(sys.platform == "win32", "Windows-only binary layout")
    def test_windows_chromium_headless_shell_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shell_path = Path(temp_dir) / "chromium_headless_shell-1208" / "chrome-headless-shell-win64" / "chrome-headless-shell.exe"
            shell_path.parent.mkdir(parents=True)
            shell_path.write_bytes(b"fake")
            with patch.dict("os.environ", {"PLAYWRIGHT_BROWSERS_PATH": temp_dir}, clear=False):
                result = check_chromium_available()
        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "ok")


if __name__ == "__main__":
    unittest.main()
