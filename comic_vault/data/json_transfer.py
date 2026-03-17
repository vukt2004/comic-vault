from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlmodel import delete, select

from comic_vault.data.backup import create_backup_archive, make_backup_name
from comic_vault.data.db import CURRENT_SCHEMA_VERSION, get_session
from comic_vault.data.models import Series
from comic_vault.data.storage import ensure_data_dirs, get_backups_dir, get_exports_dir, resolve_app_path
from comic_vault.data.validation import (
    build_dedupe_key,
    normalize_optional_text,
    normalize_rating,
    normalize_status,
    normalize_url,
)


@dataclass(frozen=True)
class JsonImportResult:
    imported_count: int
    skipped_count: int
    duplicate_count: int = 0
    invalid_count: int = 0
    missing_cover_count: int = 0
    backup_path: Path | None = None


def export_library_json(destination: str | Path | None = None) -> Path:
    ensure_data_dirs()

    output = Path(destination) if destination else get_exports_dir() / _make_export_name()
    output.parent.mkdir(parents=True, exist_ok=True)

    with get_session() as session:
        rows = session.exec(select(Series).order_by(Series.updated_at.desc(), Series.id.desc())).all()

    payload = {
        "app": "Comic Vault",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat(timespec="seconds"),
        "series": [_serialize_series(row) for row in rows],
    }

    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def import_library_json(source: str | Path, *, overwrite: bool = True) -> JsonImportResult:
    ensure_data_dirs()

    path = Path(source)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"JSON export not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("series")
    if not isinstance(rows, list):
        raise ValueError("Invalid JSON export format: missing 'series' list.")

    prepared_rows, stats = _prepare_import_rows(rows)

    backup_path: Path | None = None
    if overwrite:
        backup_path = create_backup_archive(get_backups_dir() / make_backup_name("ComicVault_PreJsonImport"))

    with get_session() as session:
        if overwrite:
            session.exec(delete(Series))
            session.commit()

        for row in prepared_rows:
            session.add(Series(**row))

        session.commit()

    return JsonImportResult(
        imported_count=len(prepared_rows),
        skipped_count=stats["skipped"],
        duplicate_count=stats["duplicates"],
        invalid_count=stats["invalid"],
        missing_cover_count=stats["missing_covers"],
        backup_path=backup_path,
    )


def _make_export_name() -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"ComicVault_Export_{stamp}.json"


def _serialize_series(series: Series) -> dict[str, object]:
    return {
        "title": series.title,
        "source": series.source,
        "url": series.url,
        "cover_path": series.cover_path,
        "status": series.status,
        "rating": series.rating,
        "notes": series.notes,
        "current_chapter": series.current_chapter,
        "current_url": series.current_url,
        "created_at": series.created_at.isoformat(timespec="seconds"),
        "updated_at": series.updated_at.isoformat(timespec="seconds"),
    }


def _prepare_import_rows(rows: list[object]) -> tuple[list[dict[str, object]], dict[str, int]]:
    prepared: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str]] = set()
    stats = {
        "skipped": 0,
        "duplicates": 0,
        "invalid": 0,
        "missing_covers": 0,
    }

    for item in rows:
        if not isinstance(item, dict):
            stats["skipped"] += 1
            stats["invalid"] += 1
            continue

        title = str(item.get("title") or "").strip()
        if not title:
            stats["skipped"] += 1
            stats["invalid"] += 1
            continue

        try:
            url = normalize_url(item.get("url"))
            current_url = normalize_url(item.get("current_url"))
        except ValueError:
            stats["skipped"] += 1
            stats["invalid"] += 1
            continue

        source = normalize_optional_text(item.get("source"))
        dedupe_key = build_dedupe_key(title, source, url)
        if dedupe_key in seen_keys:
            stats["skipped"] += 1
            stats["duplicates"] += 1
            continue
        seen_keys.add(dedupe_key)

        status = normalize_status(item.get("status"))
        rating_value = normalize_rating(item.get("rating"))

        cover_path = normalize_optional_text(item.get("cover_path"))
        resolved_cover = resolve_app_path(cover_path)
        if cover_path and (resolved_cover is None or not resolved_cover.exists()):
            cover_path = None
            stats["missing_covers"] += 1

        created_at = _parse_datetime(item.get("created_at"))
        updated_at = _parse_datetime(item.get("updated_at")) or created_at

        prepared.append(
            {
                "title": title,
                "source": source,
                "url": url,
                "cover_path": cover_path,
                "status": status,
                "rating": rating_value,
                "notes": normalize_optional_text(item.get("notes")),
                "current_chapter": normalize_optional_text(item.get("current_chapter")),
                "current_url": current_url,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    return prepared, stats


def _parse_datetime(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.utcnow()
