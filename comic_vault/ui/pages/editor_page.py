from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QInputDialog,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from comic_vault.data.covers import delete_managed_cover, import_cover, save_cover_image
from comic_vault.data.db import get_session
from comic_vault.data.models import Series
from comic_vault.data.storage import resolve_app_path
from comic_vault.data.validation import normalize_url
from comic_vault.ui.utils.browser import open_url, open_url_private
from comic_vault.ui.utils.remote_image import RemoteImageLoader, RemoteImageResult
from comic_vault.ui.utils.web_cover import CoverResult, WebCoverResolver
from comic_vault.ui.utils.web_title import TitleResult, WebTitleResolver


STATUSES = ["reading", "paused", "completed", "dropped"]


class EditorPage(QWidget):
    def __init__(self, *, on_back: Callable[[], None], on_saved: Callable[[], None]) -> None:
        super().__init__()
        self.setObjectName("Page")

        self.on_back = on_back
        self.on_saved = on_saved
        self._selected_id: Optional[int] = None

        self._cover_db_path: Optional[str] = None
        self._cover_source_path: Optional[str] = None
        self._cover_fetched_image: Optional[QImage] = None
        self._cover_removed = False

        self._title_resolver = WebTitleResolver(self)
        self._cover_resolver = WebCoverResolver(self)
        self._remote_image_loader = RemoteImageLoader(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        root.addWidget(self._build_top_bar())

        self.header = QLabel("Add Comic")
        self.header.setObjectName("H1")
        root.addWidget(self.header)

        root.addLayout(self._build_cover_block())
        root.addWidget(self._build_form())
        root.addLayout(self._build_actions())

        self.fetch_status = QLabel("")
        self.fetch_status.setObjectName("Muted")
        root.addWidget(self.fetch_status)

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

        label = QLabel("Cover Image")
        label.setObjectName("H2")

        self.cover_path = QLineEdit()
        self.cover_path.setObjectName("CoverPath")
        self.cover_path.setReadOnly(True)

        btn_pick = QPushButton("Choose Image...")
        btn_pick.setObjectName("Ghost")
        btn_pick.clicked.connect(self.pick_image)

        self.btn_link = QPushButton("Load from Link...")
        self.btn_link.setObjectName("Ghost")
        self.btn_link.clicked.connect(self.load_cover_from_link)

        btn_clear = QPushButton("Clear Image")
        btn_clear.setObjectName("Ghost")
        btn_clear.clicked.connect(self.clear_image)

        right.addWidget(label)
        right.addWidget(self.cover_path)
        right.addWidget(btn_pick)
        right.addWidget(self.btn_link)
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

        self.btn_open_private = QPushButton("Private")
        self.btn_open_private.setObjectName("Ghost")
        self.btn_open_private.clicked.connect(self.open_url_private)

        self.btn_fetch = QPushButton("Fetch Title")
        self.btn_fetch.setObjectName("Ghost")
        self.btn_fetch.clicked.connect(self.fetch_title)

        self.btn_fetch_cover = QPushButton("Fetch Cover")
        self.btn_fetch_cover.setObjectName("Ghost")
        self.btn_fetch_cover.clicked.connect(self.fetch_cover)

        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.btn_paste)
        url_layout.addWidget(self.btn_open)
        url_layout.addWidget(self.btn_open_private)
        url_layout.addWidget(self.btn_fetch)
        url_layout.addWidget(self.btn_fetch_cover)

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

    def load_series(self, series_id: Optional[int]) -> None:
        self._selected_id = series_id
        self.fetch_status.setText("")

        if series_id is None:
            self.header.setText("Add Comic")
            self._reset_form()
            return

        with get_session() as session:
            series = session.get(Series, series_id)

        if not series:
            self.header.setText("Add Comic")
            self._reset_form()
            return

        self.header.setText("Edit Comic")
        self.title_input.setText(series.title or "")
        self.source_input.setText(series.source or "")
        self.url_input.setText(series.url or "")
        self.status_input.setCurrentText(series.status if series.status in STATUSES else "reading")
        self.rating_input.setValue(int(series.rating or 0))
        self.current_chapter_input.setText(series.current_chapter or "")
        self.current_url_input.setText(series.current_url or "")
        self.notes_input.setPlainText(series.notes or "")

        self._cover_db_path = series.cover_path
        self._cover_source_path = None
        self._cover_fetched_image = None
        self._cover_removed = False
        self._set_cover_display(series.cover_path)

    def set_url(self, url: str) -> None:
        self.url_input.setText((url or "").strip())

    def pick_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not file_path:
            return

        self._cover_source_path = file_path
        self._cover_fetched_image = None
        self._cover_removed = False
        self.cover_path.setText(file_path)
        self._render_preview(file_path)

    def clear_image(self) -> None:
        self._cover_source_path = None
        self._cover_fetched_image = None
        self._cover_removed = True
        self.cover_path.clear()
        self.preview.setPixmap(QPixmap())
        self.preview.setText("No Image")

    def _set_cover_display(self, stored_path: Optional[str]) -> None:
        resolved = resolve_app_path(stored_path)
        self.cover_path.setText("" if resolved is None else str(resolved))
        self._render_preview(stored_path)

    def _render_preview(self, path: Optional[str]) -> None:
        resolved = resolve_app_path(path)
        if resolved is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        file_path = Path(resolved)
        if not file_path.exists():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        pix = QPixmap(str(file_path))
        if pix.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        self.preview.setPixmap(
            pix.scaled(self.preview.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )
        self.preview.setText("")

    def paste_url(self) -> None:
        text = (QApplication.clipboard().text() or "").strip()
        if not text:
            QMessageBox.information(self, "Clipboard", "Clipboard is empty.")
            return
        self.url_input.setText(text)

    def open_url(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Open URL", "URL is empty.")
            return
        if not open_url(url):
            QMessageBox.warning(self, "Open URL", "Could not open the browser.")

    def open_url_private(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Open Private", "URL is empty.")
            return
        ok, error = open_url_private(url)
        if not ok:
            QMessageBox.warning(self, "Open Private", error)

    def fetch_cover(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Fetch Cover", "URL is empty.")
            return

        has_existing_cover = bool(self._cover_source_path or self._cover_fetched_image or self._cover_db_path) and not self._cover_removed
        if has_existing_cover:
            resp = QMessageBox.question(
                self,
                "Fetch Cover",
                "Overwrite the current cover preview?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        self._set_fetch_ui(True)
        self.fetch_status.setText("Fetching cover...")

        def done(result: CoverResult) -> None:
            self._set_fetch_ui(False)

            if not result.ok:
                self.fetch_status.setText("")
                QMessageBox.critical(self, "Fetch Cover failed", result.error or "Unknown error")
                return

            image = QImage()
            if not image.loadFromData(result.image_data):
                self.fetch_status.setText("")
                QMessageBox.critical(self, "Fetch Cover failed", "Downloaded file is not a valid image.")
                return

            if result.final_url and result.final_url != url:
                self.url_input.setText(result.final_url)

            self._apply_remote_cover(image, result.image_url or "Fetched cover")
            self.fetch_status.setText("Cover fetched")

        self._cover_resolver.resolve(url, done, timeout_ms=18000)

    def load_cover_from_link(self) -> None:
        current_value = self.cover_path.text() if self.cover_path.text().startswith(("http://", "https://")) else ""
        image_url, ok = QInputDialog.getText(self, "Load Cover from Link", "Image URL:", text=current_value)
        if not ok:
            return

        image_url = image_url.strip()
        if not image_url:
            return

        try:
            normalized_url = normalize_url(image_url)
        except ValueError as exc:
            QMessageBox.warning(self, "Load Cover from Link", str(exc))
            return

        has_existing_cover = bool(self._cover_source_path or self._cover_fetched_image or self._cover_db_path) and not self._cover_removed
        if has_existing_cover:
            resp = QMessageBox.question(
                self,
                "Load Cover from Link",
                "Overwrite the current cover preview?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        self._set_fetch_ui(True)
        self.fetch_status.setText("Downloading cover from link...")

        def done(result: RemoteImageResult) -> None:
            self._set_fetch_ui(False)

            if not result.ok:
                self.fetch_status.setText("")
                QMessageBox.critical(self, "Load Cover from Link failed", result.error or "Unknown error")
                return

            image = QImage()
            if not image.loadFromData(result.image_data):
                self.fetch_status.setText("")
                QMessageBox.critical(
                    self,
                    "Load Cover from Link failed",
                    "Downloaded file is not a valid image.",
                )
                return

            self._apply_remote_cover(image, result.image_url or normalized_url or image_url)
            self.fetch_status.setText("Cover loaded")

        self._remote_image_loader.download(normalized_url or image_url, done, timeout_ms=15000)

    def fetch_title(self) -> None:
        url = (self.url_input.text() or "").strip()
        if not url:
            QMessageBox.information(self, "Fetch Title", "URL is empty.")
            return

        self._set_fetch_ui(True)
        self.fetch_status.setText("Fetching title...")

        def done(result: TitleResult) -> None:
            self._set_fetch_ui(False)

            if not result.ok:
                self.fetch_status.setText("")
                QMessageBox.critical(self, "Fetch Title failed", result.error or "Unknown error")
                return

            if result.final_url and result.final_url != url:
                self.url_input.setText(result.final_url)

            current = (self.title_input.text() or "").strip()
            if not current:
                self.title_input.setText(result.title)
                self.fetch_status.setText("Fetched")
                return

            resp = QMessageBox.question(
                self,
                "Fetch Title",
                "Overwrite current title?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp == QMessageBox.Yes:
                self.title_input.setText(result.title)
            self.fetch_status.setText("Fetched")

        self._title_resolver.resolve(url, done, timeout_ms=15000)

    def _set_fetch_ui(self, fetching: bool) -> None:
        self.btn_fetch.setEnabled(not fetching)
        self.btn_fetch_cover.setEnabled(not fetching)
        self.btn_link.setEnabled(not fetching)
        self.btn_paste.setEnabled(not fetching)
        self.btn_open.setEnabled(not fetching)
        self.btn_open_private.setEnabled(not fetching)

    def _render_preview_image(self, image: QImage) -> None:
        pix = QPixmap.fromImage(image)
        if pix.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No Image")
            return

        self.preview.setPixmap(
            pix.scaled(self.preview.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )
        self.preview.setText("")

    def _apply_remote_cover(self, image: QImage, label: str) -> None:
        self._cover_source_path = None
        self._cover_fetched_image = image
        self._cover_removed = False
        self.cover_path.setText(label)
        self._render_preview_image(image)

    def on_save(self) -> None:
        title = (self.title_input.text() or "").strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Title is required.")
            return

        try:
            url = normalize_url(self.url_input.text())
            current_url = normalize_url(self.current_url_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Validation", str(exc))
            return

        source = (self.source_input.text() or "").strip() or None
        status = self.status_input.currentText()
        rating_raw = int(self.rating_input.value())
        rating = None if rating_raw == 0 else rating_raw
        current_chapter = (self.current_chapter_input.text() or "").strip() or None
        notes = (self.notes_input.toPlainText() or "").strip() or None
        now = datetime.utcnow()

        with get_session() as session:
            duplicate = None
            if url:
                duplicate = session.exec(select(Series).where(Series.url == url)).first()

            if duplicate and duplicate.id != self._selected_id:
                resp = QMessageBox.question(
                    self,
                    "Duplicate URL",
                    "Another comic already uses this URL. Save anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if resp != QMessageBox.Yes:
                    return

            if self._selected_id is None:
                series = Series(
                    title=title,
                    source=source,
                    url=url,
                    cover_path=None,
                    status=status,
                    rating=rating,
                    current_chapter=current_chapter,
                    current_url=current_url,
                    notes=notes,
                    created_at=now,
                    updated_at=now,
                )
                session.add(series)
                session.commit()
                session.refresh(series)
                old_cover_path = None
            else:
                series = session.get(Series, self._selected_id)
                if not series:
                    QMessageBox.warning(self, "Error", "Selected record no longer exists.")
                    return

                old_cover_path = series.cover_path
                series.title = title
                series.source = source
                series.url = url
                series.status = status
                series.rating = rating
                series.current_chapter = current_chapter
                series.current_url = current_url
                series.notes = notes
                series.updated_at = now
                session.add(series)
                session.commit()
                session.refresh(series)

            new_cover_path = self._cover_db_path
            delete_after_save = False

            if self._cover_removed:
                new_cover_path = None
                delete_after_save = bool(old_cover_path)
            elif self._cover_fetched_image is not None:
                try:
                    new_cover_path = save_cover_image(self._cover_fetched_image, series_id=int(series.id))
                except Exception as exc:
                    QMessageBox.warning(
                        self,
                        "Cover Import",
                        f"Comic was saved, but the fetched cover could not be imported.\n\n{exc}",
                    )
                    new_cover_path = old_cover_path
                else:
                    delete_after_save = old_cover_path != new_cover_path
            elif self._cover_source_path:
                try:
                    new_cover_path = import_cover(self._cover_source_path, series_id=int(series.id))
                except Exception as exc:
                    QMessageBox.warning(
                        self,
                        "Cover Import",
                        f"Comic was saved, but the cover could not be imported.\n\n{exc}",
                    )
                    new_cover_path = old_cover_path
                else:
                    delete_after_save = old_cover_path != new_cover_path

            series.cover_path = new_cover_path
            series.updated_at = now
            session.add(series)
            session.commit()

        if delete_after_save and old_cover_path and old_cover_path != new_cover_path:
            delete_managed_cover(old_cover_path)
        elif self._cover_removed and old_cover_path:
            delete_managed_cover(old_cover_path)

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
        self.fetch_status.setText("")

        self._cover_db_path = None
        self._cover_source_path = None
        self._cover_fetched_image = None
        self._cover_removed = False
        self.cover_path.clear()
        self._render_preview(None)
