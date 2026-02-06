from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from sqlmodel import select

from comic_vault.data.db import get_session
from comic_vault.data.models import Series
from comic_vault.ui.widgets.comic_card import ComicCard
from comic_vault.ui.widgets.flow_layout import FlowLayout
import webbrowser


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

        # ===== Top bar =====
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

        btn_add = QPushButton("Add Comic")
        btn_add.setObjectName("Ghost")
        btn_add.clicked.connect(self.on_add)

        top.addWidget(btn_library)
        top.addWidget(btn_paste_add)
        top.addWidget(btn_add)

        root.addWidget(top_host)

        # ===== Header + search =====
        header = QHBoxLayout()
        header.setSpacing(12)

        self.count_label = QLabel("My Library (0 comic)")
        self.count_label.setObjectName("H1")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title / source / status ...")
        self.search.textChanged.connect(self.reload)

        header.addWidget(self.count_label)
        header.addStretch(1)
        header.addWidget(self.search)

        root.addLayout(header)

        # ===== Scroll + grid =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.grid_host = QWidget()
        self.flow = FlowLayout(self.grid_host, spacing=16)
        self.grid_host.setLayout(self.flow)

        self.scroll.setWidget(self.grid_host)
        root.addWidget(self.scroll, 1)

        self.reload()

    def _paste_and_add(self) -> None:
        txt = (QApplication.clipboard().text() or "").strip()
        if not txt:
            QMessageBox.information(self, "Clipboard", "Clipboard is empty.")
            return
        self.on_add_from_clipboard(txt)

    def reload(self) -> None:
        q = (self.search.text() or "").strip().lower()

        with get_session() as session:
            rows = session.exec(select(Series).order_by(Series.updated_at.desc(), Series.id.desc())).all()

        if q:
            def match(s: Series) -> bool:
                blob = " ".join([s.title or "", s.source or "", s.status or ""]).lower()
                return q in blob
            rows = [r for r in rows if match(r)]

        while self.flow.count():
            item = self.flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self.count_label.setText(f"My Library ({len(rows)} comic)")

        for s in rows:
            subtitle = f"{(s.source or '')}  •  {(s.status or '')}".strip(" •")
            notes = (s.notes or "").strip()

            card = ComicCard(
                title=s.title,
                subtitle=subtitle,
                notes=notes,
                current_chapter= "Chapter " + s.current_chapter,  # NEW
                cover_path=s.cover_path,
                rating_10=s.rating,
                on_open=lambda url=s.url: self._open_url(url),
                on_edit=lambda sid=s.id: self.on_edit(int(sid)),
                on_delete=lambda sid=s.id: self._delete_series(int(sid)),
            )
            self.flow.addWidget(card)

    def _delete_series(self, series_id: int) -> None:
        resp = QMessageBox.question(self, "Delete", "Delete this comic?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        with get_session() as session:
            s = session.get(Series, series_id)
            if s:
                session.delete(s)
                session.commit()
        self.reload()
    def _open_url(self, url: str | None) -> None:
        u = (url or "").strip()
        if not u:
            QMessageBox.information(self, "Open", "No URL saved for this comic.")
            return
        webbrowser.open(u)
