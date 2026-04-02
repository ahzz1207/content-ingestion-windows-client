from __future__ import annotations

import json
import logging
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from PySide6.QtCore import Qt, QTimer, QUrl, Signal as _Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from windows_client.app.result_workspace import ResultWorkspaceEntry, load_job_result
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


logger = logging.getLogger(__name__)


STAGE_LABELS = {
    "idle": "Ready",
    "analyzing_url": "正在检查链接…",
    "checking_runtime": "正在启动浏览器…",
    "opening_browser": "正在打开浏览器…",
    "waiting_for_login": "等待登录…",
    "collecting": "正在采集页面内容…",
    "downloading_video": "正在下载视频（通常需要 1–3 分钟）…",
    "exporting": "正在打包任务…",
    "processing": "AI 正在分析中…",
    "transcript_done": "转录完成，AI 正在分析中…",
    "awaiting_llm": "正在等待 LLM 响应…",
    "done": "完成",
    "failed": "处理失败",
}

RESULT_REFRESH_INTERVAL_SECONDS = 2.0
AUTO_RESULT_POLL_INTERVAL_MS = 3000        # first 60s: fast
AUTO_RESULT_POLL_SLOW_INTERVAL_MS = 10_000  # 60s–5min: patient wait for transcription
AUTO_RESULT_POLL_VERY_SLOW_MS = 20_000      # 5min–12min: long video
AUTO_RESULT_POLL_TIMEOUT_SECONDS = 720      # hard cap: 12 minutes

ANALYSIS_MODE_OPTIONS = [
    ("Auto", "auto"),
    ("深度分析", "argument"),
    ("实用提炼", "guide"),
    ("推荐导览", "review"),
]


def _safe_domain(url: str) -> str:
    return urlparse(url).netloc or url


def _normalize_url(url: str) -> str:
    """Strip known tracking/session params from platform URLs."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if "mp.weixin.qq.com" in netloc:
        keep = {"__biz", "mid", "sn", "idx"}
        qs = {k: v for k, v in parse_qs(parsed.query, keep_blank_values=False).items() if k in keep}
        return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    if "bilibili.com" in netloc:
        qs = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: v for k, v in qs.items() if k == "p"}
        return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True) if filtered else ""))
    return url


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
    if state.error.code == "video_download_failed":
        stderr = (state.error.details or {}).get("stderr", "")
        last_error = next(
            (ln.strip() for ln in reversed(stderr.splitlines()) if ln.strip()),
            "",
        )
        return f"视频下载失败。{(' — ' + last_error) if last_error else ''}"
    if state.error.code == "video_download_requires_ffmpeg":
        return "视频下载需要 ffmpeg，请先安装 ffmpeg。"
    return state.summary


def _load_export_metadata(metadata_path: Path) -> dict[str, object]:
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _resolved_mode_from_entry(entry: ResultWorkspaceEntry) -> str | None:
    normalized = entry.details.get("normalized")
    if not isinstance(normalized, dict):
        return None
    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        return None
    llm_processing = metadata.get("llm_processing")
    if not isinstance(llm_processing, dict):
        return None
    value = str(llm_processing.get("resolved_mode") or "").strip().lower()
    return value or None


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
    _status_ready = _Signal(object, object)  # (doctor_state, watcher_status) — thread-safe delivery

    def __init__(self, *, workflow: WindowsClientWorkflow) -> None:
        super().__init__()
        self.workflow = workflow
        self.wsl_bridge = WslBridge(workflow.service.settings)
        self._task_thread: WorkflowTaskThread | None = None
        self._current_route: PlatformRoute | None = None
        self._current_url: str = ""
        self._current_state: OperationViewState | None = None
        self._latest_result_entry: ResultWorkspaceEntry | None = None
        self._watcher_running: bool | None = None  # cached from last status refresh
        self._result_poll_timer = QTimer(self)
        self._result_poll_timer.setSingleShot(True)
        self._result_poll_timer.timeout.connect(self._poll_current_job_result)
        self._result_poll_start_time: float = 0.0
        self._last_inferred_stage: str = ""
        self._watcher_poll_timer = QTimer(self)
        self._watcher_poll_timer.setInterval(15_000)
        self._watcher_poll_timer.timeout.connect(self._poll_watcher_status)

        self.setWindowTitle("Collect")
        self.resize(980, 700)
        self.setMinimumSize(860, 620)

        self._build_ui()
        self._apply_styles()
        self._status_ready.connect(self._apply_status_result)
        # Show placeholder immediately so the window opens without blocking
        self._set_pills([("Checking status…", True)])
        self._launch_status_refresh()
        self._watcher_poll_timer.start()
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
        self.result_inline.new_url_button.clicked.connect(self._reset_to_ready_state)
        self.result_inline.reanalyze_requested.connect(self._reanalyze_url)
        self.result_inline.history_button.clicked.connect(self._open_history_from_result)
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

        self.analysis_mode_combo = QComboBox()
        self.analysis_mode_combo.setObjectName("GhostButton")
        for label, value in ANALYSIS_MODE_OPTIONS:
            self.analysis_mode_combo.addItem(label, value)

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
        self.latest_result_button = QPushButton("History")
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
        card_layout.addWidget(self.analysis_mode_combo, 0, Qt.AlignLeft)
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
        self._elapsed_label = QLabel("")
        self._elapsed_label.setObjectName("ElapsedText")
        self._elapsed_label.hide()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._task_start_time: float = 0.0

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
        self.retry_button = QPushButton("Retry")
        self.retry_button.setObjectName("GhostButton")
        self.retry_button.clicked.connect(self._retry_current_url)
        self.new_url_button = QPushButton("New URL")
        self.new_url_button.setObjectName("PrimaryButton")
        self.new_url_button.clicked.connect(self._reset_to_ready_state)
        for button in (
            self.retry_browser_button,
            self.retry_button,
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
        card_layout.addWidget(self._elapsed_label)
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
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
            #SectionLabelBlue {
                font-size: 12px;
                font-weight: 700;
                color: #2563eb;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
            #HeroTake {
                font-size: 18px;
                font-weight: 500;
                color: #16202b;
            }
            #TakeawayIndexed {
                font-size: 15px;
                font-weight: 600;
                color: #2f4558;
            }
            #BodyText {
                font-size: 15px;
                color: #2f4558;
            }
            #SecondaryText {
                font-size: 14px;
                color: #6b7280;
            }
            #ElapsedText {
                font-size: 13px;
                color: #9ca3af;
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
            #BottomLineCard {
                background: rgba(37, 99, 235, 0.06);
                border: 1px solid rgba(37, 99, 235, 0.18);
                border-radius: 14px;
            }
            QFrame#InsightCardFrame {
                background: transparent;
                border: none;
            }
            #CoverageBanner {
                background: rgba(239, 68, 68, 0.10);
                border: 1px solid rgba(239, 68, 68, 0.24);
                border-radius: 14px;
            }
            #VerificationCard {
                background: rgba(255, 255, 255, 0.60);
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 12px;
            }
            #VerifChip_supported {
                background: rgba(22, 163, 74, 0.13);
                color: #15803d;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            #VerifChip_partial {
                background: rgba(245, 158, 11, 0.14);
                color: #b45309;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            #VerifChip_unsupported, #VerifChip_unclear {
                background: rgba(220, 38, 38, 0.10);
                color: #b91c1c;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            #TagChip {
                background: rgba(163, 75, 45, 0.09);
                color: #8f3f25;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            #TagChipMuted {
                background: rgba(148, 163, 184, 0.12);
                color: #475569;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 12px;
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
                font-size: 16px;
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

    def _launch_status_refresh(self) -> None:
        """Fetch doctor + watcher status in a background thread; emit signal to update UI."""
        def _worker() -> None:
            try:
                doctor_state = self.workflow.run_doctor()
            except Exception:
                doctor_state = None
            try:
                watcher_status = self.wsl_bridge.watch_status()
            except Exception:
                watcher_status = None
            self._status_ready.emit(doctor_state, watcher_status)

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_status_result(
        self,
        doctor_state: object,
        watcher_status: dict[str, str] | None,
    ) -> None:
        """Update the header pills from pre-fetched doctor + watcher data (main thread)."""
        running = watcher_status.get("running") == "True" if watcher_status else False
        self._watcher_running = running

        from windows_client.app.view_models import OperationViewState  # local to avoid circular
        if (
            not isinstance(doctor_state, OperationViewState)
            or doctor_state.status != "success"
            or doctor_state.doctor is None
        ):
            watcher_pill = "WSL 处理中 ●" if running else "WSL 未运行 ○"
            self._set_pills([("Status unavailable", False), (watcher_pill, running)])
            return

        values = doctor_state.doctor.values
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
        if watcher_status is None:
            pills.append(("WSL 未启动 ○", False))
        else:
            pills.append(("WSL 处理中 ●" if running else "WSL 已停止 ○", running))
        profiles_dir = Path(values.get("browser_profiles_dir", ""))
        for slug, label in (("wechat", "WeChat profile"), ("xiaohongshu", "Xiaohongshu profile"), ("youtube", "YouTube profile")):
            pills.append((f"{label} ready" if (profiles_dir / slug).exists() else f"{label} missing", (profiles_dir / slug).exists()))
        self._set_pills(pills)

    def _poll_watcher_status(self) -> None:
        """Lightweight periodic check — only re-fetches watcher state (no WSL subprocess)."""
        try:
            watcher_status = self.wsl_bridge.watch_status()
        except Exception:
            watcher_status = None
        running = watcher_status.get("running") == "True" if watcher_status else False
        if running != self._watcher_running:
            self._launch_status_refresh()

    def _refresh_environment_status(self) -> None:
        self._launch_status_refresh()

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
        self.analysis_mode_combo.setCurrentIndex(0)
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
        url = _normalize_url(url)
        self._current_url = url
        route = resolve_platform_route(url)
        self._current_route = route
        # Warn if WSL watcher appears to be stopped — use cached status, no blocking call
        if not self._watcher_running:
            answer = QMessageBox.question(
                self,
                "Processor not running",
                "The WSL processor doesn't appear to be running.\n"
                "The job will be queued but may not be analysed automatically.\n\n"
                "Continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
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
        requested_mode = self._selected_requested_mode()

        if strategy == "browser":
            profile_dir = route.profile_dir(self.workflow.service.settings)
            self._task_thread = WorkflowTaskThread(
                lambda progress: self.workflow.export_browser_job(
                    url=url,
                    platform=route.platform,
                    requested_mode=requested_mode,
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
                    requested_mode=requested_mode,
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
        self.retry_button.hide()
        self.new_url_button.hide()
        self._set_meta_grid_visible(False)
        for value_label in self.meta_labels.values():
            value_label.clear()
        self.progress_bar.show()
        self.back_button.setEnabled(False)
        self._task_start_time = time.monotonic()
        self._elapsed_label.setText("已用时 00:00")
        self._elapsed_label.show()
        self._elapsed_timer.start()

    def _sync_video_download_controls(self, text: str) -> None:
        route = resolve_platform_route(text.strip()) if text.strip() else None
        visible = route is not None and route.is_video
        self.save_video_checkbox.setVisible(visible)
        self.video_mode_hint.setVisible(visible)

    def _selected_video_download_mode(self, route: PlatformRoute) -> str:
        if route.is_video and self.save_video_checkbox.isChecked():
            return "video"
        return "audio"

    def _selected_requested_mode(self) -> str:
        return str(self.analysis_mode_combo.currentData() or "auto")

    def _on_task_progress(self, stage: str) -> None:
        self.stage_label.setText(STAGE_LABELS.get(stage, stage))

    def _on_task_completed(self, state: OperationViewState) -> None:
        self._current_state = state
        self._elapsed_timer.stop()
        self._elapsed_label.hide()
        self.back_button.setEnabled(True)
        self.progress_bar.hide()
        if state.status == "success":
            self.stage_label.setText(STAGE_LABELS["done"])
            self._render_success(state)
        else:
            self.stage_label.setText(STAGE_LABELS["failed"])
            self._render_failure(state)
        self._task_thread = None

    def _on_task_crashed(self, message: str) -> None:
        self._elapsed_timer.stop()
        self._elapsed_label.hide()
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
        self.stage_label.setText(STAGE_LABELS["processing"])
        self._elapsed_label.show()
        self._elapsed_timer.start()
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
        self.new_url_button.show()
        if self._current_route is not None and self._current_route.strategy == "http":
            self.retry_browser_button.show()

    def _retry_in_browser(self) -> None:
        if self._current_route is None or not self._current_url:
            return
        self._run_export(route=self._current_route, url=self._current_url, force_browser=True)

    def _retry_current_url(self) -> None:
        if self._current_route is None or not self._current_url:
            return
        self._run_export(route=self._current_route, url=self._current_url)

    def _reanalyze_url(self, url: str) -> None:
        self.url_input.setText(url)
        self._start_from_input()

    def _toggle_details(self, visible: bool) -> None:
        self.details_toggle.setText("Hide technical details" if visible else "Show technical details")
        self.details_text.setVisible(visible)

    def _open_latest_result(self) -> None:
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        self._show_result_workspace(shared_root=shared_root, selected_job_id=None)

    def _open_history_from_result(self) -> None:
        """Open history dialog from the result view; return to ready page if nothing is selected."""
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        job_id = self._latest_result_entry.job_id if self._latest_result_entry else None
        # Navigate away from the result view first so closing the dialog
        # without selecting a new entry lands on the ready page, not the old result.
        self._reset_to_ready_state()
        self._show_result_workspace(shared_root=shared_root, selected_job_id=job_id)

    def _start_result_polling(self) -> None:
        self._result_poll_start_time = time.monotonic()
        self._last_inferred_stage = ""
        self._schedule_result_poll()

    def _update_elapsed(self) -> None:
        elapsed = int(time.monotonic() - self._task_start_time)
        minutes, seconds = divmod(elapsed, 60)
        self._elapsed_label.setText(f"已用时 {minutes:02d}:{seconds:02d}")

    def _stop_result_polling(self) -> None:
        self._result_poll_timer.stop()

    def _poll_elapsed_seconds(self) -> float:
        """Seconds since result polling started."""
        if self._result_poll_start_time == 0.0:
            return 0.0
        return time.monotonic() - self._result_poll_start_time

    def _schedule_result_poll(self) -> None:
        elapsed = self._poll_elapsed_seconds()
        if elapsed >= AUTO_RESULT_POLL_TIMEOUT_SECONDS:
            return
        if elapsed >= 300:  # 5 min+: very slow
            interval = AUTO_RESULT_POLL_VERY_SLOW_MS
        elif elapsed >= 60:  # 1–5 min: slow
            interval = AUTO_RESULT_POLL_SLOW_INTERVAL_MS
        else:
            interval = AUTO_RESULT_POLL_INTERVAL_MS
        self._result_poll_timer.start(interval)

    def _poll_current_job_result(self) -> None:
        state = self._refresh_current_job_result(from_auto_poll=True)
        if state in {"processed", "failed"}:
            self._stop_result_polling()
            return
        if self._poll_elapsed_seconds() >= AUTO_RESULT_POLL_TIMEOUT_SECONDS:
            self.result_summary.setText(
                "Analysis is still in progress. Check back later."
            )
            return
        self._schedule_result_poll()

    def _refresh_current_job_result(self, *, from_auto_poll: bool = False) -> str:
        if self._current_state is None or self._current_state.job is None:
            return "unavailable"
        shared_root = self.workflow.service.settings.effective_shared_inbox_root
        try:
            result_entry = load_job_result(shared_root, self._current_state.job.job_id)
        except Exception as exc:
            logger.warning(
                "failed to load current job result for %s: %s",
                self._current_state.job.job_id,
                exc,
            )
            self.result_summary.setText(
                "Result is being prepared, but the GUI could not load it yet. Retrying automatically..."
                if from_auto_poll
                else "The analysis result is not ready for display yet. The GUI will retry automatically."
            )
            self.result_summary.show()
            self._latest_result_entry = None
            return "unavailable"
        if result_entry is None:
            self.result_summary.setText(
                "No analysis result yet."
                if not from_auto_poll
                else "Waiting for the processor to pick this up..."
            )
            self._latest_result_entry = None
            return "missing"
        if result_entry.state == "processed":
            self._latest_result_entry = result_entry
            brief = result_entry.details.get("insight_brief")
            self.result_inline.load_entry(
                result_entry,
                brief=brief,
                resolved_mode=_resolved_mode_from_entry(result_entry),
            )
            self._stop_result_polling()
            self._elapsed_timer.stop()
            self._elapsed_label.hide()
            self.stack.setCurrentWidget(self.result_inline)
            return "processed"
        if result_entry.state == "failed":
            error_msg = result_entry.summary or "Processing failed."
            if len(error_msg) > 300:
                error_msg = error_msg[:297] + "..."
            self.result_summary.setText(f"Processing failed: {error_msg}")
            self.result_summary.show()
            self.retry_button.show()
            self.new_url_button.show()
            self._latest_result_entry = result_entry
            return "failed"
        if result_entry.state == "processing" and result_entry.job_id:
            inferred = self._infer_processing_stage(
                shared_root / "processing" / result_entry.job_id
            )
            if inferred != self._last_inferred_stage:
                self._last_inferred_stage = inferred
                self.stage_label.setText(inferred)
        self.result_summary.setText(result_entry.summary)
        self._latest_result_entry = result_entry
        return result_entry.state

    def _infer_processing_stage(self, processing_job_dir: Path) -> str:
        """Infer the current WSL pipeline stage from intermediate files."""
        if (processing_job_dir / "analysis" / "llm" / "text_request.json").exists():
            return STAGE_LABELS["awaiting_llm"]
        if (processing_job_dir / "analysis" / "transcript" / "transcript.json").exists():
            return STAGE_LABELS["transcript_done"]
        return STAGE_LABELS["processing"]

    def _show_result_workspace(self, *, shared_root: Path, selected_job_id: str | None) -> None:
        try:
            dialog = ResultWorkspaceDialog(parent=self, shared_root=shared_root, selected_job_id=selected_job_id)
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            dialog.exec()
            if dialog.entry_to_open is not None:
                self._load_entry_into_result_view(dialog.entry_to_open)
        except Exception as exc:  # pragma: no cover - GUI boundary
            QMessageBox.critical(self, "Result workspace failed", str(exc) or type(exc).__name__)

    def _load_entry_into_result_view(self, entry: ResultWorkspaceEntry) -> None:
        """Load a history entry directly into the inline result view."""
        from windows_client.app.insight_brief import InsightBriefV2
        brief = entry.details.get("insight_brief") if entry.details else None
        if not isinstance(brief, InsightBriefV2):
            brief = None
        self._latest_result_entry = entry
        self.result_inline.load_entry(entry, brief=brief, resolved_mode=_resolved_mode_from_entry(entry))
        self.stack.setCurrentWidget(self.result_inline)

    def _set_meta_grid_visible(self, visible: bool) -> None:
        for index in range(self.meta_grid.count()):
            item = self.meta_grid.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(visible)
