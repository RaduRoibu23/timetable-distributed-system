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
        <div className="subtitle">Timetable Management System</div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <div className="label">Username</div>
            <input
              className="input"
              id="username"
              name="username"
              autoComplete="off"
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
              name="password"
              autoComplete="off"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="parola"
              required
            />
          </div>

          <button className="btn btn-primary loginMainBtn" type="submit" disabled={loading}>
            {loading ? 'Se conecteaza...' : 'Login'}
          </button>

          <div className="quickLoginGrid">
            {demoUsers.map((u) => (
              <button
                key={u.label}
                className="btn btnSmall"
                type="button"
                onClick={() => loginPreset(u)}
                disabled={loading}
                title={`Login: ${u.username}`}
              >
                {u.label}
              </button>
            ))}
          </div>

          {error && <div className="alert">{error}</div>}
        </form>
      </div>

      <div className="loginFooter">
        {CONFIG.keycloak.url} | {CONFIG.keycloak.realm} | {CONFIG.keycloak.clientId}
      </div>
    </div>
  );
}
