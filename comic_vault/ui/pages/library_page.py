from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlmodel import select

from comic_vault.data.backup import create_backup_archive, restore_backup_archive
from comic_vault.data.covers import delete_managed_cover
from comic_vault.data.db import get_session
from comic_vault.data.json_transfer import export_library_json, import_library_json
from comic_vault.data.models import Series
from comic_vault.data.storage import get_backups_dir, get_data_dir, get_exports_dir
from comic_vault.data.validation import normalize_url
from comic_vault.ui.utils.browser import open_url, open_url_private
from comic_vault.ui.utils.desktop import open_local_path
from comic_vault.ui.widgets.comic_card import ComicCard
from comic_vault.ui.widgets.flow_layout import FlowLayout
from comic_vault.ui.widgets.quick_update_dialog import QuickUpdateDialog


SORT_OPTIONS = {
    "updated_desc": "Recently Updated",
    "created_desc": "Newest Added",
    "title_asc": "Title A-Z",
    "title_desc": "Title Z-A",
    "rating_desc": "Highest Rated",
}


FILTER_OPTIONS = {
    "all": "All Statuses",
    "reading": "Reading",
    "paused": "Paused",
    "completed": "Completed",
    "dropped": "Dropped",
    "resume_ready": "Resume Ready",
    "missing_cover": "Missing Cover",
}


class LibraryPage(QWidget):
    def __init__(
        self,
        *,
        on_add: Callable[[], None],
        on_edit: Callable[[int], None],
        on_add_from_clipboard: Callable[[Optional[str]], None],
    ) -> None:
        super().__init__()
        self.setObjectName("Page")

        self.on_add = on_add
        self.on_edit = on_edit
        self.on_add_from_clipboard = on_add_from_clipboard

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        top_host = QWidget()
        top_host.setObjectName("TopBar")
        top = QHBoxLayout(top_host)
        top.setContentsMargins(14, 10, 14, 10)
        top.setSpacing(10)

        title = QLabel("Comic Vault")
        title.setObjectName("TopTitle")

        top.addWidget(title)
        top.addStretch(1)

        btn_library = QPushButton("Library")
        btn_library.setEnabled(False)
        btn_library.setObjectName("Primary")

        btn_paste_add = QPushButton("Paste & Add")
        btn_paste_add.setObjectName("Ghost")
        btn_paste_add.clicked.connect(self._paste_and_add)

        btn_data_dir = QPushButton("Data Folder")
        btn_data_dir.setObjectName("Ghost")
        btn_data_dir.clicked.connect(self._open_data_dir)

        btn_backup = QPushButton("Backup")
        btn_backup.setObjectName("Ghost")
        btn_backup.clicked.connect(self._create_backup)

        btn_restore = QPushButton("Restore")
        btn_restore.setObjectName("Ghost")
        btn_restore.clicked.connect(self._restore_backup)

        btn_export_json = QPushButton("Export JSON")
        btn_export_json.setObjectName("Ghost")
        btn_export_json.clicked.connect(self._export_json)

        btn_import_json = QPushButton("Import JSON")
        btn_import_json.setObjectName("Ghost")
        btn_import_json.clicked.connect(self._import_json)

        btn_add = QPushButton("Add Comic")
        btn_add.setObjectName("Ghost")
        btn_add.clicked.connect(self.on_add)

        top.addWidget(btn_library)
        top.addWidget(btn_paste_add)
        top.addWidget(btn_data_dir)
        top.addWidget(btn_backup)
        top.addWidget(btn_restore)
        top.addWidget(btn_export_json)
        top.addWidget(btn_import_json)
        top.addWidget(btn_add)

        root.addWidget(top_host)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.count_label = QLabel("My Library (0 comics)")
        self.count_label.setObjectName("H1")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title / source / status ...")
        self.search.textChanged.connect(self.reload)

        self.status_filter = QComboBox()
        for key, label in FILTER_OPTIONS.items():
            self.status_filter.addItem(label, key)
        self.status_filter.currentIndexChanged.connect(self.reload)

        self.sort_combo = QComboBox()
        for key, label in SORT_OPTIONS.items():
            self.sort_combo.addItem(label, key)
        self.sort_combo.currentIndexChanged.connect(self.reload)

        header.addWidget(self.count_label)
        header.addStretch(1)
        header.addWidget(self.status_filter)
        header.addWidget(self.sort_combo)
        header.addWidget(self.search)

        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.grid_host = QWidget()
        self.flow = FlowLayout(self.grid_host, spacing=16)
        self.grid_host.setLayout(self.flow)

        self.scroll.setWidget(self.grid_host)
        root.addWidget(self.scroll, 1)

        self.reload()

    def _paste_and_add(self) -> None:
        text = (QApplication.clipboard().text() or "").strip()
        if not text:
            QMessageBox.information(self, "Clipboard", "Clipboard is empty.")
            return
        self.on_add_from_clipboard(text)

    def reload(self) -> None:
        query = (self.search.text() or "").strip().lower()
        filter_mode = str(self.status_filter.currentData() or "all")
        sort_mode = str(self.sort_combo.currentData() or "updated_desc")

        with get_session() as session:
            rows = session.exec(select(Series)).all()

        total_rows = len(rows)

        if filter_mode != "all":
            rows = [row for row in rows if self._matches_filter(row, filter_mode)]

        if query:
            rows = [row for row in rows if query in " ".join([row.title or "", row.source or "", row.status or ""]).lower()]

        rows = self._sort_rows(rows, sort_mode)

        while self.flow.count():
            item = self.flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        noun = "comic" if len(rows) == 1 else "comics"
        if len(rows) == total_rows:
            self.count_label.setText(f"My Library ({len(rows)} {noun})")
        else:
            self.count_label.setText(f"My Library ({len(rows)}/{total_rows} {noun})")

        for series in rows:
            subtitle = f"{(series.source or '')}  •  {(series.status or '')}".strip(" •")
            notes = (series.notes or "").strip()
            current_chapter = (series.current_chapter or "").strip()

            card = ComicCard(
                title=series.title,
                subtitle=subtitle,
                notes=notes,
                current_chapter=f"Chapter {current_chapter}" if current_chapter else None,
                cover_path=series.cover_path,
                rating_10=series.rating,
                on_open=lambda url=series.url: self._open_url(url),
                on_open_private=lambda url=series.url: self._open_url_private(url),
                on_resume=lambda sid=series.id: self._resume_series(int(sid)),
                on_quick_increment=lambda sid=series.id: self._quick_increment(int(sid)),
                on_quick_edit=lambda sid=series.id: self._quick_edit(int(sid)),
                on_edit=lambda sid=series.id: self.on_edit(int(sid)),
                on_delete=lambda sid=series.id: self._delete_series(int(sid)),
            )
            self.flow.addWidget(card)

    def _delete_series(self, series_id: int) -> None:
        resp = QMessageBox.question(
            self,
            "Delete",
            "Delete this comic?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        with get_session() as session:
            series = session.get(Series, series_id)
            if series:
                delete_managed_cover(series.cover_path)
                session.delete(series)
                session.commit()
        self.reload()

    def _open_url(self, url: str | None) -> None:
        value = (url or "").strip()
        if not value:
            QMessageBox.information(self, "Open", "No URL saved for this comic.")
            return
        if not open_url(value):
            QMessageBox.warning(self, "Open", "Could not open the browser.")

    def _open_url_private(self, url: str | None) -> None:
        value = (url or "").strip()
        if not value:
            QMessageBox.information(self, "Open Private", "No URL saved for this comic.")
            return
        ok, error = open_url_private(value)
        if not ok:
            QMessageBox.warning(self, "Open Private", error)

    def _resume_series(self, series_id: int) -> None:
        with get_session() as session:
            series = session.get(Series, series_id)

        if not series:
            QMessageBox.warning(self, "Resume", "This comic no longer exists.")
            self.reload()
            return

        value = (series.current_url or "").strip() or (series.url or "").strip()
        if not value:
            QMessageBox.information(self, "Resume", "No current URL or main URL saved for this comic.")
            return

        if not open_url(value):
            QMessageBox.warning(self, "Resume", "Could not open the browser.")

    def _quick_increment(self, series_id: int) -> None:
        with get_session() as session:
            series = session.get(Series, series_id)
            if not series:
                QMessageBox.warning(self, "Quick Update", "This comic no longer exists.")
                self.reload()
                return

            next_chapter = self._increment_chapter_value(series.current_chapter)
            if next_chapter is not None:
                series.current_chapter = next_chapter
                series.updated_at = datetime.utcnow()
                session.add(series)
                session.commit()
                self.reload()
                return

        self._quick_edit(series_id)

    def _quick_edit(self, series_id: int) -> None:
        while True:
            with get_session() as session:
                series = session.get(Series, series_id)
                if not series:
                    QMessageBox.warning(self, "Quick Update", "This comic no longer exists.")
                    self.reload()
                    return

                dialog = QuickUpdateDialog(
                    title=series.title,
                    current_chapter=series.current_chapter,
                    current_url=series.current_url,
                    parent=self,
                )

            if dialog.exec() != QDialog.Accepted:
                return

            current_chapter, current_url = dialog.values()
            try:
                normalized_current_url = normalize_url(current_url)
            except ValueError as exc:
                QMessageBox.warning(self, "Quick Update", str(exc))
                continue

            with get_session() as session:
                series = session.get(Series, series_id)
                if not series:
                    QMessageBox.warning(self, "Quick Update", "This comic no longer exists.")
                    self.reload()
                    return

                series.current_chapter = current_chapter
                series.current_url = normalized_current_url
                series.updated_at = datetime.utcnow()
                session.add(series)
                session.commit()

            self.reload()
            return

    def _increment_chapter_value(self, current_chapter: str | None) -> str | None:
        raw = (current_chapter or "").strip()
        if not raw:
            return "1"

        match = re.search(r"(\d+)(?!.*\d)", raw)
        if not match:
            return None

        digits = match.group(1)
        incremented = str(int(digits) + 1).zfill(len(digits))
        return f"{raw[:match.start(1)]}{incremented}{raw[match.end(1):]}"

    def _matches_filter(self, series: Series, filter_mode: str) -> bool:
        if filter_mode in {"reading", "paused", "completed", "dropped"}:
            return (series.status or "") == filter_mode
        if filter_mode == "resume_ready":
            return bool((series.current_url or "").strip() or (series.url or "").strip())
        if filter_mode == "missing_cover":
            return not bool((series.cover_path or "").strip())
        return True

    def _sort_rows(self, rows: list[Series], sort_mode: str) -> list[Series]:
        if sort_mode == "created_desc":
            return sorted(rows, key=lambda row: (row.created_at, row.id or 0), reverse=True)
        if sort_mode == "title_asc":
            return sorted(rows, key=lambda row: ((row.title or "").lower(), -(row.id or 0)))
        if sort_mode == "title_desc":
            return sorted(rows, key=lambda row: ((row.title or "").lower(), row.id or 0), reverse=True)
        if sort_mode == "rating_desc":
            return sorted(rows, key=lambda row: (row.rating or 0, row.updated_at, row.id or 0), reverse=True)
        return sorted(rows, key=lambda row: (row.updated_at, row.id or 0), reverse=True)

    def _open_data_dir(self) -> None:
        if not open_local_path(get_data_dir()):
            QMessageBox.warning(self, "Open Data Folder", "Could not open the app data folder.")

    def _create_backup(self) -> None:
        default_path = get_backups_dir() / "ComicVault_Backup.zip"
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Create Backup",
            str(default_path),
            "Zip files (*.zip)",
        )
        if not target:
            return

        try:
            output = create_backup_archive(target)
        except Exception as exc:
            QMessageBox.critical(self, "Backup failed", str(exc))
            return

        QMessageBox.information(self, "Backup created", f"Backup saved to:\n{output}")

    def _restore_backup(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Backup",
            str(get_backups_dir()),
            "Zip files (*.zip)",
        )
        if not source:
            return

        resp = QMessageBox.question(
            self,
            "Restore Backup",
            "Restore will replace the current library and covers. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            auto_backup = restore_backup_archive(source)
        except Exception as exc:
            QMessageBox.critical(self, "Restore failed", str(exc))
            return

        self.reload()
        QMessageBox.information(
            self,
            "Restore complete",
            f"Backup restored successfully.\nA safety backup was created at:\n{auto_backup}",
        )

    def _export_json(self) -> None:
        default_path = get_exports_dir() / "ComicVault_Export.json"
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON",
            str(default_path),
            "JSON files (*.json)",
        )
        if not target:
            return

        try:
            output = export_library_json(target)
        except Exception as exc:
            QMessageBox.critical(self, "Export JSON failed", str(exc))
            return

        QMessageBox.information(self, "Export JSON complete", f"Export saved to:\n{output}")

    def _import_json(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Import JSON",
            str(get_exports_dir()),
            "JSON files (*.json)",
        )
        if not source:
            return

        resp = QMessageBox.question(
            self,
            "Import JSON",
            "Import JSON will replace the current library records. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            result = import_library_json(source, overwrite=True)
        except Exception as exc:
            QMessageBox.critical(self, "Import JSON failed", str(exc))
            return

        self.reload()
        backup_note = f"\nSafety backup:\n{result.backup_path}" if result.backup_path else ""
        QMessageBox.information(
            self,
            "Import JSON complete",
            (
                f"Imported: {result.imported_count}\n"
                f"Skipped: {result.skipped_count}\n"
                f"Duplicates skipped: {result.duplicate_count}\n"
                f"Invalid rows skipped: {result.invalid_count}\n"
                f"Missing covers cleared: {result.missing_cover_count}"
                f"{backup_note}"
            ),
        )
