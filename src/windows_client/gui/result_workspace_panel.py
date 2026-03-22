"""ResultListItemWidget and ResultWorkspaceDialog extracted from main_window.py."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.result_workspace import ResultWorkspaceEntry, list_recent_results
from windows_client.gui.refresh_policy import RefreshGate

RESULT_REFRESH_INTERVAL_SECONDS = 2.0

_STATE_COLORS = {
    "processed": ("#15803d", "rgba(22, 163, 74, 0.10)"),   # green
    "failed":    ("#b91c1c", "rgba(239, 68, 68, 0.10)"),    # red
    "processing":("#b45309", "rgba(245, 158, 11, 0.10)"),   # amber
    "pending":   ("#6b7280", "rgba(107, 114, 128, 0.08)"),  # grey
}


def _format_updated_at(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M")


def _start_button_cooldown(button: QPushButton, *, seconds: float, label: str) -> None:
    from PySide6.QtCore import QTimer

    button.setEnabled(False)
    button.setText(f"{label}...")

    def _restore() -> None:
        button.setEnabled(True)
        button.setText(label)

    QTimer.singleShot(int(seconds * 1000), _restore)


def _state_dot(state: str) -> str:
    return {"processed": "●", "failed": "✕", "processing": "◌", "pending": "○"}.get(state, "○")


class ResultListItemWidget(QFrame):
    def __init__(self, entry: ResultWorkspaceEntry) -> None:
        super().__init__()
        self.entry = entry
        self.setObjectName("ResultListItem")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        title = entry.title or entry.job_id
        if len(title) > 52:
            title = title[:50] + "…"
        self.title_label = QLabel(title)
        self.title_label.setObjectName("ResultListTitle")
        self.title_label.setWordWrap(False)

        dot = _state_dot(entry.state)
        platform = (entry.platform or "Unknown").title()
        self.meta_label = QLabel(f"{dot} {platform} · {_format_updated_at(entry.updated_at)}")
        self.meta_label.setObjectName("ResultListMeta")

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        text_color, meta_color = _STATE_COLORS.get(self.entry.state, _STATE_COLORS["pending"])
        if selected:
            self.setStyleSheet(f"""
                QFrame#ResultListItem {{
                    background: rgba(163, 75, 45, 0.10);
                    border: 1px solid rgba(163, 75, 45, 0.22);
                    border-radius: 14px;
                }}
                QLabel#ResultListTitle {{
                    color: #0f172a;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QLabel#ResultListMeta {{
                    color: #8f3f25;
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ResultListItem {{
                    background: rgba(248, 250, 252, 0.82);
                    border: 1px solid rgba(148, 163, 184, 0.10);
                    border-radius: 14px;
                }}
                QLabel#ResultListTitle {{
                    color: #18222f;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QLabel#ResultListMeta {{
                    color: {meta_color[0] if self.entry.state in ("failed",) else "#64748b"};
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)


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
        self.entry_to_open: ResultWorkspaceEntry | None = None  # set when user clicks View

        self.setWindowTitle("历史记录")
        self.resize(1100, 680)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(16)

        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(10)

        sidebar_header = QHBoxLayout()
        sidebar_title = QLabel("最近处理")
        sidebar_title.setObjectName("SectionLabel")
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("GhostButton")
        self.refresh_button.setToolTip("每 2 秒最多刷新一次")
        self.refresh_button.clicked.connect(self._request_reload_entries)
        sidebar_header.addWidget(sidebar_title)
        sidebar_header.addStretch(1)
        sidebar_header.addWidget(self.refresh_button)

        self.results_list = QListWidget()
        self.results_list.setObjectName("ResultList")
        self.results_list.setSpacing(6)
        self.results_list.currentRowChanged.connect(self._render_selected_entry)
        self.results_list.itemDoubleClicked.connect(self._on_double_click)

        sidebar_layout.addLayout(sidebar_header)
        sidebar_layout.addWidget(self.results_list, 1)

        # ── Detail panel ─────────────────────────────────────────────
        detail_card = QFrame()
        detail_card.setObjectName("DetailCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(28, 24, 28, 24)
        detail_layout.setSpacing(0)

        # Empty / placeholder
        self.empty_label = QLabel("从左侧选择一条记录")
        self.empty_label.setObjectName("SecondaryText")
        self.empty_label.setAlignment(Qt.AlignCenter)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content_widget = QWidget()
        self._content_layout = QVBoxLayout(content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(16)

        # Hero block
        self._hero_frame = QFrame()
        self._hero_frame.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(self._hero_frame)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(8)

        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        self._state_pill = QLabel("")
        self._state_pill.setObjectName("StatePill")
        self._analysis_pill = QLabel("")
        self._analysis_pill.setObjectName("StatePill")
        pill_row.addWidget(self._state_pill)
        pill_row.addWidget(self._analysis_pill)
        pill_row.addStretch(1)

        self._title_label = QLabel("")
        self._title_label.setObjectName("ResultTitle")
        self._title_label.setWordWrap(True)
        self._take_label = QLabel("")
        self._take_label.setObjectName("HeroTake")
        self._take_label.setWordWrap(True)
        self._byline_label = QLabel("")
        self._byline_label.setObjectName("SecondaryText")
        self._byline_label.setWordWrap(True)
        self._source_label = QLabel("")
        self._source_label.setObjectName("SecondaryText")
        self._source_label.setOpenExternalLinks(True)
        self._source_label.setTextFormat(Qt.RichText)
        self._source_label.setWordWrap(True)

        hero_layout.addLayout(pill_row)
        hero_layout.addWidget(self._title_label)
        hero_layout.addWidget(self._take_label)
        hero_layout.addWidget(self._byline_label)
        hero_layout.addWidget(self._source_label)

        # Key points block
        self._kp_frame = QFrame()
        self._kp_frame.setObjectName("PreviewCard")
        kp_layout = QVBoxLayout(self._kp_frame)
        kp_layout.setContentsMargins(20, 16, 20, 16)
        kp_layout.setSpacing(10)
        kp_heading = QLabel("作者观点")
        kp_heading.setObjectName("SectionLabel")
        kp_layout.addWidget(kp_heading)
        self._kp_list_layout = QVBoxLayout()
        self._kp_list_layout.setSpacing(8)
        kp_layout.addLayout(self._kp_list_layout)

        # Bottom line block
        self._bl_frame = QFrame()
        self._bl_frame.setObjectName("BottomLineCard")
        bl_layout = QVBoxLayout(self._bl_frame)
        bl_layout.setContentsMargins(20, 14, 20, 14)
        bl_layout.setSpacing(6)
        bl_heading = QLabel("Bottom Line")
        bl_heading.setObjectName("SectionLabel")
        self._bl_label = QLabel("")
        self._bl_label.setObjectName("BodyText")
        self._bl_label.setWordWrap(True)
        bl_layout.addWidget(bl_heading)
        bl_layout.addWidget(self._bl_label)

        # Error / status note for non-processed entries
        self._status_note = QLabel("")
        self._status_note.setObjectName("SecondaryText")
        self._status_note.setWordWrap(True)
        self._status_note.setAlignment(Qt.AlignCenter)

        self._content_layout.addWidget(self._hero_frame)
        self._content_layout.addWidget(self._kp_frame)
        self._content_layout.addWidget(self._bl_frame)
        self._content_layout.addWidget(self._status_note)
        self._content_layout.addStretch(1)

        scroll.setWidget(content_widget)

        # Action row
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.view_button = QPushButton("查看完整分析")
        self.view_button.setObjectName("PrimaryButton")
        self.view_button.clicked.connect(self._open_entry)
        self.folder_button = QPushButton("打开文件夹")
        self.folder_button.setObjectName("GhostButton")
        self.folder_button.clicked.connect(self._open_folder)
        self.json_button = QPushButton("导出 JSON")
        self.json_button.setObjectName("GhostButton")
        self.json_button.clicked.connect(self._open_json)
        close_button = QPushButton("关闭")
        close_button.setObjectName("GhostButton")
        close_button.clicked.connect(self.reject)
        actions.addWidget(self.view_button)
        actions.addWidget(self.folder_button)
        actions.addWidget(self.json_button)
        actions.addStretch(1)
        actions.addWidget(close_button)

        detail_layout.addWidget(self.empty_label)
        detail_layout.addWidget(scroll, 1)
        detail_layout.addSpacing(12)
        detail_layout.addLayout(actions)

        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(detail_card, 1)

        self._set_empty_state()
        self._reload_entries()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        geo = parent.frameGeometry()
        if not geo.isValid():
            return
        self.frameGeometry().moveCenter(geo.center())
        self.move(self.frameGeometry().topLeft())

    # ── Loading ───────────────────────────────────────────────────────

    def _request_reload_entries(self) -> None:
        if not self._refresh_gate.allow_now():
            return
        self._refresh_gate.mark()
        _start_button_cooldown(self.refresh_button, seconds=RESULT_REFRESH_INTERVAL_SECONDS, label="刷新")
        self._reload_entries()

    def _reload_entries(self) -> None:
        current = self._selected_entry()
        selected_job_id = current.job_id if current is not None else self._selected_job_id
        self.entries = list_recent_results(self.shared_root, limit=30)
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
            self._set_empty_state("暂无处理记录")
            return
        selected_index = 0
        if selected_job_id is not None:
            for i, e in enumerate(self.entries):
                if e.job_id == selected_job_id:
                    selected_index = i
                    break
        self.results_list.setCurrentRow(selected_index)
        self._selected_job_id = self.entries[selected_index].job_id

    # ── State ─────────────────────────────────────────────────────────

    def _set_empty_state(self, message: str = "从左侧选择一条记录") -> None:
        self.empty_label.setText(message)
        self.empty_label.show()
        self._hero_frame.hide()
        self._kp_frame.hide()
        self._bl_frame.hide()
        self._status_note.hide()
        self.view_button.setEnabled(False)
        self.folder_button.setEnabled(False)
        self.json_button.setEnabled(False)

    def _selected_entry(self) -> ResultWorkspaceEntry | None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self.entries):
            return None
        return self.entries[row]

    def _sync_item_selection(self, selected_row: int) -> None:
        for i, w in enumerate(self._item_widgets):
            w.set_selected(i == selected_row)

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_selected_entry(self, row: int) -> None:
        if row < 0 or row >= len(self.entries):
            self._sync_item_selection(-1)
            self._set_empty_state()
            return
        entry = self.entries[row]
        self._sync_item_selection(row)
        self._selected_job_id = entry.job_id
        self.empty_label.hide()

        # Pills
        state_color, state_bg = _STATE_COLORS.get(entry.state, _STATE_COLORS["pending"])
        state_text = {"processed": "已完成", "failed": "失败", "processing": "处理中", "pending": "待处理"}.get(entry.state, entry.state)
        self._state_pill.setText(state_text)
        self._state_pill.setStyleSheet(f"""
            QLabel {{ background: {state_bg}; color: {state_color};
                      border-radius: 999px; padding: 4px 12px;
                      font-size: 12px; font-weight: 600; }}
        """)
        analysis_text = {"pass": "LLM ✓", "warn": "LLM ⚠", "skipped": "LLM 跳过", "failed": "LLM 失败"}.get(entry.analysis_state or "", "")
        if analysis_text:
            self._analysis_pill.setText(analysis_text)
            self._analysis_pill.show()
        else:
            self._analysis_pill.hide()

        # Hero
        brief = entry.details.get("insight_brief") if entry.details else None
        if brief is not None:
            self._title_label.setText(getattr(brief.hero, "title", entry.title or entry.job_id))
            self._take_label.setText(getattr(brief.hero, "one_sentence_take", ""))
            self._take_label.setVisible(bool(self._take_label.text()))
        else:
            self._title_label.setText(entry.title or entry.job_id)
            self._take_label.setText(entry.summary or "")
            self._take_label.setVisible(bool(entry.summary))

        byline_parts = [v for v in (entry.author, entry.published_at, entry.platform) if v]
        self._byline_label.setText("  ·  ".join(byline_parts))
        self._byline_label.setVisible(bool(byline_parts))

        url = entry.source_url or entry.canonical_url
        if url:
            import html as _html
            display = url if len(url) <= 60 else url[:57] + "…"
            self._source_label.setText(f"<a href='{_html.escape(url)}'>{_html.escape(display)}</a>")
            self._source_label.show()
        else:
            self._source_label.hide()

        self._hero_frame.show()

        # Key points
        self._clear_layout(self._kp_list_layout)
        viewpoints = []
        if brief is not None:
            viewpoints = [v for v in (brief.viewpoints or []) if v.kind == "key_point"]
        if viewpoints:
            for i, vp in enumerate(viewpoints[:6], start=1):
                lbl = QLabel(f"{i:02d} · {vp.statement}")
                lbl.setObjectName("BodyText")
                lbl.setWordWrap(True)
                self._kp_list_layout.addWidget(lbl)
                if vp.why_it_matters:
                    detail_lbl = QLabel(vp.why_it_matters)
                    detail_lbl.setObjectName("SecondaryText")
                    detail_lbl.setWordWrap(True)
                    detail_lbl.setContentsMargins(20, 0, 0, 4)
                    self._kp_list_layout.addWidget(detail_lbl)
            if len(viewpoints) > 6:
                more = QLabel(f"…还有 {len(viewpoints) - 6} 条观点，点击「查看完整分析」")
                more.setObjectName("SecondaryText")
                self._kp_list_layout.addWidget(more)
            self._kp_frame.show()
        else:
            self._kp_frame.hide()

        # Bottom line
        conclusion = getattr(brief, "synthesis_conclusion", None) if brief is not None else None
        if conclusion:
            self._bl_label.setText(conclusion)
            self._bl_frame.show()
        else:
            self._bl_frame.hide()

        # Status note for non-processed / failed
        if entry.state == "failed":
            error_msg = ""
            if entry.details:
                err = entry.details.get("error") or {}
                if isinstance(err, dict):
                    error_msg = err.get("message") or err.get("code") or ""
            self._status_note.setText(f"处理失败：{error_msg}" if error_msg else "处理失败")
            self._status_note.show()
        elif entry.state == "processing":
            self._status_note.setText("正在处理中…")
            self._status_note.show()
        else:
            self._status_note.hide()

        # Buttons
        self.view_button.setEnabled(entry.state == "processed" and brief is not None)
        self.folder_button.setEnabled(entry.job_dir is not None)
        self.json_button.setEnabled(
            entry.analysis_json_path is not None or entry.normalized_json_path is not None
        )

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Actions ───────────────────────────────────────────────────────

    def _on_double_click(self, _item: QListWidgetItem) -> None:
        self._open_entry()

    def _open_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None or entry.state != "processed":
            return
        self.entry_to_open = entry
        self.accept()

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
        path = entry.analysis_json_path or entry.normalized_json_path
        if path is None:
            return
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
