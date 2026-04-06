"""Inline result view — shows InsightBriefV2 directly in the main window stack."""
from __future__ import annotations

import html
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from windows_client.gui.result_renderer import PREVIEW_STYLESHEET, _markdown_filename, _preview_html, entry_to_markdown

MODE_LABELS = {
    "argument": "深度分析",
    "guide": "实用提炼",
    "review": "推荐导览",
}


class InlineResultView(QWidget):
    """Full-window widget that renders an InsightBriefV2 as the main content."""

    reanalyze_requested = Signal(str)  # emits source_url
    reinterpret_requested = Signal()

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry: ResultWorkspaceEntry | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top action bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 16)
        self._new_url_button = QPushButton("New URL")
        self._new_url_button.setObjectName("PrimaryButton")
        self._reanalyze_btn = QPushButton("Re-analyze")
        self._reanalyze_btn.setObjectName("GhostButton")
        self._reanalyze_btn.clicked.connect(self._on_reanalyze)
        self._reanalyze_btn.setEnabled(False)
        self._reinterpret_btn = QPushButton("Re-interpret as...")
        self._reinterpret_btn.setObjectName("GhostButton")
        self._reinterpret_btn.clicked.connect(self.reinterpret_requested.emit)
        self._reinterpret_btn.setEnabled(False)
        self._history_btn = QPushButton("历史记录")
        self._history_btn.setObjectName("GhostButton")
        top_bar.addWidget(self._new_url_button, 0, Qt.AlignLeft)
        top_bar.addWidget(self._reanalyze_btn, 0, Qt.AlignLeft)
        top_bar.addWidget(self._reinterpret_btn, 0, Qt.AlignLeft)
        top_bar.addWidget(self._history_btn, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        root.addLayout(top_bar)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 16, 0)
        content_layout.setSpacing(20)

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
        self._hero_take.setObjectName("HeroTake")
        self._hero_take.setWordWrap(True)
        self._hero_byline = QLabel("")
        self._hero_byline.setObjectName("SecondaryText")
        self._hero_byline.setWordWrap(True)
        # Clickable source URL
        self._hero_source = QLabel("")
        self._hero_source.setObjectName("SecondaryText")
        self._hero_source.setOpenExternalLinks(True)
        self._hero_source.setTextFormat(Qt.RichText)
        self._hero_source.hide()
        # Content-kind and author-stance tag chips (horizontal row)
        self._hero_tags_row = QWidget()
        tags_row_layout = QHBoxLayout(self._hero_tags_row)
        tags_row_layout.setContentsMargins(0, 0, 0, 0)
        tags_row_layout.setSpacing(8)
        self._mode_chip = QLabel("")
        self._mode_chip.setObjectName("TagChip")
        self._content_kind_chip = QLabel("")
        self._content_kind_chip.setObjectName("TagChip")
        self._author_stance_chip = QLabel("")
        self._author_stance_chip.setObjectName("TagChipMuted")
        tags_row_layout.addWidget(self._mode_chip)
        tags_row_layout.addWidget(self._content_kind_chip)
        tags_row_layout.addWidget(self._author_stance_chip)
        tags_row_layout.addStretch(1)
        self._hero_tags_row.hide()
        hero_layout.addWidget(self._hero_title)
        hero_layout.addWidget(self._hero_take)
        hero_layout.addWidget(self._hero_byline)
        hero_layout.addWidget(self._hero_source)
        hero_layout.addWidget(self._hero_tags_row)

        # Quick takeaways block (作者观点)
        self._takeaways_frame = QFrame()
        self._takeaways_frame.setObjectName("PreviewCard")
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
        verification_heading = QLabel("Fact Check")
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
        bottom_line_heading = QLabel("Bottom Line")
        bottom_line_heading.setObjectName("SectionLabel")
        bottom_line_layout.addWidget(bottom_line_heading)
        self._bottom_line_label = QLabel("")
        self._bottom_line_label.setObjectName("BodyText")
        self._bottom_line_label.setWordWrap(True)
        bottom_line_layout.addWidget(self._bottom_line_label)
        self._bottom_line_frame.hide()

        # Insight card (generated image — hidden until card exists)
        self._card_frame = QFrame()
        self._card_frame.setObjectName("InsightCardFrame")
        _cfl = QVBoxLayout(self._card_frame)
        _cfl.setContentsMargins(0, 4, 0, 4)
        _cfl.setSpacing(8)
        _card_heading = QLabel("精华卡片")
        _card_heading.setObjectName("SectionLabel")
        _save_row = QHBoxLayout()
        self._card_save_btn = QPushButton("保存图片")
        self._card_save_btn.setObjectName("GhostButton")
        self._card_save_btn.clicked.connect(self._save_insight_card)
        _save_row.addWidget(_card_heading)
        _save_row.addStretch(1)
        _save_row.addWidget(self._card_save_btn)
        self._card_image_label = QLabel()
        self._card_image_label.setAlignment(Qt.AlignLeft)
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
        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDocumentMargin(0)
        self._browser.document().setDefaultStyleSheet(PREVIEW_STYLESHEET)
        self._browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._browser.setMinimumHeight(300)

        # Gaps block (open questions + next steps)
        self._gaps_frame = QFrame()
        self._gaps_frame.setObjectName("PreviewCard")
        gaps_layout = QVBoxLayout(self._gaps_frame)
        gaps_layout.setContentsMargins(24, 20, 24, 20)
        gaps_layout.setSpacing(8)
        gaps_heading = QLabel("Questions & Next Steps")
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
        visual_heading = QLabel("Visual Evidence")
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
        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setObjectName("GhostButton")
        self._open_folder_btn.clicked.connect(self._open_folder)
        self._export_json_btn = QPushButton("Export JSON")
        self._export_json_btn.setObjectName("GhostButton")
        self._export_json_btn.clicked.connect(self._open_analysis)
        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("GhostButton")
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("GhostButton")
        self._save_btn.clicked.connect(self._save_as_markdown)
        action_layout.addWidget(self._open_folder_btn)
        action_layout.addWidget(self._export_json_btn)
        action_layout.addWidget(self._copy_btn)
        action_layout.addWidget(self._save_btn)
        action_layout.addStretch(1)

        content_layout.addWidget(self._hero_frame)
        content_layout.addWidget(self._card_frame)
        content_layout.addWidget(self._takeaways_frame)
        content_layout.addWidget(self._verification_frame)
        content_layout.addWidget(self._bottom_line_frame)
        content_layout.addWidget(self._divergent_frame)
        content_layout.addWidget(self._gaps_frame)
        content_layout.addWidget(self._coverage_banner)
        content_layout.addWidget(self._image_truncation_banner)
        content_layout.addWidget(self._browser, 1)
        content_layout.addWidget(self._visual_frame)
        content_layout.addWidget(action_frame)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    @property
    def new_url_button(self) -> QPushButton:
        return self._new_url_button

    @property
    def history_button(self) -> QPushButton:
        return self._history_btn

    def load_entry(
        self,
        entry: ResultWorkspaceEntry,
        *,
        brief: InsightBriefV2 | None,
        resolved_mode: str | None = None,
    ) -> None:
        """Populate the view from a ResultWorkspaceEntry with an optional InsightBriefV2."""
        self._entry = entry
        mode_label = MODE_LABELS.get((resolved_mode or "").strip().lower(), "")

        # Hero fields common to both paths
        source = entry.source_url or entry.canonical_url
        if source:
            display = source if len(source) <= 72 else source[:69] + "…"
            self._hero_source.setText(f"<a href='{html.escape(source)}'>{html.escape(display)}</a>")
            self._hero_source.show()
        else:
            self._hero_source.hide()
        self._reanalyze_btn.setEnabled(bool(source))
        self._reinterpret_btn.setEnabled(entry.state == "processed")

        if brief is not None:
            # Full view
            self._hero_title.setText(brief.hero.title)
            self._hero_take.setText(brief.hero.one_sentence_take)
            byline_parts = [v for v in (entry.author, entry.published_at, entry.platform) if v]
            self._hero_byline.setText("  ·  ".join(byline_parts) if byline_parts else "")
            self._hero_byline.setVisible(bool(byline_parts))

            # Content-kind / author-stance chips
            kind = str(getattr(brief.hero, "content_kind", None) or "").strip()
            stance = str(getattr(brief.hero, "author_stance", None) or "").strip()
            self._mode_chip.setText(mode_label)
            self._mode_chip.setVisible(bool(mode_label))
            self._content_kind_chip.setText(kind)
            self._content_kind_chip.setVisible(bool(kind))
            self._author_stance_chip.setText(stance)
            self._author_stance_chip.setVisible(bool(stance))
            self._hero_tags_row.setVisible(bool(mode_label or kind or stance))

            key_point_viewpoints = [v for v in brief.viewpoints if v.kind == "key_point"]
            self._clear_layout(self._takeaways_list_layout)
            for index, vp in enumerate(key_point_viewpoints, start=1):
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
                    f"\u26a0 Coverage warning: only {pct}% of source segments were analysed "
                    f"({coverage.used_segments}/{coverage.total_segments}). "
                    "Conclusions may be incomplete."
                )
                self._coverage_banner.show()
            else:
                self._coverage_banner.hide()

            # Image input truncation banner
            llm_image = entry.details.get("llm_image_input", {})
            if llm_image.get("image_input_truncated"):
                count = llm_image.get("image_input_count", "?")
                self._image_truncation_label.setText(
                    f"\u26a0 Image input limit reached: {count} image(s) were sent to the model. "
                    "Visual analysis may be incomplete."
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
            self._hero_title.setText(entry.title or "Analysis Complete")
            self._hero_take.setText(getattr(entry, "summary", "") or "")
            self._hero_byline.setVisible(False)
            self._mode_chip.setText(mode_label)
            self._mode_chip.setVisible(bool(mode_label))
            self._content_kind_chip.setVisible(False)
            self._author_stance_chip.setVisible(False)
            self._hero_tags_row.setVisible(bool(mode_label))
            self._takeaways_frame.hide()
            self._verification_frame.hide()
            self._bottom_line_frame.hide()
            self._divergent_frame.hide()
            self._coverage_banner.hide()
            self._image_truncation_banner.hide()
            self._gaps_frame.hide()

        # Visual Evidence (video content — always populated from entry, not brief)
        visual_findings = [f for f in entry.details.get("visual_findings") or [] if isinstance(f, dict)]
        self._clear_layout(self._visual_list_layout)
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
        self._visual_frame.setVisible(bool(visual_findings))

        # Insight card image (shown when PNG exists)
        card_path = entry.details.get("insight_card_path")
        if card_path is not None:
            pixmap = QPixmap(str(card_path))
            if not pixmap.isNull():
                if pixmap.width() > 700:
                    pixmap = pixmap.scaledToWidth(700, Qt.SmoothTransformation)
                self._card_image_label.setPixmap(pixmap)
                self._card_frame.show()
            else:
                self._card_frame.hide()
        else:
            self._card_frame.hide()

        if brief is None:
            self._browser.setHtml(_preview_html(entry, resolved_mode=resolved_mode))
            self._browser.show()
        else:
            self._browser.setHtml("")
            self._browser.hide()

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
        frame.setObjectName("CoverageBanner")
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

    def _copy_to_clipboard(self) -> None:
        if self._entry is None:
            return
        QApplication.clipboard().setText(entry_to_markdown(self._entry))
        self._copy_btn.setEnabled(False)
        self._copy_btn.setText("Copied!")
        QTimer.singleShot(1500, self._restore_copy_button)

    def _restore_copy_button(self) -> None:
        self._copy_btn.setEnabled(True)
        self._copy_btn.setText("Copy")

    def _save_as_markdown(self) -> None:
        if self._entry is None:
            return
        default_name = _markdown_filename(self._entry)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as Markdown",
            default_name,
            "Markdown files (*.md);;All files (*)",
        )
        if not path:
            return
        Path(path).write_text(entry_to_markdown(self._entry), encoding="utf-8")
        saved_name = Path(path).name
        self._save_btn.setEnabled(False)
        self._save_btn.setText(f"Saved: {saved_name}")
        QTimer.singleShot(2500, self._restore_save_button)

    def _restore_save_button(self) -> None:
        self._save_btn.setEnabled(True)
        self._save_btn.setText("Save")

    def _on_reanalyze(self) -> None:
        if self._entry is None:
            return
        url = self._entry.source_url or self._entry.canonical_url
        if url:
            self.reanalyze_requested.emit(url)

    @staticmethod
    def _make_key_point_item(index: int, statement: str, details: str | None) -> QWidget:
        item = QWidget()
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
        import shutil
        shutil.copy2(str(card_path), dest)
        self._card_save_btn.setEnabled(False)
        self._card_save_btn.setText("已保存")
        QTimer.singleShot(2000, self._restore_card_save_btn)

    def _restore_card_save_btn(self) -> None:
        self._card_save_btn.setEnabled(True)
        self._card_save_btn.setText("保存图片")

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
