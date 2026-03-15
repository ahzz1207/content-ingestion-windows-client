from __future__ import annotations

import html
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.result_workspace import ResultWorkspaceEntry, list_recent_results, load_job_result
from windows_client.app.view_models import OperationViewState
from windows_client.app.workflow import WindowsClientWorkflow
from windows_client.app.wsl_bridge import WslBridge
from windows_client.gui.platform_router import PlatformRoute, resolve_platform_route
from windows_client.gui.refresh_policy import RefreshGate
from windows_client.gui.workers import WorkflowTaskThread


STAGE_LABELS = {
    "idle": "Ready",
    "analyzing_url": "Checking link",
    "checking_runtime": "Checking browser",
    "opening_browser": "Opening browser",
    "waiting_for_login": "Waiting for login",
    "collecting": "Capturing page",
    "exporting": "Writing job",
    "done": "Done",
    "failed": "Failed",
}

RESULT_REFRESH_INTERVAL_SECONDS = 2.0
AUTO_RESULT_POLL_INTERVAL_MS = 3000
AUTO_RESULT_POLL_MAX_ATTEMPTS = 6


def _safe_domain(url: str) -> str:
    return urlparse(url).netloc or url


def _friendly_error_summary(state: OperationViewState) -> str:
    if state.error is None:
        return state.summary
    if state.error.code == "browser_runtime_unavailable":
        return "The browser runtime is not ready on this machine."
    if state.error.code in {"browser_navigation_timeout", "browser_selector_timeout"}:
        return "This page took too long to become ready in the browser."
    if state.error.code == "http_status_error":
        return "The page could not be fetched directly. A browser retry may help."
    if state.error.code == "invalid_source_url":
        return "This link format is not supported."
    return state.summary


def _load_export_metadata(metadata_path: Path) -> dict[str, object]:
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _format_updated_at(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M")


def _start_button_cooldown(button: QPushButton, *, seconds: float, label: str) -> None:
    button.setEnabled(False)
    button.setText(f"{label}...")

    def _restore() -> None:
        button.setEnabled(True)
        button.setText(label)

    QTimer.singleShot(int(seconds * 1000), _restore)


def _apply_result_state_pill(label: QLabel, state: str) -> None:
    styles = {
        "pending": ("#9a3412", "rgba(249, 115, 22, 0.14)"),
        "processing": ("#1d4ed8", "rgba(37, 99, 235, 0.14)"),
        "processed": ("#15803d", "rgba(22, 163, 74, 0.14)"),
        "failed": ("#b91c1c", "rgba(239, 68, 68, 0.14)"),
    }
    foreground, background = styles.get(state, ("#475569", "rgba(148, 163, 184, 0.16)"))
    label.setStyleSheet(
        f"""
        QLabel {{
            background: {background};
            color: {foreground};
            border-radius: 14px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 600;
        }}
        """
    )
    label.setText(state.capitalize())


def _format_result_origin(entry: ResultWorkspaceEntry) -> str:
    if entry.canonical_url:
        return entry.canonical_url
    if entry.source_url:
        return entry.source_url
    return "Source unavailable"


def _format_result_byline(entry: ResultWorkspaceEntry) -> str:
    parts = [value for value in (entry.author, entry.published_at) if value]
    if not parts:
        return "Author and publication time are not available yet."
    return "  |  ".join(parts)


def _preview_body(entry: ResultWorkspaceEntry) -> str:
    if entry.preview_text:
        return entry.preview_text
    if entry.state == "processed":
        return "No readable markdown preview is available for this processed result yet."
    return json.dumps(entry.details, ensure_ascii=False, indent=2)


def _preview_html(entry: ResultWorkspaceEntry) -> str:
    if entry.state == "processed":
        preview_text = _preview_body(entry)
        paragraphs = [part.strip() for part in preview_text.split("\n\n") if part.strip()]
        rendered = "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs)
        return f"<div class='preview-reading'>{rendered}</div>"
    return f"<pre>{html.escape(_preview_body(entry))}</pre>"


def _truncate_title(text: str, *, max_length: int = 64) -> str:
    stripped = text.strip()
    if len(stripped) <= max_length:
        return stripped
    return f"{stripped[: max_length - 1].rstrip()}..."


class ResultListItemWidget(QFrame):
    def __init__(self, entry: ResultWorkspaceEntry) -> None:
        super().__init__()
        self.entry = entry
        self.setObjectName("ResultListItem")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(_truncate_title(entry.title or entry.job_id))
        self.title_label.setObjectName("ResultListTitle")
        self.title_label.setWordWrap(True)

        self.meta_label = QLabel(
            f"{(entry.platform or 'Unknown').title()} | {entry.state.capitalize()} | {_format_updated_at(entry.updated_at)}"
        )
        self.meta_label.setObjectName("ResultListMeta")
        self.meta_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(
                """
                QFrame#ResultListItem {
                    background: rgba(163, 75, 45, 0.10);
                    border: 1px solid rgba(163, 75, 45, 0.18);
                    border-radius: 16px;
                }
                QLabel#ResultListTitle {
                    color: #0f172a;
                    font-size: 14px;
                    font-weight: 600;
                }
                QLabel#ResultListMeta {
                    color: #8f3f25;
                    font-size: 12px;
                    font-weight: 600;
                }
                """
            )
            return
        self.setStyleSheet(
            """
            QFrame#ResultListItem {
                background: rgba(248, 250, 252, 0.82);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 16px;
            }
            QLabel#ResultListTitle {
                color: #18222f;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#ResultListMeta {
                color: #64748b;
                font-size: 12px;
                font-weight: 500;
            }
            """
        )


class LoginPromptDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget | None,
        workflow: WindowsClientWorkflow,
        route: PlatformRoute,
    ) -> None:
        super().__init__(parent)
        self.workflow = workflow
        self.route = route
        self._close_event = threading.Event()
        self._worker: WorkflowTaskThread | None = None
        self._accepted = False

        self.setWindowTitle(f"{route.display_name} login required")
        self.setModal(True)
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(f"{route.display_name} login required")
        title.setObjectName("SheetTitle")
        body = QLabel(
            "A browser window will open. Complete login or warm the profile, then return here and continue."
        )
        body.setWordWrap(True)
        self.status_label = QLabel("Open the browser session to continue.")
        self.status_label.setObjectName("SecondaryText")

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.open_button = QPushButton("Open Browser")
        self.done_button = QPushButton("I've Logged In")
        self.done_button.setEnabled(False)
        self.open_button.setObjectName("PrimaryButton")
        self.done_button.setObjectName("PrimaryButton")
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.open_button)
        actions.addWidget(self.done_button)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        layout.addLayout(actions)

        self.cancel_button.clicked.connect(self.reject)
        self.open_button.clicked.connect(self._open_browser)
        self.done_button.clicked.connect(self._confirm_login)

    def exec_and_confirm(self) -> bool:
        return self.exec() == QDialog.Accepted and self._accepted

    def reject(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._close_event.set()
            self._worker.wait(5000)
        super().reject()

    def _open_browser(self) -> None:
        if self._worker is not None:
            return
        profile_dir = self.route.profile_dir(self.workflow.service.settings)
        if profile_dir is None or self.route.start_url is None:
            QMessageBox.warning(self, "Login unavailable", "This route does not define a browser login flow.")
            return

        self._close_event.clear()
        self.open_button.setEnabled(False)
        self.done_button.setEnabled(True)
        self.status_label.setText("Browser opened. Complete login, then click 'I've Logged In'.")

        self._worker = WorkflowTaskThread(
            lambda progress: self.workflow.browser_login(
                start_url=self.route.start_url,
                profile_dir=profile_dir,
                completion_waiter=self._close_event.wait,
                on_progress=progress,
            )
        )
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.crashed.connect(self._on_crashed)
        self._worker.start()

    def _confirm_login(self) -> None:
        self.done_button.setEnabled(False)
        self.status_label.setText("Saving browser profile...")
        self._accepted = True
        self._close_event.set()

    def _on_progress(self, stage: str) -> None:
        self.status_label.setText(STAGE_LABELS.get(stage, stage))

    def _on_completed(self, state: OperationViewState) -> None:
        if state.status == "success":
            self.accept()
            return
        self._accepted = False
        self.status_label.setText(_friendly_error_summary(state))
        self.done_button.setEnabled(False)
        self.open_button.setEnabled(True)
        self._worker = None

    def _on_crashed(self, message: str) -> None:
        self._accepted = False
        self.status_label.setText(message)
        self.done_button.setEnabled(False)
        self.open_button.setEnabled(True)
        self._worker = None


class ResultWorkspaceDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget | None,
        shared_root: Path,
        selected_job_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.shared_root = shared_root
        self.entries: list[ResultWorkspaceEntry] = []
        self._item_widgets: list[ResultListItemWidget] = []
        self._selected_job_id = selected_job_id
        self._refresh_gate = RefreshGate(min_interval_seconds=RESULT_REFRESH_INTERVAL_SECONDS)

        self.setWindowTitle("Result Workspace")
        self.resize(1080, 720)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(312)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(10)
        sidebar_header = QHBoxLayout()
        sidebar_title = QLabel("Recent Results")
        sidebar_title.setObjectName("SectionLabel")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("GhostButton")
        self.refresh_button.setToolTip("Refresh is limited to once every 2 seconds.")
        self.refresh_button.clicked.connect(self._request_reload_entries)
        self.results_list = QListWidget()
        self.results_list.setObjectName("ResultList")
        self.results_list.setSpacing(8)
        self.results_list.currentRowChanged.connect(self._render_selected_entry)
        sidebar_header.addWidget(sidebar_title)
        sidebar_header.addStretch(1)
        sidebar_header.addWidget(self.refresh_button)
        sidebar_layout.addLayout(sidebar_header)
        sidebar_layout.addWidget(self.results_list, 1)

        detail_card = QFrame()
        detail_card.setObjectName("DetailCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(26, 26, 26, 26)
        detail_layout.setSpacing(12)
        self.workspace_label = QLabel("Workspace")
        self.workspace_label.setObjectName("EyebrowText")

        self.status_pill = QLabel("")
        self.status_pill.setObjectName("PlatformPill")
        self.empty_label = QLabel("Select a result to inspect its current state.")
        self.empty_label.setObjectName("SecondaryText")
        self.title_label = QLabel("")
        self.title_label.setObjectName("ResultTitle")
        self.source_label = QLabel("")
        self.source_label.setObjectName("CaptionText")
        self.source_label.setWordWrap(True)
        self.byline_label = QLabel("")
        self.byline_label.setObjectName("BylineText")
        self.byline_label.setWordWrap(True)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("BodyText")
        self.summary_label.setWordWrap(True)
        self.meta_toggle = QToolButton()
        self.meta_toggle.setText("Show metadata")
        self.meta_toggle.setCheckable(True)
        self.meta_toggle.toggled.connect(self._toggle_metadata)

        self.meta_frame = QFrame()
        self.meta_frame.setObjectName("PreviewCard")
        self.meta_grid = QGridLayout(self.meta_frame)
        self.meta_grid.setHorizontalSpacing(18)
        self.meta_grid.setVerticalSpacing(8)
        self.meta_value_labels: dict[str, QLabel] = {}
        for row, label in enumerate(("Job ID", "Platform", "Source URL", "Canonical URL", "Author", "Published", "Location")):
            label_widget = QLabel(f"{label}:")
            label_widget.setObjectName("SecondaryText")
            value_widget = QLabel("")
            value_widget.setWordWrap(True)
            self.meta_grid.addWidget(label_widget, row, 0)
            self.meta_grid.addWidget(value_widget, row, 1)
            self.meta_value_labels[label] = value_widget

        preview_label = QLabel("Preview")
        preview_label.setObjectName("SectionLabel")
        self.preview_hint_label = QLabel("")
        self.preview_hint_label.setObjectName("SecondaryText")
        self.preview_hint_label.setWordWrap(True)
        self.preview = QTextBrowser()
        self.preview.setReadOnly(True)
        self.preview.setOpenExternalLinks(True)
        self.preview.document().setDocumentMargin(0)
        self.preview.document().setDefaultStyleSheet(
            """
            .preview-reading p {
                margin: 0 0 14px 0;
                line-height: 1.7;
            }
            pre {
                white-space: pre-wrap;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.5;
                color: #334155;
            }
            """
        )

        actions = QHBoxLayout()
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("GhostButton")
        self.open_folder_button.clicked.connect(self._open_folder)
        self.open_json_button = QPushButton("Open JSON")
        self.open_json_button.setObjectName("GhostButton")
        self.open_json_button.clicked.connect(self._open_json)
        self.open_markdown_button = QPushButton("Open Markdown")
        self.open_markdown_button.setObjectName("GhostButton")
        self.open_markdown_button.clicked.connect(self._open_markdown)
        close_button = QPushButton("Close")
        close_button.setObjectName("PrimaryButton")
        close_button.clicked.connect(self.accept)
        actions.addWidget(self.open_folder_button)
        actions.addWidget(self.open_json_button)
        actions.addWidget(self.open_markdown_button)
        actions.addStretch(1)
        actions.addWidget(close_button)

        detail_layout.addWidget(self.workspace_label)
        detail_layout.addWidget(self.status_pill, 0, Qt.AlignLeft)
        detail_layout.addWidget(self.empty_label)
        detail_layout.addWidget(self.title_label)
        detail_layout.addWidget(self.source_label)
        detail_layout.addWidget(self.byline_label)
        detail_layout.addWidget(self.summary_label)
        detail_layout.addWidget(self.meta_toggle, 0, Qt.AlignLeft)
        detail_layout.addWidget(self.meta_frame)
        detail_layout.addWidget(preview_label)
        detail_layout.addWidget(self.preview_hint_label)
        detail_layout.addWidget(self.preview, 1)
        detail_layout.addLayout(actions)

        layout.addWidget(sidebar, 0)
        layout.addWidget(detail_card, 1)

        self._set_empty_state()
        self._reload_entries()

    def _entry_list_label(self, entry: ResultWorkspaceEntry) -> str:
        title = entry.title or entry.job_id
        platform = entry.platform or entry.state
        return f"{title}\n{platform} · {entry.state}"

    def _sidebar_entry_label(self, entry: ResultWorkspaceEntry) -> str:
        title = entry.title or entry.job_id
        platform = entry.platform or "Unknown"
        return f"{title}\n{platform} · {entry.state} · {_format_updated_at(entry.updated_at)}"

    def _request_reload_entries(self) -> None:
        if not self._refresh_gate.allow_now():
            return
        self._refresh_gate.mark()
        _start_button_cooldown(
            self.refresh_button,
            seconds=RESULT_REFRESH_INTERVAL_SECONDS,
            label="Refresh",
        )
        self._reload_entries()

    def _reload_entries(self) -> None:
        current_entry = self._selected_entry()
        selected_job_id = current_entry.job_id if current_entry is not None else self._selected_job_id
        self.entries = list_recent_results(self.shared_root, limit=24)
        self._item_widgets = []
        self.results_list.clear()
        for entry in self.entries:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry.job_id)
            widget = ResultListItemWidget(entry)
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
            self._item_widgets.append(widget)
        if not self.entries:
            self._selected_job_id = None
            self._set_empty_state("No results are available yet in the shared inbox.")
            return

        selected_index = 0
        if selected_job_id is not None:
            for index, entry in enumerate(self.entries):
                if entry.job_id == selected_job_id:
                    selected_index = index
                    break
        self.results_list.setCurrentRow(selected_index)
        self._selected_job_id = self.entries[selected_index].job_id

    def _result_list_label(self, entry: ResultWorkspaceEntry) -> str:
        title = entry.title or entry.job_id
        platform = entry.platform or "Unknown"
        return f"{title}\n{platform} · {entry.state} · {_format_updated_at(entry.updated_at)}"

    def _result_list_label_ascii(self, entry: ResultWorkspaceEntry) -> str:
        title = entry.title or entry.job_id
        platform = entry.platform or "Unknown"
        return f"{title}\n{platform} | {entry.state} | {_format_updated_at(entry.updated_at)}"

    def _set_empty_state(self, message: str = "Select a result to inspect its current state.") -> None:
        self.status_pill.hide()
        self.empty_label.setText(message)
        self.empty_label.show()
        self.title_label.clear()
        self.source_label.clear()
        self.byline_label.clear()
        self.summary_label.clear()
        self.preview_hint_label.clear()
        self.preview.clear()
        self.meta_toggle.setChecked(False)
        self.meta_toggle.hide()
        self.meta_frame.hide()
        for label in self.meta_value_labels.values():
            label.clear()
        self.open_folder_button.setEnabled(False)
        self.open_json_button.setEnabled(False)
        self.open_markdown_button.setEnabled(False)

    def _selected_entry(self) -> ResultWorkspaceEntry | None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self.entries):
            return None
        return self.entries[row]

    def _sync_item_widget_selection(self, selected_row: int) -> None:
        for index, widget in enumerate(self._item_widgets):
            widget.set_selected(index == selected_row)

    def _toggle_metadata(self, visible: bool) -> None:
        self.meta_toggle.setText("Hide metadata" if visible else "Show metadata")
        self.meta_frame.setVisible(visible)

    def _preview_hint(self, entry: ResultWorkspaceEntry) -> str:
        if entry.state == "processed":
            return "Reading extract from the normalized WSL output."
        if entry.state == "failed":
            return "Structured failure details from the WSL result directory."
        if entry.state == "processing":
            return "This job is still being processed. Metadata below reflects the latest handoff state."
        return "This job is still waiting in the shared inbox. Details below come from the Windows handoff metadata."

    def _render_selected_entry(self, row: int) -> None:
        if row < 0 or row >= len(self.entries):
            self._sync_item_widget_selection(-1)
            self._set_empty_state()
            return
        entry = self.entries[row]
        self._sync_item_widget_selection(row)
        self._selected_job_id = entry.job_id
        self.status_pill.show()
        self.empty_label.hide()
        _apply_result_state_pill(self.status_pill, entry.state)
        self.title_label.setText(entry.title or entry.job_id)
        self.source_label.setText(_format_result_origin(entry))
        self.byline_label.setText(_format_result_byline(entry))
        self.summary_label.setText(entry.summary)
        values = {
            "Job ID": entry.job_id,
            "Platform": entry.platform or "Unknown",
            "Source URL": entry.source_url or "Unknown",
            "Canonical URL": entry.canonical_url or "Unknown",
            "Author": entry.author or "Unknown",
            "Published": entry.published_at or "Unknown",
            "Location": str(entry.job_dir) if entry.job_dir is not None else "Unknown",
        }
        for label, value in values.items():
            self.meta_value_labels[label].setText(value)
        self.meta_toggle.show()
        self.meta_toggle.setChecked(False)
        self.preview_hint_label.setText(self._preview_hint(entry))
        self.preview.setHtml(_preview_html(entry))
        self.open_folder_button.setEnabled(entry.job_dir is not None)
        self.open_json_button.setEnabled(
            entry.normalized_json_path is not None or entry.error_path is not None or entry.metadata_path is not None
        )
        self.open_markdown_button.setEnabled(entry.normalized_md_path is not None)

    def _open_folder(self) -> None:
        entry = self._selected_entry()
        if entry is None or entry.job_dir is None:
            return
        if os.name == "nt":
            os.startfile(entry.job_dir)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(entry.job_dir)))

    def _open_json(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        path = entry.normalized_json_path or entry.error_path or entry.metadata_path
        if path is None:
            return
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_markdown(self) -> None:
        entry = self._selected_entry()
        if entry is None or entry.normalized_md_path is None:
            return
        if os.name == "nt":
            os.startfile(entry.normalized_md_path)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(entry.normalized_md_path)))


class MainWindow(QMainWindow):
    def __init__(self, *, workflow: WindowsClientWorkflow) -> None:
        super().__init__()
        self.workflow = workflow
        self.wsl_bridge = WslBridge(workflow.service.settings)
        self._task_thread: WorkflowTaskThread | None = None
        self._current_route: PlatformRoute | None = None
        self._current_url: str = ""
        self._current_state: OperationViewState | None = None
        self._latest_result_entry: ResultWorkspaceEntry | None = None
        self._result_poll_timer = QTimer(self)
        self._result_poll_timer.setSingleShot(True)
        self._result_poll_timer.timeout.connect(self._poll_current_job_result)
        self._result_poll_attempts = 0

        self.setWindowTitle("Collect")
        self.resize(980, 700)
        self.setMinimumSize(860, 620)

        self._build_ui()
        self._apply_styles()
        self._refresh_environment_status()
        self._show_ready_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Collect")
        self.title_label.setObjectName("WindowTitle")
        self.subtitle_label = QLabel("Turn a link into a processed job")
        self.subtitle_label.setObjectName("SecondaryText")
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)

        self.pills_container = QWidget()
        self.pills_layout = QHBoxLayout(self.pills_container)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(10)
        self.pills_layout.addStretch(1)

        header_layout.addLayout(title_block)
        header_layout.addStretch(1)
        header_layout.addWidget(self.pills_container, 0, Qt.AlignRight)

        self.stack = QStackedWidget()
        self.ready_page = self._build_ready_page()
        self.task_page = self._build_task_page()
        self.stack.addWidget(self.ready_page)
        self.stack.addWidget(self.task_page)

        self.footer_label = QLabel("Automatic platform detection and browser guidance are enabled.")
        self.footer_label.setObjectName("SecondaryText")

        root_layout.addWidget(header)
        root_layout.addWidget(self.stack, 1)
        root_layout.addWidget(self.footer_label)

        self.setCentralWidget(root)

        refresh_action = QAction("Refresh status", self)
        refresh_action.triggered.connect(self._refresh_environment_status)
        self.addAction(refresh_action)

    def _build_ready_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("HeroCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 52, 48, 52)
        card_layout.setSpacing(18)

        eyebrow = QLabel("Windows  ->  WSL")
        eyebrow.setObjectName("EyebrowText")

        intro = QLabel("Paste a URL to get started.")
        intro.setObjectName("HeroText")
        intro.setAlignment(Qt.AlignLeft)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/article")
        self.url_input.returnPressed.connect(self._start_from_input)
        self.url_input.textChanged.connect(self._sync_video_download_controls)
        self.url_input.setObjectName("UrlInput")

        self.save_video_checkbox = QCheckBox("Also save the video file")
        self.save_video_checkbox.setObjectName("SecondaryText")
        self.save_video_checkbox.setChecked(False)
        self.save_video_checkbox.hide()

        self.video_mode_hint = QLabel("Video sites default to audio-only export. Turn this on to keep the full video.")
        self.video_mode_hint.setObjectName("SecondaryText")
        self.video_mode_hint.setWordWrap(True)
        self.video_mode_hint.hide()

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self._start_from_input)
        self.start_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.latest_result_button = QPushButton("Result Workspace")
        self.latest_result_button.setObjectName("GhostButton")
        self.latest_result_button.clicked.connect(self._open_latest_result)
        self.latest_result_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        actions = QHBoxLayout()
        actions.addWidget(self.start_button)
        actions.addWidget(self.latest_result_button)
        actions.addStretch(1)

        hint = QLabel("Known platforms are routed automatically. Login guidance appears only when needed.")
        hint.setObjectName("SecondaryText")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignLeft)

        card_layout.addWidget(eyebrow, 0, Qt.AlignLeft)
        card_layout.addWidget(intro)
        card_layout.addWidget(self.url_input)
        card_layout.addWidget(self.save_video_checkbox, 0, Qt.AlignLeft)
        card_layout.addWidget(self.video_mode_hint)
        card_layout.addLayout(actions)
        card_layout.addWidget(hint)
        card_layout.addStretch(1)

        layout.addWidget(card, 1)
        return page

    def _build_task_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("TaskCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 30)
        card_layout.setSpacing(20)

        top_row = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("GhostButton")
        self.back_button.clicked.connect(self._reset_to_ready_state)
        top_row.addWidget(self.back_button, 0, Qt.AlignLeft)
        top_row.addStretch(1)

        self.run_label = QLabel("Current Run")
        self.run_label.setObjectName("EyebrowText")
        self.domain_label = QLabel("")
        self.domain_label.setObjectName("DomainText")
        self.platform_label = QLabel("")
        self.platform_label.setObjectName("PlatformPill")
        self.stage_label = QLabel("")
        self.stage_label.setObjectName("StageText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)

        self.result_title = QLabel("")
        self.result_title.setObjectName("ResultTitle")
        self.result_title.setWordWrap(True)
        self.result_summary = QLabel("")
        self.result_summary.setWordWrap(True)
        self.result_summary.setObjectName("BodyText")

        self.meta_grid = QGridLayout()
        self.meta_grid.setHorizontalSpacing(18)
        self.meta_grid.setVerticalSpacing(10)
        self.meta_labels: dict[str, QLabel] = {}
        for row, key in enumerate(("Author", "Published", "Job ID", "Location")):
            key_label = QLabel(f"{key}:")
            key_label.setObjectName("SecondaryText")
            value_label = QLabel("")
            value_label.setWordWrap(True)
            self.meta_grid.addWidget(key_label, row, 0)
            self.meta_grid.addWidget(value_label, row, 1)
            self.meta_labels[key] = value_label

        self.action_row = QHBoxLayout()
        self.retry_browser_button = QPushButton("Retry in Browser")
        self.retry_browser_button.setObjectName("GhostButton")
        self.retry_browser_button.clicked.connect(self._retry_in_browser)
        self.open_result_button = QPushButton("Open Result")
        self.open_result_button.setObjectName("GhostButton")
        self.open_result_button.clicked.connect(self._open_current_job_result)
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("GhostButton")
        self.open_folder_button.clicked.connect(self._open_job_folder)
        self.copy_job_id_button = QPushButton("Copy Job ID")
        self.copy_job_id_button.setObjectName("GhostButton")
        self.copy_job_id_button.clicked.connect(self._copy_job_id)
        self.new_url_button = QPushButton("New URL")
        self.new_url_button.setObjectName("PrimaryButton")
        self.new_url_button.clicked.connect(self._reset_to_ready_state)
        for button in (
            self.retry_browser_button,
            self.open_result_button,
            self.open_folder_button,
            self.copy_job_id_button,
            self.new_url_button,
        ):
            self.action_row.addWidget(button)
        self.action_row.addStretch(1)

        self.details_toggle = QToolButton()
        self.details_toggle.setText("Show technical details")
        self.details_toggle.setCheckable(True)
        self.details_toggle.toggled.connect(self._toggle_details)
        self.details_text = QPlainTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(180)
        self.details_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.details_text.hide()

        card_layout.addLayout(top_row)
        card_layout.addWidget(self.run_label)
        card_layout.addWidget(self.domain_label)
        card_layout.addWidget(self.platform_label, 0, Qt.AlignLeft)
        card_layout.addWidget(self.stage_label)
        card_layout.addWidget(self.progress_bar)
        card_layout.addWidget(self.result_title)
        card_layout.addWidget(self.result_summary)
        card_layout.addLayout(self.meta_grid)
        card_layout.addLayout(self.action_row)
        card_layout.addWidget(self.details_toggle, 0, Qt.AlignLeft)
        card_layout.addWidget(self.details_text)
        layout.addWidget(card, 1)
        return page

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f5ede3,
                    stop: 0.48 #eef1f4,
                    stop: 1 #e4e8ee
                );
                color: #16202b;
            }
            #WindowTitle {
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 38px;
                font-weight: 700;
                color: #16202b;
            }
            #HeroText {
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 36px;
                font-weight: 600;
                color: #16202b;
            }
            #ResultTitle {
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 31px;
                font-weight: 600;
                color: #16202b;
            }
            #BylineText {
                font-size: 15px;
                font-weight: 600;
                color: #2f4558;
            }
            #EyebrowText {
                font-size: 12px;
                font-weight: 700;
                color: #a34b2d;
            }
            #CaptionText {
                font-size: 13px;
                color: #6b7280;
            }
            #DomainText {
                font-size: 16px;
                color: #6b7280;
            }
            #StageText {
                font-size: 17px;
                font-weight: 600;
                color: #16202b;
            }
            #SectionLabel {
                font-size: 12px;
                font-weight: 700;
                color: #a34b2d;
            }
            #BodyText {
                font-size: 15px;
                color: #2f4558;
            }
            #SecondaryText {
                font-size: 14px;
                color: #6b7280;
            }
            #PlatformPill {
                background: rgba(163, 75, 45, 0.10);
                color: #8f3f25;
                border: 1px solid rgba(163, 75, 45, 0.14);
                border-radius: 999px;
                padding: 7px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            #HeroCard {
                background: rgba(255, 251, 247, 0.84);
                border: 1px solid rgba(172, 139, 108, 0.18);
                border-radius: 34px;
            }
            #TaskCard, #DetailCard {
                background: rgba(255, 253, 250, 0.84);
                border: 1px solid rgba(172, 139, 108, 0.16);
                border-radius: 30px;
            }
            #SidebarCard {
                background: rgba(244, 240, 233, 0.82);
                border: 1px solid rgba(172, 139, 108, 0.15);
                border-radius: 26px;
            }
            #PreviewCard {
                background: rgba(248, 243, 236, 0.92);
                border: 1px solid rgba(172, 139, 108, 0.12);
                border-radius: 20px;
            }
            QListWidget#ResultList {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget#ResultList::item {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QListWidget#ResultList::item:selected {
                background: transparent;
                border: none;
            }
            #UrlInput {
                min-height: 62px;
                border-radius: 22px;
                border: 1px solid rgba(172, 139, 108, 0.22);
                background: rgba(255, 255, 255, 0.94);
                padding: 0 22px;
                font-size: 18px;
                color: #16202b;
            }
            #PrimaryButton, #GhostButton, QToolButton {
                min-height: 46px;
                border-radius: 18px;
                padding: 0 18px;
                font-size: 14px;
                font-weight: 600;
            }
            #PrimaryButton {
                background: #16202b;
                color: white;
                border: 1px solid rgba(22, 32, 43, 0.08);
            }
            #PrimaryButton:hover {
                background: #232f3d;
            }
            #GhostButton, QToolButton {
                background: rgba(255, 255, 255, 0.52);
                color: #16202b;
                border: 1px solid rgba(172, 139, 108, 0.16);
            }
            #GhostButton:hover, QToolButton:hover {
                background: rgba(255, 248, 242, 0.88);
            }
            #GhostButton:disabled, #PrimaryButton:disabled {
                color: #9ca3af;
                background: rgba(235, 236, 239, 0.92);
                border: 1px solid rgba(172, 139, 108, 0.12);
            }
            QProgressBar {
                min-height: 10px;
                border-radius: 5px;
                background: rgba(172, 139, 108, 0.16);
                border: none;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #d97745,
                    stop: 1 #8f3f25
                );
            }
            QTextBrowser {
                border-radius: 22px;
                border: 1px solid rgba(172, 139, 108, 0.12);
                background: rgba(255, 251, 247, 0.92);
                padding: 20px;
                font-size: 15px;
                color: #233445;
                selection-background-color: rgba(163, 75, 45, 0.16);
            }
            QPlainTextEdit {
                border-radius: 18px;
                border: 1px solid rgba(172, 139, 108, 0.12);
                background: rgba(248, 243, 236, 0.92);
                padding: 16px;
                color: #334155;
            }
            """
        )

    def _set_pills(self, pills: list[tuple[str, bool]]) -> None:
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for text, ok in pills:
            pill = QLabel(text)
            pill.setStyleSheet(
                f"""
                QLabel {{
                    background: {'rgba(15, 118, 110, 0.12)' if ok else 'rgba(172, 139, 108, 0.16)'};
                    color: {'#0f766e' if ok else '#6b7280'};
                    border: 1px solid {'rgba(15, 118, 110, 0.10)' if ok else 'rgba(172, 139, 108, 0.12)'};
                    border-radius: 999px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                """
            )
            self.pills_layout.addWidget(pill)
        self.pills_layout.addStretch(1)

    def _refresh_environment_status(self) -> None:
        state = self.workflow.run_doctor()
        if state.status != "success" or state.doctor is None:
            self._set_pills([("Status unavailable", False)])
            return
        values = state.doctor.values
        pills = [
            ("Browser ready" if values.get("browser_collector_available") == "True" else "Browser unavailable",
             values.get("browser_collector_available") == "True"),
            ("Inbox ready" if values.get("shared_inbox_exists") == "True" else "Inbox will be created",
             True),
        ]
        try:
            watcher_status = self.wsl_bridge.watch_status()
        except Exception:
            watcher_status = None
        if watcher_status is None:
            pills.append(("WSL watcher not started", False))
        else:
            pills.append(
                (
                    "WSL watcher running" if watcher_status.get("running") == "True" else "WSL watcher stopped",
                    watcher_status.get("running") == "True",
                )
            )
        profiles_dir = Path(values.get("browser_profiles_dir", ""))
        for slug, label in (("wechat", "WeChat profile"), ("xiaohongshu", "Xiaohongshu profile"), ("youtube", "YouTube profile")):
            pills.append((f"{label} ready" if (profiles_dir / slug).exists() else f"{label} missing", (profiles_dir / slug).exists()))
        self._set_pills(pills)

    def _show_ready_state(self) -> None:
        if self._task_thread is not None and self._task_thread.isRunning():
            return
        self.stack.setCurrentWidget(self.ready_page)
        self._sync_video_download_controls(self.url_input.text())
        self.url_input.setFocus()

    def _reset_to_ready_state(self) -> None:
        self._stop_result_polling()
        self.url_input.clear()
        self.save_video_checkbox.setChecked(False)
        self._sync_video_download_controls("")
        self._current_url = ""
        self._current_route = None
        self._current_state = None
        self._latest_result_entry = None
        self._show_ready_state()

    def _start_from_input(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            QMessageBox.warning(self, "Unsupported URL", "Please enter a full http or https URL.")
            return
        self._current_url = url
        route = resolve_platform_route(url)
        self._current_route = route
        if route.strategy == "browser" and not route.profile_exists(self.workflow.service.settings):
            dialog = LoginPromptDialog(parent=self, workflow=self.workflow, route=route)
            if not dialog.exec_and_confirm():
                self._refresh_environment_status()
                return
            self._refresh_environment_status()
        self._run_export(route=route, url=url)

    def _run_export(self, *, route: PlatformRoute, url: str, force_browser: bool = False) -> None:
        self._stop_result_polling()
        self._set_task_state(route=route, url=url, stage="analyzing_url")
        self.stack.setCurrentWidget(self.task_page)
        strategy = "browser" if force_browser else route.strategy
        video_download_mode = self._selected_video_download_mode(route)

        if strategy == "browser":
            profile_dir = route.profile_dir(self.workflow.service.settings)
            self._task_thread = WorkflowTaskThread(
                lambda progress: self.workflow.export_browser_job(
                    url=url,
                    platform=route.platform,
                    video_download_mode=video_download_mode,
                    profile_dir=profile_dir,
                    wait_for_selector=route.wait_for_selector,
                    wait_for_selector_state=route.wait_for_selector_state,
                    on_progress=progress,
                )
            )
        else:
            self._task_thread = WorkflowTaskThread(
                lambda progress: self.workflow.export_url_job(
                    url=url,
                    platform=route.platform,
                    video_download_mode=video_download_mode,
                    on_progress=progress,
                )
            )
        self._task_thread.progress_changed.connect(self._on_task_progress)
        self._task_thread.completed.connect(self._on_task_completed)
        self._task_thread.crashed.connect(self._on_task_crashed)
        self._task_thread.start()

    def _set_task_state(self, *, route: PlatformRoute, url: str, stage: str) -> None:
        self.domain_label.setText(_safe_domain(url))
        download_mode_label = "Video saved" if self._selected_video_download_mode(route) == "video" else "Audio only"
        self.platform_label.setText(
            f"{route.display_name} | {download_mode_label}" if route.is_video else route.display_name
        )
        self.stage_label.setText(STAGE_LABELS.get(stage, stage))
        self.result_title.clear()
        self.result_summary.clear()
        self.result_title.hide()
        self.result_summary.hide()
        self.details_text.clear()
        self.details_toggle.setChecked(False)
        self.details_text.hide()
        self.details_toggle.hide()
        self.retry_browser_button.hide()
        self.open_result_button.hide()
        self.open_folder_button.hide()
        self.copy_job_id_button.hide()
        self.new_url_button.hide()
        self._set_meta_grid_visible(False)
        for value_label in self.meta_labels.values():
            value_label.clear()
        self.progress_bar.show()
        self.back_button.setEnabled(False)

    def _sync_video_download_controls(self, text: str) -> None:
        route = resolve_platform_route(text.strip()) if text.strip() else None
        visible = route is not None and route.is_video
        self.save_video_checkbox.setVisible(visible)
        self.video_mode_hint.setVisible(visible)

    def _selected_video_download_mode(self, route: PlatformRoute) -> str:
        if route.is_video and self.save_video_checkbox.isChecked():
            return "video"
        return "audio"

    def _on_task_progress(self, stage: str) -> None:
        self.stage_label.setText(STAGE_LABELS.get(stage, stage))

    def _on_task_completed(self, state: OperationViewState) -> None:
        self._current_state = state
        self.back_button.setEnabled(True)
        self.progress_bar.hide()
        self.new_url_button.show()
        if state.status == "success":
            self.stage_label.setText(STAGE_LABELS["done"])
            self._render_success(state)
        else:
            self.stage_label.setText(STAGE_LABELS["failed"])
            self._render_failure(state)
        self._task_thread = None

    def _on_task_crashed(self, message: str) -> None:
        self._stop_result_polling()
        self.back_button.setEnabled(True)
        self.progress_bar.hide()
        self.result_title.setText("Unexpected GUI worker failure")
        self.result_summary.setText(message)
        self.new_url_button.show()
        self._task_thread = None

    def _render_success(self, state: OperationViewState) -> None:
        assert state.job is not None
        metadata = _load_export_metadata(state.job.metadata_path)
        self.result_summary.setText("The Windows job was written to the shared inbox. WSL results appear here once processed.")
        self.result_summary.show()
        details_text = json.dumps(metadata, ensure_ascii=False, indent=2) if metadata else "No technical details are available."
        self.details_text.setPlainText(details_text)
        self.details_toggle.show()
        self.open_folder_button.show()
        self.copy_job_id_button.show()
        self._refresh_current_job_result()
        self._start_result_polling()

    def _render_failure(self, state: OperationViewState) -> None:
        self._stop_result_polling()
        self.result_title.setText("Couldn't capture this page")
        self.result_summary.setText(_friendly_error_summary(state))
        self.result_title.show()
        self.result_summary.show()
        self.meta_labels["Author"].setText("")
        self.meta_labels["Published"].setText("")
        self.meta_labels["Job ID"].setText("")
        self.meta_labels["Location"].setText("")
        details = {
            "operation": state.operation,
            "summary": state.summary,
        }
        if state.error is not None:
            details["error_code"] = state.error.code
            details["stage"] = state.error.stage
            details["details"] = state.error.details
            if state.error.cause_type is not None:
                details["cause_type"] = state.error.cause_type
        self.details_text.setPlainText(json.dumps(details, ensure_ascii=False, indent=2))
        self.details_toggle.show()
        if self._current_route is not None and self._current_route.strategy == "http":
            self.retry_browser_button.show()

    def _retry_in_browser(self) -> None:
        if self._current_route is None or not self._current_url:
            return
        self._run_export(route=self._current_route, url=self._current_url, force_browser=True)

    def _toggle_details(self, visible: bool) -> None:
        self.details_toggle.setText("Hide technical details" if visible else "Show technical details")
        self.details_text.setVisible(visible)

    def _open_job_folder(self) -> None:
        if self._current_state is None or self._current_state.job is None:
            return
        job_dir = self._current_state.job.job_dir
        if os.name == "nt":
            os.startfile(job_dir)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(job_dir)))

    def _copy_job_id(self) -> None:
        if self._current_state is None or self._current_state.job is None:
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._current_state.job.job_id)

    def _open_latest_result(self) -> None:
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        entries = list_recent_results(shared_root, limit=24)
        if not entries:
            QMessageBox.information(self, "No results yet", "No WSL results are available yet.")
            return
        ResultWorkspaceDialog(parent=self, shared_root=shared_root).exec()

    def _start_result_polling(self) -> None:
        self._result_poll_attempts = 0
        self._schedule_result_poll()

    def _stop_result_polling(self) -> None:
        self._result_poll_timer.stop()
        self._result_poll_attempts = 0

    def _schedule_result_poll(self) -> None:
        if self._result_poll_attempts >= AUTO_RESULT_POLL_MAX_ATTEMPTS:
            return
        self._result_poll_timer.start(AUTO_RESULT_POLL_INTERVAL_MS)

    def _poll_current_job_result(self) -> None:
        self._result_poll_attempts += 1
        state = self._refresh_current_job_result(from_auto_poll=True)
        if state in {"processed", "failed"}:
            self._stop_result_polling()
            return
        if self._result_poll_attempts >= AUTO_RESULT_POLL_MAX_ATTEMPTS:
            self.result_summary.setText(
                "The Windows job was written to the shared inbox. WSL has not finished yet; you can check again later."
            )
            return
        self._schedule_result_poll()

    def _refresh_current_job_result(self, *, from_auto_poll: bool = False) -> str:
        if self._current_state is None or self._current_state.job is None:
            return "unavailable"
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        result_entry = load_job_result(shared_root, self._current_state.job.job_id)
        if result_entry is None:
            self.result_summary.setText(
                "The Windows job was written to the shared inbox. WSL has not created a result yet."
                if not from_auto_poll
                else "The Windows job was written to the shared inbox. Waiting for WSL to pick it up..."
            )
            self._latest_result_entry = None
            self.open_result_button.hide()
            return "missing"
        if result_entry.state == "processed":
            self.result_summary.setText("WSL processed this job. Open the result workspace to review it.")
            self.open_result_button.setText("Open Result")
            self.open_result_button.show()
            self._latest_result_entry = result_entry
            return "processed"
        if result_entry.state == "failed":
            self.result_summary.setText("WSL failed to process this job. Open the result workspace for details.")
            self.open_result_button.setText("Open Failed Result")
            self.open_result_button.show()
            self._latest_result_entry = result_entry
            return "failed"
        self.result_summary.setText(result_entry.summary)
        self.open_result_button.setText("Track in Workspace")
        self.open_result_button.show()
        self._latest_result_entry = result_entry
        return result_entry.state

    def _open_current_job_result(self) -> None:
        result_entry = getattr(self, "_latest_result_entry", None)
        if result_entry is None:
            self._refresh_current_job_result()
            result_entry = getattr(self, "_latest_result_entry", None)
        if result_entry is None:
            QMessageBox.information(self, "Result unavailable", "No WSL result is available for this job yet.")
            return
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        ResultWorkspaceDialog(parent=self, shared_root=shared_root, selected_job_id=result_entry.job_id).exec()

    def _set_meta_grid_visible(self, visible: bool) -> None:
        for index in range(self.meta_grid.count()):
            item = self.meta_grid.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(visible)
