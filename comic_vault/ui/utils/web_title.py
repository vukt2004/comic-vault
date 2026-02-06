from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings


@dataclass(frozen=True)
class TitleResult:
    ok: bool
    title: str = ""
    final_url: str = ""
    error: str = ""


class WebTitleResolver(QObject):
    """
    Resolve document.title using QtWebEngine (browser-like), async.

    Notes about compatibility:
    - Some PySide6 versions don't expose QWebEngineProfile.setOffTheRecord().
      We therefore avoid calling it and use a safe profile initialization path.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # ---- Profile: choose a safe, version-compatible option ----
        # Prefer an "off-the-record" profile if available; otherwise fall back to defaultProfile.
        profile = None

        # Some versions expose offTheRecordProfile() as a @staticmethod
        if hasattr(QWebEngineProfile, "offTheRecordProfile"):
            try:
                profile = QWebEngineProfile.offTheRecordProfile()
            except Exception:
                profile = None

        if profile is None:
            # Default profile is always available across versions
            profile = QWebEngineProfile.defaultProfile()

        self._profile = profile

        # Set UA if supported
        if hasattr(self._profile, "setHttpUserAgent"):
            self._profile.setHttpUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )

        # Optional: make it a bit "clean" even if using default profile
        # (won't crash if not supported)
        if hasattr(self._profile, "clearHttpCache"):
            try:
                self._profile.clearHttpCache()
            except Exception:
                pass

        cookie_store = getattr(self._profile, "cookieStore", None)
        if callable(cookie_store):
            try:
                store = self._profile.cookieStore()
                if hasattr(store, "deleteAllCookies"):
                    store.deleteAllCookies()
            except Exception:
                pass

        self._page = QWebEnginePage(self._profile, self)

        s = self._page.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._done = False
        self._callback: Optional[Callable[[TitleResult], None]] = None

        self._page.loadFinished.connect(self._on_load_finished)

    def resolve(self, url: str, callback: Callable[[TitleResult], None], timeout_ms: int = 12000) -> None:
        self._done = False
        self._callback = callback

        qurl = QUrl(url.strip())
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            self._finish(TitleResult(ok=False, error="Invalid URL"))
            return

        self._timer.start(timeout_ms)
        self._page.load(qurl)

    def _on_timeout(self) -> None:
        self._finish(TitleResult(ok=False, error="Timeout while loading page"))

    def _on_load_finished(self, ok: bool) -> None:
        if self._done:
            return

        if not ok:
            self._finish(
                TitleResult(
                    ok=False,
                    final_url=self._page.url().toString(),
                    error="Page failed to load (blocked / network / SSL / WAF)",
                )
            )
            return

        self._page.runJavaScript("document.title", self._on_title_js)

    def _on_title_js(self, value) -> None:
        if self._done:
            return

        title = (value or "").strip()
        final_url = self._page.url().toString()

        if title:
            self._finish(TitleResult(ok=True, title=title, final_url=final_url))
            return

        self._page.runJavaScript(
            "(() => { const h = document.querySelector('h1'); return h ? h.textContent : ''; })()",
            lambda v: self._finish(
                TitleResult(
                    ok=bool((v or "").strip()),
                    title=(v or "").strip(),
                    final_url=final_url,
                    error="" if (v or "").strip() else "Title not found",
                )
            ),
        )

    def _finish(self, result: TitleResult) -> None:
        if self._done:
            return
        self._done = True

        if self._timer.isActive():
            self._timer.stop()

        cb = self._callback
        self._callback = None
        if cb:
            cb(result)
