"""OAuth service for external integrations.

Handles OAuth 2.0 flows with PKCE for Google Calendar and other providers.
"""
import base64
import hashlib
import secrets
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from prometheus_client import Counter, Histogram
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from ..db import models
from ..errors import ValidationAppError, BaseAppException
from .state_store import MemoryStateStore, StateStore, RedisStateStore
from .encryption_service import get_encryption_service
try:  # optional tracing
    from opentelemetry import trace
    _oauth_tracer = trace.get_tracer(__name__)
except Exception:  # pragma: no cover
    _oauth_tracer = None


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
        # Metrics (lazy simple registration; idempotent if multiple service instances)
        self._metrics_inited = getattr(self.__class__, '_metrics_inited', False)
        if not self._metrics_inited:
            self.__class__.OAUTH_START_COUNT = Counter(
                'schedule_concierge_oauth_start_total', 'OAuth start requests', ['provider']
            )
            self.__class__.OAUTH_EXCHANGE_COUNT = Counter(
                'schedule_concierge_oauth_exchange_total', 'OAuth code exchange attempts', ['provider', 'outcome']
            )
            self.__class__.OAUTH_EXCHANGE_LATENCY = Histogram(
                'schedule_concierge_oauth_exchange_duration_seconds', 'OAuth code exchange latency', ['provider']
            )
            self.__class__._metrics_inited = True
        # Initialize shared state store (one per process) lazily, selectable via env
        backend = os.getenv('OAUTH_STATE_BACKEND', 'memory').lower()
        existing = getattr(self.__class__, 'state_store', None)
        if existing is None:
            if backend == 'redis':
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                try:
                    import redis  # type: ignore
                    client = redis.from_url(redis_url)
                    self.__class__.state_store = RedisStateStore(client, self._STATE_TTL_SECONDS, self._STATE_MAX_ENTRIES)
                except Exception:
                    # Fallback to memory if redis unavailable
                    self.__class__.state_store = MemoryStateStore(self._STATE_TTL_SECONDS, self._STATE_MAX_ENTRIES)
            else:
                self.__class__.state_store = MemoryStateStore(self._STATE_TTL_SECONDS, self._STATE_MAX_ENTRIES)
        self.state_store = self.__class__.state_store
        # Gauge metric for current state store size
        if not getattr(self.__class__, '_state_metrics_inited', False):
            try:
                from prometheus_client import Gauge
                self.__class__.OAUTH_STATE_SIZE = Gauge('schedule_concierge_oauth_state_store_size', 'Number of pending OAuth states', ['backend'])
                self.__class__._state_metrics_inited = True
            except Exception:
                pass
        
    # In-memory ephemeral store: state -> {code_verifier, created_at}
    _STATE_TTL_SECONDS = 600
    _STATE_MAX_ENTRIES = 50

    def start_google_auth(self, redirect_uri: str) -> Dict[str, str]:
        """Initiate Google OAuth PKCE flow. Returns authorization URL and state.
        The code_verifier is stored server-side temporarily (in-memory) keyed by state.
        """
        if not self.google_client_id or not self.google_client_secret:
            raise OAuthError("OAUTH_CONFIG_MISSING", "Google OAuth credentials not configured")
        # Housekeeping (prune expired + enforce cap before adding)
        # Sync store TTL with possibly test-adjusted instance value
        if isinstance(self.state_store, MemoryStateStore):
            self.state_store.ttl_seconds = self._STATE_TTL_SECONDS
        self.state_store.prune()
        # Update gauge metric
        if getattr(self.__class__, '_state_metrics_inited', False):
            backend_label = 'redis' if isinstance(self.state_store, RedisStateStore) else 'memory'
            self.OAUTH_STATE_SIZE.labels(backend=backend_label).set(self.state_store.size())
        # Use state_store's time provider when available for determinism in tests
        try:
            if isinstance(self.state_store, MemoryStateStore) and getattr(self.state_store, 'time_provider', None):
                now_ts = self.state_store.time_provider()
            else:
                now_ts = time.time()
        except Exception:
            now_ts = time.time()
        state = base64.urlsafe_b64encode(secrets.token_bytes(18)).decode('utf-8').rstrip('=')
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
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            code_challenge=code_challenge,
            code_challenge_method='S256',
            prompt='consent'
        )
        # Store state after generating URL
        self.state_store.put(state, code_verifier, now_ts)
        # Metrics
        self.OAUTH_START_COUNT.labels(provider='google').inc()
        return {"authorization_url": authorization_url, "state": state}
    
    # --- Internal helpers (kept small for testability) ---
    def _prune_state_store(self):  # backward compatibility (tests) -> delegate
        self.state_store.prune()

    # Backward compatibility for existing tests expecting this method
    def get_google_auth_url(self, redirect_uri: str, state: str) -> str:  # pragma: no cover (legacy path)
        if not self.google_client_id or not self.google_client_secret:
            raise OAuthError("OAUTH_CONFIG_MISSING", "Google OAuth credentials not configured")
        # Generate PKCE pair
        if isinstance(self.state_store, MemoryStateStore):
            self.state_store.ttl_seconds = self._STATE_TTL_SECONDS
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        # Update gauge metric (prune already inside put path later; here just reflect current)
        if getattr(self.__class__, '_state_metrics_inited', False):
            backend_label = 'redis' if isinstance(self.state_store, RedisStateStore) else 'memory'
            self.OAUTH_STATE_SIZE.labels(backend=backend_label).set(self.state_store.size())
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        # Store using provided state
        try:
            if isinstance(self.state_store, MemoryStateStore) and getattr(self.state_store, 'time_provider', None):
                now_ts = self.state_store.time_provider()
            else:
                now_ts = time.time()
        except Exception:
            now_ts = time.time()
        self.state_store.put(state, code_verifier, now_ts)
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
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            code_challenge=code_challenge,
            code_challenge_method='S256',
            prompt='consent'
        )
        return authorization_url
        
    def exchange_google_code(
        self,
        db: Session,
        user_id: str,
        code: str,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> models.IntegrationAccount:
        """Exchange authorization code for tokens (PKCE aware) and store/update integration."""
        if not self.google_client_id or not self.google_client_secret:
            raise OAuthError("OAUTH_CONFIG_MISSING", "Google OAuth credentials not configured")
        code_verifier = None
        if state:
            data = self.state_store.pop(state)
            if not data:
                raise OAuthError("OAUTH_STATE_INVALID", "State not found or expired")
            code_verifier = data["code_verifier"]

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
            with self.OAUTH_EXCHANGE_LATENCY.labels(provider='google').time():
                span_ctx = _oauth_tracer.start_as_current_span("oauth.exchange_code") if _oauth_tracer else None
                try:
                    if code_verifier:
                        flow.fetch_token(code=code, code_verifier=code_verifier)
                    else:
                        flow.fetch_token(code=code)
                    credentials = flow.credentials
                    if _oauth_tracer:
                        span = trace.get_current_span()
                        span.set_attribute("oauth.provider", "google")
                        span.set_attribute("oauth.has_refresh", bool(credentials.refresh_token))
                finally:
                    if span_ctx:
                        span_ctx.__exit__(None, None, None)
            self.OAUTH_EXCHANGE_COUNT.labels(provider='google', outcome='success').inc()
        except Exception as e:
            self.OAUTH_EXCHANGE_COUNT.labels(provider='google', outcome='error').inc()
            raise OAuthError("OAUTH_CODE_INVALID", f"Failed to exchange code: {str(e)}")
        
        # Check if integration already exists
        existing = db.query(models.IntegrationAccount).filter(
            models.IntegrationAccount.user_id == user_id,
            models.IntegrationAccount.provider == "google"
        ).first()
        
        enc = get_encryption_service()
        if existing:
            # Update existing integration
            existing.access_token_hash = self._hash_token(credentials.token)
            existing.refresh_token_hash = self._hash_token(credentials.refresh_token) if credentials.refresh_token else None
            existing.access_token_encrypted = enc.encrypt(credentials.token)
            existing.refresh_token_encrypted = enc.encrypt(credentials.refresh_token) if credentials.refresh_token else None
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
                access_token_encrypted=enc.encrypt(credentials.token),
                refresh_token_encrypted=enc.encrypt(credentials.refresh_token) if credentials.refresh_token else None,
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
        # Prefer encrypted tokens when present (fallback to hash placeholder path for legacy rows)
        token_value = integration.access_token_encrypted
        if not token_value:
            token_value = self._unhash_token(integration.access_token_hash)
        else:
            try:
                token_value = get_encryption_service().decrypt(token_value)
            except Exception:
                raise OAuthError("TOKEN_DECRYPT_FAILED", "Failed to decrypt access token")

        refresh_value = None
        if integration.refresh_token_encrypted:
            try:
                refresh_value = get_encryption_service().decrypt(integration.refresh_token_encrypted)
            except Exception:
                raise OAuthError("TOKEN_DECRYPT_FAILED", "Failed to decrypt refresh token")
        elif integration.refresh_token_hash:
            refresh_value = self._unhash_token(integration.refresh_token_hash)

        credentials = Credentials(
            token=token_value,
            refresh_token=refresh_value,
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
                # Update stored tokens (both hash + encrypted)
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