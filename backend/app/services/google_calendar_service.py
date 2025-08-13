"""Google Calendar integration service.

Handles bidirectional synchronization between Schedule Concierge and Google Calendar.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from ..db import models
from ..errors import BaseAppException
from .oauth_service import OAuthService


class GoogleCalendarError(BaseAppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, http_status=502)


class GoogleCalendarService:
    """Service for Google Calendar API operations."""
    
    def __init__(self, oauth_service: OAuthService):
        self.oauth_service = oauth_service
        
    def sync_calendars(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Sync user's Google calendars and return sync results."""
        integration = self._get_integration(db, user_id)
        credentials = self.oauth_service.get_valid_credentials(db, integration)
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # List Google calendars
            calendar_list = service.calendarList().list().execute()
            
            synced_calendars = []
            for google_cal in calendar_list.get('items', []):
                calendar = self._sync_calendar(db, user_id, google_cal)
                synced_calendars.append(calendar)
                
            return {
                "syncedCalendars": len(synced_calendars),
                "calendars": [{"id": c.id, "name": c.name} for c in synced_calendars]
            }
            
        except HttpError as e:
            raise GoogleCalendarError("GOOGLE_API_ERROR", f"Google API error: {e}")
        except Exception as e:
            raise GoogleCalendarError("SYNC_ERROR", f"Calendar sync failed: {e}")
            
    def sync_events(self, db: Session, user_id: str, calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """Sync events from Google Calendar to local database."""
        integration = self._get_integration(db, user_id)
        credentials = self.oauth_service.get_valid_credentials(db, integration)
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get calendars to sync
            if calendar_id:
                calendars = [db.query(models.Calendar).filter(
                    models.Calendar.id == calendar_id,
                    models.Calendar.user_id == user_id
                ).first()]
                if not calendars[0]:
                    raise GoogleCalendarError("CALENDAR_NOT_FOUND", "Calendar not found")
            else:
                calendars = db.query(models.Calendar).filter(
                    models.Calendar.user_id == user_id,
                    models.Calendar.external_provider == "google"
                ).all()
                
            synced_events = 0
            for calendar in calendars:
                if not calendar.external_id:
                    continue
                    
                # Use sync token for incremental sync if available
                sync_token = integration.sync_token
                
                # Get events from Google Calendar
                events_request = service.events().list(
                    calendarId=calendar.external_id,
                    syncToken=sync_token if sync_token else None,
                    timeMin=datetime.now(timezone.utc).isoformat() if not sync_token else None,
                    maxResults=2500,
                    singleEvents=True,
                    orderBy='startTime' if not sync_token else None
                )
                
                events_result = events_request.execute()
                
                # Process events
                for google_event in events_result.get('items', []):
                    self._sync_event(db, calendar, google_event)
                    synced_events += 1
                    
                # Update sync token
                if 'nextSyncToken' in events_result:
                    integration.sync_token = events_result['nextSyncToken']
                    
            db.commit()
            return {"syncedEvents": synced_events}
            
        except HttpError as e:
            if e.resp.status == 410:  # Sync token invalid
                integration.sync_token = None
                db.commit()
                return self.sync_events(db, user_id, calendar_id)  # Retry without sync token
            raise GoogleCalendarError("GOOGLE_API_ERROR", f"Google API error: {e}")
        except Exception as e:
            raise GoogleCalendarError("SYNC_ERROR", f"Event sync failed: {e}")
            
    def create_google_event(
        self, 
        db: Session, 
        user_id: str, 
        event: models.Event
    ) -> str:
        """Create event in Google Calendar and return external event ID."""
        integration = self._get_integration(db, user_id)
        credentials = self.oauth_service.get_valid_credentials(db, integration)
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get calendar
            calendar = db.query(models.Calendar).filter(
                models.Calendar.id == event.calendar_id
            ).first()
            
            if not calendar or not calendar.external_id:
                raise GoogleCalendarError("CALENDAR_NOT_FOUND", "Google calendar not found")
                
            # Create Google event structure
            google_event = {
                'summary': event.title,
                'description': event.description or '',
                'start': {
                    'dateTime': event.start_at.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': event.end_at.isoformat(), 
                    'timeZone': 'UTC'
                },
                'extendedProperties': {
                    'private': {
                        'scheduleConciergeFocus': 'true' if event.type == 'FOCUS' else 'false',
                        'scheduleConciergeId': str(event.id)
                    }
                }
            }
            
            # Create event in Google Calendar
            created_event = service.events().insert(
                calendarId=calendar.external_id,
                body=google_event
            ).execute()
            
            # Update local event with external ID
            event.external_event_id = created_event['id']
            db.commit()
            
            return created_event['id']
            
        except HttpError as e:
            raise GoogleCalendarError("GOOGLE_API_ERROR", f"Failed to create Google event: {e}")
        except Exception as e:
            raise GoogleCalendarError("CREATE_ERROR", f"Event creation failed: {e}")
            
    def update_google_event(
        self, 
        db: Session, 
        user_id: str, 
        event: models.Event
    ) -> bool:
        """Update existing event in Google Calendar."""
        if not event.external_event_id:
            return False
            
        integration = self._get_integration(db, user_id)
        credentials = self.oauth_service.get_valid_credentials(db, integration)
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            calendar = db.query(models.Calendar).filter(
                models.Calendar.id == event.calendar_id
            ).first()
            
            if not calendar or not calendar.external_id:
                return False
                
            # Update Google event
            google_event = {
                'summary': event.title,
                'description': event.description or '',
                'start': {
                    'dateTime': event.start_at.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': event.end_at.isoformat(),
                    'timeZone': 'UTC'
                }
            }
            
            service.events().update(
                calendarId=calendar.external_id,
                eventId=event.external_event_id,
                body=google_event
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event no longer exists in Google Calendar
                event.external_event_id = None
                db.commit()
                return False
            raise GoogleCalendarError("GOOGLE_API_ERROR", f"Failed to update Google event: {e}")
        except Exception as e:
            raise GoogleCalendarError("UPDATE_ERROR", f"Event update failed: {e}")
            
    def delete_google_event(
        self, 
        db: Session, 
        user_id: str, 
        event: models.Event
    ) -> bool:
        """Delete event from Google Calendar."""
        if not event.external_event_id:
            return False
            
        integration = self._get_integration(db, user_id)
        credentials = self.oauth_service.get_valid_credentials(db, integration)
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            calendar = db.query(models.Calendar).filter(
                models.Calendar.id == event.calendar_id
            ).first()
            
            if not calendar or not calendar.external_id:
                return False
                
            service.events().delete(
                calendarId=calendar.external_id,
                eventId=event.external_event_id
            ).execute()
            
            event.external_event_id = None
            db.commit()
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                event.external_event_id = None
                db.commit()
                return True
            raise GoogleCalendarError("GOOGLE_API_ERROR", f"Failed to delete Google event: {e}")
        except Exception as e:
            raise GoogleCalendarError("DELETE_ERROR", f"Event deletion failed: {e}")
            
    def _get_integration(self, db: Session, user_id: str) -> models.IntegrationAccount:
        """Get Google integration for user."""
        integration = db.query(models.IntegrationAccount).filter(
            models.IntegrationAccount.user_id == user_id,
            models.IntegrationAccount.provider == "google",
            models.IntegrationAccount.revoked_at.is_(None)
        ).first()
        
        if not integration:
            raise GoogleCalendarError("INTEGRATION_NOT_FOUND", "Google Calendar integration not found")
            
        return integration
        
    def _sync_calendar(
        self, 
        db: Session, 
        user_id: str, 
        google_calendar: Dict[str, Any]
    ) -> models.Calendar:
        """Sync a single Google calendar to local database."""
        # Check if calendar already exists
        existing = db.query(models.Calendar).filter(
            models.Calendar.user_id == user_id,
            models.Calendar.external_provider == "google",
            models.Calendar.external_id == google_calendar['id']
        ).first()
        
        if existing:
            # Update existing calendar
            existing.name = google_calendar.get('summary', 'Untitled Calendar')
            return existing
        else:
            # Create new calendar
            calendar = models.Calendar(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=google_calendar.get('summary', 'Untitled Calendar'),
                external_provider="google",
                external_id=google_calendar['id']
            )
            db.add(calendar)
            return calendar
            
    def _sync_event(
        self, 
        db: Session, 
        calendar: models.Calendar, 
        google_event: Dict[str, Any]
    ):
        """Sync a single Google event to local database."""
        if google_event.get('status') == 'cancelled':
            # Handle deleted events
            existing = db.query(models.Event).filter(
                models.Event.external_event_id == google_event['id']
            ).first()
            if existing:
                db.delete(existing)
            return
            
        # Parse start/end times
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        if 'dateTime' not in start or 'dateTime' not in end:
            return  # Skip all-day events for now
            
        start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        
        # Check if event already exists
        existing = db.query(models.Event).filter(
            models.Event.external_event_id == google_event['id']
        ).first()
        
        if existing:
            # Update existing event
            existing.title = google_event.get('summary', 'Untitled Event')
            existing.description = google_event.get('description')
            existing.start_at = start_dt
            existing.end_at = end_dt
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new event
            event = models.Event(
                id=str(uuid.uuid4()),
                calendar_id=calendar.id,
                user_id=calendar.user_id,
                title=google_event.get('summary', 'Untitled Event'),
                description=google_event.get('description'),
                start_at=start_dt,
                end_at=end_dt,
                type='GENERAL',  # Default type for imported events
                external_event_id=google_event['id']
            )
            db.add(event)