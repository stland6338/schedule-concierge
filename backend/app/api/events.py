from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from ..db.session import get_db
from ..db import models
from ..services.event_service import EventService, EventNotFound
from ..services.conflict_service import ConflictService, ConflictDetected
from .auth import get_current_user_optional
from ..services.demo_user import get_or_create_demo_user
from ..errors import ValidationAppError, ConflictError, NotFoundError
from ..domain.enums import EventType

router = APIRouter(prefix="/events", tags=["events"])

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1)
    start_at: datetime = Field(..., alias="startAt")
    end_at: datetime = Field(..., alias="endAt")
    type: EventType = Field(default=EventType.GENERAL)
    description: Optional[str] = None
    override_focus_protection: bool = Field(default=False, alias="overrideFocusProtection")

class EventOut(BaseModel):
    id: str
    title: str
    start_at: datetime = Field(..., alias="startAt")
    end_at: datetime = Field(..., alias="endAt") 
    type: str
    description: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_at: Optional[datetime] = Field(None, alias="startAt")
    end_at: Optional[datetime] = Field(None, alias="endAt")
    type: Optional[EventType] = None
    description: Optional[str] = None

@router.post("", response_model=EventOut, status_code=201)
def create_event(body: EventCreate, db: Session = Depends(get_db), current_user: models.User | None = Depends(get_current_user_optional)):
    user = current_user or get_or_create_demo_user(db)
    user_id = user.id
    
    # ensure calendar exists
    calendar = db.query(models.Calendar).filter(models.Calendar.user_id == user_id).first()
    if not calendar:
        calendar = models.Calendar(user_id=user_id, name="Default Calendar", is_default=1, selected=1)
        db.add(calendar)
        db.commit()
    
    # Basic temporal validation
    if body.end_at <= body.start_at:
        raise ValidationAppError("EVENT_INVALID_TIME", "end before start")

    # Create temporary event for conflict detection
    temp_event = models.Event(
        user_id=user_id,
        calendar_id=calendar.id,
        title=body.title,
        start_at=body.start_at,
        end_at=body.end_at,
        type=body.type,
        description=body.description
    )
    
    # Check for conflicts before creating
    conflict_service = ConflictService()
    try:
        conflict_service.validate_event_creation(
            db, 
            temp_event, 
            allow_focus_override=body.override_focus_protection
        )
    except ConflictDetected as e:
        raise ConflictError("FOCUS_PROTECTED", str(e))
    
    event_service = EventService()
    event = event_service.create_event(
        db=db,
        user_id=user_id,
        calendar_id=calendar.id,
        title=body.title,
        start_at=body.start_at,
        end_at=body.end_at,
        type=body.type,
        description=body.description
    )
    
    return EventOut(
        id=event.id,
        title=event.title,
        startAt=event.start_at,
        endAt=event.end_at,
        type=event.type,
        description=event.description,
        createdAt=event.created_at
    )

@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event_service = EventService()
    try:
        event = event_service.get_event(db, event_id)
    except EventNotFound:
        raise NotFoundError("EVENT_NOT_FOUND", "Event not found")
    
    return EventOut(
        id=event.id,
        title=event.title,
        startAt=event.start_at,
        endAt=event.end_at,
        type=event.type,
        description=event.description,
        createdAt=event.created_at
    )

@router.get("", response_model=List[EventOut])
def list_events(db: Session = Depends(get_db), current_user: models.User | None = Depends(get_current_user_optional)):
    user = current_user or get_or_create_demo_user(db)
    user_id = user.id
    events = (
        db.query(models.Event)
        .join(models.Calendar, models.Calendar.id == models.Event.calendar_id)
        .filter(models.Event.user_id == user_id, models.Calendar.selected == 1)
        .all()
    )
    return [
        EventOut(
            id=event.id,
            title=event.title,
            startAt=event.start_at,
            endAt=event.end_at,
            type=event.type,
            description=event.description,
            createdAt=event.created_at
        ) for event in events
    ]

@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: str, body: EventUpdate, db: Session = Depends(get_db)):
    event_service = EventService()
    try:
        event = event_service.update_event(
            db=db,
            event_id=event_id,
            title=body.title,
            start_at=body.start_at,
            end_at=body.end_at,
            type=body.type,
            description=body.description
        )
    except EventNotFound:
        raise NotFoundError("EVENT_NOT_FOUND", "Event not found")
    
    return EventOut(
        id=event.id,
        title=event.title,
        startAt=event.start_at,
        endAt=event.end_at,
        type=event.type,
        description=event.description,
        createdAt=event.created_at
    )

@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db)):
    event_service = EventService()
    try:
        event_service.delete_event(db, event_id)
    except EventNotFound:
        raise HTTPException(status_code=404, detail={"code": "EVENT_NOT_FOUND", "message": "Event not found"})