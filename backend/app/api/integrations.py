from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db import models
from ..services.oauth_service import OAuthService, OAuthError
from ..services.google_calendar_service import GoogleCalendarService, GoogleCalendarError
from ..adapters.google_calendar_provider import GoogleCalendarProvider
from ..usecases.sync_calendars import SyncCalendarsUseCase
from ..usecases.sync_events import SyncEventsUseCase
from ..services.demo_user import get_or_create_demo_user

router = APIRouter(prefix="/integrations", tags=["integrations"])

oauth_service = OAuthService()
google_service = GoogleCalendarService(oauth_service)

@router.get("/google/auth-url")
def get_google_auth_url(redirect_uri: str = Query(...)):
    """Return Google OAuth authorization URL or 400 if config missing.
    Authentication不要 (テスト仕様)。"""
    from os import getenv
    if not getenv('GOOGLE_CLIENT_ID') or not getenv('GOOGLE_CLIENT_SECRET'):
        raise HTTPException(status_code=400, detail={"code": "OAUTH_CONFIG_MISSING", "message": "missing config"})
    try:
        state = "test_state"
        url = oauth_service.get_google_auth_url(redirect_uri, state=state)
        # Return both camelCase and snake_case for frontend compatibility, and echo state
        return {"authorizationUrl": url, "authorization_url": url, "state": state}
    except OAuthError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})

@router.get("/")
def list_integrations(db: Session = Depends(get_db)):
    user = get_or_create_demo_user(db)
    integrations = db.query(models.IntegrationAccount).filter(models.IntegrationAccount.user_id == user.id).all()
    return {"integrations": [
        {"id": i.id, "provider": i.provider, "expiresAt": i.expires_at, "revoked": bool(i.revoked_at)} for i in integrations
    ]}

@router.post("/google/sync-calendars")
def sync_google_calendars(db: Session = Depends(get_db)):
    user = get_or_create_demo_user(db)
    try:
        # Use new use case + provider
        integration = db.query(models.IntegrationAccount).filter(
            models.IntegrationAccount.user_id == user.id,
            models.IntegrationAccount.provider == "google",
            models.IntegrationAccount.revoked_at.is_(None),
        ).first()
        if not integration:
            raise GoogleCalendarError("INTEGRATION_NOT_FOUND", "Google Calendar integration not found")
        creds = oauth_service.get_valid_credentials(db, integration)
        provider = GoogleCalendarProvider(creds)
        uc = SyncCalendarsUseCase(provider)
        res = uc.execute(db, user, user_context={})
        # Keep response shape for frontend
        cals = db.query(models.Calendar).filter(models.Calendar.user_id == user.id).all()
        return {"syncedCalendars": res.synced_calendars, "calendars": [{"id": c.id, "name": c.name} for c in cals]}
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})

@router.post("/google/sync-events")
def sync_google_events(
    db: Session = Depends(get_db),
    calendar_id: Optional[str] = Query(default=None, alias="calendarId")
):
    """Sync events from Google to local DB. Optional calendarId to target one calendar."""
    user = get_or_create_demo_user(db)
    try:
        integration = db.query(models.IntegrationAccount).filter(
            models.IntegrationAccount.user_id == user.id,
            models.IntegrationAccount.provider == "google",
            models.IntegrationAccount.revoked_at.is_(None),
        ).first()
        if not integration:
            raise GoogleCalendarError("INTEGRATION_NOT_FOUND", "Google Calendar integration not found")
        creds = oauth_service.get_valid_credentials(db, integration)
        provider = GoogleCalendarProvider(creds)
        uc = SyncEventsUseCase(provider)
        res = uc.execute(db, user, user_context={}, calendar_id=calendar_id, sync_token=integration.sync_token)
        if res.next_sync_token:
            integration.sync_token = res.next_sync_token
            db.commit()
        return {"syncedEvents": res.synced_events}
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})