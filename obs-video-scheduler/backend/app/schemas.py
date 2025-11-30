from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str
    duration: int = Field(ge=0)
    is_video: bool = True


class ItemRead(ItemCreate):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScheduleEntryCreate(BaseModel):
    start_timestamp: int
    item_id: str


class ScheduleEntryRead(BaseModel):
    id: str
    start_timestamp: int
    item: ItemRead

    class Config:
        from_attributes = True


class SchedulePayload(BaseModel):
    contest_timestamp: Optional[int]
    schedule: List[ScheduleEntryRead]


class ScheduleSnapshotCreate(BaseModel):
    label: str


class ScheduleSnapshotRead(BaseModel):
    id: str
    label: str
    created_at: datetime
    start_timestamp: int

    class Config:
        from_attributes = True


class ContestUpdate(BaseModel):
    start_timestamp: Optional[int] = None


class MediaUrlImport(BaseModel):
    urls: List[str]


class ObsLaunchRequest(BaseModel):
    path: str
    layer: int = 0
    scene_name: str
    source_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    clear_on_media_end: bool = True


class ObsSourceRequest(BaseModel):
    scene_name: str
    source_name: str


class ObsMuteRequest(BaseModel):
    source_name: str
