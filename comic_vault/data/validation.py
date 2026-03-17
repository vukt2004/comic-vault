from __future__ import annotations

from urllib.parse import urlparse, urlunparse


VALID_STATUSES = {"reading", "paused", "completed", "dropped"}


def normalize_url(value: str | None) -> str | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")

    path = parsed.path or ""
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    cleaned = parsed._replace(path=path, fragment="")
    return urlunparse(cleaned)


def normalize_optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_status(value: object) -> str:
    status = normalize_optional_text(value) or "reading"
    return status if status in VALID_STATUSES else "reading"


def normalize_rating(value: object) -> int | None:
    if value in (None, "", 0, "0"):
        return None

    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None

    return rating if 1 <= rating <= 10 else None


def build_dedupe_key(title: str, source: str | None, url: str | None) -> tuple[str, str]:
    return (
        (url or "").lower(),
        f"{title.strip().lower()}|{(source or '').strip().lower()}",
    )
