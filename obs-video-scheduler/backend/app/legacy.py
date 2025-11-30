import json
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from . import models

DATA_DIR = Path("../../data")


def _load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def import_items(db: Session) -> None:
    for file_name, is_video in [("filelist.txt", True), ("alist.txt", False)]:
        payload = _load_json(DATA_DIR / file_name)
        if not payload:
            continue
        for entry in payload:
            if db.query(models.Item).filter_by(name=entry.get("name")).first():
                continue
            item = models.Item(
                id=entry.get("uuid"),
                name=entry.get("name"),
                duration=entry.get("duration", 0),
                is_video=entry.get("isVideo", is_video),
            )
            db.add(item)
    db.commit()


def import_schedule(db: Session) -> None:
    payload = _load_json(DATA_DIR / "schedule.json")
    if not payload:
        return
    for entry in payload:
        name = entry.get("name")
        item = db.query(models.Item).filter_by(name=name).first()
        if not item:
            continue
        schedule_entry = models.ScheduleEntry(
            id=entry.get("uuid"),
            start_timestamp=entry.get("start_timestamp") or entry.get("start"),
            item_id=item.id,
        )
        db.add(schedule_entry)
    db.commit()


def import_contest_timestamp(db: Session) -> None:
    timestamp_path = DATA_DIR / "timestamp"
    if not timestamp_path.exists():
        return
    try:
        timestamp = int(timestamp_path.read_text().strip())
    except ValueError:
        return
    state = db.query(models.ContestState).first()
    if not state:
        state = models.ContestState(id=1, start_timestamp=timestamp)
        db.add(state)
    else:
        state.start_timestamp = state.start_timestamp or timestamp
    db.commit()


def bootstrap_from_legacy(db: Session) -> None:
    import_items(db)
    import_schedule(db)
    import_contest_timestamp(db)
