import { useState, useEffect } from 'react';
import { rolesFromToken, tokenExpiryText, refreshAccessToken, loadSession } from '../services/authService';
import { apiGet } from '../services/apiService';
import { CONFIG } from '../config';
import ActionsList from './ActionsList';
import ResultsPanel from './ResultsPanel';

export default function Dashboard({ accessToken, idToken, onRefreshToken, onLogout }) {
  const [userInfo, setUserInfo] = useState(null);
  const [results, setResults] = useState({ title: '', content: '', visible: false });

  useEffect(() => {
    if (accessToken) {
      loadUserInfo();
    }
  }, [accessToken]);

  const loadUserInfo = async () => {
    try {
      const data = await apiGet('/me', accessToken);
      setUserInfo(data);
    } catch (err) {
      console.error('Failed to load user info:', err);
    }
  };

  const handleRefreshToken = async () => {
    try {
      const session = loadSession();
      if (session?.refreshToken) {
        const tokens = await refreshAccessToken(session.refreshToken);
        onRefreshToken(tokens);
        await loadUserInfo();
      }
    } catch (err) {
      console.error('Token refresh failed:', err);
    }
  };

  const roles = rolesFromToken(accessToken);
  const tokenExp = tokenExpiryText(accessToken);

  return (
    <div className="card" id="dashboard-card">
      <div className="card-header">
        <h2>Dashboard</h2>
        <p>Informații sesiune, roluri și operații demo pe API.</p>
      </div>

      <div className="card-body">
        <div className="dashboard-grid">
          <div className="dashboard-left">
            <div className="kv">
              <div className="k">User</div>
              <div className="v" id="user-info">
                {userInfo ? `${userInfo.username || '—'}` : '—'}
              </div>

              <div className="k">Roles</div>
              <div className="v">
                <div className="pills">
                  {roles.map((role) => (
                    <span key={role} className="pill ok">
                      {role}
                    </span>
                  ))}
                </div>
              </div>

              <div className="k">Token expires</div>
              <div className="v" id="token-exp">{tokenExp}</div>

              <div className="k">API Base</div>
              <div className="v">
                <code className="inline">{CONFIG.api.baseUrl}</code>
              </div>
            </div>

            <ActionsList
              accessToken={accessToken}
              roles={roles}
              onActionResult={(title, content) => {
                setResults({ title, content, visible: true });
              }}
            />
          </div>

          <div className="dashboard-right">
            <ResultsPanel
              title={results.title}
              content={results.content}
              visible={results.visible}
              onClose={() => setResults({ ...results, visible: false })}
            />
          </div>
        </div>

        <div className="row row-wrap" style={{ marginTop: '12px' }}>
          <button className="btn" onClick={handleRefreshToken}>
            Refresh token
          </button>
          <button className="btn btn-danger" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
