from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QFrame, 
    QHBoxLayout, 
    QLabel, 
    QPushButton, 
    QVBoxLayout, 
    QWidget,
    QMenu,
)

from comic_vault.data.storage import resolve_app_path


class ComicCard(QFrame):
    def __init__(
        self,
        *,
        title: str,
        subtitle: str,
        status: str,
        notes: str,
        current_chapter: Optional[str],
        cover_path: Optional[str],
        rating_10: Optional[int],
        on_open: Callable[[], None],
        on_open_private: Callable[[], None],
        on_resume: Callable[[], None],
        on_quick_increment: Callable[[], None],
        on_quick_edit: Callable[[], None],
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

        # Cover section with corner menu
        cover_container = QWidget()
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(0)

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

        # Create corner menu button for actions
        self.menu_btn = QPushButton("⋮")
        self.menu_btn.setObjectName("CornerMenuBtn")
        self.menu_btn.setMaximumSize(36, 36)
        self.menu_btn.setToolTip("Actions menu")
        
        menu = QMenu(self.menu_btn)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0F1A2B;
                color: #E6EDF7;
                border: 1px solid #20324C;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(123, 58, 237, 0.2);
            }
            QMenu::item:pressed {
                background-color: rgba(123, 58, 237, 0.3);
            }
        """)
        
        action_open = menu.addAction("🌐 Open in Browser")
        action_open.triggered.connect(lambda: on_open())
        
        action_private = menu.addAction("🔒 Private Window")
        action_private.triggered.connect(lambda: on_open_private())
        
        menu.addSeparator()
        
        action_resume = menu.addAction("▶ Resume Reading")
        action_resume.triggered.connect(lambda: on_resume())
        
        action_increment = menu.addAction("+1 Chapter")
        action_increment.triggered.connect(lambda: on_quick_increment())
        
        menu.addSeparator()
        
        action_edit = menu.addAction("✏️ Edit")
        action_edit.triggered.connect(lambda: on_edit())
        
        action_delete = menu.addAction("🗑️ Delete")
        action_delete.triggered.connect(lambda: on_delete())
        
        self.menu_btn.setMenu(menu)
        
        # Position menu button in top right corner
        cover_top_layout = QHBoxLayout()
        cover_top_layout.setContentsMargins(8, 8, 8, 0)
        cover_top_layout.addStretch(1)
        cover_top_layout.addWidget(self.menu_btn)
        
        cover_wrapper = QWidget()
        cover_wrapper_layout = QVBoxLayout(cover_wrapper)
        cover_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        cover_wrapper_layout.setSpacing(0)
        cover_wrapper_layout.addLayout(cover_top_layout)
        cover_wrapper_layout.addWidget(self.cover)
        
        cover_layout.addWidget(cover_wrapper)

        # Info section
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("H2")
        title_label.setWordWrap(True)

        # Source and Status row
        source_status_layout = QHBoxLayout()
        source_status_layout.setSpacing(8)
        source_status_layout.setContentsMargins(0, 0, 0, 0)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Muted")
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #A6B3C7; font-size: 12px;")

        # Status badge
        status_label = QLabel(status.capitalize())
        status_label.setObjectName("StatusBadge")
        status_color = self._get_status_color(status)
        status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
            }}
        """)

        source_status_layout.addWidget(subtitle_label, 1)
        source_status_layout.addWidget(status_label, 0, Qt.AlignRight)

        chapter_text = (current_chapter or "").strip()
        if chapter_text:
            chapter_label = QLabel(f"📖 Ch. {chapter_text}")
            chapter_label.setObjectName("Muted")
            chapter_label.setWordWrap(True)
            chapter_label.setStyleSheet("color: #A6B3C7; font-size: 12px; margin-top: 4px;")

        notes_label = QLabel(notes)
        notes_label.setObjectName("Muted")
        notes_label.setWordWrap(True)
        notes_label.setStyleSheet("color: #A6B3C7; font-size: 12px;")

        stars_label = QLabel(self._rating_to_stars(rating_10))
        stars_label.setObjectName("Stars")

        info_layout.addWidget(title_label)
        info_layout.addLayout(source_status_layout)
        if chapter_text:
            info_layout.addWidget(chapter_label)
        if notes:
            info_layout.addWidget(notes_label)
        info_layout.addWidget(stars_label)
        info_layout.addStretch(1)

        outer.addWidget(cover_container)
        outer.addWidget(info)

    def _get_status_color(self, status: str) -> str:
        """Return appropriate color for status badge"""
        colors = {
            "reading": "#7C3AED",      # Purple
            "paused": "#F59E0B",       # Amber
            "completed": "#22C55E",    # Green
            "dropped": "#EF4444",      # Red
        }
        return colors.get(status.lower(), "#7C3AED")

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
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("H2")
        title_label.setWordWrap(True)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Muted")
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #A6B3C7; font-size: 12px;")

        chapter_text = (current_chapter or "").strip()
        chapter_label = QLabel(f"📖 {chapter_text}" if chapter_text else "")
        chapter_label.setObjectName("Muted")
        chapter_label.setWordWrap(True)
        chapter_label.setStyleSheet("color: #A6B3C7; font-size: 12px; margin-top: 4px;")

        notes_label = QLabel(notes)
        notes_label.setObjectName("Muted")
        notes_label.setWordWrap(True)
        notes_label.setStyleSheet("color: #A6B3C7; font-size: 12px;")

        stars_label = QLabel(self._rating_to_stars(rating_10))
        stars_label.setObjectName("Stars")

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 6, 0, 0)
        actions_layout.setSpacing(8)

        resume_btn = QPushButton("▶ Resume")
        resume_btn.setObjectName("Primary")
        resume_btn.clicked.connect(lambda _=False: on_resume())

        plus_btn = QPushButton("+1")
        plus_btn.setObjectName("Ghost")
        plus_btn.clicked.connect(lambda _=False: on_quick_increment())

        quick_btn = QPushButton("⚡")
        quick_btn.setObjectName("Ghost")
        quick_btn.setToolTip("Quick edit")
        quick_btn.clicked.connect(lambda _=False: on_quick_edit())

        actions_layout.addWidget(resume_btn, 1)
        actions_layout.addWidget(plus_btn)
        actions_layout.addWidget(quick_btn)

        info_layout.addWidget(title_label)
        info_layout.addWidget(subtitle_label)
        if chapter_text:
            info_layout.addWidget(chapter_label)
        if notes:
            info_layout.addWidget(notes_label)
        info_layout.addWidget(stars_label)
        info_layout.addStretch(1)
        info_layout.addWidget(actions)

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
            return "⭐ Not rated"
        rating = max(1, min(10, int(rating_10)))
        stars = int(round(rating / 2))
        return "⭐ " * stars + "☆ " * (5 - stars)
