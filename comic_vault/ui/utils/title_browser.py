from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QLabel

from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView


@dataclass(frozen=True)
class BrowserTitleResult:
    ok: bool
    title: str = ""
    final_url: str = ""
    error: str = ""


class TitleBrowserDialog(QDialog):
    """
    Interactive browser dialog for sites that block headless/background loads.
    User can solve challenges; then we read document.title.
    """

    def __init__(self, url: str, on_done: Callable[[BrowserTitleResult], None], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fetch title (Browser)")
        self.resize(1000, 700)

        self._on_done = on_done
        self._url = url

        layout = QVBoxLayout(self)

        hint = QLabel("If the site shows a verification / captcha, complete it, then click “Use Title”.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignLeft)
        layout.addWidget(hint)

        # Use default profile so it behaves like a real browser (cookies, etc.)
        profile = QWebEngineProfile.defaultProfile()
        if hasattr(profile, "setHttpUserAgent"):
            profile.setHttpUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )

        self.view = QWebEngineView()
        self.view.setPage(profile.newPage()) if hasattr(profile, "newPage") else None  # safe no-op on older versions
        layout.addWidget(self.view, 1)

        btn_row = QHBoxLayout()
        self.btn_use = QPushButton("Use Title")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_use)
        layout.addLayout(btn_row)

        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_use.clicked.connect(self._use_title)

        self.view.load(QUrl(url))

    def _cancel(self) -> None:
        self._on_done(BrowserTitleResult(ok=False, error="Cancelled"))
        self.close()

    def _use_title(self) -> None:
        page = self.view.page()
        if not page:
            self._on_done(BrowserTitleResult(ok=False, error="No web page"))
            self.close()
            return

        def got_title(title):
            t = (title or "").strip()
            final_url = self.view.url().toString()
            if not t:
                self._on_done(BrowserTitleResult(ok=False, final_url=final_url, error="Title not found"))
            else:
                self._on_done(BrowserTitleResult(ok=True, title=t, final_url=final_url))
            self.close()

        page.runJavaScript("document.title", got_title)
