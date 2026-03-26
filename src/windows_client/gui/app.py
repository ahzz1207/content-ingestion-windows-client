from __future__ import annotations

from windows_client.app.cli import _ensure_wsl_watch_running, build_service
from windows_client.app.workflow import WindowsClientWorkflow


def launch_gui() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("PySide6 is not installed. Install the 'gui' optional dependency first.") from exc

    from windows_client.gui.main_window import MainWindow

    _ensure_wsl_watch_running()
    app = QApplication.instance() or QApplication([])
    window = MainWindow(workflow=WindowsClientWorkflow(build_service()))
    window.show()
    return app.exec()
