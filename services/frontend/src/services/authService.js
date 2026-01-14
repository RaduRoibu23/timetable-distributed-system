import { CONFIG } from '../config';

const STORAGE_KEY = CONFIG.auth.storageKey;
const KEYCLOAK_URL = CONFIG.keycloak.url;
const REALM = CONFIG.keycloak.realm;
const CLIENT_ID = CONFIG.keycloak.clientId;

export function decodeJwt(token) {
  try {
    const parts = token.split('.');
    const payload = parts[1];
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

export function persistSession(accessToken, idToken, refreshToken) {
  const payload = {
    accessToken,
    idToken,
    refreshToken,
    savedAt: Date.now()
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
}

export function loadSession() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    return {
      accessToken: data.accessToken || null,
      idToken: data.idToken || null,
      refreshToken: data.refreshToken || null
    };
  } catch {
    return null;
  }
}

export function rolesFromToken(accessToken) {
  const tk = accessToken ? decodeJwt(accessToken) : null;
  const roles = (tk && tk.realm_access && Array.isArray(tk.realm_access.roles))
    ? tk.realm_access.roles
    : [];
  return roles;
}

export function tokenExpiryText(token) {
  const tk = token ? decodeJwt(token) : null;
  if (!tk || !tk.exp) return '—';
  const ms = tk.exp * 1000;
  const d = new Date(ms);
  return `${d.toLocaleString()} (exp=${tk.exp})`;
}

export async function login(username, password) {
  const response = await fetch(
    `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'password',
        client_id: CLIENT_ID,
        username,
        password,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error_description || error.error || 'Login failed');
  }

  const data = await response.json();
  persistSession(data.access_token, data.id_token, data.refresh_token);
  return {
    accessToken: data.access_token,
    idToken: data.id_token,
    refreshToken: data.refresh_token
  };
}

export async function refreshAccessToken(refreshToken) {
  const response = await fetch(
    `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: refreshToken,
      }),
    }
  );

  if (!response.ok) {
    throw new Error('Token refresh failed');
  }

  const data = await response.json();
  persistSession(data.access_token, data.id_token, data.refresh_token);
  return {
    accessToken: data.access_token,
    idToken: data.id_token,
    refreshToken: data.refresh_token
  };
}
