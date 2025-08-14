from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..services.oauth_service import OAuthService, OAuthError
from ..db import models
from .auth import get_current_user_optional

router = APIRouter(prefix="/oauth", tags=["oauth"])

oauth_service = OAuthService()

@router.get("/google/auth")
def start_google_auth(redirect_uri: str = Query(...)):
    try:
        return oauth_service.start_google_auth(redirect_uri)
    except OAuthError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})

@router.post("/google/exchange")
def exchange_google_code(
    code: str = Query(...),
    redirect_uri: str = Query(...),
    state: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional)
):
    if not current_user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "login required"})
    try:
        integration = oauth_service.exchange_google_code(db, current_user.id, code, redirect_uri, state)
        return {
            "id": integration.id,
            "provider": integration.provider,
            "scopes": integration.scopes,
            "expiresAt": integration.expires_at,
        }
    except OAuthError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})
