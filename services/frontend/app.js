// app.js
const CFG = window.APP_CONFIG;

const KEYCLOAK_URL = CFG.keycloak.url;
const REALM = CFG.keycloak.realm;
const CLIENT_ID = CFG.keycloak.clientId;

const API_BASE = CFG.api.baseUrl;
const STORAGE_KEY = CFG.auth.storageKey;

let accessToken = null;
let idToken = null;
let refreshToken = null;

function $(id){ return document.getElementById(id); }

function decodeJwt(token) {
  try {
    const parts = token.split('.');
    const payload = parts[1];
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

function setBadge(text){
  $('status-badge').textContent = text;
}

function showError(msg){
  const el = $('login-error');
  if (!msg){
    el.classList.add('hidden');
    el.textContent = '';
    return;
  }
  el.classList.remove('hidden');
  el.textContent = msg;
}

function persistSession(){
  const payload = {
    accessToken,
    idToken,
    refreshToken,
    savedAt: Date.now()
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function clearSession(){
  accessToken = null;
  idToken = null;
  refreshToken = null;
  localStorage.removeItem(STORAGE_KEY);
}

function loadSession(){
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return false;
  try{
    const data = JSON.parse(raw);
    accessToken = data.accessToken || null;
    idToken = data.idToken || null;
    refreshToken = data.refreshToken || null;
    return !!accessToken;
  }catch{
    return false;
  }
}

function tokenExpiryText(token){
  const tk = token ? decodeJwt(token) : null;
  if (!tk || !tk.exp) return '—';
  const ms = tk.exp * 1000;
  const d = new Date(ms);
  return `${d.toLocaleString()} (exp=${tk.exp})`;
}

function rolesFromToken(){
  const tk = accessToken ? decodeJwt(accessToken) : null;
  const roles = (tk && tk.realm_access && Array.isArray(tk.realm_access.roles))
    ? tk.realm_access.roles
    : [];
  return roles;
}

function buildUserLabel(){
  const tk = accessToken ? decodeJwt(accessToken) : null;
  if (!tk) return '—';
  const name = tk.given_name
    ? `${tk.given_name} ${tk.family_name || ''}`.trim()
    : (tk.preferred_username || 'Unknown');

  const uname = tk.preferred_username || '';
  return `${name}${uname ? ` (${uname})` : ''}`;
}

function showAuthenticatedUI(){
  $('login-card').style.display = 'none';
  $('dashboard-card').style.display = 'block';
  setBadge('Status: autentificat');

  $('user-info').textContent = buildUserLabel();
  $('token-exp').textContent = tokenExpiryText(accessToken);
  $('api-base').textContent = API_BASE;

  // roles pills
  const roles = rolesFromToken();
  const pills = $('roles-pills');
  pills.innerHTML = '';
  if (!roles.length){
    const p = document.createElement('span');
    p.className = 'pill warn';
    p.textContent = 'no roles';
    pills.appendChild(p);
  } else {
    roles.forEach(r => {
      const p = document.createElement('span');
      p.className = 'pill info';
      p.textContent = r;
      pills.appendChild(p);
    });
  }

  // role view
  const rv = $('role-view');
  if (roles.includes('admin')) {
    rv.innerHTML =
      `<div class="pills">
        <span class="pill ok">admin</span>
        <span class="pill">manage users</span>
        <span class="pill">manage rooms</span>
        <span class="pill">audit</span>
      </div>
      <div style="margin-top:10px" class="hint">
        Recomandare SCD: arată aici operații “admin only” (ex: creare sală, import orar, management profesori).
      </div>`;
  } else if (roles.includes('professor')) {
    rv.innerHTML =
      `<div class="pills">
        <span class="pill ok">professor</span>
        <span class="pill">my lessons</span>
        <span class="pill">attendance</span>
      </div>
      <div style="margin-top:10px" class="hint">
        Exemplu: listare cursuri/seminare alocate și modificări permise doar profesorului.
      </div>`;
  } else if (roles.includes('student')) {
    rv.innerHTML =
      `<div class="pills">
        <span class="pill ok">student</span>
        <span class="pill">my timetable</span>
        <span class="pill">enrollments</span>
      </div>
      <div style="margin-top:10px" class="hint">
        Exemplu: vizualizare orar personal, săli, notificări de schimbări.
      </div>`;
  } else {
    rv.textContent = 'Nu există o vedere specifică (rol necunoscut).';
  }
}

function showUnauthenticatedUI(){
  $('login-card').style.display = 'block';
  $('dashboard-card').style.display = 'none';
  setBadge('Status: neautentificat');
  showError('');
  $('api-result').textContent = '';
}

async function attemptLogin(username, password) {
  const tokenUrl = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`;
  const body = new URLSearchParams();
  body.set('grant_type', 'password');
  body.set('client_id', CLIENT_ID);
  body.set('username', username);
  body.set('password', password);

  const res = await fetch(tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  });

  if (!res.ok) {
    // încearcă să extragi eroarea Keycloak
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }

  const data = await res.json();
  accessToken = data.access_token || null;
  idToken = data.id_token || null;
  refreshToken = data.refresh_token || null;

  if (!accessToken) throw new Error('Keycloak a răspuns fără access_token.');

  persistSession();
  return true;
}

async function refreshAccessToken(){
  if (!refreshToken) throw new Error('Nu există refresh_token în sesiune.');

  const tokenUrl = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`;
  const body = new URLSearchParams();
  body.set('grant_type', 'refresh_token');
  body.set('client_id', CLIENT_ID);
  body.set('refresh_token', refreshToken);

  const res = await fetch(tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }

  const data = await res.json();
  accessToken = data.access_token || accessToken;
  idToken = data.id_token || idToken;
  refreshToken = data.refresh_token || refreshToken;

  persistSession();
  $('token-exp').textContent = tokenExpiryText(accessToken);
  return true;
}

async function apiGet(path){
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/json'
    }
  });

  const txt = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(txt); } catch { /* ignore */ }

  if (!res.ok){
    const msg = parsed ? JSON.stringify(parsed, null, 2) : txt;
    throw new Error(`API error ${res.status}\n${msg}`);
  }
  return parsed ?? txt;
}

// Tabs
function setActiveTab(name){
  document.querySelectorAll('.tab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === name);
  });
  $('tab-overview').style.display = (name === 'overview') ? 'block' : 'none';
  $('tab-role').style.display = (name === 'role') ? 'block' : 'none';
  $('tab-api').style.display = (name === 'api') ? 'block' : 'none';
}

// Wire UI
function wireUI(){
  // config hints
  $('kc-url').textContent = KEYCLOAK_URL;
  $('kc-realm').textContent = REALM;
  $('kc-client').textContent = CLIENT_ID;
  $('api-base').textContent = API_BASE;

  $('btn-fill-admin').addEventListener('click', () => {
    $('username').value = 'admin';
    $('password').value = 'admin';
  });
  $('btn-fill-student').addEventListener('click', () => {
    $('username').value = 'student';
    $('password').value = 'student';
  });

  $('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    showError('');

    const username = $('username').value.trim();
    const password = $('password').value;

    if (!username || !password) {
      showError('Completează username și password.');
      return;
    }

    $('btn-login').disabled = true;
    $('btn-login').textContent = 'Se autentifică...';

    try{
      await attemptLogin(username, password);
      showAuthenticatedUI();
    } catch (err){
      console.error('login error', err);
      showError('Autentificare eșuată — verifică credentialele sau configurarea Keycloak.');
    } finally {
      $('btn-login').disabled = false;
      $('btn-login').textContent = 'Login';
    }
  });

  $('btn-logout').addEventListener('click', () => {
    clearSession();
    showUnauthenticatedUI();
  });

  $('btn-refresh').addEventListener('click', async () => {
    $('api-result').textContent = '';
    try{
      await refreshAccessToken();
      showAuthenticatedUI();
    } catch (err){
      console.error(err);
      $('api-result').textContent = String(err.message || err);
    }
  });

  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => setActiveTab(btn.getAttribute('data-tab')));
  });

  $('btn-call-me').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      // Ajustează endpoint-ul după backend-ul tău
      const data = await apiGet('/me');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-rooms').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      // Ajustează endpoint-ul după backend-ul tău
      const data = await apiGet('/rooms');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });
}

// Init
(function init(){
  wireUI();
  setActiveTab('overview');

  const restored = loadSession();
  if (restored) {
    // dacă token-ul e expirat, încearcă refresh
    const tk = decodeJwt(accessToken);
    const now = Math.floor(Date.now()/1000);
    if (tk && tk.exp && tk.exp < now + 10) {
      refreshAccessToken()
        .then(showAuthenticatedUI)
        .catch(() => { clearSession(); showUnauthenticatedUI(); });
    } else {
      showAuthenticatedUI();
    }
  } else {
    showUnauthenticatedUI();
  }
})();
