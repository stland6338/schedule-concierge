import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api-client';

interface Integration {
  id: string;
  provider: string;
  scopes: string[];
  connected_at: string;
  expires_at: string;
}

interface SyncResult {
  syncedCalendars?: number;
  syncedEvents?: number;
  calendars?: Array<{ id: string; name: string }>;
}

export function GoogleCalendarIntegration() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    try {
      const response = await apiClient.get('/integrations/');
      setIntegrations(response.integrations || []);
    } catch (err) {
      setError('Failed to load integrations');
    }
  };

  const connectGoogle = async () => {
    setIsConnecting(true);
    setError(null);
    
    try {
      const redirectUri = `${window.location.origin}/oauth/callback`;
      const authResponse = await apiClient.get(`/integrations/google/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`);
      
      // Store state for verification
      sessionStorage.setItem('oauth_state', authResponse.state);
      
      // Redirect to Google OAuth
      window.location.href = authResponse.authorization_url;
    } catch (err) {
      setError('Failed to start Google connection');
      setIsConnecting(false);
    }
  };

  const syncCalendars = async () => {
    setIsSyncing(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/integrations/google/sync-calendars');
      setSyncResult(response);
      await loadIntegrations(); // Refresh integration list
    } catch (err) {
      setError('Failed to sync calendars');
    } finally {
      setIsSyncing(false);
    }
  };

  const syncEvents = async () => {
    setIsSyncing(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/integrations/google/sync-events');
      setSyncResult(response);
    } catch (err) {
      setError('Failed to sync events');
    } finally {
      setIsSyncing(false);
    }
  };

  const disconnectGoogle = async () => {
    try {
      await apiClient.delete('/integrations/google/disconnect');
      await loadIntegrations();
      setSyncResult(null);
    } catch (err) {
      setError('Failed to disconnect Google Calendar');
    }
  };

  const googleIntegration = integrations.find(i => i.provider === 'google');

  return (
    <div className="google-calendar-integration">
      <h3>Google Calendar Integration</h3>
      
      {error && (
        <div className="error-message" style={{ color: 'red', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {!googleIntegration ? (
        <div className="connect-section">
          <p>Connect your Google Calendar to sync events automatically.</p>
          <button 
            onClick={connectGoogle} 
            disabled={isConnecting}
            className="connect-button"
          >
            {isConnecting ? 'Connecting...' : 'Connect Google Calendar'}
          </button>
        </div>
      ) : (
        <div className="connected-section">
          <div className="integration-status">
            <h4>✅ Connected to Google Calendar</h4>
            <p>Connected on: {new Date(googleIntegration.connected_at).toLocaleDateString()}</p>
            <p>Expires: {new Date(googleIntegration.expires_at).toLocaleDateString()}</p>
          </div>

          <div className="sync-controls">
            <button 
              onClick={syncCalendars} 
              disabled={isSyncing}
              className="sync-button"
            >
              {isSyncing ? 'Syncing...' : 'Sync Calendars'}
            </button>
            <button 
              onClick={syncEvents} 
              disabled={isSyncing}
              className="sync-button"
            >
              {isSyncing ? 'Syncing...' : 'Sync Events'}
            </button>
            <button 
              onClick={disconnectGoogle}
              className="disconnect-button"
            >
              Disconnect
            </button>
          </div>

          {syncResult && (
            <div className="sync-result">
              <h4>Last Sync Result:</h4>
              {syncResult.syncedCalendars !== undefined && (
                <p>Calendars synced: {syncResult.syncedCalendars}</p>
              )}
              {syncResult.syncedEvents !== undefined && (
                <p>Events synced: {syncResult.syncedEvents}</p>
              )}
              {syncResult.calendars && (
                <div>
                  <p>Available calendars:</p>
                  <ul>
                    {syncResult.calendars.map(cal => (
                      <li key={cal.id}>{cal.name}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .google-calendar-integration {
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 1.5rem;
          margin: 1rem 0;
        }
        .connect-button, .sync-button {
          background: #4285f4;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          margin-right: 0.5rem;
          cursor: pointer;
        }
        .connect-button:disabled, .sync-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        .disconnect-button {
          background: #dc3545;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
        }
        .sync-result {
          background: #f8f9fa;
          padding: 1rem;
          border-radius: 4px;
          margin-top: 1rem;
        }
        .integration-status {
          margin-bottom: 1rem;
        }
      `}</style>
    </div>
  );
}

export default GoogleCalendarIntegration;