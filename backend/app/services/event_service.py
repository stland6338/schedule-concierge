from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from ..db import models
from .google_calendar_service import GoogleCalendarService
from .oauth_service import OAuthService

class EventNotFound(Exception):
    pass

class EventService:
    def __init__(self):
        self.oauth_service = OAuthService()
        self.google_service = GoogleCalendarService(self.oauth_service)
        
    def create_event(self, db: Session, user_id: str, calendar_id: str, title: str,
                    start_at: datetime, end_at: datetime, type: str = "GENERAL",
                    description: Optional[str] = None, sync_to_google: bool = True) -> models.Event:
        event = models.Event(
            user_id=user_id,
            calendar_id=calendar_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            type=type,
            description=description
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Sync to Google Calendar if enabled and integration exists
        if sync_to_google:
            try:
                self.google_service.create_google_event(db, user_id, event)
            except Exception:
                pass  # Don't fail event creation if Google sync fails
                
        return event
    
    def get_event(self, db: Session, event_id: str) -> models.Event:
        event = db.query(models.Event).filter(models.Event.id == event_id).first()
        if not event:
            raise EventNotFound()
        return event
    
    def update_event(self, db: Session, event_id: str,
                    title: Optional[str] = None,
                    start_at: Optional[datetime] = None,
                    end_at: Optional[datetime] = None,
                    type: Optional[str] = None,
                    description: Optional[str] = None,
                    sync_to_google: bool = True) -> models.Event:
        event = self.get_event(db, event_id)
        
        if title is not None:
            event.title = title
        if start_at is not None:
            event.start_at = start_at
        if end_at is not None:
            event.end_at = end_at
        if type is not None:
            event.type = type
        if description is not None:
            event.description = description
        
        event.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(event)
        
        # Sync updates to Google Calendar if enabled
        if sync_to_google:
            try:
                self.google_service.update_google_event(db, event.user_id, event)
            except Exception:
                pass  # Don't fail update if Google sync fails
                
        return event
    
    def delete_event(self, db: Session, event_id: str, sync_to_google: bool = True):
        event = self.get_event(db, event_id)
        
        # Sync deletion to Google Calendar if enabled
        if sync_to_google and event.external_event_id:
            try:
                self.google_service.delete_google_event(db, event.user_id, event)
            except Exception:
                pass  # Don't fail deletion if Google sync fails
                
        db.delete(event)
        db.commit()