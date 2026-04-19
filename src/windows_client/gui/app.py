from __future__ import annotations

from windows_client.app.browser_preflight import INSTALL_COMMAND, check_chromium_available
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
    _warn_if_chromium_missing(app)
    window = MainWindow(workflow=WindowsClientWorkflow(build_service()))
    window.show()
    return app.exec()


def _warn_if_chromium_missing(app) -> None:
    """Show a one-time dialog if Playwright's Chromium binary is not installed.

    Runs after QApplication is created but before the main window is shown,
    so the user sees an explicit remediation step instead of a cryptic
    "Executable doesn't exist" error the first time they submit a URL.
    """
    result = check_chromium_available()
    if result.ok:
        return
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QMessageBox
    except ImportError:  # pragma: no cover - GUI path only
        return
    box = QMessageBox()
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("需要安装 Chromium 浏览器")
    box.setText("Playwright 浏览器未就绪，无法采集需要渲染的网页（如微信文章）。")
    box.setInformativeText(result.hint)
    copy_button = box.addButton("复制安装命令", QMessageBox.ActionRole)
    box.addButton("我知道了", QMessageBox.AcceptRole)
    box.exec()
    if box.clickedButton() is copy_button:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(INSTALL_COMMAND)
