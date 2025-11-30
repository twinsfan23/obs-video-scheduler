from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List

from sqlalchemy.orm import Session

from . import models
from .config import Settings

MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".mpg", ".mpeg", ".m4v", ".webm"}


def ensure_media_dir(settings: Settings) -> Path:
    settings.server_video_dir.mkdir(parents=True, exist_ok=True)
    return settings.server_video_dir


def probe_duration_ms(path: Path) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration_seconds = float(result.stdout.strip())
        return int(duration_seconds * 1000)
    except Exception:
        return 0


def upsert_item(db: Session, name: str, duration: int, is_video: bool = True) -> models.Item:
    item = db.query(models.Item).filter_by(name=name).first()
    if not item:
        item = models.Item(name=name, duration=duration, is_video=is_video)
        db.add(item)
    else:
        item.duration = duration
        item.is_video = is_video
    db.commit()
    db.refresh(item)
    return item


def scan_media_library(settings: Settings, db: Session) -> List[models.Item]:
    media_root = ensure_media_dir(settings)
    found_items: List[models.Item] = []
    for file_path in media_root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        relative_name = str(file_path.relative_to(media_root))
        duration = probe_duration_ms(file_path)
        item = upsert_item(db, name=relative_name, duration=duration, is_video=True)
        found_items.append(item)
    return found_items


def persist_uploaded_files(files: Iterable, settings: Settings, db: Session) -> List[models.Item]:
    media_root = ensure_media_dir(settings)
    saved_items: List[models.Item] = []
    for upload in files:
        target_path = media_root / Path(upload.filename).name
        with target_path.open("wb") as buffer:
            buffer.write(upload.file.read())
        duration = probe_duration_ms(target_path)
        item = upsert_item(db, name=str(target_path.relative_to(media_root)), duration=duration, is_video=True)
        saved_items.append(item)
    return saved_items


def persist_urls(urls: List[str], db: Session) -> List[models.Item]:
    stored_items: List[models.Item] = []
    for url in urls:
        if not url:
            continue
        item = upsert_item(db, name=url, duration=0, is_video=True)
        stored_items.append(item)
    return stored_items
