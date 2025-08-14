from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from sqlalchemy.orm import Session

from ..ports.calendar_provider import CalendarProvider
from ..repositories.calendar_repository import CalendarRepository, SqlAlchemyCalendarRepository
from ..db import models


@dataclass
class SyncCalendarsResult:
    synced_calendars: int


class SyncCalendarsUseCase:
    def __init__(
        self,
        provider: CalendarProvider,
        calendar_repo: CalendarRepository | None = None,
    ):
        self.provider = provider
        self.calendar_repo = calendar_repo or SqlAlchemyCalendarRepository()

    def execute(self, db: Session, user: models.User, user_context: Dict[str, Any]) -> SyncCalendarsResult:
        externals = self.provider.list_calendars(user_context)
        count = 0
        for cal in externals:
            self.calendar_repo.upsert_from_external(db, user.id, "google", cal)
            count += 1
        db.commit()
        return SyncCalendarsResult(synced_calendars=count)
