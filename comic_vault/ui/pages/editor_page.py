from __future__ import annotations

import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from comic_vault.data.db import get_session
from comic_vault.data.models import Series
from comic_vault.ui.utils.web_title import TitleResult, WebTitleResolver

STATUSES = ["reading", "paused", "completed", "dropped"]


class EditorPage(QWidget):
    def __init__(self, *, on_back: Callable[[], None], on_saved: Callable[[], None]) -> None:
        super().__init__()
        self.setObjectName("Page")

        self.on_back = on_back
        self.on_saved = on_saved
        self._selected_id: Optional[int] = None

        # Web title resolver (browser-like, async)
        self._title_resolver = WebTitleResolver(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        # ===== Top bar =====
        root.addWidget(self._build_top_bar())

        # ===== Header =====
        self.header = QLabel("Add Comic")
        self.header.setObjectName("H1")
        root.addWidget(self.header)

        # ===== Cover block =====
        root.addLayout(self._build_cover_block())

        # ===== Form =====
        root.addWidget(self._build_form())

        # ===== Actions =====
        root.addLayout(self._build_actions())

        # ===== Status line =====
        self.fetch_status = QLabel("")
        self.fetch_status.setObjectName("Muted")
        root.addWidget(self.fetch_status)

    # ---------------------------------------------------------------------
    # UI builders
    # ---------------------------------------------------------------------
    def _build_top_bar(self) -> QWidget:
        top_host = QWidget()
        top_host.setObjectName("TopBar")

        top = QHBoxLayout(top_host)
        top.setContentsMargins(14, 10, 14, 10)
        top.setSpacing(10)

        title = QLabel("Comic Vault")
        title.setObjectName("TopTitle")

        btn_library = QPushButton("Library")
        btn_library.setObjectName("Primary")
        btn_library.clicked.connect(self.on_back)

        btn_add = QPushButton("Add Comic")
        btn_add.setObjectName("Ghost")
        btn_add.setEnabled(False)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_library)
        top.addWidget(btn_add)
        return top_host

    def _build_cover_block(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)

        self.preview = QLabel("No Image")
        self.preview.setObjectName("CoverPreview")
        self.preview.setFixedSize(240, 330)
        self.preview.setAlignment(Qt.AlignCenter)

        right = QVBoxLayout()
        right.setSpacing(8)

        lbl = QLabel("Cover Image")
        lbl.setObjectName("H2")

        self.cover_path = QLineEdit()
        self.cover_path.setObjectName("CoverPath")
        self.cover_path.setReadOnly(True)

        btn_pick = QPushButton("Choose Image…")
        btn_pick.setObjectName("Ghost")
        btn_pick.clicked.connect(self.pick_image)

        btn_clear = QPushButton("Clear Image")
        btn_clear.setObjectName("Ghost")
        btn_clear.clicked.connect(self.clear_image)

        right.addWidget(lbl)
        right.addWidget(self.cover_path)
        right.addWidget(btn_pick)
        right.addWidget(btn_clear)
        right.addStretch(1)

        row.addWidget(self.preview)
        row.addLayout(right)
        return row

    def _build_form(self) -> QWidget:
        host = QWidget()
        form = QFormLayout(host)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.title_input = QLineEdit()
        self.source_input = QLineEdit()

        # URL row + actions
        self.url_input = QLineEdit()

        url_row = QWidget()
        url_layout = QHBoxLayout(url_row)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(8)

        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setObjectName("Ghost")
        self.btn_paste.clicked.connect(self.paste_url)

        self.btn_open = QPushButton("Open")
        self.btn_open.setObjectName("Ghost")
        self.btn_open.clicked.connect(self.open_url)

        self.btn_fetch = QPushButton("Fetch Title")
        self.btn_fetch.setObjectName("Ghost")
        self.btn_fetch.clicked.connect(self.fetch_title)

        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.btn_paste)
        url_layout.addWidget(self.btn_open)
        url_layout.addWidget(self.btn_fetch)

        self.status_input = QComboBox()
        self.status_input.addItems(STATUSES)

        self.rating_input = QSpinBox()
        self.rating_input.setRange(0, 10)
        self.rating_input.setSpecialValueText("None (0)")
        self.rating_input.setValue(0)

        self.current_chapter_input = QLineEdit()
        self.current_url_input = QLineEdit()
        self.notes_input = QTextEdit()

        form.addRow("Title *", self.title_input)
        form.addRow("Source", self.source_input)
        form.addRow("URL", url_row)
        form.addRow("Status", self.status_input)
        form.addRow("Rating (0=None)", self.rating_input)
        form.addRow("Current Chapter", self.current_chapter_input)
        form.addRow("Current URL", self.current_url_input)
        form.addRow("Notes", self.notes_input)

        return host

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("Ghost")
        self.btn_cancel.clicked.connect(self.on_back)

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.on_save)

        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        return row

    # ---------------------------------------------------------------------
    # Public API used by MainWindow
    # ---------------------------------------------------------------------
    def load_series(self, series_id: Optional[int]) -> None:
        self._selected_id = series_id
        self.fetch_status.setText("")

        if series_id is None:
            self.header.setText("Add Comic")
            self._reset_form()
            return

        with get_session() as session:
            s = session.get(Series, series_id)

        if not s:
            self.header.setText("Add Comic")
            self._reset_form()
            return

        self.header.setText("Edit Comic")
        self.title_input.setText(s.title or "")
        self.source_input.setText(s.source or "")
        self.url_input.setText(s.url or "")
        self.status_input.setCurrentText(s.status if s.status in STATUSES else "reading")
        self.rating_input.setValue(int(s.rating or 0))
        self.current_chapter_input.setText(s.current_chapter or "")
        self.current_url_input.setText(s.current_url or "")
        self.notes_input.setPlainText(s.notes or "")

        self.cover_path.setText(s.cover_path or "")
        self._render_preview(s.cover_path)

    def set_url(self, url: str) -> None:
        self.url_input.setText((url or "").strip())

    # ---------------------------------------------------------------------
    # Cover
    # ---------------------------------------------------------------------
    def pick_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return
        self.cover_path.setText(file_path)
        self._render_preview(file_path)

    def clear_image(self) -> None:
        self.cover_path.clear()
        self.preview.setPixmap(QPixmap())
        self.preview.setText("No Image")

    def _render_preview(self, path: Optional[str]) -> None:
        if not path:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        p = Path(path)
        if not p.exists():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        pix = QPixmap(str(p))
        if pix.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        self.preview.setPixmap(
            pix.scaled(self.preview.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )
        self.preview.setText("")

    # ---------------------------------------------------------------------
    # URL actions (G2)
    # ---------------------------------------------------------------------
    def paste_url(self) -> None:
        txt = (QApplication.clipboard().text() or "").strip()
        if not txt:
            QMessageBox.information(self, "Clipboard", "Clipboard is empty.")
            return
        self.url_input.setText(txt)

    def open_url(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Open URL", "URL is empty.")
            return
        webbrowser.open(url)

    def fetch_title(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Fetch Title", "URL is empty.")
            return

        self._set_fetch_ui(True)
        self.fetch_status.setText("Fetching title…")

        def done(res: TitleResult) -> None:
            # callback runs in GUI thread (QtWebEngine)
            self._set_fetch_ui(False)

            if not res.ok:
                self.fetch_status.setText("")
                QMessageBox.critical(self, "Fetch Title failed", res.error or "Unknown error")
                return

            # if redirected, update URL
            if res.final_url and res.final_url != url:
                self.url_input.setText(res.final_url)

            current = (self.title_input.text() or "").strip()
            if not current:
                self.title_input.setText(res.title)
                self.fetch_status.setText("Fetched ✅")
            else:
                resp = QMessageBox.question(
                    self,
                    "Fetch Title",
                    "Overwrite current title?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if resp == QMessageBox.Yes:
                    self.title_input.setText(res.title)
                self.fetch_status.setText("Fetched ✅")

        self._title_resolver.resolve(url, done, timeout_ms=15000)

    def _set_fetch_ui(self, fetching: bool) -> None:
        # prevent spam clicks during fetch
        self.btn_fetch.setEnabled(not fetching)
        self.btn_paste.setEnabled(not fetching)
        self.btn_open.setEnabled(not fetching)

    # ---------------------------------------------------------------------
    # Save
    # ---------------------------------------------------------------------
    def on_save(self) -> None:
        title = (self.title_input.text() or "").strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Title is required.")
            return

        source = (self.source_input.text() or "").strip() or None
        url = (self.url_input.text() or "").strip() or None
        status = self.status_input.currentText()

        rating_raw = int(self.rating_input.value())
        rating = None if rating_raw == 0 else rating_raw

        current_chapter = (self.current_chapter_input.text() or "").strip() or None
        current_url = (self.current_url_input.text() or "").strip() or None
        notes = (self.notes_input.toPlainText() or "").strip() or None

        cover_path = (self.cover_path.text() or "").strip() or None
        now = datetime.utcnow()

        with get_session() as session:
            if self._selected_id is None:
                s = Series(
                    title=title,
                    source=source,
                    url=url,
                    cover_path=cover_path,
                    status=status,
                    rating=rating,
                    current_chapter=current_chapter,
                    current_url=current_url,
                    notes=notes,
                    created_at=now,
                    updated_at=now,
                )
                session.add(s)
                session.commit()
            else:
                s = session.get(Series, self._selected_id)
                if not s:
                    QMessageBox.warning(self, "Error", "Selected record no longer exists.")
                    return
                s.title = title
                s.source = source
                s.url = url
                s.cover_path = cover_path
                s.status = status
                s.rating = rating
                s.current_chapter = current_chapter
                s.current_url = current_url
                s.notes = notes
                s.updated_at = now
                session.add(s)
                session.commit()

        self.on_saved()

    def _reset_form(self) -> None:
        self.title_input.clear()
        self.source_input.clear()
        self.url_input.clear()
        self.status_input.setCurrentText("reading")
        self.rating_input.setValue(0)
        self.current_chapter_input.clear()
        self.current_url_input.clear()
        self.notes_input.clear()
        self.cover_path.clear()
        self._render_preview(None)
