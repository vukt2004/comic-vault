from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine, text

DB_PATH = Path(__file__).resolve().parent / "comic_vault.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def _ensure_columns() -> None:
    """
    Minimal migration: if table exists but missing columns, add them.
    """
    with Session(ENGINE) as session:
        # table exists?
        tables = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='series'")).all()
        if not tables:
            return

        cols = session.exec(text("PRAGMA table_info(series)")).all()
        col_names = {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)

        if "cover_path" not in col_names:
            session.exec(text("ALTER TABLE series ADD COLUMN cover_path TEXT"))
            session.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(ENGINE)
    _ensure_columns()


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(ENGINE) as session:
        yield session
