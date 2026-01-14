import { useState, useEffect } from 'react';
import { loadSession, clearSession } from './services/authService';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Header from './components/Header';

function App() {
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState('neautentificat');

  useEffect(() => {
    const savedSession = loadSession();
    if (savedSession?.accessToken) {
      setSession(savedSession);
      setStatus('autentificat');
    }
  }, []);

  const handleLogin = (tokens) => {
    setSession(tokens);
    setStatus('autentificat');
  };

  const handleLogout = () => {
    clearSession();
    setSession(null);
    setStatus('neautentificat');
  };

  const handleRefreshToken = (tokens) => {
    setSession(tokens);
  };

  return (
    <div className="container">
      <Header status={status} />
      
      <div className="grid">
        {!session ? (
          <Login onLogin={handleLogin} />
        ) : (
          <Dashboard
            accessToken={session.accessToken}
            idToken={session.idToken}
            onRefreshToken={handleRefreshToken}
            onLogout={handleLogout}
          />
        )}
      </div>
    </div>
  );
}

export default App;
