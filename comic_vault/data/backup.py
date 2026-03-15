from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from comic_vault.data.db import CURRENT_SCHEMA_VERSION, close_engine, init_db
from comic_vault.data.storage import (
    ensure_data_dirs,
    get_backups_dir,
    get_covers_dir,
    get_data_dir,
    get_db_path,
)


def make_backup_name(prefix: str = "ComicVault_Backup") -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{prefix}_{stamp}.zip"


def create_backup_archive(destination: str | Path | None = None) -> Path:
    ensure_data_dirs()

    output = Path(destination) if destination else get_backups_dir() / make_backup_name()
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "app": "Comic Vault",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "schema_version": CURRENT_SCHEMA_VERSION,
        "db_name": get_db_path().name,
        "covers_dir": "covers",
    }

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        if get_db_path().exists():
            archive.write(get_db_path(), arcname="library.db")

        covers_dir = get_covers_dir()
        if covers_dir.exists():
            for file_path in covers_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, arcname=str(Path("covers") / file_path.relative_to(covers_dir)))

    return output


def restore_backup_archive(archive_path: str | Path) -> Path:
    ensure_data_dirs()

    source = Path(archive_path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Backup archive not found: {source}")

    with ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        if "library.db" not in names:
            raise ValueError("Backup archive is missing library.db.")
        if "manifest.json" not in names:
            raise ValueError("Backup archive is missing manifest.json.")

        auto_backup = create_backup_archive(get_backups_dir() / make_backup_name("ComicVault_PreRestore"))

        staging_root = get_data_dir() / ".restore_staging"
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)
        staging_root.mkdir(parents=True, exist_ok=True)

        try:
            extracted_db = staging_root / "library.db"
            with archive.open("library.db", "r") as src_file, extracted_db.open("wb") as dst_file:
                shutil.copyfileobj(src_file, dst_file)

            extracted_covers = staging_root / "covers"
            extracted_covers.mkdir(parents=True, exist_ok=True)
            for name in names:
                if not name.startswith("covers/") or name.endswith("/"):
                    continue
                rel_path = Path(name).relative_to("covers")
                target = extracted_covers / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name, "r") as src_file, target.open("wb") as dst_file:
                    shutil.copyfileobj(src_file, dst_file)

            close_engine()

            get_data_dir().mkdir(parents=True, exist_ok=True)
            shutil.copy2(extracted_db, get_db_path())

            if get_covers_dir().exists():
                shutil.rmtree(get_covers_dir())
            get_covers_dir().mkdir(parents=True, exist_ok=True)

            for file_path in extracted_covers.rglob("*"):
                if file_path.is_dir():
                    continue
                target = get_covers_dir() / file_path.relative_to(extracted_covers)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    init_db()
    return auto_backup
