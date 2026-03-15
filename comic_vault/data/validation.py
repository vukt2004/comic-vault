from __future__ import annotations

from urllib.parse import urlparse, urlunparse


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

