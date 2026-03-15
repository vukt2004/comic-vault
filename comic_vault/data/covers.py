from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from comic_vault.data.storage import ensure_data_dirs, get_covers_dir, resolve_app_path


MAX_COVER_WIDTH = 900
MAX_COVER_HEIGHT = 1200


def _normalize_cover_image(image: QImage) -> QImage:
    if image.width() > MAX_COVER_WIDTH or image.height() > MAX_COVER_HEIGHT:
        image = image.scaled(
            MAX_COVER_WIDTH,
            MAX_COVER_HEIGHT,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    return image


def save_cover_image(image: QImage, *, series_id: int) -> str:
    ensure_data_dirs()

    if image.isNull():
        raise ValueError("Cover image is empty.")

    image = _normalize_cover_image(image)

    rel_path = Path("covers") / f"series_{series_id}_{uuid4().hex[:8]}.webp"
    target = get_covers_dir() / rel_path.name

    if not image.save(str(target), "WEBP", quality=85):
        raise ValueError("Could not save cover into managed storage.")

    return rel_path.as_posix()


def import_cover(source_path: str, *, series_id: int) -> str:
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Cover file not found: {source}")

    image = QImage(str(source))
    if image.isNull():
        raise ValueError("Selected file is not a supported image.")

    return save_cover_image(image, series_id=series_id)


def delete_managed_cover(value: str | None) -> None:
    path = resolve_app_path(value)
    if path is None:
        return

    covers_dir = get_covers_dir().resolve()

    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return

    if covers_dir not in resolved.parents:
        return

    if resolved.exists() and resolved.is_file():
        resolved.unlink()
