from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Callable, Iterator

from sqlmodel import SQLModel, Session, create_engine, text

from comic_vault.data.storage import adopt_legacy_db_if_needed, ensure_data_dirs, get_db_path


CURRENT_SCHEMA_VERSION = 3


def _build_engine():
    return create_engine(f"sqlite:///{get_db_path()}", echo=False)


ENGINE = _build_engine()


def close_engine() -> None:
    ENGINE.dispose()


def _ensure_meta_table(session: Session) -> None:
    session.exec(
        text(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
    )
    session.commit()


def _get_meta(session: Session, key: str) -> str | None:
    row = session.exec(text("SELECT value FROM app_meta WHERE key = :key").bindparams(key=key)).first()
    if row is None:
        return None
    try:
        return str(row[0])
    except (TypeError, KeyError, IndexError):
        pass
    return str(row)


def _set_meta(session: Session, key: str, value: str) -> None:
    session.exec(
        text(
            """
            INSERT INTO app_meta(key, value)
            VALUES (:key, :value)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        ).bindparams(key=key, value=value),
    )
    session.commit()


def _series_table_exists(session: Session) -> bool:
    row = session.exec(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='series'")
    ).first()
    return row is not None


def _get_series_columns(session: Session) -> set[str]:
    if not _series_table_exists(session):
        return set()
    cols = session.exec(text("PRAGMA table_info(series)")).all()
    return {str(col[1]) for col in cols}


def _detect_schema_version(session: Session) -> int:
    columns = _get_series_columns(session)
    if not columns:
        return CURRENT_SCHEMA_VERSION

    version = 1
    if "current_url" in columns:
        version = 2
    if "cover_path" in columns:
        version = 3
    return version


def _migration_add_current_url(session: Session) -> None:
    columns = _get_series_columns(session)
    if "current_url" not in columns:
        session.exec(text("ALTER TABLE series ADD COLUMN current_url TEXT"))
        session.commit()


def _migration_add_cover_path(session: Session) -> None:
    columns = _get_series_columns(session)
    if "cover_path" not in columns:
        session.exec(text("ALTER TABLE series ADD COLUMN cover_path TEXT"))
        session.commit()


MIGRATIONS: dict[int, Callable[[Session], None]] = {
    2: _migration_add_current_url,
    3: _migration_add_cover_path,
}


def _run_migrations(session: Session) -> None:
    _ensure_meta_table(session)

    raw_version = _get_meta(session, "schema_version")
    current_version = int(raw_version) if raw_version is not None else _detect_schema_version(session)
    _set_meta(session, "schema_version", str(current_version))

    for version in range(current_version + 1, CURRENT_SCHEMA_VERSION + 1):
        migration = MIGRATIONS.get(version)
        if migration is None:
            continue
        migration(session)
        _set_meta(session, "schema_version", str(version))
        _set_meta(session, "last_migrated_at", datetime.utcnow().isoformat(timespec="seconds"))


def init_db() -> None:
    ensure_data_dirs()
    adopt_legacy_db_if_needed()
    SQLModel.metadata.create_all(ENGINE)
    with Session(ENGINE) as session:
        _run_migrations(session)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(ENGINE) as session:
        yield session
