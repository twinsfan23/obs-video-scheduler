from __future__ import annotations

import json
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from . import models, obs
from .config import get_settings
from .database import Base, engine, get_db
from .legacy import bootstrap_from_legacy
from .schemas import (
    ContestUpdate,
    ItemCreate,
    ItemRead,
    ObsLaunchRequest,
    ObsMuteRequest,
    ObsSourceRequest,
    ScheduleEntryCreate,
    ScheduleEntryRead,
    SchedulePayload,
    ScheduleSnapshotCreate,
    ScheduleSnapshotRead,
)

app = FastAPI(title="OBS Video Scheduler", version="2.0")


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        bootstrap_from_legacy(db)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "database": settings.database_url}


@app.get("/items", response_model=List[ItemRead])
def list_items(kind: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Item)
    if kind == "video":
        query = query.filter(models.Item.is_video.is_(True))
    elif kind == "activity":
        query = query.filter(models.Item.is_video.is_(False))
    items = query.order_by(models.Item.name.asc()).all()
    return items


@app.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    if db.query(models.Item).filter_by(name=payload.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item already exists")
    item = models.Item(name=payload.name, duration=payload.duration, is_video=payload.is_video)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}", response_model=ItemRead)
def update_item(item_id: str, payload: ItemCreate, db: Session = Depends(get_db)):
    item = db.query(models.Item).get(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    item.name = payload.name
    item.duration = payload.duration
    item.is_video = payload.is_video
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(models.Item).get(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


@app.get("/schedule", response_model=SchedulePayload)
def get_schedule(db: Session = Depends(get_db)):
    entries = (
        db.query(models.ScheduleEntry)
        .options(joinedload(models.ScheduleEntry.item))
        .order_by(models.ScheduleEntry.start_timestamp)
        .all()
    )
    contest = db.query(models.ContestState).first()
    return {"contest_timestamp": contest.start_timestamp if contest else None, "schedule": entries}


@app.put("/schedule", response_model=SchedulePayload)
def replace_schedule(payload: List[ScheduleEntryCreate], db: Session = Depends(get_db)):
    db.query(models.ScheduleEntry).delete()
    db.commit()
    entries: List[models.ScheduleEntry] = []
    for entry in payload:
        item = db.query(models.Item).get(entry.item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown item {entry.item_id}")
        model_entry = models.ScheduleEntry(start_timestamp=entry.start_timestamp, item_id=item.id)
        db.add(model_entry)
        entries.append(model_entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    contest = db.query(models.ContestState).first()
    return {"contest_timestamp": contest.start_timestamp if contest else None, "schedule": entries}


@app.post("/schedule/snapshots", response_model=ScheduleSnapshotRead, status_code=status.HTTP_201_CREATED)
def save_schedule(payload: ScheduleSnapshotCreate, db: Session = Depends(get_db)):
    contest = db.query(models.ContestState).first()
    schedule_entries = (
        db.query(models.ScheduleEntry)
        .options(joinedload(models.ScheduleEntry.item))
        .order_by(models.ScheduleEntry.start_timestamp)
        .all()
    )
    snapshot = models.ScheduleSnapshot(
        label=payload.label,
        start_timestamp=contest.start_timestamp if contest else 0,
        payload=json.dumps(
            [
                {"id": e.id, "start_timestamp": e.start_timestamp, "item_id": e.item_id}
                for e in schedule_entries
            ]
        ),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@app.get("/schedule/snapshots", response_model=List[ScheduleSnapshotRead])
def list_snapshots(db: Session = Depends(get_db)):
    return db.query(models.ScheduleSnapshot).order_by(models.ScheduleSnapshot.created_at.desc()).all()


@app.post("/schedule/snapshots/{snapshot_id}", response_model=SchedulePayload)
def load_snapshot(snapshot_id: str, db: Session = Depends(get_db)):
    snapshot = db.query(models.ScheduleSnapshot).get(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    db.query(models.ScheduleEntry).delete()
    db.commit()

    entries_data = json.loads(snapshot.payload)
    entries: List[models.ScheduleEntry] = []
    for entry in entries_data:
        item = db.query(models.Item).get(entry["item_id"])
        if not item:
            continue
        se = models.ScheduleEntry(id=entry.get("id"), start_timestamp=entry["start_timestamp"], item_id=item.id)
        db.add(se)
        entries.append(se)
    contest = db.query(models.ContestState).first()
    if not contest:
        contest = models.ContestState(id=1)
        db.add(contest)
    contest.start_timestamp = snapshot.start_timestamp
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return {"contest_timestamp": contest.start_timestamp, "schedule": entries}


@app.post("/contest", response_model=SchedulePayload)
def update_contest(payload: ContestUpdate, db: Session = Depends(get_db)):
    contest = db.query(models.ContestState).first()
    if not contest:
        contest = models.ContestState(id=1)
        db.add(contest)
    contest.start_timestamp = payload.start_timestamp
    db.commit()
    db.refresh(contest)
    entries = (
        db.query(models.ScheduleEntry)
        .options(joinedload(models.ScheduleEntry.item))
        .order_by(models.ScheduleEntry.start_timestamp)
        .all()
    )
    return {"contest_timestamp": contest.start_timestamp, "schedule": entries}


@app.post("/obs/launch", status_code=status.HTTP_202_ACCEPTED)
def launch_video(payload: ObsLaunchRequest):
    obs.launch_media(
        path=payload.path,
        layer=payload.layer,
        scene_name=payload.scene_name,
        source_name=payload.source_name,
        width=payload.width,
        height=payload.height,
        clear_on_media_end=payload.clear_on_media_end,
    )
    return {"status": "queued"}


@app.post("/obs/remove", status_code=status.HTTP_202_ACCEPTED)
def remove_source(payload: ObsSourceRequest):
    obs.remove_source(scene_name=payload.scene_name, source_name=payload.source_name)
    return {"status": "queued"}


@app.post("/obs/mute", status_code=status.HTTP_202_ACCEPTED)
def mute_source(payload: ObsMuteRequest):
    obs.mute_source(source_name=payload.source_name)
    return {"status": "queued"}


@app.post("/obs/unmute", status_code=status.HTTP_202_ACCEPTED)
def unmute_source(payload: ObsMuteRequest):
    obs.unmute_source(source_name=payload.source_name)
    return {"status": "queued"}


@app.get("/obs/heartbeat")
def obs_heartbeat():
    obs.heartbeat()
    return {"status": "ok"}
