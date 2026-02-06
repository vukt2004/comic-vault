from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.utcnow()


class Series(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    title: str = Field(index=True)
    source: Optional[str] = Field(default=None, index=True)
    url: Optional[str] = Field(default=None)

    # NEW: ảnh bìa (lưu path local)
    cover_path: Optional[str] = Field(default=None)

    status: str = Field(default="reading", index=True)
    rating: Optional[int] = Field(default=None)  # 1..10
    notes: Optional[str] = Field(default=None)

    current_chapter: Optional[str] = Field(default=None, index=True)
    current_url: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
