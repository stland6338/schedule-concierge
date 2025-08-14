from __future__ import annotations
from typing import Protocol, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..db import models


class EventRepository(Protocol):
    def find_overlapping(self, db: Session, user_id: str, start: datetime, end: datetime) -> List[models.Event]: ...
    def find_future_events(self, db: Session, user_id: str, now: datetime, end_window: datetime, exclude_event_id: Optional[str] = None) -> List[models.Event]: ...


class SqlAlchemyEventRepository:
    """SQLAlchemy-backed implementation that respects selected calendars."""

    def find_overlapping(self, db: Session, user_id: str, start: datetime, end: datetime) -> List[models.Event]:
        q = db.query(models.Event)
        q = q.join(models.Calendar, models.Calendar.id == models.Event.calendar_id)
        q = q.filter(models.Calendar.selected == 1)
        q = q.filter(models.Event.user_id == user_id)
        q = q.filter(models.Event.start_at < end)
        q = q.filter(models.Event.end_at > start)
        return q.all()

    def find_future_events(self, db: Session, user_id: str, now: datetime, end_window: datetime, exclude_event_id: Optional[str] = None) -> List[models.Event]:
        q = db.query(models.Event)
        q = q.join(models.Calendar, models.Calendar.id == models.Event.calendar_id)
        q = q.filter(models.Calendar.selected == 1)
        q = q.filter(models.Event.user_id == user_id)
        q = q.filter(models.Event.start_at >= now)
        q = q.filter(models.Event.start_at <= end_window)
        if exclude_event_id:
            q = q.filter(models.Event.id != exclude_event_id)
        return q.all()
