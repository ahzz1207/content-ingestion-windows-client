from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal


class WorkflowTaskThread(QThread):
    progress_changed = Signal(str)
    completed = Signal(object)
    crashed = Signal(str)

    def __init__(self, task: Callable[[Callable[[str], None]], object]) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            result = self._task(self.progress_changed.emit)
        except Exception as exc:  # pragma: no cover - GUI worker boundary
            self.crashed.emit(str(exc) or type(exc).__name__)
            return
        self.completed.emit(result)
