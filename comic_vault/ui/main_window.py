from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from comic_vault.data.db import init_db
from comic_vault.data.integrity import format_integrity_report, run_integrity_check
from comic_vault.data.storage import get_backups_dir, get_data_dir
from comic_vault.ui.pages.library_page import LibraryPage
from comic_vault.ui.pages.editor_page import EditorPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Comic Vault")
        self.resize(1200, 750)

        self._integrity_report = None

        try:
            init_db()
            self._integrity_report = run_integrity_check()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Startup Error",
                (
                    f"The library could not be initialized.\n\n{exc}\n\n"
                    f"Data folder:\n{get_data_dir()}\n\n"
                    f"Backups folder:\n{get_backups_dir()}"
                ),
            )
            raise

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.editor_page = EditorPage(
            on_back=self.go_library,
            on_saved=self.go_library_refresh,
        )

        self.library_page = LibraryPage(
            on_add=self.go_add,
            on_edit=self.go_edit,
            on_add_from_clipboard=self.go_add_from_clipboard,
        )

        self.stack.addWidget(self.library_page)
        self.stack.addWidget(self.editor_page)

        self.go_library()
        QTimer.singleShot(0, self._show_integrity_notice)

    def go_library(self) -> None:
        self.stack.setCurrentWidget(self.library_page)

    def go_library_refresh(self) -> None:
        self.library_page.reload()
        self.go_library()

    def go_add(self) -> None:
        self.editor_page.load_series(None)
        self.stack.setCurrentWidget(self.editor_page)

    def go_add_with_url(self, url: Optional[str]) -> None:
        self.editor_page.load_series(None)
        if url:
            self.editor_page.set_url(url)
        self.stack.setCurrentWidget(self.editor_page)

    def go_add_from_clipboard(self, url: Optional[str]) -> None:
        self.go_add_with_url(url)

    def go_edit(self, series_id: int) -> None:
        self.editor_page.load_series(series_id)
        self.stack.setCurrentWidget(self.editor_page)

    def _show_integrity_notice(self) -> None:
        if not self._integrity_report or not self._integrity_report.has_issues:
            return
        QMessageBox.warning(
            self,
            "Library Integrity Check",
            format_integrity_report(self._integrity_report),
        )
