from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..ports.calendar_provider import CalendarProvider
from ..repositories.calendar_repository import CalendarRepository, SqlAlchemyCalendarRepository
from ..db import models


@dataclass
class SyncEventsResult:
    synced_events: int
    next_sync_token: Optional[str]


class SyncEventsUseCase:
    def __init__(
        self,
        provider: CalendarProvider,
        calendar_repo: CalendarRepository | None = None,
    ):
        self.provider = provider
        self.calendar_repo = calendar_repo or SqlAlchemyCalendarRepository()

    def execute(
        self,
        db: Session,
        user: models.User,
        user_context: Dict[str, Any],
        calendar_id: Optional[str] = None,
        sync_token: Optional[str] = None,
    ) -> SyncEventsResult:
        # Determine calendars
        cals = (
            [db.query(models.Calendar).filter(models.Calendar.id == calendar_id, models.Calendar.user_id == user.id).first()]
            if calendar_id
            else self.calendar_repo.list_selected_by_user(db, user.id)
        )
        cals = [c for c in cals if c]
        total = 0
        next_token: Optional[str] = None

        for cal in cals:
            since_iso = None if sync_token else datetime.now(timezone.utc).isoformat()
            res = self.provider.list_events(user_context, cal.external_id, sync_token=sync_token, since_iso=since_iso)
            for ge in res.get("items", []):
                self._upsert_event(db, cal, ge)
                total += 1
            nt = res.get("nextSyncToken")
            if nt:
                next_token = nt
        db.commit()
        return SyncEventsResult(synced_events=total, next_sync_token=next_token)

    def _upsert_event(self, db: Session, calendar: models.Calendar, google_event: Dict[str, Any]):
        if google_event.get("status") == "cancelled":
            existing = db.query(models.Event).filter(models.Event.external_event_id == google_event["id"]).first()
            if existing:
                db.delete(existing)
            return
        start = google_event.get("start", {})
        end = google_event.get("end", {})
        if "dateTime" not in start or "dateTime" not in end:
            return
        start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        existing = db.query(models.Event).filter(models.Event.external_event_id == google_event["id"]).first()
        if existing:
            existing.title = google_event.get("summary", "Untitled Event")
            existing.description = google_event.get("description")
            existing.start_at = start_dt
            existing.end_at = end_dt
            existing.updated_at = datetime.now(timezone.utc)
        else:
            import uuid
            ev = models.Event(
                id=str(uuid.uuid4()),
                calendar_id=calendar.id,
                user_id=calendar.user_id,
                title=google_event.get("summary", "Untitled Event"),
                description=google_event.get("description"),
                start_at=start_dt,
                end_at=end_dt,
                type="GENERAL",
                external_event_id=google_event["id"],
            )
            db.add(ev)
