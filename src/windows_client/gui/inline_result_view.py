"""Inline result view — shows InsightBriefV2 directly in the main window stack."""
from __future__ import annotations

import html
import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
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
from windows_client.gui.result_renderer import (
    PREVIEW_STYLESHEET,
    _markdown_filename,
    _mode_pill_html,
    _preview_html,
    _product_view_payload,
    _product_view_html,
    entry_to_markdown,
)

MODE_LABELS = {
    "argument": "深度分析",
    "guide": "实用提炼",
    "review": "推荐导览",
}

DOMAIN_LABELS = {
    "macro_business": "宏观商业",
    "politics_public_issue": "公共议题",
    "game_guide": "游戏攻略",
    "personal_narrative": "个人叙事",
    "generic": "通用",
    "market-intel": "宏观商业",
    "briefing": "简报",
}


class _ClickableImageLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class InlineResultView(QWidget):
    _NARROW_LAYOUT_BREAKPOINT = 1100
    """Full-window widget that renders an InsightBriefV2 as the main content."""

    reanalyze_requested = Signal(str)  # emits source_url
    reinterpret_requested = Signal()
    save_to_library_requested = Signal()
    open_library_requested = Signal()
    open_library_entry_requested = Signal(str)

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry: ResultWorkspaceEntry | None = None
        self._current_card_path: Path | None = None
        self._update_banner_generation = 0
        self._library_banner_entry_id: str | None = None
        self._library_banner_timer = QTimer(self)
        self._library_banner_timer.setSingleShot(True)
        self._library_banner_timer.timeout.connect(self._hide_library_banner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top action bar
        self._top_bar_widget = QWidget()
        self._top_bar_widget.setObjectName("ResultGlobalBar")
        top_bar = QHBoxLayout(self._top_bar_widget)
        top_bar.setContentsMargins(0, 0, 0, 16)
        self._new_url_button = QPushButton("新的链接")
        self._new_url_button.setObjectName("GhostButton")
        self._reanalyze_btn = QPushButton("重新分析")
        self._reanalyze_btn.setObjectName("GhostButton")
        self._reanalyze_btn.clicked.connect(self._on_reanalyze)
        self._reanalyze_btn.setEnabled(False)
        self._reinterpret_btn = QPushButton("切换解读方式")
        self._reinterpret_btn.setObjectName("GhostButton")
        self._reinterpret_btn.clicked.connect(self.reinterpret_requested.emit)
        self._reinterpret_btn.setEnabled(False)
        self._save_to_library_btn = QPushButton("保存进知识库")
        self._save_to_library_btn.setObjectName("PrimaryButton")
        self._save_to_library_btn.clicked.connect(self.save_to_library_requested.emit)
        self._save_to_library_btn.hide()
        self._save_to_library_btn.setEnabled(False)
        self._open_library_btn = QPushButton("知识库")
        self._open_library_btn.setObjectName("GhostButton")
        self._open_library_btn.clicked.connect(self.open_library_requested.emit)
        self._open_library_btn.hide()
        self._history_btn = QPushButton("历史记录")
        self._history_btn.setObjectName("GhostButton")
        top_bar.addWidget(self._new_url_button, 0, Qt.AlignLeft)
        top_bar.addWidget(self._history_btn, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        root.addWidget(self._top_bar_widget)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 16, 0)
        self._content_layout.setSpacing(20)

        self._content_shell = QWidget()
        self._content_shell_layout = QGridLayout(self._content_shell)
        self._content_shell_layout.setContentsMargins(0, 0, 0, 0)
        self._content_shell_layout.setHorizontalSpacing(24)
        self._content_shell_layout.setVerticalSpacing(0)
        self._content_shell_layout.setColumnStretch(0, 4)
        self._content_shell_layout.setColumnStretch(1, 1)

        self._reading_stream_frame = QFrame()
        self._reading_stream_frame.setObjectName("ReadingStream")
        self._reading_stream_layout = QVBoxLayout(self._reading_stream_frame)
        self._reading_stream_layout.setContentsMargins(0, 0, 0, 0)
        self._reading_stream_layout.setSpacing(18)

        self._reading_stream_shell = QWidget()
        self._reading_stream_shell.setObjectName("ReadingStreamShell")
        self._reading_stream_shell_layout = QVBoxLayout(self._reading_stream_shell)
        self._reading_stream_shell_layout.setContentsMargins(0, 0, 0, 0)
        self._reading_stream_shell_layout.setSpacing(0)
        self._reading_stream_shell_layout.addWidget(self._reading_stream_frame)

        self._context_rail_frame = QFrame()
        self._context_rail_frame.setObjectName("ContextRail")
        self._context_rail_layout = QVBoxLayout(self._context_rail_frame)
        self._context_rail_layout.setContentsMargins(0, 0, 0, 0)
        self._context_rail_layout.setSpacing(16)

        self._context_rail_shell = QFrame()
        self._context_rail_shell.setObjectName("ContextRailShell")
        self._context_rail_shell_layout = QVBoxLayout(self._context_rail_shell)
        self._context_rail_shell_layout.setContentsMargins(0, 0, 0, 0)
        self._context_rail_shell_layout.setSpacing(0)
        self._context_rail_shell_layout.addWidget(self._context_rail_frame)

        self._context_title = QLabel("Library Context")
        self._context_title.setObjectName("SectionLabel")
        self._context_summary = QLabel("围绕当前解读的轻量上下文、导出动作和版本入口。")
        self._context_summary.setObjectName("SecondaryText")
        self._context_summary.setWordWrap(True)

        self._update_banner_frame = QFrame()
        self._update_banner_frame.setObjectName("CoverageBanner")
        update_banner_layout = QHBoxLayout(self._update_banner_frame)
        update_banner_layout.setContentsMargins(18, 12, 18, 12)
        self._update_banner_label = QLabel("")
        self._update_banner_label.setObjectName("BodyText")
        self._update_banner_label.setWordWrap(True)
        update_banner_layout.addWidget(self._update_banner_label)
        self._update_banner_frame.hide()

        self._library_banner_frame = QFrame()
        self._library_banner_frame.setObjectName("CoverageBanner")
        library_banner_layout = QHBoxLayout(self._library_banner_frame)
        library_banner_layout.setContentsMargins(18, 12, 18, 12)
        self._library_banner_label = QLabel("")
        self._library_banner_label.setObjectName("BodyText")
        self._library_banner_label.setWordWrap(True)
        library_banner_layout.addWidget(self._library_banner_label, 1)
        self._open_library_entry_btn = QPushButton("打开条目")
        self._open_library_entry_btn.setObjectName("GhostButton")
        self._open_library_entry_btn.clicked.connect(self._open_library_entry_from_banner)
        self._open_library_entry_btn.hide()
        self._open_library_banner_btn = QPushButton("查看知识库")
        self._open_library_banner_btn.setObjectName("GhostButton")
        self._open_library_banner_btn.clicked.connect(self.open_library_requested.emit)
        self._open_library_banner_btn.hide()
        library_banner_layout.addWidget(self._open_library_entry_btn, 0, Qt.AlignRight)
        library_banner_layout.addWidget(self._open_library_banner_btn, 0, Qt.AlignRight)
        self._library_banner_frame.hide()

        # Hero block
        self._hero_shell = QFrame()
        self._hero_shell.setObjectName("ImmersiveHero")
        hero_shell_layout = QVBoxLayout(self._hero_shell)
        hero_shell_layout.setContentsMargins(0, 0, 0, 0)
        hero_shell_layout.setSpacing(0)

        self._hero_topbar = QWidget()
        self._hero_topbar.setObjectName("HeroTopBar")
        hero_topbar_layout = QHBoxLayout(self._hero_topbar)
        hero_topbar_layout.setContentsMargins(24, 18, 24, 0)
        hero_topbar_layout.setSpacing(12)

        self._hero_action_strip = QWidget()
        self._hero_action_strip.setObjectName("HeroActionStrip")
        hero_action_layout = QHBoxLayout(self._hero_action_strip)
        hero_action_layout.setContentsMargins(0, 0, 0, 0)
        hero_action_layout.setSpacing(10)
        hero_action_layout.addWidget(self._reanalyze_btn)
        hero_action_layout.addWidget(self._reinterpret_btn)
        hero_action_layout.addWidget(self._save_to_library_btn)
        hero_action_layout.addWidget(self._open_library_btn)
        hero_action_layout.addStretch(1)
        hero_topbar_layout.addStretch(1)
        hero_topbar_layout.addWidget(self._hero_action_strip, 1)

        self._hero_frame = QFrame()
        self._hero_frame.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(self._hero_frame)
        hero_layout.setContentsMargins(24, 18, 24, 22)
        hero_layout.setSpacing(8)
        self._hero_title = QLabel("")
        self._hero_title.setObjectName("ResultTitle")
        self._hero_title.setWordWrap(True)
        self._hero_take = QLabel("")
        self._hero_take.setObjectName("HeroTake")
        self._hero_take.setWordWrap(True)
        self._hero_meta_row = QWidget()
        self._hero_meta_row.setObjectName("HeroMetaRow")
        hero_meta_layout = QVBoxLayout(self._hero_meta_row)
        hero_meta_layout.setContentsMargins(0, 0, 0, 0)
        hero_meta_layout.setSpacing(6)
        self._hero_byline = QLabel("")
        self._hero_byline.setObjectName("SecondaryText")
        self._hero_byline.setWordWrap(True)
        # Clickable source URL
        self._hero_source = QLabel("")
        self._hero_source.setObjectName("SecondaryText")
        self._hero_source.setOpenExternalLinks(True)
        self._hero_source.setTextFormat(Qt.RichText)
        self._hero_source.hide()
        hero_meta_layout.addWidget(self._hero_byline)
        hero_meta_layout.addWidget(self._hero_source)
        # Content-kind and author-stance tag chips (horizontal row)
        self._hero_tags_row = QWidget()
        tags_row_layout = QHBoxLayout(self._hero_tags_row)
        tags_row_layout.setContentsMargins(0, 0, 0, 0)
        tags_row_layout.setSpacing(6)
        self._mode_chip = QLabel("")
        self._mode_chip.setObjectName("TagChip")
        self._content_kind_chip = QLabel("")
        self._content_kind_chip.setObjectName("TagChip")
        self._author_stance_chip = QLabel("")
        self._author_stance_chip.setObjectName("TagChipMuted")
        self._domain_chip = QLabel("")
        self._domain_chip.setObjectName("TagChipMuted")
        tags_row_layout.addWidget(self._mode_chip)
        tags_row_layout.addWidget(self._content_kind_chip)
        tags_row_layout.addWidget(self._domain_chip)
        tags_row_layout.addWidget(self._author_stance_chip)
        tags_row_layout.addStretch(1)
        self._hero_tags_row.hide()
        hero_layout.addWidget(self._hero_title)
        hero_layout.addWidget(self._hero_take)
        hero_layout.addWidget(self._hero_meta_row)
        hero_layout.addWidget(self._hero_tags_row)
        hero_shell_layout.addWidget(self._hero_topbar)
        hero_shell_layout.addWidget(self._hero_frame)

        # Quick takeaways block (作者观点)
        self._takeaways_frame = QFrame()
        self._takeaways_frame.setObjectName("StreamSection")
        takeaways_layout = QVBoxLayout(self._takeaways_frame)
        takeaways_layout.setContentsMargins(24, 20, 24, 20)
        takeaways_layout.setSpacing(8)
        takeaways_heading = QLabel("作者观点")
        takeaways_heading.setObjectName("SectionLabel")
        takeaways_layout.addWidget(takeaways_heading)
        self._takeaways_list_layout = QVBoxLayout()
        self._takeaways_list_layout.setSpacing(12)
        takeaways_layout.addLayout(self._takeaways_list_layout)

        # Verification section (fact-check results — hidden by default)
        self._verification_frame = QFrame()
        self._verification_frame.setObjectName("PreviewCard")
        verification_layout = QVBoxLayout(self._verification_frame)
        verification_layout.setContentsMargins(24, 20, 24, 20)
        verification_layout.setSpacing(10)
        verification_heading = QLabel("事实核验")
        verification_heading.setObjectName("SectionLabel")
        verification_layout.addWidget(verification_heading)
        self._verification_list_layout = QVBoxLayout()
        self._verification_list_layout.setSpacing(8)
        verification_layout.addLayout(self._verification_list_layout)
        self._verification_frame.hide()

        # Bottom Line card (synthesis_conclusion — hidden by default)
        self._bottom_line_frame = QFrame()
        self._bottom_line_frame.setObjectName("BottomLineCard")
        bottom_line_layout = QVBoxLayout(self._bottom_line_frame)
        bottom_line_layout.setContentsMargins(24, 20, 24, 20)
        bottom_line_layout.setSpacing(8)
        bottom_line_heading = QLabel("核心结论")
        bottom_line_heading.setObjectName("SectionLabel")
        bottom_line_layout.addWidget(bottom_line_heading)
        self._bottom_line_label = QLabel("")
        self._bottom_line_label.setObjectName("BodyText")
        self._bottom_line_label.setWordWrap(True)
        bottom_line_layout.addWidget(self._bottom_line_label)
        self._bottom_line_frame.hide()

        # Insight card (generated image — hidden until card exists)
        self._card_frame = QFrame()
        self._card_frame.setObjectName("ImageSummaryCard")
        _cfl = QVBoxLayout(self._card_frame)
        _cfl.setContentsMargins(0, 4, 0, 4)
        _cfl.setSpacing(8)
        self._image_summary_heading = QLabel("视觉总结")
        self._image_summary_heading.setObjectName("SectionLabel")
        _save_row = QHBoxLayout()
        self._card_save_btn = QPushButton("保存图片")
        self._card_save_btn.setObjectName("GhostButton")
        self._card_save_btn.clicked.connect(self._save_insight_card)
        _save_row.addWidget(self._image_summary_heading)
        _save_row.addStretch(1)
        _save_row.addWidget(self._card_save_btn)
        self._card_image_label = _ClickableImageLabel()
        self._card_image_label.setAlignment(Qt.AlignLeft)
        self._card_image_label.clicked.connect(lambda: self._open_card_fullscreen())
        _cfl.addLayout(_save_row)
        _cfl.addWidget(self._card_image_label)
        self._card_frame.hide()

        # Divergent thinking block (延伸思考 — analysis items: implication / alternative)
        self._divergent_frame = QFrame()
        self._divergent_frame.setObjectName("PreviewCard")
        divergent_layout = QVBoxLayout(self._divergent_frame)
        divergent_layout.setContentsMargins(24, 20, 24, 20)
        divergent_layout.setSpacing(8)
        divergent_heading = QLabel("延伸思考")
        divergent_heading.setObjectName("SectionLabelBlue")
        divergent_layout.addWidget(divergent_heading)
        self._divergent_list_layout = QVBoxLayout()
        self._divergent_list_layout.setSpacing(6)
        divergent_layout.addLayout(self._divergent_list_layout)
        self._divergent_frame.hide()

        self._coverage_banner, self._coverage_label = self._make_warning_banner()
        self._image_truncation_banner, self._image_truncation_label = self._make_warning_banner()

        # Viewpoints / evidence browser
        self._long_reading_heading = QLabel("深度解读")
        self._long_reading_heading.setObjectName("SectionLabel")
        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDocumentMargin(0)
        self._browser.document().setDefaultStyleSheet(PREVIEW_STYLESHEET)
        self._browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._browser.setMinimumHeight(300)

        # Gaps block (open questions + next steps)
        self._gaps_frame = QFrame()
        self._gaps_frame.setObjectName("StreamSection")
        gaps_layout = QVBoxLayout(self._gaps_frame)
        gaps_layout.setContentsMargins(24, 20, 24, 20)
        gaps_layout.setSpacing(8)
        gaps_heading = QLabel("问题与下一步")
        gaps_heading.setObjectName("SectionLabelBlue")
        gaps_layout.addWidget(gaps_heading)
        self._gaps_list_layout = QVBoxLayout()
        self._gaps_list_layout.setSpacing(6)
        gaps_layout.addLayout(self._gaps_list_layout)
        self._gaps_frame.hide()

        # Visual Evidence block (video content only, hidden by default)
        self._visual_frame = QFrame()
        self._visual_frame.setObjectName("PreviewCard")
        visual_layout = QVBoxLayout(self._visual_frame)
        visual_layout.setContentsMargins(24, 20, 24, 20)
        visual_layout.setSpacing(8)
        visual_heading = QLabel("视觉证据")
        visual_heading.setObjectName("SectionLabel")
        visual_layout.addWidget(visual_heading)
        self._visual_list_layout = QVBoxLayout()
        self._visual_list_layout.setSpacing(6)
        visual_layout.addLayout(self._visual_list_layout)
        self._visual_frame.hide()

        # Action row (bottom)
        action_frame = QWidget()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        self._open_folder_btn = QPushButton("打开目录")
        self._open_folder_btn.setObjectName("GhostButton")
        self._open_folder_btn.clicked.connect(self._open_folder)
        self._export_json_btn = QPushButton("导出 JSON")
        self._export_json_btn.setObjectName("GhostButton")
        self._export_json_btn.clicked.connect(self._open_analysis)
        self._copy_btn = QPushButton("复制")
        self._copy_btn.setObjectName("GhostButton")
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        self._save_btn = QPushButton("保存 Markdown")
        self._save_btn.setObjectName("GhostButton")
        self._save_btn.clicked.connect(self._save_as_markdown)
        action_layout.addWidget(self._open_folder_btn)
        action_layout.addWidget(self._export_json_btn)
        action_layout.addWidget(self._copy_btn)
        action_layout.addWidget(self._save_btn)
        action_layout.addStretch(1)

        self._content_layout.addWidget(self._update_banner_frame)
        self._content_layout.addWidget(self._library_banner_frame)
        self._content_layout.addWidget(self._content_shell)
        self._content_shell_layout.addWidget(self._reading_stream_shell, 0, 0)
        self._content_shell_layout.addWidget(self._context_rail_shell, 0, 1)
        self._apply_layout_mode(self.width())
        self._reading_stream_layout.addWidget(self._hero_shell)
        self._reading_stream_layout.addWidget(self._card_frame)
        self._reading_stream_layout.addWidget(self._takeaways_frame)
        self._reading_stream_layout.addWidget(self._verification_frame)
        self._reading_stream_layout.addWidget(self._bottom_line_frame)
        self._reading_stream_layout.addWidget(self._divergent_frame)
        self._reading_stream_layout.addWidget(self._gaps_frame)
        self._reading_stream_layout.addWidget(self._coverage_banner)
        self._reading_stream_layout.addWidget(self._image_truncation_banner)
        self._reading_stream_layout.addWidget(self._long_reading_heading)
        self._reading_stream_layout.addWidget(self._browser, 1)
        self._reading_stream_layout.addStretch(1)

        self._context_rail_layout.addWidget(self._context_title)
        self._context_rail_layout.addWidget(self._context_summary)
        self._context_rail_layout.addWidget(self._visual_frame)
        self._context_rail_layout.addWidget(action_frame)
        self._context_rail_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    @property
    def new_url_button(self) -> QPushButton:
        return self._new_url_button

    @property
    def history_button(self) -> QPushButton:
        return self._history_btn

    @property
    def save_to_library_button(self) -> QPushButton:
        return self._save_to_library_btn

    @property
    def open_library_button(self) -> QPushButton:
        return self._open_library_btn

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_layout_mode(event.size().width())

    def _set_layout_state(self, *, narrow: bool) -> None:
        self._reading_stream_layout.setSpacing(16 if narrow else 18)
        widgets = (
            self,
            self._hero_shell,
            self._hero_frame,
            self._hero_topbar,
            self._hero_action_strip,
            self._card_frame,
            self._reading_stream_frame,
        )
        for widget in widgets:
            widget.setProperty("isNarrowLayout", narrow)
            widget.update()

    def _apply_layout_mode(self, available_width: int) -> None:
        narrow = available_width <= self._NARROW_LAYOUT_BREAKPOINT
        self._set_layout_state(narrow=narrow)
        if narrow:
            self._content_shell_layout.setHorizontalSpacing(0)
            self._content_shell_layout.setColumnStretch(0, 1)
            self._content_shell_layout.setColumnStretch(1, 0)
            self._content_shell_layout.addWidget(self._reading_stream_shell, 0, 0)
            self._content_shell_layout.addWidget(self._context_rail_shell, 1, 0)
            return
        self._content_shell_layout.setHorizontalSpacing(24)
        self._content_shell_layout.setColumnStretch(0, 4)
        self._content_shell_layout.setColumnStretch(1, 1)
        self._content_shell_layout.addWidget(self._reading_stream_shell, 0, 0)
        self._content_shell_layout.addWidget(self._context_rail_shell, 0, 1)

    def _set_insight_card_state(self, has_card: bool) -> None:
        widgets = (self, self._card_frame, self._reading_stream_frame)
        for widget in widgets:
            widget.setProperty("hasInsightCard", has_card)
            widget.update()

    def _load_insight_card(self, card_path: object) -> None:
        self._current_card_path = None
        self._card_image_label.clear()
        if card_path is None:
            self._card_frame.hide()
            self._set_insight_card_state(False)
            return
        pixmap = QPixmap(str(card_path))
        if pixmap.isNull():
            self._card_frame.hide()
            self._set_insight_card_state(False)
            return
        max_width = 820 if not self.property("isNarrowLayout") else 760
        if pixmap.width() > max_width:
            pixmap = pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
        self._card_image_label.setPixmap(pixmap)
        self._current_card_path = Path(card_path)
        self._card_frame.show()
        self._set_insight_card_state(True)

    def load_entry(
        self,
        entry: ResultWorkspaceEntry,
        *,
        brief: InsightBriefV2 | None,
        resolved_mode: str | None = None,
    ) -> None:
        """Populate the view from a ResultWorkspaceEntry with an optional InsightBriefV2."""
        self._entry = entry
        self._hide_update_banner()
        self._hide_library_banner()
        mode_label = MODE_LABELS.get((resolved_mode or "").strip().lower(), "")
        domain_label = self._resolved_domain_label(entry)
        warnings_brief = brief
        product_view = _product_view_payload(entry)
        product_hero = product_view.get("hero") if isinstance(product_view, dict) else None
        if not isinstance(product_hero, dict):
            product_hero = None
        if product_view is not None:
            brief = None

        # Hero fields common to both paths
        source = entry.source_url or entry.canonical_url
        if source and not self._is_local_source(source):
            display = source if len(source) <= 72 else source[:69] + "…"
            self._hero_source.setText(f"<a href='{html.escape(source)}'>{html.escape(display)}</a>")
            self._hero_source.show()
        else:
            self._hero_source.hide()
        self._reanalyze_btn.setEnabled(bool(source))
        self._reinterpret_btn.setEnabled(entry.state == "processed")
        self._save_to_library_btn.setVisible(True)
        self._save_to_library_btn.setEnabled(entry.state == "processed")
        self._open_library_btn.setVisible(True)

        if brief is not None:
            # Full view
            resolved_title = str(brief.hero.title or "").strip() or entry.title or self._local_title_fallback(entry)
            self._hero_title.setText(resolved_title)
            hero_take = str(brief.hero.one_sentence_take or "").strip()
            self._hero_take.setText(hero_take)
            self._hero_take.setVisible(bool(hero_take and not self._looks_like_duplicate(hero_take, brief.hero.title)))
            byline_parts = self._byline_parts(entry)
            self._hero_byline.setText("  ·  ".join(byline_parts) if byline_parts else "")
            self._hero_byline.setVisible(bool(byline_parts))

            # Content-kind / author-stance chips
            kind = str(getattr(brief.hero, "content_kind", None) or "").strip()
            stance = str(getattr(brief.hero, "author_stance", None) or "").strip()
            self._mode_chip.setText(mode_label)
            self._mode_chip.setVisible(bool(mode_label))
            self._content_kind_chip.setText(kind)
            self._content_kind_chip.setVisible(bool(kind))
            self._domain_chip.setText(domain_label)
            self._domain_chip.setVisible(bool(domain_label))
            self._author_stance_chip.setText(stance)
            self._author_stance_chip.setVisible(bool(stance))
            self._hero_tags_row.setVisible(bool(mode_label or kind or domain_label or stance))

            key_point_viewpoints = [v for v in brief.viewpoints if v.kind == "key_point"]
            self._clear_layout(self._takeaways_list_layout)
            for index, vp in enumerate(key_point_viewpoints, start=1):
                if (resolved_mode or "").strip().lower() == "guide":
                    self._takeaways_list_layout.addWidget(
                        self._make_guide_step_item(index, vp.statement, vp.why_it_matters)
                    )
                else:
                    self._takeaways_list_layout.addWidget(
                        self._make_key_point_item(index, vp.statement, vp.why_it_matters)
                    )
            self._takeaways_frame.setVisible(bool(key_point_viewpoints))

            # Verification items
            verifications = [v for v in brief.viewpoints if v.kind == "verification"]
            self._clear_layout(self._verification_list_layout)
            for item in verifications:
                self._verification_list_layout.addWidget(
                    self._make_verification_card(item.statement, item.support_level, item.why_it_matters)
                )
            self._verification_frame.setVisible(bool(verifications))

            # Bottom Line card
            conclusion = getattr(brief, "synthesis_conclusion", None)
            if conclusion:
                self._bottom_line_label.setText(conclusion)
                self._bottom_line_frame.show()
            else:
                self._bottom_line_frame.hide()

            # Coverage banner
            coverage = brief.coverage
            if coverage is not None and coverage.input_truncated:
                pct = int(coverage.coverage_ratio * 100)
                self._coverage_label.setText(
                    f"\u26a0 覆盖范围提示：当前只分析了 {pct}% 的原始分段 "
                    f"({coverage.used_segments}/{coverage.total_segments})。"
                    "结论可能并不完整。"
                )
                self._coverage_banner.show()
            else:
                self._coverage_banner.hide()

            # Image input truncation banner
            llm_image = entry.details.get("llm_image_input", {})
            if llm_image.get("image_input_truncated"):
                count = llm_image.get("image_input_count", "?")
                self._image_truncation_label.setText(
                    f"\u26a0 图片输入达到上限：本次共向模型发送了 {count} 张图片。"
                    "视觉分析可能并不完整。"
                )
                self._image_truncation_banner.show()
            else:
                self._image_truncation_banner.hide()

            # Divergent thinking: analysis_items (implication / alternative)
            analysis_viewpoints = [v for v in brief.viewpoints if v.kind == "analysis"]
            self._clear_layout(self._divergent_list_layout)
            for vp in analysis_viewpoints:
                lbl = QLabel(f"→ {vp.statement}")
                lbl.setObjectName("BodyText")
                lbl.setWordWrap(True)
                self._divergent_list_layout.addWidget(lbl)
            self._divergent_frame.setVisible(bool(analysis_viewpoints))

            # Gaps
            gaps = list(getattr(brief, "gaps", None) or [])
            self._clear_layout(self._gaps_list_layout)
            for text in gaps:
                lbl = QLabel(f"· {text}")
                lbl.setObjectName("BodyText")
                lbl.setWordWrap(True)
                self._gaps_list_layout.addWidget(lbl)
            self._gaps_frame.setVisible(bool(gaps))
        else:
            # Degraded view — no structured brief
            hero_title = str(product_hero.get("title") or "").strip() if product_hero else ""
            hero_take = (
                str(product_hero.get("dek") or product_hero.get("bottom_line") or "").strip()
                if product_hero
                else ""
            )
            self._hero_title.setText(hero_title or entry.title or self._local_title_fallback(entry))
            resolved_take = hero_take or getattr(entry, "summary", "") or ""
            self._hero_take.setText(resolved_take)
            self._hero_take.setVisible(bool(resolved_take and not self._looks_like_duplicate(resolved_take, self._hero_title.text())))
            byline_parts = self._byline_parts(entry)
            self._hero_byline.setText("  ·  ".join(byline_parts) if byline_parts else "")
            self._hero_byline.setVisible(bool(byline_parts))
            self._mode_chip.setText(mode_label)
            self._mode_chip.setVisible(bool(mode_label))
            self._content_kind_chip.setText(domain_label)
            self._content_kind_chip.setVisible(bool(domain_label))
            self._domain_chip.clear()
            self._domain_chip.hide()
            self._author_stance_chip.setVisible(False)
            self._hero_tags_row.setVisible(bool(mode_label or domain_label))
            self._takeaways_frame.hide()
            self._verification_frame.hide()
            self._bottom_line_frame.hide()
            self._divergent_frame.hide()
            self._gaps_frame.hide()

        coverage = getattr(warnings_brief, "coverage", None)
        if coverage is not None and coverage.input_truncated:
            pct = int(coverage.coverage_ratio * 100)
            self._coverage_label.setText(
                f"\u26a0 覆盖范围提示：当前只分析了 {pct}% 的原始分段 "
                f"({coverage.used_segments}/{coverage.total_segments})。"
                "结论可能并不完整。"
            )
            self._coverage_banner.show()
        else:
            self._coverage_banner.hide()

        llm_image = entry.details.get("llm_image_input", {})
        if llm_image.get("image_input_truncated"):
            count = llm_image.get("image_input_count", "?")
            self._image_truncation_label.setText(
                f"\u26a0 图片输入达到上限：本次共向模型发送了 {count} 张图片。"
                "视觉分析可能并不完整。"
            )
            self._image_truncation_banner.show()
        else:
            self._image_truncation_banner.hide()

        # Visual Evidence (video content — always populated from entry, not brief)
        visual_findings = [f for f in entry.details.get("visual_findings") or [] if isinstance(f, dict)]
        self._clear_layout(self._visual_list_layout)
        rendered_visual_findings = 0
        for finding in visual_findings:
            description = str(finding.get("description") or "").strip()
            if not description:
                continue
            ts_ms = finding.get("frame_timestamp_ms")
            if ts_ms is not None:
                try:
                    m, s = divmod(int(ts_ms) // 1000, 60)
                    prefix = f"[{m}:{s:02d}] "
                except (TypeError, ValueError):
                    prefix = ""
            else:
                prefix = ""
            lbl = QLabel(f"{prefix}{description}")
            lbl.setObjectName("BodyText")
            lbl.setWordWrap(True)
            self._visual_list_layout.addWidget(lbl)
            rendered_visual_findings += 1
        self._visual_frame.setVisible(rendered_visual_findings > 0)

        # Insight card image (shown when PNG exists)
        self._load_insight_card(entry.details.get("insight_card_path"))

        if product_view is not None:
            sections: list[str] = []
            mode_pill = _mode_pill_html(entry, resolved_mode)
            if mode_pill:
                sections.append(mode_pill)
            sections.append(_product_view_html(product_view))
            self._browser.setHtml(f"<div class='preview-reading structured-result'>{''.join(sections)}</div>")
            self._browser.show()
            self._long_reading_heading.show()
        elif brief is None:
            self._browser.setHtml(_preview_html(entry, resolved_mode=resolved_mode))
            self._browser.show()
            self._long_reading_heading.show()
        else:
            self._browser.setHtml("")
            self._browser.hide()
            self._long_reading_heading.hide()

        # Action buttons
        self._open_folder_btn.setEnabled(entry.job_dir is not None)
        self._export_json_btn.setEnabled(entry.analysis_json_path is not None)
        self._copy_btn.setEnabled(True)
        self._save_btn.setEnabled(True)

    def load_brief(self, brief: InsightBriefV2, entry: ResultWorkspaceEntry) -> None:
        """Compatibility shim — delegates to load_entry."""
        self.load_entry(entry, brief=brief)

    @staticmethod
    def _make_warning_banner() -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("EditorialWarning")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 12, 18, 12)
        label = QLabel("")
        label.setWordWrap(True)
        label.setObjectName("BodyText")
        layout.addWidget(label)
        frame.hide()
        return frame, label

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _looks_like_duplicate(candidate: str, title: str) -> bool:
        normalized_candidate = " ".join(candidate.split())
        normalized_title = " ".join(title.split())
        return bool(normalized_candidate and normalized_title and normalized_candidate == normalized_title)

    @staticmethod
    def _resolved_domain_label(entry: ResultWorkspaceEntry) -> str:
        normalized = entry.details.get("normalized") if isinstance(entry.details, dict) else None
        if not isinstance(normalized, dict):
            return ""
        metadata = normalized.get("metadata")
        if not isinstance(metadata, dict):
            return ""
        llm_processing = metadata.get("llm_processing")
        if not isinstance(llm_processing, dict):
            return ""
        value = str(
            llm_processing.get("resolved_domain_template")
            or llm_processing.get("domain_template")
            or ""
        ).strip()
        return DOMAIN_LABELS.get(value, value.replace("_", " ").strip())

    @staticmethod
    def _is_local_source(source: str | None) -> bool:
        value = str(source or "").strip().lower()
        return value.startswith("file://") or value.startswith("local://")

    @staticmethod
    def _local_title_fallback(entry: ResultWorkspaceEntry) -> str:
        if str(getattr(entry, "platform", "") or "").strip().lower() == "local":
            source = str(getattr(entry, "source_url", "") or "").strip()
            if source.startswith("file://"):
                return Path(source.replace("file:///", "", 1)).name or "未命名文档"
            return "未命名文档"
        return "解读已完成"

    @staticmethod
    def _byline_parts(entry: ResultWorkspaceEntry) -> list[str]:
        platform = str(getattr(entry, "platform", "") or "").strip()
        source = str(getattr(entry, "source_url", "") or getattr(entry, "canonical_url", "") or "").strip()
        if platform.lower() == "local":
            label = "本地文件"
            if source.startswith("file://"):
                label = Path(source.replace("file:///", "", 1)).name or label
            parts = [v for v in (getattr(entry, "author", ""), getattr(entry, "published_at", ""), label) if v]
            return [str(v) for v in parts]
        parts = [v for v in (getattr(entry, "author", ""), getattr(entry, "published_at", ""), platform) if v]
        return [str(v) for v in parts]

    def show_update_banner(self, message: str) -> None:
        text = message.strip()
        self._update_banner_generation += 1
        if not text:
            self._hide_update_banner()
            return
        self._update_banner_label.setText(text)
        self._update_banner_frame.show()
        generation = self._update_banner_generation
        QTimer.singleShot(5000, lambda: self._hide_update_banner(generation))

    def show_library_banner(self, message: str, *, entry_id: str | None = None) -> None:
        text = message.strip()
        self._library_banner_timer.stop()
        if not text:
            self._hide_library_banner()
            return
        self._library_banner_entry_id = entry_id
        self._library_banner_label.setText(text)
        self._open_library_entry_btn.setVisible(bool(entry_id))
        self._open_library_banner_btn.show()
        self._library_banner_frame.show()
        self._library_banner_timer.start(5000)

    def _hide_update_banner(self, generation: int | None = None) -> None:
        if generation is not None and generation != self._update_banner_generation:
            return
        self._update_banner_label.clear()
        self._update_banner_frame.hide()

    def _hide_library_banner(self) -> None:
        self._library_banner_timer.stop()
        self._library_banner_entry_id = None
        self._library_banner_label.clear()
        self._open_library_entry_btn.hide()
        self._open_library_banner_btn.hide()
        self._library_banner_frame.hide()

    def _open_library_entry_from_banner(self) -> None:
        if self._library_banner_entry_id:
            self.open_library_entry_requested.emit(self._library_banner_entry_id)
            return
        self.open_library_requested.emit()

    def _copy_to_clipboard(self) -> None:
        if self._entry is None:
            return
        QApplication.clipboard().setText(entry_to_markdown(self._entry))
        self._copy_btn.setEnabled(False)
        self._copy_btn.setText("已复制")
        QTimer.singleShot(1500, self._restore_copy_button)

    def _restore_copy_button(self) -> None:
        self._copy_btn.setEnabled(True)
        self._copy_btn.setText("复制")

    def _save_as_markdown(self) -> None:
        if self._entry is None:
            return
        default_name = _markdown_filename(self._entry)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存为 Markdown",
            default_name,
            "Markdown 文件 (*.md);;所有文件 (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(entry_to_markdown(self._entry), encoding="utf-8")
        except OSError:
            self._save_btn.setEnabled(True)
            self._save_btn.setText("保存失败")
            QTimer.singleShot(2500, self._restore_save_button)
            return
        saved_name = Path(path).name
        self._save_btn.setEnabled(False)
        self._save_btn.setText(f"已保存：{saved_name}")
        QTimer.singleShot(2500, self._restore_save_button)

    def _restore_save_button(self) -> None:
        self._save_btn.setEnabled(True)
        self._save_btn.setText("保存 Markdown")

    def _on_reanalyze(self) -> None:
        if self._entry is None:
            return
        url = self._entry.source_url or self._entry.canonical_url
        if url:
            self.reanalyze_requested.emit(url)

    @staticmethod
    def _make_key_point_item(index: int, statement: str, details: str | None) -> QWidget:
        item = QWidget()
        item.setObjectName("EditorialKeyPoint")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_lbl = QLabel(f"{index:02d} · {statement}")
        title_lbl.setObjectName("TakeawayIndexed")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        if details:
            details_lbl = QLabel(details)
            details_lbl.setObjectName("SecondaryText")
            details_lbl.setWordWrap(True)
            details_lbl.setContentsMargins(24, 0, 0, 0)
            layout.addWidget(details_lbl)
        return item

    @staticmethod
    def _make_guide_step_item(index: int, statement: str, details: str | None) -> QWidget:
        item = QFrame()
        item.setObjectName("GuideStepItem")
        layout = QHBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        index_lbl = QLabel(f"步骤 {index}")
        index_lbl.setObjectName("GuideStepIndex")
        index_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(index_lbl, 0, Qt.AlignTop)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        title_lbl = QLabel(statement)
        title_lbl.setObjectName("GuideStepBody")
        title_lbl.setWordWrap(True)
        content_layout.addWidget(title_lbl)
        if details:
            details_lbl = QLabel(details)
            details_lbl.setObjectName("GuideStepDetail")
            details_lbl.setWordWrap(True)
            content_layout.addWidget(details_lbl)
        layout.addWidget(content, 1)
        return item

    @staticmethod
    def _make_verification_card(statement: str, support_level: str | None, rationale: str | None) -> QFrame:
        card = QFrame()
        card.setObjectName("VerificationCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        status_chip = QLabel(support_level or "unclear")
        status_key = (support_level or "unclear").lower()
        status_chip.setObjectName(f"VerifChip_{status_key}")
        claim_lbl = QLabel(statement)
        claim_lbl.setObjectName("BodyText")
        claim_lbl.setWordWrap(True)
        top_row.addWidget(status_chip, 0, Qt.AlignTop)
        top_row.addWidget(claim_lbl, 1)
        layout.addLayout(top_row)

        if rationale:
            rationale_lbl = QLabel(rationale)
            rationale_lbl.setObjectName("SecondaryText")
            rationale_lbl.setWordWrap(True)
            layout.addWidget(rationale_lbl)

        return card

    def _save_insight_card(self) -> None:
        if self._entry is None:
            return
        card_path = self._entry.details.get("insight_card_path")
        if not card_path:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "保存洞察卡片", "insight_card.png",
            "PNG 图片 (*.png);;所有文件 (*)",
        )
        if not dest:
            return
        try:
            shutil.copy2(str(card_path), dest)
        except OSError:
            self._card_save_btn.setEnabled(True)
            self._card_save_btn.setText("保存失败")
            QTimer.singleShot(2000, self._restore_card_save_btn)
            return
        self._card_save_btn.setEnabled(False)
        self._card_save_btn.setText("已保存")
        QTimer.singleShot(2000, self._restore_card_save_btn)

    def _restore_card_save_btn(self) -> None:
        self._card_save_btn.setEnabled(True)
        self._card_save_btn.setText("保存图片")

    def _open_card_fullscreen(self) -> None:
        if self._current_card_path is None:
            return
        pixmap = QPixmap(str(self._current_card_path))
        if pixmap.isNull():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("视觉总结")
        screen = self.screen()
        available_height = screen.availableGeometry().height() if screen is not None else 1080
        dialog.resize(900, min(1200, max(480, available_height - 80)))
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(pixmap)
        scroll.setWidget(label)
        layout.addWidget(scroll)
        dialog.exec()

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
