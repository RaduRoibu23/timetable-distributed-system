import { useState } from 'react';
import { login } from '../services/authService';
import { CONFIG } from '../config';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const doLogin = async (u, p) => {
    setError('');
    setLoading(true);
    try {
      const tokens = await login(u, p);
      onLogin(tokens);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await doLogin(username, password);
  };

  const demoUsers = CONFIG.demoUsers || [];

  const loginPreset = async (u) => {
    // ca să vezi în UI cu ce user ești logat
    setUsername(u.username);
    setPassword(u.password);
    await doLogin(u.username, u.password);
  };

  return (
      <div className="loginPage">
       <div className="loginCard">
          <div className="title">Login</div>
          <div className="subtitle">Keycloak Direct Grant</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <div className="label">Username</div>
            <input
              className="input"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="user"
              required
            />
          </div>

          <div className="field">
            <div className="label">Password</div>
            <input
              className="input"
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="parola"
              required
            />
          </div>

          <div className="row row-wrap">
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Se conectează...' : 'Login'}
            </button>

            {demoUsers.map((u) => (
              <button
                key={u.label}
                className="btn"
                type="button"
                onClick={() => loginPreset(u)}
                disabled={loading}
                title={`Login: ${u.username}`}
              >
                Login {u.label}
              </button>
            ))}
          </div>

          <div className="hint" style={{ marginTop: '10px' }}>
            Keycloak: <code className="inline">{CONFIG.keycloak.url}</code><br />
            Realm: <code className="inline">{CONFIG.keycloak.realm}</code><br />
            Client: <code className="inline">{CONFIG.keycloak.clientId}</code>
          </div>

          {error && <div className="alert">{error}</div>}
        </form>
      </div>
  );
}
