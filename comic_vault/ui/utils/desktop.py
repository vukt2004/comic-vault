from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_local_path(path: str | Path) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

