from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import select

from comic_vault.data.db import get_session
from comic_vault.data.models import Series
from comic_vault.data.storage import ensure_data_dirs, resolve_app_path
from comic_vault.data.validation import VALID_STATUSES, build_dedupe_key, normalize_rating, normalize_url


@dataclass(frozen=True)
class IntegrityReport:
    total_series: int
    duplicate_count: int = 0
    invalid_url_count: int = 0
    invalid_current_url_count: int = 0
    invalid_status_count: int = 0
    invalid_rating_count: int = 0
    missing_cover_count: int = 0

    @property
    def has_issues(self) -> bool:
        return any(
            [
                self.duplicate_count,
                self.invalid_url_count,
                self.invalid_current_url_count,
                self.invalid_status_count,
                self.invalid_rating_count,
                self.missing_cover_count,
            ]
        )


def run_integrity_check() -> IntegrityReport:
    ensure_data_dirs()

    with get_session() as session:
        rows = session.exec(select(Series)).all()

    seen_keys: set[tuple[str, str]] = set()
    duplicate_count = 0
    invalid_url_count = 0
    invalid_current_url_count = 0
    invalid_status_count = 0
    invalid_rating_count = 0
    missing_cover_count = 0

    for row in rows:
        try:
            url = normalize_url(row.url)
        except ValueError:
            invalid_url_count += 1
            url = None

        try:
            normalize_url(row.current_url)
        except ValueError:
            invalid_current_url_count += 1

        if row.status not in VALID_STATUSES:
            invalid_status_count += 1

        if row.rating != normalize_rating(row.rating):
            invalid_rating_count += 1

        dedupe_key = build_dedupe_key(row.title, row.source, url)
        if dedupe_key in seen_keys:
            duplicate_count += 1
        else:
            seen_keys.add(dedupe_key)

        resolved_cover = resolve_app_path(row.cover_path)
        if row.cover_path and (resolved_cover is None or not resolved_cover.exists()):
            missing_cover_count += 1

    return IntegrityReport(
        total_series=len(rows),
        duplicate_count=duplicate_count,
        invalid_url_count=invalid_url_count,
        invalid_current_url_count=invalid_current_url_count,
        invalid_status_count=invalid_status_count,
        invalid_rating_count=invalid_rating_count,
        missing_cover_count=missing_cover_count,
    )


def format_integrity_report(report: IntegrityReport) -> str:
    lines = [f"Library checked: {report.total_series} series"]

    if report.duplicate_count:
        lines.append(f"- Potential duplicates: {report.duplicate_count}")
    if report.invalid_url_count:
        lines.append(f"- Invalid URL values: {report.invalid_url_count}")
    if report.invalid_current_url_count:
        lines.append(f"- Invalid current URL values: {report.invalid_current_url_count}")
    if report.invalid_status_count:
        lines.append(f"- Invalid status values: {report.invalid_status_count}")
    if report.invalid_rating_count:
        lines.append(f"- Invalid rating values: {report.invalid_rating_count}")
    if report.missing_cover_count:
        lines.append(f"- Missing cover files: {report.missing_cover_count}")

    if len(lines) == 1:
        lines.append("- No issues found")

    return "\n".join(lines)
