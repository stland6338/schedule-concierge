from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db import models
from .auth import get_current_user_optional
from ..services.demo_user import get_or_create_demo_user

router = APIRouter(prefix="/calendars", tags=["calendars"])


class CalendarOut(BaseModel):
    id: str
    name: Optional[str]
    externalProvider: Optional[str] = Field(alias="external_provider", default=None)
    externalId: Optional[str] = Field(alias="external_id", default=None)
    timeZone: Optional[str] = Field(alias="time_zone", default=None)
    accessRole: Optional[str] = Field(alias="access_role", default=None)
    color: Optional[str] = None
    isPrimary: bool = Field(alias="is_primary")
    isDefault: bool = Field(alias="is_default")
    selected: bool

    model_config = ConfigDict(populate_by_name=True)


class CalendarUpdate(BaseModel):
    name: Optional[str] = None
    isDefault: Optional[bool] = None
    selected: Optional[bool] = None


@router.get("", response_model=List[CalendarOut])
def list_calendars(
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    user = current_user or get_or_create_demo_user(db)
    cals = (
        db.query(models.Calendar)
        .filter(models.Calendar.user_id == user.id)
        .order_by(models.Calendar.is_default.desc(), models.Calendar.name)
        .all()
    )
    return [
        CalendarOut(
            id=c.id,
            name=c.name,
            external_provider=c.external_provider,
            external_id=c.external_id,
            time_zone=c.time_zone,
            access_role=c.access_role,
            color=c.color,
            is_primary=bool(c.is_primary),
            is_default=bool(c.is_default),
            selected=bool(c.selected),
        )
        for c in cals
    ]


@router.put("/{calendar_id}", response_model=CalendarOut)
def update_calendar(
    calendar_id: str,
    body: CalendarUpdate,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    user = current_user or get_or_create_demo_user(db)
    cal = (
        db.query(models.Calendar)
        .filter(models.Calendar.id == calendar_id, models.Calendar.user_id == user.id)
        .first()
    )
    if not cal:
        raise HTTPException(status_code=404, detail={"code": "CALENDAR_NOT_FOUND", "message": "Calendar not found"})

    if body.name is not None:
        cal.name = body.name
    if body.selected is not None:
        cal.selected = 1 if body.selected else 0
    if body.isDefault is not None and body.isDefault:
        # unset others
        db.query(models.Calendar).filter(
            models.Calendar.user_id == user.id, models.Calendar.id != cal.id
        ).update({models.Calendar.is_default: 0})
        cal.is_default = 1

    db.commit()
    db.refresh(cal)
    return CalendarOut(
        id=cal.id,
        name=cal.name,
        external_provider=cal.external_provider,
        external_id=cal.external_id,
        time_zone=cal.time_zone,
        access_role=cal.access_role,
        color=cal.color,
        is_primary=bool(cal.is_primary),
        is_default=bool(cal.is_default),
        selected=bool(cal.selected),
    )
