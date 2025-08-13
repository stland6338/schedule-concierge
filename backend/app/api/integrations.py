"""Integration API endpoints for external calendar connections."""
from typing import Dict, Any, Optional
import secrets
import uuid

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.session import get_db
from ..db import models
from ..api.auth import get_current_user
from ..services.oauth_service import OAuthService, OAuthError
from ..services.google_calendar_service import GoogleCalendarService, GoogleCalendarError
from ..services.demo_user import get_or_create_demo_user

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Initialize services
oauth_service = OAuthService()
google_service = GoogleCalendarService(oauth_service)


class ConnectRequest(BaseModel):
    code: str
    redirect_uri: str
    

class AuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


@router.get("/google/auth-url", response_model=AuthUrlResponse)
async def get_google_auth_url(
    redirect_uri: str = Query(...),
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google OAuth authorization URL."""
    user = current_user or get_or_create_demo_user(db)
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    try:
        auth_url = oauth_service.get_google_auth_url(redirect_uri, state)
        return AuthUrlResponse(authorization_url=auth_url, state=state)
    except OAuthError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})


@router.post("/google/connect", status_code=201)
async def connect_google(
    request: ConnectRequest,
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect Google Calendar integration."""
    user = current_user or get_or_create_demo_user(db)
    
    try:
        integration = oauth_service.exchange_google_code(
            db, user.id, request.code, request.redirect_uri
        )
        
        return {
            "id": integration.id,
            "provider": integration.provider,
            "scopes": integration.scopes,
            "connected_at": integration.created_at
        }
    except OAuthError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})


@router.post("/google/sync-calendars")
async def sync_google_calendars(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Google calendars to local database."""
    user = current_user or get_or_create_demo_user(db)
    
    try:
        result = google_service.sync_calendars(db, user.id)
        return result
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})


@router.post("/google/sync-events")
async def sync_google_events(
    calendar_id: Optional[str] = Query(None),
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Google Calendar events to local database."""
    user = current_user or get_or_create_demo_user(db)
    
    try:
        result = google_service.sync_events(db, user.id, calendar_id)
        return result
    except GoogleCalendarError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})


@router.get("/")
async def list_integrations(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's active integrations."""
    user = current_user or get_or_create_demo_user(db)
    
    integrations = db.query(models.IntegrationAccount).filter(
        models.IntegrationAccount.user_id == user.id,
        models.IntegrationAccount.revoked_at.is_(None)
    ).all()
    
    return {
        "integrations": [
            {
                "id": integration.id,
                "provider": integration.provider,
                "scopes": integration.scopes,
                "connected_at": integration.created_at,
                "expires_at": integration.expires_at
            }
            for integration in integrations
        ]
    }


@router.delete("/google/disconnect")
async def disconnect_google(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Google Calendar integration."""
    user = current_user or get_or_create_demo_user(db)
    
    integration = db.query(models.IntegrationAccount).filter(
        models.IntegrationAccount.user_id == user.id,
        models.IntegrationAccount.provider == "google",
        models.IntegrationAccount.revoked_at.is_(None)
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail={"code": "INTEGRATION_NOT_FOUND", "message": "Google integration not found"})
    
    try:
        oauth_service.revoke_integration(db, integration)
        return {"message": "Google Calendar integration disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "REVOKE_ERROR", "message": f"Failed to disconnect: {e}"})


@router.post("/webhooks/google", status_code=200)
async def google_webhook(
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Handle Google Calendar webhook notifications."""
    # Extract resource information from webhook
    resource_id = request.get('resourceId')
    resource_state = request.get('resourceState')
    
    if not resource_id or resource_state not in ['exists', 'not_exists']:
        return {"message": "ignored"}
        
    # Find integration by resource ID (stored in sync_token for simplicity)
    integration = db.query(models.IntegrationAccount).filter(
        models.IntegrationAccount.provider == "google",
        models.IntegrationAccount.sync_token.contains(resource_id)
    ).first()
    
    if not integration:
        return {"message": "integration not found"}
        
    try:
        # Trigger incremental sync for this user
        result = google_service.sync_events(db, integration.user_id)
        return {"message": "sync completed", "events": result.get("syncedEvents", 0)}
    except Exception as e:
        return {"message": "sync failed", "error": str(e)}