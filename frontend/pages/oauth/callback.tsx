import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { apiClient } from '../../services/api-client';

export default function OAuthCallback() {
  const router = useRouter();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing OAuth callback...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const { code, state, error } = router.query;

        // Check for OAuth error
        if (error) {
          setStatus('error');
          setMessage(`OAuth error: ${error}`);
          return;
        }

        // Verify state parameter
        const storedState = sessionStorage.getItem('oauth_state');
        if (!state || state !== storedState) {
          setStatus('error');
          setMessage('Invalid state parameter');
          return;
        }

        // Clear stored state
        sessionStorage.removeItem('oauth_state');

        if (!code) {
          setStatus('error');
          setMessage('No authorization code received');
          return;
        }

        // Exchange code for tokens
  const origin = (typeof window !== 'undefined' && (window as any).location?.origin) || 'http://localhost';
  const redirectUri = `${origin}/oauth/callback`;
        await apiClient.post('/integrations/google/connect', {
          code: code as string,
          redirect_uri: redirectUri
        });

        setStatus('success');
        setMessage('Google Calendar connected successfully!');
        
        // Redirect to main page after 2 seconds
        setTimeout(() => {
          router.push('/');
        }, 2000);

      } catch (err: any) {
        setStatus('error');
        setMessage(err.response?.data?.detail?.message || 'Failed to connect Google Calendar');
      }
    };

  // Defer to next tick so initial state renders
  setTimeout(() => { handleCallback(); }, 0);
  }, []);

  return (
    <div className="oauth-callback">
      <div className="callback-container">
        <h2>Google Calendar Integration</h2>
        
        <div className={`status-message ${status}`}>
          {status === 'processing' && <div className="spinner">⏳</div>}
          {status === 'success' && <div className="success">✅</div>}
          {status === 'error' && <div className="error">❌</div>}
          <p>{message}</p>
        </div>

        {status === 'success' && (
          <p className="redirect-message">Redirecting to main page...</p>
        )}

        {status === 'error' && (
          <button onClick={() => router.push('/')} className="return-button">
            Return to Main Page
          </button>
        )}
      </div>

      <style jsx>{`
        .oauth-callback {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background-color: #f5f5f5;
        }
        .callback-container {
          background: white;
          padding: 2rem;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
          text-align: center;
          max-width: 400px;
        }
        .status-message {
          margin: 2rem 0;
        }
        .status-message.processing {
          color: #666;
        }
        .status-message.success {
          color: #28a745;
        }
        .status-message.error {
          color: #dc3545;
        }
        .spinner, .success, .error {
          font-size: 2rem;
          margin-bottom: 1rem;
        }
        .redirect-message {
          color: #666;
          font-style: italic;
        }
        .return-button {
          background: #007bff;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          margin-top: 1rem;
        }
        .return-button:hover {
          background: #0056b3;
        }
      `}</style>
    </div>
  );
}