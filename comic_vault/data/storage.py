from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_DIR_NAME = "ComicVault"
LEGACY_DB_PATH = Path(__file__).resolve().parent / "comic_vault.db"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_RESOLVED_DATA_DIR: Path | None = None


def get_data_dir() -> Path:
    global _RESOLVED_DATA_DIR
    if _RESOLVED_DATA_DIR is None:
        _RESOLVED_DATA_DIR = _resolve_data_dir()
    return _RESOLVED_DATA_DIR


def get_db_path() -> Path:
    return get_data_dir() / "library.db"


def get_covers_dir() -> Path:
    return get_data_dir() / "covers"


def get_backups_dir() -> Path:
    return get_data_dir() / "backups"


def get_exports_dir() -> Path:
    return get_data_dir() / "exports"


def ensure_data_dirs() -> None:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    get_covers_dir().mkdir(parents=True, exist_ok=True)
    get_backups_dir().mkdir(parents=True, exist_ok=True)
    get_exports_dir().mkdir(parents=True, exist_ok=True)


def adopt_legacy_db_if_needed() -> None:
    db_path = get_db_path()
    if db_path.exists() or not LEGACY_DB_PATH.exists():
        return

    ensure_data_dirs()
    shutil.copy2(LEGACY_DB_PATH, db_path)


def resolve_app_path(value: str | None) -> Path | None:
    if not value:
        return None

    path = Path(value)
    if path.is_absolute():
        return path

    return get_data_dir() / path


def reset_data_dir_cache() -> None:
    global _RESOLVED_DATA_DIR
    _RESOLVED_DATA_DIR = None


def _resolve_data_dir() -> Path:
    override = os.environ.get("COMIC_VAULT_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    preferred = _get_os_data_dir()
    if _is_writable_directory(preferred):
        return preferred

    return (PROJECT_ROOT / ".comic_vault_data").resolve()


def _get_os_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    return Path.home() / ".local" / "share" / APP_DIR_NAME


def _is_writable_directory(path: Path) -> bool:
    probe_dir = path
    probe_file = probe_dir / ".write_test"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        return True
    except OSError:
        return False
