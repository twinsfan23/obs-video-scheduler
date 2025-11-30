import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def default_uuid() -> str:
    return str(uuid.uuid4())


class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, default=default_uuid)
    name = Column(String, unique=True, nullable=False)
    duration = Column(Integer, nullable=False)
    is_video = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schedule_entries = relationship("ScheduleEntry", back_populates="item", cascade="all, delete")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id = Column(String, primary_key=True, default=default_uuid)
    start_timestamp = Column(Integer, nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)

    item = relationship("Item", back_populates="schedule_entries")


class ScheduleSnapshot(Base):
    __tablename__ = "schedule_snapshots"

    id = Column(String, primary_key=True, default=default_uuid)
    label = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    start_timestamp = Column(Integer, nullable=False)
    payload = Column(String, nullable=False)


class ContestState(Base):
    __tablename__ = "contest_state"

    id = Column(Integer, primary_key=True, default=1)
    start_timestamp = Column(Integer, nullable=True)
