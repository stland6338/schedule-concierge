import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GoogleCalendarIntegration } from '../../components/GoogleCalendarIntegration';
import { apiClient } from '../../services/api-client';

// Mock API client
jest.mock('../../services/api-client', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  }
}));
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Mock window.location (jsdom will log a navigation warning, but tests remain green)
delete (window as any).location;
(window as any).location = {
  origin: 'http://localhost:3000',
  href: '',
};

describe('GoogleCalendarIntegration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock sessionStorage
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      writable: true,
    });
  });

  describe('when no integration exists', () => {
    beforeEach(() => {
      mockApiClient.get.mockResolvedValue({ integrations: [] });
    });

    it('should render connect button', async () => {
      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Connect Google Calendar')).toBeInTheDocument();
      });
    });

    it('should start OAuth flow when connect button is clicked', async () => {
      const mockAuthResponse = {
        authorization_url: 'https://accounts.google.com/oauth/authorize?client_id=test',
        state: 'test_state'
      };
      
      mockApiClient.get.mockResolvedValueOnce({ integrations: [] });
      mockApiClient.get.mockResolvedValueOnce(mockAuthResponse);

      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Connect Google Calendar')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Connect Google Calendar'));

      await waitFor(() => {
        expect(mockApiClient.get).toHaveBeenCalledWith(
          '/integrations/google/auth-url?redirect_uri=http%3A//localhost%3A3000/oauth/callback'
        );
      });

      expect(window.sessionStorage.setItem).toHaveBeenCalledWith('oauth_state', 'test_state');
    });
  });

  describe('when integration exists', () => {
    const mockIntegration = {
      id: 'integration-1',
      provider: 'google',
      scopes: ['calendar.readonly', 'calendar.events'],
      connected_at: '2025-08-13T10:00:00Z',
      expires_at: '2025-08-14T10:00:00Z'
    };

    beforeEach(() => {
      mockApiClient.get.mockResolvedValue({ 
        integrations: [mockIntegration] 
      });
    });

    it('should show connected status', async () => {
      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('✅ Connected to Google Calendar')).toBeInTheDocument();
      });
    });

    it('should show sync controls', async () => {
      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Sync Calendars')).toBeInTheDocument();
        expect(screen.getByText('Sync Events')).toBeInTheDocument();
        expect(screen.getByText('Disconnect')).toBeInTheDocument();
      });
    });

    it('should sync calendars when button is clicked', async () => {
      const mockSyncResponse = {
        syncedCalendars: 2,
        calendars: [
          { id: 'cal1', name: 'Primary' },
          { id: 'cal2', name: 'Work' }
        ]
      };
      
      mockApiClient.post.mockResolvedValue(mockSyncResponse);

      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Sync Calendars')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Sync Calendars'));

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith('/integrations/google/sync-calendars');
      });

      await waitFor(() => {
        expect(screen.getByText('Calendars synced: 2')).toBeInTheDocument();
        expect(screen.getByText('Primary')).toBeInTheDocument();
        expect(screen.getByText('Work')).toBeInTheDocument();
      });
    });

    it('should sync events when button is clicked', async () => {
      const mockSyncResponse = { syncedEvents: 5 };
      mockApiClient.post.mockResolvedValue(mockSyncResponse);

      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Sync Events')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Sync Events'));

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith('/integrations/google/sync-events');
      });

      await waitFor(() => {
        expect(screen.getByText('Events synced: 5')).toBeInTheDocument();
      });
    });

    it('should disconnect integration', async () => {
      mockApiClient.delete.mockResolvedValue({ message: 'Disconnected' });
      
      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Disconnect')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Disconnect'));

      await waitFor(() => {
        expect(mockApiClient.delete).toHaveBeenCalledWith('/integrations/google/disconnect');
      });
    });
  });

  describe('error handling', () => {
    it('should display error when API calls fail', async () => {
      mockApiClient.get.mockRejectedValue(new Error('API Error'));

      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load integrations')).toBeInTheDocument();
      });
    });

    it('should handle sync errors gracefully', async () => {
      mockApiClient.get.mockResolvedValue({ integrations: [
        {
          id: 'integration-1',
          provider: 'google',
          scopes: ['calendar.readonly'],
          connected_at: '2025-08-13T10:00:00Z',
          expires_at: '2025-08-14T10:00:00Z'
        }
      ]});
      
      mockApiClient.post.mockRejectedValue(new Error('Sync failed'));

      render(<GoogleCalendarIntegration />);
      
      await waitFor(() => {
        expect(screen.getByText('Sync Calendars')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Sync Calendars'));

      await waitFor(() => {
        expect(screen.getByText('Failed to sync calendars')).toBeInTheDocument();
      });
    });
  });
});