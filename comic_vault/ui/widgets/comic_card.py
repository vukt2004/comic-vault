from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from comic_vault.data.storage import resolve_app_path


class ComicCard(QFrame):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str,
        notes: str,
        current_chapter: Optional[str],
        cover_path: Optional[str],
        rating_10: Optional[int],
        on_open: Callable[[], None],
        on_open_private: Callable[[], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ComicCard")
        self.setFixedWidth(300)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.cover = QLabel()
        self.cover.setFixedSize(QSize(300, 420))
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setObjectName("Cover")

        pix = self._load_cover(cover_path)
        if pix:
            self.cover.setPixmap(
                pix.scaled(self.cover.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            )
        else:
            self.cover.setText("No Image")

        self.overlay = QWidget(self.cover)
        self.overlay.setObjectName("Overlay")
        self.overlay.setGeometry(0, 0, 300, 420)
        self.overlay.hide()

        overlay_layout = QHBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(10)

        open_btn = QPushButton("Open")
        private_btn = QPushButton("P")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Del")

        open_btn.setObjectName("OverlayBtn")
        private_btn.setObjectName("OverlayBtn")
        edit_btn.setObjectName("OverlayBtn")
        del_btn.setObjectName("OverlayBtnDanger")

        open_btn.setToolTip("Open in browser")
        private_btn.setToolTip("Open in private window")
        edit_btn.setToolTip("Edit")
        del_btn.setToolTip("Delete")

        open_btn.clicked.connect(lambda _=False: on_open())
        private_btn.clicked.connect(lambda _=False: on_open_private())
        edit_btn.clicked.connect(lambda _=False: on_edit())
        del_btn.clicked.connect(lambda _=False: on_delete())

        overlay_layout.addWidget(open_btn)
        overlay_layout.addWidget(private_btn)
        overlay_layout.addWidget(edit_btn)
        overlay_layout.addWidget(del_btn)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("H2")
        title_label.setWordWrap(True)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Muted")
        subtitle_label.setWordWrap(True)

        chapter_text = (current_chapter or "").strip()
        chapter_label = QLabel(f"Current: {chapter_text}" if chapter_text else "Current: -")
        chapter_label.setObjectName("Muted")
        chapter_label.setWordWrap(True)

        notes_label = QLabel(notes)
        notes_label.setObjectName("Muted")
        notes_label.setWordWrap(True)

        stars_label = QLabel(self._rating_to_stars(rating_10))
        stars_label.setObjectName("Stars")

        info_layout.addWidget(title_label)
        info_layout.addWidget(subtitle_label)
        info_layout.addWidget(chapter_label)
        info_layout.addWidget(notes_label)
        info_layout.addWidget(stars_label)

        outer.addWidget(self.cover)
        outer.addWidget(info)

    def enterEvent(self, event) -> None:
        self.overlay.show()
        return super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.overlay.hide()
        return super().leaveEvent(event)

    def _load_cover(self, cover_path: Optional[str]) -> Optional[QPixmap]:
        if not cover_path:
            return None
        resolved = resolve_app_path(cover_path)
        if resolved is None:
            return None
        path = Path(resolved)
        if not path.exists() or not path.is_file():
            return None
        pix = QPixmap(str(path))
        return pix if not pix.isNull() else None

    def _rating_to_stars(self, rating_10: Optional[int]) -> str:
        if not rating_10:
            return "-----"
        rating = max(1, min(10, int(rating_10)))
        stars = int(round(rating / 2))
        return "*" * stars + "-" * (5 - stars)
