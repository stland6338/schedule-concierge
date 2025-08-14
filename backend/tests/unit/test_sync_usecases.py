from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from app.usecases.sync_calendars import SyncCalendarsUseCase
from app.usecases.sync_events import SyncEventsUseCase
from app.ports.calendar_provider import CalendarProvider
from app.db.session import get_db
from app.db import models
from sqlalchemy.orm import Session


class FakeProvider(CalendarProvider):
    def __init__(self, calendars: List[Dict[str, Any]], events_by_cal: Dict[str, Dict[str, Any]]):
        self._cals = calendars
        self._events = events_by_cal

    def list_calendars(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._cals

    def list_events(self, user_context: Dict[str, Any], calendar_external_id: str, sync_token: Optional[str] = None, since_iso: Optional[str] = None) -> Dict[str, Any]:
        return self._events.get(calendar_external_id, {"items": [], "nextSyncToken": None})


def make_user(db: Session) -> models.User:
    u = models.User(id="u1", email="u1@example.com")
    db.add(u)
    db.commit()
    return u


def test_sync_calendars_creates_and_updates(client):
    from app.db.session import SessionLocal
    db: Session = SessionLocal()
    user = make_user(db)

    provider = FakeProvider(
        calendars=[
            {"id": "cal_1", "summary": "Primary", "primary": True, "timeZone": "UTC"},
            {"id": "cal_2", "summary": "Work", "timeZone": "UTC"},
        ],
        events_by_cal={},
    )

    uc = SyncCalendarsUseCase(provider)
    res = uc.execute(db, user, user_context={})

    assert res.synced_calendars == 2
    cals = db.query(models.Calendar).filter(models.Calendar.user_id == user.id).all()
    assert {c.external_id for c in cals} == {"cal_1", "cal_2"}
    assert any(c.is_default == 1 for c in cals)


def test_sync_events_inserts_and_updates(client):
    from app.db.session import SessionLocal
    db: Session = SessionLocal()
    user = make_user(db)
    # Seed one calendar (selected)
    cal = models.Calendar(id="cid1", user_id=user.id, name="Primary", external_provider="google", external_id="cal_1", is_primary=1, is_default=1, selected=1)
    db.add(cal)
    db.commit()

    event_id = "gevt_1"
    provider = FakeProvider(
        calendars=[],
        events_by_cal={
            "cal_1": {
                "items": [
                    {
                        "id": event_id,
                        "summary": "Meeting",
                        "start": {"dateTime": datetime.now(timezone.utc).isoformat()},
                        "end": {"dateTime": (datetime.now(timezone.utc)).isoformat()},
                    }
                ],
                "nextSyncToken": "tok_next",
            }
        },
    )

    ue = SyncEventsUseCase(provider)
    res = ue.execute(db, user, user_context={}, sync_token=None)

    assert res.synced_events == 1
    assert res.next_sync_token == "tok_next"
    ev = db.query(models.Event).filter(models.Event.external_event_id == event_id).first()
    assert ev is not None
