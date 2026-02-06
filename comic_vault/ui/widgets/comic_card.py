from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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
        on_open: Callable[[], None],          # NEW
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
            self.cover.setPixmap(pix.scaled(self.cover.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        else:
            self.cover.setText("No Image")

        # Overlay
        self.overlay = QWidget(self.cover)
        self.overlay.setObjectName("Overlay")
        self.overlay.setGeometry(0, 0, 300, 420)
        self.overlay.hide()

        overlay_layout = QHBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(12)

        open_btn = QPushButton("↗")          # NEW
        edit_btn = QPushButton("✎")
        del_btn = QPushButton("🗑")

        open_btn.setObjectName("OverlayBtn")  # NEW
        edit_btn.setObjectName("OverlayBtn")
        del_btn.setObjectName("OverlayBtnDanger")

        # IMPORTANT: swallow checked(bool)
        open_btn.clicked.connect(lambda _=False: on_open())
        edit_btn.clicked.connect(lambda _=False: on_edit())
        del_btn.clicked.connect(lambda _=False: on_delete())

        overlay_layout.addWidget(open_btn)
        overlay_layout.addWidget(edit_btn)
        overlay_layout.addWidget(del_btn)

        # Info block (giữ như bạn đang dùng)
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)

        t = QLabel(title)
        t.setObjectName("H2")
        t.setWordWrap(True)

        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        sub.setWordWrap(True)

        chap_text = (current_chapter or "").strip()
        chap = QLabel(f"Current: {chap_text}" if chap_text else "Current: -")  # NEW
        chap.setObjectName("Muted")
        chap.setWordWrap(True)

        n = QLabel(notes)
        n.setObjectName("Muted")
        n.setWordWrap(True)

        stars = QLabel(self._rating_to_stars(rating_10))
        stars.setObjectName("Stars")

        info_layout.addWidget(t)
        info_layout.addWidget(sub)
        info_layout.addWidget(chap)   # NEW
        info_layout.addWidget(n)
        info_layout.addWidget(stars)

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
        p = Path(cover_path)
        if not p.exists() or not p.is_file():
            return None
        pix = QPixmap(str(p))
        return pix if not pix.isNull() else None

    def _rating_to_stars(self, rating_10: Optional[int]) -> str:
        if not rating_10:
            return "☆☆☆☆☆"
        r = max(1, min(10, int(rating_10)))
        stars = int(round(r / 2))
        return "★" * stars + "☆" * (5 - stars)
