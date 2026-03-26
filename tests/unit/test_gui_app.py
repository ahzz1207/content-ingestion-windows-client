import sys
import unittest
from unittest.mock import MagicMock, patch

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.gui.app import launch_gui


class GuiAppTests(unittest.TestCase):
    def test_launch_gui_ensures_wsl_watch_running_before_showing_window(self) -> None:
        fake_app = MagicMock()
        fake_app.exec.return_value = 0
        fake_window = MagicMock()

        with patch("windows_client.gui.app._ensure_wsl_watch_running") as ensure_watch:
            with patch("PySide6.QtWidgets.QApplication.instance", return_value=fake_app):
                with patch("windows_client.gui.main_window.MainWindow", return_value=fake_window):
                    exit_code = launch_gui()

        self.assertEqual(exit_code, 0)
        ensure_watch.assert_called_once()
        fake_window.show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
