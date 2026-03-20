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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.result_workspace import ResultWorkspaceEntry, list_recent_results
from windows_client.gui.refresh_policy import RefreshGate
from windows_client.gui.result_renderer import (
    PREVIEW_STYLESHEET,
    _analysis_skip_reason,
    _apply_analysis_state_pill,
    _apply_result_state_pill,
    _format_result_byline,
    _format_result_origin,
    _preview_hint,
    _preview_html,
    _primary_result_button_text,
    _structured_result_payload,
    _truncate_title,
)

RESULT_REFRESH_INTERVAL_SECONDS = 2.0


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
        self.analysis_pill = QLabel("")
        self.analysis_pill.setObjectName("PlatformPill")
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
        self.preview.document().setDefaultStyleSheet(PREVIEW_STYLESHEET)

        actions = QHBoxLayout()
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("GhostButton")
        self.open_folder_button.clicked.connect(self._open_folder)
        self.open_json_button = QPushButton("Open Final Result")
        self.open_json_button.setObjectName("GhostButton")
        self.open_json_button.clicked.connect(self._open_json)
        self.open_markdown_button = QPushButton("Open Technical Markdown")
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

        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 0, 0, 0)
        pill_row.setSpacing(10)
        pill_row.addWidget(self.status_pill, 0, Qt.AlignLeft)
        pill_row.addWidget(self.analysis_pill, 0, Qt.AlignLeft)
        pill_row.addStretch(1)

        detail_layout.addWidget(self.workspace_label)
        detail_layout.addLayout(pill_row)
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

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        parent_geometry = parent.frameGeometry()
        if not parent_geometry.isValid():
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(parent_geometry.center())
        self.move(geometry.topLeft())

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

    def _set_empty_state(self, message: str = "Select a result to inspect its current state.") -> None:
        self.status_pill.hide()
        self.analysis_pill.hide()
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
        self.open_json_button.setText("Open Final Result")
        self.open_markdown_button.hide()
        self.open_markdown_button.setEnabled(False)
        self.open_markdown_button.setText("Open Technical Markdown")

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

    def _render_selected_entry(self, row: int) -> None:
        if row < 0 or row >= len(self.entries):
            self._sync_item_widget_selection(-1)
            self._set_empty_state()
            return
        entry = self.entries[row]
        self._sync_item_widget_selection(row)
        self._selected_job_id = entry.job_id
        self.status_pill.show()
        self.analysis_pill.show()
        self.empty_label.hide()
        _apply_result_state_pill(self.status_pill, entry.state)
        _apply_analysis_state_pill(self.analysis_pill, entry.analysis_state)
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
        self.preview_hint_label.setText(_preview_hint(entry))
        self.preview.setHtml(_preview_html(entry))
        self.open_folder_button.setEnabled(entry.job_dir is not None)
        self.open_json_button.setEnabled(
            entry.analysis_json_path is not None
            or entry.normalized_json_path is not None
            or entry.error_path is not None
            or entry.metadata_path is not None
        )
        self.open_json_button.setText(_primary_result_button_text(entry))
        self.open_markdown_button.setVisible(False)
        self.open_markdown_button.setEnabled(False)
        self.open_markdown_button.setText("Open Technical Markdown")

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
        path = entry.analysis_json_path or entry.normalized_json_path or entry.error_path or entry.metadata_path
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
