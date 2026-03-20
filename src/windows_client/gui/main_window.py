from __future__ import annotations

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
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.result_workspace import ResultWorkspaceEntry, list_recent_results, load_job_result
from windows_client.app.view_models import OperationViewState
from windows_client.app.workflow import WindowsClientWorkflow
from windows_client.app.wsl_bridge import WslBridge
from windows_client.gui.inline_result_view import InlineResultView
from windows_client.gui.platform_router import PlatformRoute, resolve_platform_route
from windows_client.gui.refresh_policy import RefreshGate
from windows_client.gui.result_renderer import (  # re-exported for test compatibility
    _preview_html,
    _structured_result_payload,
)
from windows_client.gui.result_workspace_panel import ResultListItemWidget, ResultWorkspaceDialog
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
AUTO_RESULT_POLL_MAX_ATTEMPTS = 20


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
        self.result_inline = InlineResultView(parent=self)
        self.result_inline.back_button.clicked.connect(self._show_task_state)
        self.stack.addWidget(self.ready_page)
        self.stack.addWidget(self.task_page)
        self.stack.addWidget(self.result_inline)

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

        eyebrow = QLabel("Capture  →  Analyse  →  Read")
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
            (
                "LLM ready" if values.get("wsl_llm_credentials_available") == "True" else "LLM missing",
                values.get("wsl_llm_credentials_available") == "True",
            ),
            (
                f"Whisper {values.get('wsl_whisper_model_override')}"
                if values.get("wsl_whisper_model_override") not in {None, "", "default"}
                else "Whisper default",
                values.get("wsl_whisper_model_override") not in {None, "", "default"},
            ),
        ]
        try:
            watcher_status = self.wsl_bridge.watch_status()
        except Exception:
            watcher_status = None
        if watcher_status is None:
            pills.append(("Processor not started", False))
        else:
            pills.append(
                (
                    "Processor running" if watcher_status.get("running") == "True" else "Processor stopped",
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

    def _show_task_state(self) -> None:
        """Return to the task page (used by the inline result view's back button)."""
        self.stack.setCurrentWidget(self.task_page)

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
        summary = "Your content has been captured and sent for analysis. Results will appear here automatically."
        if not self.workflow.service.settings.llm_credentials_available:
            summary = (
                "Analysis is not configured — set OPENAI_API_KEY or ZENMUX_API_KEY to enable it."
            )
        elif self._current_route is not None and self._current_route.is_video and not self.workflow.service.settings.whisper_model_override:
            summary = (
                "Transcription will use the default Whisper model. "
                "Set CONTENT_INGESTION_WHISPER_MODEL to override."
            )
        self.result_summary.setText(summary)
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
            QMessageBox.information(self, "No results yet", "No results are available yet.")
            return
        self._show_result_workspace(shared_root=shared_root, selected_job_id=None)

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
                "Analysis is still in progress. Check back later."
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
                "No analysis result yet."
                if not from_auto_poll
                else "Waiting for the processor to pick this up..."
            )
            self._latest_result_entry = None
            self.open_result_button.hide()
            return "missing"
        if result_entry.state == "processed":
            self.result_summary.setText(result_entry.summary)
            self.open_result_button.setText("Open Result")
            self.open_result_button.show()
            self._latest_result_entry = result_entry
            # Navigate to inline result view if a brief is available
            brief = result_entry.details.get("insight_brief")
            if brief is not None:
                self.result_inline.load_brief(brief, entry=result_entry)
                self.stack.setCurrentWidget(self.result_inline)
            return "processed"
        if result_entry.state == "failed":
            self.result_summary.setText("Processing failed. Open the result workspace for details.")
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
            QMessageBox.information(self, "Result unavailable", "No result is available for this job yet.")
            return
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        self._show_result_workspace(shared_root=shared_root, selected_job_id=result_entry.job_id)
        refreshed_state = self._refresh_current_job_result()
        if refreshed_state not in {"processed", "failed", "unavailable"}:
            self._start_result_polling()

    def _show_result_workspace(self, *, shared_root: Path, selected_job_id: str | None) -> None:
        try:
            dialog = ResultWorkspaceDialog(parent=self, shared_root=shared_root, selected_job_id=selected_job_id)
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            dialog.exec()
        except Exception as exc:  # pragma: no cover - GUI boundary
            QMessageBox.critical(self, "Result workspace failed", str(exc) or type(exc).__name__)

    def _set_meta_grid_visible(self, visible: bool) -> None:
        for index in range(self.meta_grid.count()):
            item = self.meta_grid.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(visible)
