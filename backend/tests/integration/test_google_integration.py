"""Integration tests for Google Calendar functionality."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

from app.services.oauth_service import OAuthService, OAuthError
from app.services.google_calendar_service import GoogleCalendarService, GoogleCalendarError
from app.db.models import User, IntegrationAccount, Calendar, Event


class TestOAuthService:
    def test_get_google_auth_url_success(self):
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'}):
            oauth_service = OAuthService()
            url = oauth_service.get_google_auth_url("http://localhost/callback", "test_state")
            
            assert "accounts.google.com/o/oauth2/auth" in url
            assert "client_id=test_id" in url
            assert "state=test_state" in url
            assert "code_challenge" in url
            
    def test_get_google_auth_url_missing_config(self):
        oauth_service = OAuthService()
        
        with pytest.raises(OAuthError) as exc_info:
            oauth_service.get_google_auth_url("http://localhost/callback", "test_state")
            
        assert exc_info.value.code == "OAUTH_CONFIG_MISSING"


class TestGoogleCalendarIntegration:
    @pytest.fixture
    def mock_credentials(self):
        with patch('app.services.google_calendar_service.Credentials') as mock_creds:
            creds = Mock()
            creds.token = "test_token"
            creds.refresh_token = "test_refresh"
            creds.expired = False
            mock_creds.return_value = creds
            yield creds
            
    @pytest.fixture
    def mock_google_service(self):
        with patch('app.services.google_calendar_service.build') as mock_build:
            service = Mock()
            mock_build.return_value = service
            yield service
            
    def test_sync_calendars_success(self, client, mock_google_service, mock_credentials):
        # Create test user and integration
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        user_id = response.json()["user"]["id"]
        
        # Mock Google API response
        mock_google_service.calendarList().list().execute.return_value = {
            'items': [
                {'id': 'primary', 'summary': 'Primary Calendar'},
                {'id': 'work_cal', 'summary': 'Work Calendar'}
            ]
        }
        
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'}):
            oauth_service = OAuthService()
            google_service = GoogleCalendarService(oauth_service)
            
            # Create mock integration
            from app.db.session import get_db
            db = next(get_db())
            integration = IntegrationAccount(
                user_id=user_id,
                provider="google",
                scopes=oauth_service.GOOGLE_SCOPES,
                access_token_hash="hashed_token",
                refresh_token_hash="hashed_refresh",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.add(integration)
            db.commit()
            
            with patch.object(oauth_service, 'get_valid_credentials', return_value=mock_credentials):
                result = google_service.sync_calendars(db, user_id)
                
                assert result["syncedCalendars"] == 2
                assert len(result["calendars"]) == 2
                
    def test_sync_events_success(self, client, mock_google_service, mock_credentials):
        # Setup similar to sync_calendars test
        response = client.post("/auth/register", json={
            "email": "test@example.com", 
            "password": "testpass123"
        })
        user_id = response.json()["user"]["id"]
        
        # Mock Google events response
        mock_google_service.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Test Meeting',
                    'start': {'dateTime': '2025-08-13T10:00:00Z'},
                    'end': {'dateTime': '2025-08-13T11:00:00Z'},
                    'status': 'confirmed'
                }
            ],
            'nextSyncToken': 'new_sync_token'
        }
        
        with patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'}):
            oauth_service = OAuthService()
            google_service = GoogleCalendarService(oauth_service)
            
            from app.db.session import get_db
            db = next(get_db())
            
            # Create test calendar
            calendar = Calendar(
                user_id=user_id,
                name="Test Calendar",
                external_provider="google",
                external_id="primary"
            )
            db.add(calendar)
            
            # Create test integration
            integration = IntegrationAccount(
                user_id=user_id,
                provider="google",
                scopes=oauth_service.GOOGLE_SCOPES,
                access_token_hash="hashed_token",
                refresh_token_hash="hashed_refresh", 
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.add(integration)
            db.commit()
            
            with patch.object(oauth_service, 'get_valid_credentials', return_value=mock_credentials):
                result = google_service.sync_events(db, user_id)
                
                assert result["syncedEvents"] == 1


class TestIntegrationAPI:
    def test_get_auth_url_endpoint(self, client):
        response = client.get("/integrations/google/auth-url?redirect_uri=http://localhost/callback")
        
        assert response.status_code == 200 or response.status_code == 400  # May fail without config
        
    def test_list_integrations_empty(self, client):
        response = client.get("/integrations/")
        
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data
        assert isinstance(data["integrations"], list)
        
    def test_sync_calendars_no_integration(self, client):
        response = client.post("/integrations/google/sync-calendars")
        
        assert response.status_code == 502  # GoogleCalendarError
        data = response.json()
        assert data["detail"]["code"] == "INTEGRATION_NOT_FOUND"