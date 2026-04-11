from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from windows_client.app.library_store import LibraryEntryView, LibraryInterpretation, LibraryStore
from windows_client.gui.result_renderer import PREVIEW_STYLESHEET, _product_view_html


def _detail_section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("DetailCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("SectionLabel")
    layout.addWidget(heading)
    return frame, layout


def _trash_reason_copy(reason: str | None) -> str:
    if not reason:
        return "未记录"
    return {
        "replaced_by_new_save": "被新的保存版本替换",
        "replaced_by_restore": "因恢复旧版本而归档",
    }.get(reason, reason)


class LibraryDialog(QDialog):
    restore_requested = Signal(str, str)
    open_analysis_requested = Signal(str)

    def __init__(self, *, parent: QWidget | None, shared_root: Path, selected_entry_id: str | None = None) -> None:
        super().__init__(parent)
        self.store = LibraryStore(shared_root=shared_root)
        self.entries: list[LibraryEntryView] = []
        self._selected_entry_id = selected_entry_id

        self.setWindowTitle("知识库")
        self.resize(1180, 760)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(304)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(10)

        header = QHBoxLayout()
        self._list_heading = QLabel("相关内容")
        self._list_heading.setObjectName("SectionLabel")
        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("GhostButton")
        refresh_button.clicked.connect(self.reload)
        header.addWidget(self._list_heading)
        header.addStretch(1)
        header.addWidget(refresh_button)

        filter_title = QLabel("浏览")
        filter_title.setObjectName("SectionLabel")
        self.all_entries_filter = QCheckBox("全部条目")
        self.all_entries_filter.setChecked(True)
        self.recent_entries_filter = QCheckBox("按最近保存排序")
        self.with_images_filter = QCheckBox("有图片摘要")
        self.with_trashed_filter = QCheckBox("有旧版本")
        for control in (
            self.all_entries_filter,
            self.recent_entries_filter,
            self.with_images_filter,
            self.with_trashed_filter,
        ):
            control.toggled.connect(self.reload)

        self.filter_summary = QLabel("")
        self.filter_summary.setObjectName("SecondaryText")
        self.filter_summary.setWordWrap(True)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ResultList")
        self.list_widget.currentRowChanged.connect(self._render_entry)

        sidebar_layout.addLayout(header)
        sidebar_layout.addWidget(filter_title)
        sidebar_layout.addWidget(self.all_entries_filter)
        sidebar_layout.addWidget(self.recent_entries_filter)
        sidebar_layout.addWidget(self.with_images_filter)
        sidebar_layout.addWidget(self.with_trashed_filter)
        sidebar_layout.addWidget(self.filter_summary)
        sidebar_layout.addWidget(self.list_widget, 1)

        detail_card = QFrame()
        detail_card.setObjectName("DetailCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(24, 24, 24, 24)
        detail_layout.setSpacing(12)

        self.empty_label = QLabel("知识库里还没有条目")
        self.empty_label.setObjectName("SecondaryText")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_widget = QWidget()
        self.detail_root_layout = QHBoxLayout(self.detail_widget)
        self.detail_root_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_root_layout.setSpacing(16)
        self.main_column_layout = QVBoxLayout()
        self.main_column_layout.setSpacing(16)
        self._context_shell = QFrame()
        self._context_shell.setObjectName("ContextRailShell")
        self.side_column_layout = QVBoxLayout(self._context_shell)
        self.side_column_layout.setContentsMargins(0, 0, 0, 0)
        self.side_column_layout.setSpacing(16)
        self.detail_root_layout.addLayout(self.main_column_layout, 3)
        self.detail_root_layout.addWidget(self._context_shell, 1)
        self.detail_scroll.setWidget(self.detail_widget)
        self._timeline_heading = QLabel("版本时间线")

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.setObjectName("GhostButton")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)

        detail_layout.addWidget(self.empty_label)
        detail_layout.addWidget(self.detail_scroll, 1)
        detail_layout.addLayout(close_row)

        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(detail_card, 1)

        self.reload()

    def reload(self) -> None:
        self.entries = self._filtered_entries(self.store.list_entries())
        self.list_widget.clear()
        self.filter_summary.setText(f"当前显示 {len(self.entries)} 个条目")
        for entry in self.entries:
            title = entry.source.title or entry.entry_id
            updated_at = entry.updated_at or entry.current_interpretation.saved_at or "未知时间"
            image_text = "有图片摘要" if entry.current_interpretation.image_summary_asset is not None else "无图片摘要"
            route_text = entry.current_interpretation.route_key or "未标注路线"
            platform_text = entry.source.platform or "未知来源"
            meta = " · ".join(
                (
                    platform_text,
                    route_text,
                    image_text,
                    f"更新于 {updated_at}",
                )
            )
            item = QListWidgetItem(f"{title}\n{meta}")
            self.list_widget.addItem(item)

        if self.entries:
            self.empty_label.hide()
            self.detail_scroll.show()
            selected_row = self._selected_row()
            self.list_widget.setCurrentRow(selected_row)
            return

        self._clear_detail()
        self.empty_label.show()
        self.detail_scroll.hide()

    def _selected_row(self) -> int:
        if self._selected_entry_id is None:
            return 0
        for index, entry in enumerate(self.entries):
            if entry.entry_id == self._selected_entry_id:
                return index
        return 0

    def _render_entry(self, row: int) -> None:
        self._clear_detail()
        if row < 0 or row >= len(self.entries):
            self.empty_label.show()
            self.detail_scroll.hide()
            return

        entry = self.entries[row]
        self._selected_entry_id = entry.entry_id
        self.empty_label.hide()
        self.detail_scroll.show()
        self.main_column_layout.addWidget(self._build_image_section(entry))
        self.main_column_layout.addWidget(self._build_source_section(entry))
        self.main_column_layout.addWidget(self._build_interpretation_section(entry))
        self.main_column_layout.addStretch(1)
        self.side_column_layout.addWidget(self._build_context_rail(entry))
        self.side_column_layout.addStretch(1)

    def _build_context_rail(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        frame.setObjectName("ContextRail")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        heading = QLabel("Library Context")
        heading.setObjectName("SectionLabel")
        summary = QLabel("围绕当前保存版本的路线、上下文与可恢复历史。")
        summary.setObjectName("SecondaryText")
        summary.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(summary)
        layout.addWidget(self._build_current_metadata_section(entry))
        layout.addWidget(self._build_trash_section(entry))
        layout.addWidget(self._build_context_section(entry))
        return frame

    def _build_image_section(self, entry: LibraryEntryView) -> QWidget:
        frame, layout = _detail_section("视觉总结")
        interpretation = entry.current_interpretation

        title = QLabel(interpretation.summary_headline or entry.source.title or "当前解读")
        title.setObjectName("ResultTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        route = QLabel(interpretation.route_key or "")
        route.setObjectName("SecondaryText")
        route.setWordWrap(True)
        route.setVisible(bool(route.text()))
        layout.addWidget(route)

        summary = QLabel(interpretation.summary_short_text or "")
        summary.setObjectName("BodyText")
        summary.setWordWrap(True)
        summary.setVisible(bool(summary.text()))
        layout.addWidget(summary)

        asset = interpretation.image_summary_asset
        if asset is not None and asset.path is not None:
            image_path = self.store.entries_root / entry.entry_id / asset.path
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                if pixmap.width() > 760:
                    pixmap = pixmap.scaledToWidth(760, Qt.SmoothTransformation)
                image = QLabel()
                image.setPixmap(pixmap)
                image.setAlignment(Qt.AlignLeft)
                layout.addWidget(image)
                return frame

        empty = QLabel("该条目已保存，但当前版本暂无视觉总结，可先查看来源信息与完整解读。")
        empty.setObjectName("BodyText")
        empty.setWordWrap(True)
        layout.addWidget(empty)
        return frame

    def _build_source_section(self, entry: LibraryEntryView) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SourceHeaderCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        source = entry.source
        interpretation = entry.current_interpretation

        heading = QLabel("来源信息")
        heading.setObjectName("SectionLabel")
        layout.addWidget(heading)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title = QLabel(source.title or "未命名来源")
        title.setObjectName("SourceHeaderTitle")
        title.setWordWrap(True)
        header_row.addWidget(title, 1)

        open_button = QPushButton("查看完整分析")
        open_button.setObjectName("OpenFullAnalysisButton")
        open_button.setProperty("buttonStyle", "ghost")
        open_button.clicked.connect(
            lambda _checked=False, job_id=interpretation.saved_from_job_id: self.open_analysis_requested.emit(job_id)
        )
        open_button.setVisible(bool(interpretation.saved_from_job_id))
        header_row.addStretch(1)
        header_row.addWidget(open_button)
        layout.addLayout(header_row)

        byline_bits = [bit for bit in (source.platform, source.author, source.published_at, source.captured_at) if bit]
        byline = QLabel("  ·  ".join(byline_bits))
        byline.setObjectName("SecondaryText")
        byline.setWordWrap(True)
        byline.setVisible(bool(byline.text()))
        layout.addWidget(byline)

        if source.canonical_url or source.source_url:
            url = source.canonical_url or source.source_url or ""
            url_label = QLabel(f"<a href='{html.escape(url)}'>{html.escape(url)}</a>")
            url_label.setObjectName("SecondaryText")
            url_label.setOpenExternalLinks(True)
            url_label.setTextFormat(Qt.RichText)
            url_label.setWordWrap(True)
            layout.addWidget(url_label)

        return frame

    def _build_interpretation_section(self, entry: LibraryEntryView) -> QWidget:
        frame, layout = _detail_section("当前解读")
        interpretation = entry.current_interpretation

        summary = QLabel(interpretation.summary_short_text or interpretation.summary_headline or "当前解读")
        summary.setObjectName("SecondaryText")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        browser = QTextBrowser()
        browser.setObjectName("LibraryInterpretationBrowser")
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(True)
        browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        browser.document().setDefaultStyleSheet(PREVIEW_STYLESHEET)
        browser.setMinimumHeight(460)
        browser.setHtml(self._interpretation_html(interpretation))
        layout.addWidget(browser)
        return frame

    def _build_current_metadata_section(self, entry: LibraryEntryView) -> QWidget:
        frame, layout = _detail_section("当前版本")
        interpretation = entry.current_interpretation
        metadata_lines = [
            f"路线：{interpretation.route_key}" if interpretation.route_key else "",
            f"保存来源任务：{interpretation.saved_from_job_id}" if interpretation.saved_from_job_id else "",
            f"保存时间：{interpretation.saved_at}" if interpretation.saved_at else "",
            f"视觉总结：{'有' if interpretation.image_summary_asset is not None else '无'}",
        ]
        for line in metadata_lines:
            if not line:
                continue
            label = QLabel(line)
            label.setObjectName("BodyText")
            label.setWordWrap(True)
            layout.addWidget(label)
        return frame

    def _build_trash_section(self, entry: LibraryEntryView) -> QWidget:
        frame, layout = _detail_section(self._timeline_heading.text())
        if not entry.trashed_interpretations:
            empty = QLabel("这个条目还没有可恢复的旧版本。")
            empty.setObjectName("SecondaryText")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            return frame

        for interpretation in entry.trashed_interpretations:
            layout.addWidget(self._build_trash_row(entry.entry_id, interpretation))
        return frame

    def _build_context_section(self, entry: LibraryEntryView) -> QWidget:
        frame, layout = _detail_section("Library Context")
        interpretation_count = 1 + len(entry.trashed_interpretations)
        snapshot = entry.source.job_snapshot
        snapshot_kinds = []
        if snapshot.normalized_markdown_path is not None:
            snapshot_kinds.append("Markdown")
        if snapshot.normalized_json_path is not None:
            snapshot_kinds.append("JSON")
        if snapshot.metadata_path is not None:
            snapshot_kinds.append("元数据")
        snapshot_copy = " / ".join(snapshot_kinds) + " 已保存" if snapshot_kinds else "未保留独立来源快照"
        context_lines = [
            f"共 {interpretation_count} 个解读版本",
            f"可恢复旧版本：{'有' if entry.trashed_interpretations else '无'}",
            f"当前路线：{entry.current_interpretation.route_key}" if entry.current_interpretation.route_key else "",
            f"来源任务：{snapshot.saved_from_job_id}" if snapshot.saved_from_job_id else "",
            f"来源快照：{snapshot_copy}",
            f"来源键：{entry.source_key}",
        ]
        for line in context_lines:
            if not line:
                continue
            label = QLabel(line)
            label.setObjectName("SecondaryText")
            label.setWordWrap(True)
            layout.addWidget(label)
        return frame

    def _build_trash_row(self, entry_id: str, interpretation: LibraryInterpretation) -> QWidget:
        row = QFrame()
        row.setObjectName("PreviewCard")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        text = QLabel(
            "\n".join(
                part
                for part in (
                    interpretation.summary_headline or interpretation.route_key,
                    f"路线：{interpretation.route_key}" if interpretation.route_key else "",
                    f"归档时间：{interpretation.trashed_at}" if interpretation.trashed_at else "",
                    f"归档原因：{_trash_reason_copy(interpretation.trash_reason)}" if interpretation.trash_reason else "",
                )
                if part
            )
        )
        text.setObjectName("BodyText")
        text.setWordWrap(True)

        restore_button = QPushButton("恢复为当前")
        restore_button.setObjectName("GhostButton")
        restore_button.clicked.connect(
            lambda _checked=False, current_entry_id=entry_id, current_interpretation_id=interpretation.interpretation_id: self.restore_requested.emit(
                current_entry_id,
                current_interpretation_id,
            )
        )

        layout.addWidget(text, 1)
        layout.addWidget(restore_button, 0, Qt.AlignTop)
        return row

    def _interpretation_html(self, interpretation: LibraryInterpretation) -> str:
        payload = interpretation.payload
        product_view = payload.get("product_view")
        if isinstance(product_view, dict) and product_view:
            return f"<div class='preview-reading structured-result'>{_product_view_html(product_view)}</div>"

        editorial = payload.get("editorial")
        summary = payload.get("summary")
        if isinstance(editorial, dict) and str(editorial.get("resolved_mode") or "").strip().lower() == "guide":
            return self._guide_editorial_html(editorial, summary)

        parts = ["<div class='preview-reading structured-result'>"]
        structured = payload.get("structured_result")
        if isinstance(structured, dict) and structured:
            summary = structured.get("summary")
            if isinstance(summary, dict):
                headline = str(summary.get("headline") or "").strip()
                short_text = str(summary.get("short_text") or "").strip()
                if headline or short_text:
                    bits = []
                    if headline:
                        bits.append(f"<h2>{html.escape(headline)}</h2>")
                    if short_text:
                        bits.append(f"<p>{html.escape(short_text)}</p>")
                    parts.append(f"<div class='result-section'>{''.join(bits)}</div>")

            parts.extend(self._render_card_sections(structured.get("key_points"), title="要点提炼", title_key="title", body_key="details"))
            parts.extend(self._render_card_sections(structured.get("analysis_items"), title="分析展开", title_key="kind", body_key="statement"))
            parts.extend(self._render_verification_section(structured.get("verification_items")))
            parts.extend(self._render_synthesis_section(structured.get("synthesis")))
        else:
            summary = payload.get("summary")
            if isinstance(summary, dict):
                headline = str(summary.get("headline") or "").strip()
                short_text = str(summary.get("short_text") or "").strip()
                if headline:
                    parts.append(f"<div class='result-section'><h2>{html.escape(headline)}</h2></div>")
                if short_text:
                    parts.append(f"<div class='result-section'><p>{html.escape(short_text)}</p></div>")

        if isinstance(editorial, dict) and editorial:
            items = []
            for key in ("resolved_reading_goal", "resolved_domain_template", "route_key"):
                value = str(editorial.get(key) or "").strip()
                if value:
                    items.append(f"<li><strong>{html.escape(key)}</strong>: {html.escape(value)}</li>")
            if items:
                parts.append(f"<div class='result-section'><h2>解读线索</h2><ul>{''.join(items)}</ul></div>")

        parts.append("</div>")
        return "".join(parts)

    @classmethod
    def _guide_editorial_html(cls, editorial: dict[str, object], summary: object) -> str:
        summary_payload = summary if isinstance(summary, dict) else {}
        base = editorial.get("base") if isinstance(editorial.get("base"), dict) else {}
        mode_payload = editorial.get("mode_payload") if isinstance(editorial.get("mode_payload"), dict) else {}

        title = str(summary_payload.get("headline") or "").strip() or cls._editorial_scalar(base.get("core_summary")) or "实用提炼"
        dek = str(summary_payload.get("short_text") or "").strip() or cls._editorial_scalar(base.get("bottom_line")) or ""

        parts = ["<div class='preview-reading structured-result'><div class='guide-digest-layout'>"]
        hero_bits = [f"<h2>{html.escape(title)}</h2>"]
        if dek and dek != title:
            hero_bits.append(f"<p>{html.escape(dek)}</p>")
        parts.append(f"<section class='guide-compact-hero'>{''.join(hero_bits)}</section>")

        guide_goal = cls._editorial_scalar(mode_payload.get("guide_goal"))
        if guide_goal:
            parts.append(
                "<section class='result-section'>"
                "<div class='guide-section-label'>怎么用这篇</div>"
                f"<p>{html.escape(guide_goal)}</p>"
                "</section>"
            )

        parts.extend(cls._guide_list_section("推荐步骤", cls._editorial_list(mode_payload.get("recommended_steps")), ordered=True))
        parts.extend(cls._guide_list_section("实用提醒", cls._editorial_list(mode_payload.get("tips"))))
        parts.extend(cls._guide_list_section("常见误区", cls._editorial_list(mode_payload.get("pitfalls"))))
        parts.extend(cls._guide_list_section("开始前准备", cls._editorial_list(mode_payload.get("prerequisites"))))

        quick_win = cls._editorial_scalar(mode_payload.get("quick_win"))
        if quick_win:
            parts.append(
                "<section class='result-section'>"
                "<div class='guide-section-label'>立即行动</div>"
                f"<p>{html.escape(quick_win)}</p>"
                "</section>"
            )

        parts.append("</div></div>")
        return "".join(parts)

    @staticmethod
    def _guide_list_section(title: str, items: list[str], *, ordered: bool = False) -> list[str]:
        if not items:
            return []
        tag = "ol" if ordered else "ul"
        rendered_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        return [
            "<section class='result-section'>"
            f"<div class='guide-section-label'>{html.escape(title)}</div>"
            f"<{tag}>{rendered_items}</{tag}>"
            "</section>"
        ]

    @staticmethod
    def _editorial_scalar(value: object) -> str | None:
        if isinstance(value, dict):
            value = value.get("value")
        text = str(value or "").strip()
        return text or None

    @classmethod
    def _editorial_list(cls, values: object) -> list[str]:
        if not isinstance(values, list):
            return []
        items: list[str] = []
        for value in values:
            text = cls._editorial_scalar(value)
            if text:
                items.append(text)
        return items

    def _clear_detail(self) -> None:
        self._clear_column(self.main_column_layout)
        self._clear_column(self.side_column_layout)

    def _filtered_entries(self, entries: list[LibraryEntryView]) -> list[LibraryEntryView]:
        filtered = list(entries)
        if self.recent_entries_filter.isChecked():
            filtered = sorted(filtered, key=lambda item: item.updated_at or item.current_interpretation.saved_at or "", reverse=True)
        elif not self.all_entries_filter.isChecked():
            filtered = []

        if self.with_images_filter.isChecked():
            filtered = [item for item in filtered if item.current_interpretation.image_summary_asset is not None]
        if self.with_trashed_filter.isChecked():
            filtered = [item for item in filtered if item.trashed_interpretations]
        return filtered

    @staticmethod
    def _clear_column(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _render_card_sections(items: object, *, title: str, title_key: str, body_key: str) -> list[str]:
        if not isinstance(items, list) or not items:
            return []
        cards: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            card_title = str(item.get(title_key) or "").strip()
            card_body = str(item.get(body_key) or "").strip()
            if not card_title and not card_body:
                continue
            cards.append(
                "<article class='result-card'>"
                f"<h3>{html.escape(card_title or title)}</h3>"
                f"<p>{html.escape(card_body or card_title)}</p>"
                "</article>"
            )
        if not cards:
            return []
        return [
            "<section class='result-section'>"
            f"<h2>{html.escape(title)}</h2>"
            f"<div class='result-grid'>{''.join(cards)}</div>"
            "</section>"
        ]

    @staticmethod
    def _render_verification_section(items: object) -> list[str]:
        if not isinstance(items, list) or not items:
            return []
        cards: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            claim = str(item.get("claim") or "").strip()
            status = str(item.get("status") or "").strip() or "unclear"
            rationale = str(item.get("rationale") or "").strip()
            if not claim:
                continue
            cards.append(
                "<article class='result-card verification-card'>"
                f"<div class='status-chip status-{html.escape(status.lower())}'>{html.escape(status.title())}</div>"
                f"<h3>{html.escape(claim)}</h3>"
                f"<p>{html.escape(rationale or '暂无补充说明。')}</p>"
                "</article>"
            )
        if not cards:
            return []
        return [
            "<section class='result-section'><h2>事实核验</h2>"
            f"<div class='result-grid'>{''.join(cards)}</div></section>"
        ]

    @staticmethod
    def _render_synthesis_section(synthesis: object) -> list[str]:
        if not isinstance(synthesis, dict):
            return []
        final_answer = str(synthesis.get("final_answer") or "").strip()
        next_steps = synthesis.get("next_steps")
        open_questions = synthesis.get("open_questions")
        extras: list[str] = []
        if isinstance(next_steps, list) and next_steps:
            extras.append(
                "<div><h3>下一步</h3><ul>"
                + "".join(f"<li>{html.escape(str(step))}</li>" for step in next_steps)
                + "</ul></div>"
            )
        if isinstance(open_questions, list) and open_questions:
            extras.append(
                "<div><h3>待解问题</h3><ul>"
                + "".join(f"<li>{html.escape(str(question))}</li>" for question in open_questions)
                + "</ul></div>"
            )
        if not final_answer and not extras:
            return []
        return [
            "<section class='result-section result-takeaway'>"
            "<h2>核心结论</h2>"
            f"<p>{html.escape(final_answer)}</p>"
            f"{''.join(extras)}"
            "</section>"
        ]
