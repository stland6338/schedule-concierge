"""OAuth service for external integrations.

Handles OAuth 2.0 flows with PKCE for Google Calendar and other providers.
"""
import base64
import hashlib
import secrets
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from ..db import models
from ..errors import ValidationAppError, BaseAppException


class OAuthError(BaseAppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, http_status=400)


class OAuthService:
    """OAuth 2.0 service for external calendar integrations."""
    
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
    def get_google_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Google OAuth authorization URL with PKCE."""
        if not self.google_client_id or not self.google_client_secret:
            raise OAuthError("OAUTH_CONFIG_MISSING", "Google OAuth credentials not configured")
            
        # Create PKCE challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.GOOGLE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            code_challenge=code_challenge,
            code_challenge_method='S256'
        )
        
        return authorization_url
        
    def exchange_google_code(
        self, 
        db: Session, 
        user_id: str, 
        code: str, 
        redirect_uri: str
    ) -> models.IntegrationAccount:
        """Exchange authorization code for tokens and store integration."""
        if not self.google_client_id or not self.google_client_secret:
            raise OAuthError("OAUTH_CONFIG_MISSING", "Google OAuth credentials not configured")
            
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.GOOGLE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
        except Exception as e:
            raise OAuthError("OAUTH_CODE_INVALID", f"Failed to exchange code: {str(e)}")
        
        # Check if integration already exists
        existing = db.query(models.IntegrationAccount).filter(
            models.IntegrationAccount.user_id == user_id,
            models.IntegrationAccount.provider == "google"
        ).first()
        
        if existing:
            # Update existing integration
            existing.access_token_hash = self._hash_token(credentials.token)
            existing.refresh_token_hash = self._hash_token(credentials.refresh_token) if credentials.refresh_token else None
            existing.expires_at = credentials.expiry
            existing.scopes = self.GOOGLE_SCOPES
            existing.updated_at = datetime.now(timezone.utc)
            existing.revoked_at = None
            db.commit()
            return existing
        else:
            # Create new integration
            integration = models.IntegrationAccount(
                user_id=user_id,
                provider="google",
                scopes=self.GOOGLE_SCOPES,
                access_token_hash=self._hash_token(credentials.token),
                refresh_token_hash=self._hash_token(credentials.refresh_token) if credentials.refresh_token else None,
                expires_at=credentials.expiry,
                sync_token=None  # Will be set during first sync
            )
            db.add(integration)
            db.commit()
            return integration
            
    def get_valid_credentials(
        self, 
        db: Session, 
        integration: models.IntegrationAccount
    ) -> Credentials:
        """Get valid Google credentials, refreshing if necessary."""
        if integration.provider != "google":
            raise OAuthError("INVALID_PROVIDER", "Integration is not Google")
            
        if integration.revoked_at:
            raise OAuthError("INTEGRATION_REVOKED", "Integration has been revoked")
            
        # Create credentials object
        credentials = Credentials(
            token=self._unhash_token(integration.access_token_hash),
            refresh_token=self._unhash_token(integration.refresh_token_hash) if integration.refresh_token_hash else None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
            scopes=integration.scopes
        )
        
        # Check if token needs refresh
        if credentials.expired:
            if not credentials.refresh_token:
                raise OAuthError("TOKEN_EXPIRED", "Token expired and no refresh token available")
                
            try:
                credentials.refresh(GoogleRequest())
                # Update stored tokens
                integration.access_token_hash = self._hash_token(credentials.token)
                integration.expires_at = credentials.expiry
                integration.updated_at = datetime.now(timezone.utc)
                db.commit()
            except Exception as e:
                raise OAuthError("TOKEN_REFRESH_FAILED", f"Failed to refresh token: {str(e)}")
                
        return credentials
        
    def revoke_integration(self, db: Session, integration: models.IntegrationAccount):
        """Revoke an integration and mark as revoked."""
        if integration.provider == "google":
            try:
                credentials = self.get_valid_credentials(db, integration)
                # Revoke the token with Google
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
                requests.post(revoke_url)
            except Exception:
                pass  # Continue even if revocation fails
                
        integration.revoked_at = datetime.now(timezone.utc)
        db.commit()
        
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
        
    def _unhash_token(self, hashed: str) -> str:
        """Note: This is a placeholder. In production, use proper encryption/decryption."""
        # TODO: Implement proper token encryption/decryption with AES
        # For now, we'll store tokens in plaintext (development only)
        return hashed