import { useState, useEffect } from 'react';
import { login } from '../services/authService';
import { CONFIG } from '../config';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const tokens = await login(username, password);
      onLogin(tokens);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const fillSysadmin = () => {
    setUsername('sysadmin01');
    setPassword('sysadmin01');
  };

  const fillStudent = () => {
    setUsername('student01');
    setPassword('student01');
  };

  return (
    <div className="card" id="login-card">
      <div className="card-header">
        <h2>Autentificare</h2>
        <p>Login simplu prin Keycloak Direct Grant (pentru demo/proiect).</p>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="field">
            <div className="label">Username</div>
            <input
              className="input"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ex: admin / student1"
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
            <button className="btn" type="button" onClick={fillSysadmin}>
              Autofill sysadmin
            </button>
            <button className="btn" type="button" onClick={fillStudent}>
              Autofill student
            </button>
          </div>

          <div className="hint" style={{ marginTop: '10px' }}>
            Keycloak: <code className="inline">{CONFIG.keycloak.url}</code><br />
            Realm: <code className="inline">{CONFIG.keycloak.realm}</code><br />
            Client: <code className="inline">{CONFIG.keycloak.clientId}</code>
          </div>

          {error && (
            <div className="alert">{error}</div>
          )}
        </form>
      </div>
    </div>
  );
}
