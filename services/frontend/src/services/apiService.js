import { CONFIG } from '../config';

const API_BASE = CONFIG.api.baseUrl;

export async function apiGet(path, accessToken) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`API error ${response.status}: ${JSON.stringify(error)}`);
  }
  return response.json();
}

export async function apiPost(path, body, accessToken) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`API error ${response.status}: ${JSON.stringify(error)}`);
  }
  return response.json();
}

export async function apiPut(path, body, accessToken) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`API error ${response.status}: ${JSON.stringify(error)}`);
  }
  return response.json();
}

export async function apiPatch(path, body, accessToken) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`API error ${response.status}: ${JSON.stringify(error)}`);
  }
  return response.json();
}

export async function apiDelete(path, accessToken) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`API error ${response.status}: ${JSON.stringify(error)}`);
  }
  if (response.status === 204) return { detail: 'Deleted' };
  return response.json();
}
