from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


@dataclass(frozen=True)
class RemoteImageResult:
    ok: bool
    image_url: str = ""
    image_data: bytes = b""
    error: str = ""


class RemoteImageLoader(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._reply: Optional[QNetworkReply] = None
        self._callback: Optional[Callable[[RemoteImageResult], None]] = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def download(
        self,
        image_url: str,
        callback: Callable[[RemoteImageResult], None],
        *,
        referer: str | None = None,
        timeout_ms: int = 15000,
    ) -> None:
        self._cleanup_reply()
        self._callback = callback

        url = QUrl(image_url.strip())
        if not url.isValid() or url.scheme() not in ("http", "https"):
            self._finish(RemoteImageResult(ok=False, error="Invalid image URL"))
            return

        request = QNetworkRequest(url)
        request.setRawHeader(
            b"User-Agent",
            (
                b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                b"AppleWebKit/537.36 (KHTML, like Gecko) "
                b"Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        if referer:
            request.setRawHeader(b"Referer", referer.encode("utf-8", "ignore"))

        if hasattr(QNetworkRequest, "RedirectPolicyAttribute") and hasattr(QNetworkRequest, "NoLessSafeRedirectPolicy"):
            request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)

        self._timer.start(timeout_ms)
        self._reply = self._network.get(request)
        self._reply.finished.connect(self._on_download_finished)

    def _on_timeout(self) -> None:
        if self._reply is not None:
            self._reply.abort()
        self._finish(RemoteImageResult(ok=False, error="Timeout while downloading image"))

    def _on_download_finished(self) -> None:
        reply = self._reply
        self._reply = None
        if reply is None:
            return

        try:
            if reply.error() != QNetworkReply.NoError:
                self._finish(
                    RemoteImageResult(
                        ok=False,
                        image_url=reply.url().toString(),
                        error=reply.errorString() or "Image download failed",
                    )
                )
                return

            payload = bytes(reply.readAll())
            if not payload:
                self._finish(
                    RemoteImageResult(
                        ok=False,
                        image_url=reply.url().toString(),
                        error="Downloaded image is empty",
                    )
                )
                return

            self._finish(
                RemoteImageResult(
                    ok=True,
                    image_url=reply.url().toString(),
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

    def _finish(self, result: RemoteImageResult) -> None:
        if self._timer.isActive():
            self._timer.stop()

        callback = self._callback
        self._callback = None
        if callback:
            callback(result)
