import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';
import OAuthCallback from '../../pages/oauth/callback';
import { apiClient } from '../../services/api-client';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: jest.fn()
}));
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;

// Mock API client
jest.mock('../../services/api-client', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  }
}));
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Mock sessionStorage
const mockSessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
});

describe('OAuthCallback', () => {
  const mockPush = jest.fn();
  const mockRouter = {
    isReady: true,
    query: {},
    push: mockPush,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
  });

  it('should show processing state initially', () => {
    mockRouter.isReady = false;
    
    render(<OAuthCallback />);
    
    expect(screen.getByText('Processing OAuth callback...')).toBeInTheDocument();
    expect(screen.getByText('⏳')).toBeInTheDocument();
  });

  it('should handle successful OAuth callback', async () => {
    mockRouter.query = {
      code: 'auth_code_123',
      state: 'test_state'
    };
    
    mockSessionStorage.getItem.mockReturnValue('test_state');
    mockApiClient.post.mockResolvedValue({});

    render(<OAuthCallback />);

    await waitFor(() => {
      expect(screen.getByText('Google Calendar connected successfully!')).toBeInTheDocument();
      expect(screen.getByText('✅')).toBeInTheDocument();
    });

    expect(mockApiClient.post).toHaveBeenCalledWith('/integrations/google/connect', {
      code: 'auth_code_123',
      redirect_uri: 'http://localhost/oauth/callback'
    });

    expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state');

    // Should redirect after success
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    }, { timeout: 3000 });
  });

  it('should handle OAuth error response', async () => {
    mockRouter.query = {
      error: 'access_denied',
      error_description: 'User denied access'
    };

    render(<OAuthCallback />);

    await waitFor(() => {
      expect(screen.getByText('OAuth error: access_denied')).toBeInTheDocument();
      expect(screen.getByText('❌')).toBeInTheDocument();
    });
  });

  it('should handle invalid state parameter', async () => {
    mockRouter.query = {
      code: 'auth_code_123',
      state: 'invalid_state'
    };
    
    mockSessionStorage.getItem.mockReturnValue('different_state');

    render(<OAuthCallback />);

    await waitFor(() => {
      expect(screen.getByText('Invalid state parameter')).toBeInTheDocument();
      expect(screen.getByText('❌')).toBeInTheDocument();
    });
  });

  it('should handle API connection failure', async () => {
    mockRouter.query = {
      code: 'auth_code_123',
      state: 'test_state'
    };
    
    mockSessionStorage.getItem.mockReturnValue('test_state');
    mockApiClient.post.mockRejectedValue({
      response: {
        data: {
          detail: {
            message: 'Invalid authorization code'
          }
        }
      }
    });

    render(<OAuthCallback />);

    await waitFor(() => {
      expect(screen.getByText('Invalid authorization code')).toBeInTheDocument();
      expect(screen.getByText('❌')).toBeInTheDocument();
    });
  });

  it('should show return button on error', async () => {
    mockRouter.query = {
      error: 'access_denied'
    };

    render(<OAuthCallback />);

    await waitFor(() => {
      expect(screen.getByText('Return to Main Page')).toBeInTheDocument();
    });
  });
});