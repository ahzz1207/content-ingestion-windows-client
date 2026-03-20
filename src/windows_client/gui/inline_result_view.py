"""Inline result view — shows InsightBriefV2 directly in the main window stack."""
from __future__ import annotations

import html
import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.insight_brief import InsightBriefV2
from windows_client.app.result_workspace import ResultWorkspaceEntry
from windows_client.gui.result_renderer import PREVIEW_STYLESHEET, _preview_html


class InlineResultView(QWidget):
    """Full-window widget that renders an InsightBriefV2 as the main content."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry: ResultWorkspaceEntry | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top action bar (Back button)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 12)
        self._back_button = QPushButton("Back")
        self._back_button.setObjectName("GhostButton")
        top_bar.addWidget(self._back_button, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        root.addLayout(top_bar)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 12, 0)
        content_layout.setSpacing(18)

        # Hero block
        self._hero_frame = QFrame()
        self._hero_frame.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(self._hero_frame)
        hero_layout.setContentsMargins(32, 28, 32, 28)
        hero_layout.setSpacing(10)
        self._hero_title = QLabel("")
        self._hero_title.setObjectName("ResultTitle")
        self._hero_title.setWordWrap(True)
        self._hero_take = QLabel("")
        self._hero_take.setObjectName("BodyText")
        self._hero_take.setWordWrap(True)
        self._hero_byline = QLabel("")
        self._hero_byline.setObjectName("SecondaryText")
        self._hero_byline.setWordWrap(True)
        hero_layout.addWidget(self._hero_title)
        hero_layout.addWidget(self._hero_take)
        hero_layout.addWidget(self._hero_byline)

        # Quick takeaways block
        self._takeaways_frame = QFrame()
        self._takeaways_frame.setObjectName("PreviewCard")
        takeaways_layout = QVBoxLayout(self._takeaways_frame)
        takeaways_layout.setContentsMargins(24, 20, 24, 20)
        takeaways_layout.setSpacing(8)
        takeaways_heading = QLabel("Key Points")
        takeaways_heading.setObjectName("SectionLabel")
        takeaways_layout.addWidget(takeaways_heading)
        self._takeaways_list_layout = QVBoxLayout()
        self._takeaways_list_layout.setSpacing(6)
        takeaways_layout.addLayout(self._takeaways_list_layout)

        # Coverage warning banner (hidden by default)
        self._coverage_banner = QFrame()
        self._coverage_banner.setObjectName("CoverageBanner")
        coverage_layout = QHBoxLayout(self._coverage_banner)
        coverage_layout.setContentsMargins(18, 12, 18, 12)
        self._coverage_label = QLabel("")
        self._coverage_label.setWordWrap(True)
        self._coverage_label.setObjectName("BodyText")
        coverage_layout.addWidget(self._coverage_label)
        self._coverage_banner.hide()

        # Viewpoints / evidence browser
        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDocumentMargin(0)
        self._browser.document().setDefaultStyleSheet(PREVIEW_STYLESHEET)
        self._browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._browser.setMinimumHeight(300)

        # Action row
        action_frame = QWidget()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setObjectName("GhostButton")
        self._open_folder_btn.clicked.connect(self._open_folder)
        self._open_analysis_btn = QPushButton("Open Analysis")
        self._open_analysis_btn.setObjectName("GhostButton")
        self._open_analysis_btn.clicked.connect(self._open_analysis)
        action_layout.addWidget(self._open_folder_btn)
        action_layout.addWidget(self._open_analysis_btn)
        action_layout.addStretch(1)

        content_layout.addWidget(self._hero_frame)
        content_layout.addWidget(self._takeaways_frame)
        content_layout.addWidget(self._coverage_banner)
        content_layout.addWidget(self._browser, 1)
        content_layout.addWidget(action_frame)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    @property
    def back_button(self) -> QPushButton:
        return self._back_button

    def load_brief(self, brief: InsightBriefV2, entry: ResultWorkspaceEntry) -> None:
        """Populate the view with InsightBriefV2 data."""
        self._entry = entry

        # Hero
        self._hero_title.setText(brief.hero.title)
        self._hero_take.setText(brief.hero.one_sentence_take)
        byline_parts = [v for v in (entry.author, entry.published_at, entry.platform) if v]
        self._hero_byline.setText("  ·  ".join(byline_parts) if byline_parts else "")
        self._hero_byline.setVisible(bool(byline_parts))

        # Quick takeaways
        while self._takeaways_list_layout.count():
            item = self._takeaways_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for text in brief.quick_takeaways:
            lbl = QLabel(f"· {text}")
            lbl.setObjectName("BodyText")
            lbl.setWordWrap(True)
            self._takeaways_list_layout.addWidget(lbl)
        self._takeaways_frame.setVisible(bool(brief.quick_takeaways))

        # Coverage banner
        coverage = brief.coverage
        if coverage is not None and coverage.input_truncated:
            pct = int(coverage.coverage_ratio * 100)
            self._coverage_label.setText(
                f"\u26a0 Coverage warning: only {pct}% of source segments were analysed "
                f"({coverage.used_segments}/{coverage.total_segments}). "
                "Conclusions may be incomplete."
            )
            self._coverage_banner.setStyleSheet(
                """
                QFrame#CoverageBanner {
                    background: rgba(239, 68, 68, 0.10);
                    border: 1px solid rgba(239, 68, 68, 0.24);
                    border-radius: 14px;
                }
                """
            )
            self._coverage_banner.show()
        else:
            self._coverage_banner.hide()

        # Viewpoints browser — render via the entry's _preview_html for full fidelity
        self._browser.setHtml(_preview_html(entry))

        # Action buttons
        self._open_folder_btn.setEnabled(entry.job_dir is not None)
        self._open_analysis_btn.setEnabled(entry.analysis_json_path is not None)

    def _open_folder(self) -> None:
        if self._entry is None or self._entry.job_dir is None:
            return
        if os.name == "nt":
            os.startfile(self._entry.job_dir)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._entry.job_dir)))

    def _open_analysis(self) -> None:
        if self._entry is None or self._entry.analysis_json_path is None:
            return
        if os.name == "nt":
            os.startfile(self._entry.analysis_json_path)  # type: ignore[attr-defined]
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._entry.analysis_json_path)))
