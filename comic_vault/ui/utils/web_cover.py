from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings


INITIAL_PROBE_DELAY_MS = 600
PROBE_INTERVAL_MS = 500
MAX_PROBE_ATTEMPTS = 12


COVER_CANDIDATES_JS = """
(() => {
  const seen = new Set();
  const candidates = [];

  const toAbsolute = (value) => {
    if (!value || typeof value !== "string") return "";
    try {
      return new URL(value, document.baseURI).href;
    } catch (err) {
      return "";
    }
  };

  const push = (value, score) => {
    const url = toAbsolute(value);
    if (!url || seen.has(url) || !/^https?:/i.test(url)) return;
    seen.add(url);
    candidates.push({ url, score });
  };

  const collectJsonImages = (value, score) => {
    if (!value) return;
    if (typeof value === "string") {
      push(value, score);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => collectJsonImages(item, score));
      return;
    }
    if (typeof value === "object") {
      if (typeof value.url === "string") push(value.url, score);
      if (typeof value.contentUrl === "string") push(value.contentUrl, score);
      if (value.image) collectJsonImages(value.image, score);
    }
  };

  document.querySelectorAll('meta[property="og:image"], meta[property="og:image:url"]').forEach((el) => {
    push(el.content, 1000000);
  });
  document.querySelectorAll('meta[name="twitter:image"], meta[name="twitter:image:src"]').forEach((el) => {
    push(el.content, 900000);
  });
  document.querySelectorAll('link[rel="image_src"]').forEach((el) => {
    push(el.href, 800000);
  });

  document.querySelectorAll('script[type="application/ld+json"]').forEach((el) => {
    try {
      const parsed = JSON.parse(el.textContent);
      collectJsonImages(parsed, 700000);
    } catch (err) {
      // Ignore broken JSON-LD blocks.
    }
  });

  document.querySelectorAll("img, [data-src], [data-lazy-src], [data-original], [data-url]").forEach((img) => {
    const value =
      img.currentSrc ||
      img.getAttribute("src") ||
      img.getAttribute("data-src") ||
      img.getAttribute("data-lazy-src") ||
      img.getAttribute("data-original") ||
      img.getAttribute("data-url");
    if (!value) return;

    let score = (img.naturalWidth || img.width || 0) * (img.naturalHeight || img.height || 0);
    const blob = [img.alt, img.className, img.id].join(" ").toLowerCase();
    if (/cover|poster|thumbnail|thumb|artwork/.test(blob)) score += 250000;
    if (/logo|avatar|icon|sprite|badge/.test(blob)) score -= 250000;
    push(value, score);
  });

  return candidates
    .sort((a, b) => b.score - a.score)
    .map((item) => item.url)
    .slice(0, 10);
})()
"""


@dataclass(frozen=True)
class CoverResult:
    ok: bool
    image_url: str = ""
    final_url: str = ""
    image_data: bytes = b""
    error: str = ""


class WebCoverResolver(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        profile = None
        if hasattr(QWebEngineProfile, "offTheRecordProfile"):
            try:
                profile = QWebEngineProfile.offTheRecordProfile()
            except Exception:
                profile = None

        if profile is None:
            profile = QWebEngineProfile.defaultProfile()

        self._profile = profile
        if hasattr(self._profile, "setHttpUserAgent"):
            self._profile.setHttpUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )

        self._page = QWebEnginePage(self._profile, self)
        settings = self._page.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)

        self._network = QNetworkAccessManager(self)
        self._reply: Optional[QNetworkReply] = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._probe_timer = QTimer(self)
        self._probe_timer.setSingleShot(True)
        self._probe_timer.timeout.connect(self._probe_cover_candidates)

        self._done = False
        self._probe_attempts = 0
        self._callback: Optional[Callable[[CoverResult], None]] = None

        self._page.loadFinished.connect(self._on_load_finished)

    def resolve(self, url: str, callback: Callable[[CoverResult], None], timeout_ms: int = 18000) -> None:
        self._cleanup_reply()
        self._done = False
        self._probe_attempts = 0
        self._callback = callback

        qurl = QUrl(url.strip())
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            self._finish(CoverResult(ok=False, error="Invalid URL"))
            return

        self._timer.start(timeout_ms)
        self._page.load(qurl)

    def _on_timeout(self) -> None:
        if self._reply is not None:
            self._reply.abort()
        self._finish(CoverResult(ok=False, error="Timeout while fetching cover"))

    def _on_load_finished(self, ok: bool) -> None:
        if self._done:
            return

        if not ok:
            self._finish(
                CoverResult(
                    ok=False,
                    final_url=self._page.url().toString(),
                    error="Page failed to load (blocked / network / SSL / WAF)",
                )
            )
            return

        self._probe_timer.start(INITIAL_PROBE_DELAY_MS)

    def _probe_cover_candidates(self) -> None:
        if self._done:
            return
        self._probe_attempts += 1
        self._page.runJavaScript(COVER_CANDIDATES_JS, self._on_cover_candidates)

    def _on_cover_candidates(self, value) -> None:
        if self._done:
            return

        candidates = [item for item in (value or []) if isinstance(item, str) and item.strip()]
        if not candidates:
            if self._probe_attempts < MAX_PROBE_ATTEMPTS and self._timer.isActive():
                self._probe_timer.start(PROBE_INTERVAL_MS)
                return

            self._finish(
                CoverResult(
                    ok=False,
                    final_url=self._page.url().toString(),
                    error="No cover image found on this page",
                )
            )
            return

        self._download_image(candidates[0])

    def _download_image(self, image_url: str) -> None:
        request = QNetworkRequest(QUrl(image_url))
        request.setRawHeader(
            b"User-Agent",
            (
                b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                b"AppleWebKit/537.36 (KHTML, like Gecko) "
                b"Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        referer = self._page.url().toString()
        if referer:
            request.setRawHeader(b"Referer", referer.encode("utf-8", "ignore"))

        if hasattr(QNetworkRequest, "RedirectPolicyAttribute") and hasattr(QNetworkRequest, "NoLessSafeRedirectPolicy"):
            request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)

        self._reply = self._network.get(request)
        self._reply.finished.connect(self._on_download_finished)

    def _on_download_finished(self) -> None:
        reply = self._reply
        self._reply = None
        if reply is None or self._done:
            return

        try:
            if reply.error() != QNetworkReply.NoError:
                self._finish(
                    CoverResult(
                        ok=False,
                        image_url=reply.url().toString(),
                        final_url=self._page.url().toString(),
                        error=reply.errorString() or "Image download failed",
                    )
                )
                return

            payload = bytes(reply.readAll())
            if not payload:
                self._finish(
                    CoverResult(
                        ok=False,
                        image_url=reply.url().toString(),
                        final_url=self._page.url().toString(),
                        error="Downloaded image is empty",
                    )
                )
                return

            self._finish(
                CoverResult(
                    ok=True,
                    image_url=reply.url().toString(),
                    final_url=self._page.url().toString(),
                    image_data=payload,
                )
            )
        finally:
            reply.deleteLater()

    def _cleanup_reply(self) -> None:
        if self._reply is None:
            return
        try:
            self._reply.abort()
        except Exception:
            pass
        self._reply.deleteLater()
        self._reply = None

    def _finish(self, result: CoverResult) -> None:
        if self._done:
            return
        self._done = True

        if self._timer.isActive():
            self._timer.stop()
        if self._probe_timer.isActive():
            self._probe_timer.stop()

        self._cleanup_reply()

        callback = self._callback
        self._callback = None
        if callback:
            callback(result)
