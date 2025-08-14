from __future__ import annotations
from typing import Protocol, List
from sqlalchemy.orm import Session
from ..db import models


class CalendarRepository(Protocol):
    def list_selected_by_user(self, db: Session, user_id: str) -> List[models.Calendar]:
        ...

    def upsert_from_external(
        self,
        db: Session,
        user_id: str,
        external_provider: str,
        external_calendar: dict,
    ) -> models.Calendar:
        ...


class SqlAlchemyCalendarRepository:
    def list_selected_by_user(self, db: Session, user_id: str) -> List[models.Calendar]:
        return (
            db.query(models.Calendar)
            .filter(models.Calendar.user_id == user_id, models.Calendar.selected == 1)
            .all()
        )

    def upsert_from_external(
        self,
        db: Session,
        user_id: str,
        external_provider: str,
        external_calendar: dict,
    ) -> models.Calendar:
        existing = (
            db.query(models.Calendar)
            .filter(
                models.Calendar.user_id == user_id,
                models.Calendar.external_provider == external_provider,
                models.Calendar.external_id == external_calendar["id"],
            )
            .first()
        )
        if existing:
            existing.name = external_calendar.get("summary", existing.name)
            existing.time_zone = external_calendar.get("timeZone") or existing.time_zone
            existing.access_role = external_calendar.get("accessRole") or existing.access_role
            existing.color = external_calendar.get("backgroundColor") or existing.color
            existing.is_primary = 1 if external_calendar.get("primary") else 0
            return existing
        else:
            import uuid

            cal = models.Calendar(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=external_calendar.get("summary", "Untitled Calendar"),
                external_provider=external_provider,
                external_id=external_calendar["id"],
                time_zone=external_calendar.get("timeZone"),
                access_role=external_calendar.get("accessRole"),
                color=external_calendar.get("backgroundColor"),
                is_primary=1 if external_calendar.get("primary") else 0,
                is_default=1 if external_calendar.get("primary") else 0,
                selected=1,
            )
            db.add(cal)
            return cal
