from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class QuickUpdateDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        current_chapter: Optional[str],
        current_url: Optional[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quick Update")
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(title)
        header.setObjectName("H2")
        header.setWordWrap(True)
        layout.addWidget(header)

        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.chapter_input = QLineEdit()
        self.chapter_input.setText((current_chapter or "").strip())

        self.url_input = QLineEdit()
        self.url_input.setText((current_url or "").strip())

        form.addRow("Current Chapter", self.chapter_input)
        form.addRow("Current URL", self.url_input)
        layout.addWidget(form_host)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str | None, str | None]:
        chapter = (self.chapter_input.text() or "").strip() or None
        current_url = (self.url_input.text() or "").strip() or None
        return chapter, current_url
