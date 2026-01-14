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

// Helper function to generate unique names with timestamp
function getUniqueName(prefix) {
  const timestamp = Date.now();
  return `${prefix}-${timestamp}`;
}

// All available actions with required roles
const ALL_ACTIONS = [
  // Catalog - Classes
  { id: 'list-classes', label: 'Vezi Clase', apiPath: '/classes', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'create-class', label: 'Creează Clasă', apiPath: '/classes', method: 'POST', body: () => ({ name: getUniqueName('Clasa') }), requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'update-class', label: 'Modifică Clasă', apiPath: '/classes/{id}', method: 'PUT', body: () => ({ name: getUniqueName('Clasa-Mod') }), requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'delete-class', label: 'Șterge Clasă', apiPath: '/classes/{id}', method: 'DELETE', requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  
  // Catalog - Subjects
  { id: 'list-subjects', label: 'Vezi Materii', apiPath: '/subjects', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'create-subject', label: 'Creează Materie', apiPath: '/subjects', method: 'POST', body: () => ({ name: getUniqueName('Materie'), short_code: `M${Date.now().toString().slice(-4)}` }), requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'update-subject', label: 'Modifică Materie', apiPath: '/subjects/{id}', method: 'PUT', body: () => ({ name: getUniqueName('Materie-Mod'), short_code: `M${Date.now().toString().slice(-4)}` }), requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'delete-subject', label: 'Șterge Materie', apiPath: '/subjects/{id}', method: 'DELETE', requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  
  // Catalog - Curricula
  { id: 'list-curricula', label: 'Vezi Curricula', apiPath: '/curricula', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'create-curriculum', label: 'Creează Curriculum', apiPath: '/curricula', method: 'POST', body: async function() {
    // Need to use apiGet from outer scope - will be called with context
    const classes = await fetch(`${API_BASE}/classes`, {
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Accept': 'application/json' }
    }).then(r => r.json());
    const subjects = await fetch(`${API_BASE}/subjects`, {
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Accept': 'application/json' }
    }).then(r => r.json());
    if (!Array.isArray(classes) || classes.length === 0) throw new Error('Nu există clase disponibile');
    if (!Array.isArray(subjects) || subjects.length === 0) throw new Error('Nu există materii disponibile');
    // Find a combination that doesn't exist
    const existing = await fetch(`${API_BASE}/curricula`, {
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Accept': 'application/json' }
    }).then(r => r.json());
    const existingKeys = new Set((existing || []).map(c => `${c.class_id}-${c.subject_id}`));
    for (const cls of classes) {
      for (const subj of subjects) {
        const key = `${cls.id}-${subj.id}`;
        if (!existingKeys.has(key)) {
          return { class_id: cls.id, subject_id: subj.id, hours_per_week: 2 };
        }
      }
    }
    throw new Error('Toate combinațiile class-subject există deja');
  }, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'update-curriculum', label: 'Modifică Curriculum', apiPath: '/curricula/{id}', method: 'PUT', body: () => ({ hours_per_week: 4 }), requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  { id: 'delete-curriculum', label: 'Șterge Curriculum', apiPath: '/curricula/{id}', method: 'DELETE', requiresId: true, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  
  // Timetables
  { id: 'view-my-timetable', label: 'Vezi Orarul Meu', apiPath: '/timetables/me', method: 'GET', requiresClassId: true, requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'view-class-timetable', label: 'Vezi Orar Clasă', apiPath: '/timetables/classes/1', method: 'GET', requiredRoles: ['professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'generate-timetable', label: 'Generează Orar', apiPath: '/timetables/generate', method: 'POST', body: () => ({ class_id: 1 }), requiredRoles: ['scheduler', 'secretariat', 'admin', 'sysadmin'] },
  { id: 'modify-timetable', label: 'Modifică Orar', apiPath: '/timetables/entries/{id}', method: 'PATCH', body: async function() {
    const subjects = await this.apiGet('/subjects');
    const rooms = await this.apiGet('/rooms/');
    if (!Array.isArray(subjects) || subjects.length === 0) throw new Error('Nu există materii disponibile');
    if (!Array.isArray(rooms) || rooms.length === 0) throw new Error('Nu există săli disponibile');
    return { subject_id: subjects[0].id, room_id: rooms[0].id };
  }, requiresId: true, getIdFrom: '/timetables/classes/1', requiredRoles: ['scheduler', 'secretariat', 'admin', 'sysadmin'] },
  
  // Rooms
  { id: 'list-rooms', label: 'Vezi Săli', apiPath: '/rooms/', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'create-room', label: 'Creează Sală', apiPath: '/rooms/', method: 'POST', body: () => ({ name: getUniqueName('Sala'), capacity: 30 }), requiredRoles: ['admin', 'sysadmin'] },
  { id: 'update-room', label: 'Modifică Sală', apiPath: '/rooms/{id}', method: 'PUT', body: () => ({ name: getUniqueName('Sala-Mod'), capacity: 35 }), requiresId: true, requiredRoles: ['admin', 'sysadmin'] },
  { id: 'delete-room', label: 'Șterge Sală', apiPath: '/rooms/{id}', method: 'DELETE', requiresId: true, requiredRoles: ['admin', 'sysadmin'] },
  
  // Notifications
  { id: 'my-notifications', label: 'Notificările Mele', apiPath: '/notifications/me', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
  { id: 'send-notification', label: 'Trimite Notificare', apiPath: '/notifications/send', method: 'POST', body: async function() {
    const classes = await this.apiGet('/classes');
    if (!Array.isArray(classes) || classes.length === 0) throw new Error('Nu există clase disponibile');
    return { target_type: 'class', target_id: classes[0].id, message: `Test notification ${new Date().toLocaleTimeString()}` };
  }, requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  
  // Lessons
  { id: 'my-lessons', label: 'Lecțiile Mele', apiPath: '/lessons/mine', method: 'GET', requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  { id: 'list-lessons', label: 'Vezi Lecții', apiPath: '/lessons', method: 'GET', requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  { id: 'create-lesson', label: 'Creează Lecție', apiPath: '/lessons', method: 'POST', body: async function() {
    const subjects = await this.apiGet('/subjects');
    const classes = await this.apiGet('/classes');
    const rooms = await this.apiGet('/rooms/');
    if (!Array.isArray(subjects) || subjects.length === 0) throw new Error('Nu există materii disponibile');
    if (!Array.isArray(classes) || classes.length === 0) throw new Error('Nu există clase disponibile');
    if (!Array.isArray(rooms) || rooms.length === 0) throw new Error('Nu există săli disponibile');
    return { 
      title: `Lecție ${Date.now()}`, 
      subject_id: subjects[0].id, 
      class_id: classes[0].id, 
      room_id: rooms[0].id,
      weekday: 1,
      start_time: '08:00:00',
      end_time: '09:00:00'
    };
  }, requiredRoles: ['secretariat', 'admin', 'sysadmin'] },
  
  // User Info
  { id: 'my-info', label: 'Informații Mele', apiPath: '/me', method: 'GET', requiredRoles: ['student', 'professor', 'secretariat', 'scheduler', 'admin', 'sysadmin'] },
];

function hasPermission(roles, requiredRoles) {
  if (!requiredRoles || requiredRoles.length === 0) return true;
  return roles.some(r => requiredRoles.includes(r));
}

function renderRoleActions(){
  const list = $('actions-list');
  if (!list) {
    console.error('actions-list element not found!');
    return;
  }
  
  list.innerHTML = '';
  const roles = rolesFromToken();
  console.log('Current roles:', roles);
  console.log('Rendering', ALL_ACTIONS.length, 'actions');
  
  ALL_ACTIONS.forEach(action => {
    const hasAccess = hasPermission(roles, action.requiredRoles);
    const btn = document.createElement('button');
    btn.className = hasAccess ? 'btn' : 'btn btn-disabled';
    btn.textContent = action.label;
    btn.dataset.action = action.id;
    btn.dataset.hasAccess = hasAccess;
    
    if (hasAccess) {
      btn.addEventListener('click', async () => {
        try{
          await performAction(action);
        } catch(err){
          console.error('Button click error:', err);
          $('api-result').textContent = String(err.message || err);
        }
      });
    } else {
      btn.style.opacity = '0.5';
      btn.style.cursor = 'not-allowed';
      btn.addEventListener('click', () => {
        alert(`Rolul dvs. nu vă permite să efectuați această acțiune.\n\nAcțiune: ${action.label}\nRoluri necesare: ${action.requiredRoles.join(', ')}\nRolurile dvs.: ${roles.join(', ') || 'Niciun rol'}`);
      });
    }
    
    list.appendChild(btn);
  });
  
  console.log('Rendered', list.children.length, 'buttons');
  
  if (!list.children.length){
    const p = document.createElement('div'); 
    p.className='hint'; 
    p.textContent='Nicio acțiune disponibilă.'; 
    list.appendChild(p);
  }
}

async function performAction(action){
  console.log('Executing action:', action);
  $('api-result').textContent = `Se execută: ${action.label}...`;
  try{
    const method = action.method || 'GET';
    let apiPath = action.apiPath;
    
    // Handle dynamic IDs for update/delete operations
    if (action.requiresId && apiPath.includes('{id}')) {
      // For update/delete, we need to get an ID first
      let listPath = action.getIdFrom || apiPath.replace('/{id}', '').replace('{id}', '').replace(/\/$/, '');
      const listData = await apiGet(listPath);
      
      if (!Array.isArray(listData) || listData.length === 0) {
        throw new Error(`Nu există elemente disponibile pentru ${action.label}. Creează mai întâi un element.`);
      }
      
      // Use first item's ID
      const firstId = listData[0].id;
      apiPath = apiPath.replace('{id}', firstId);
      console.log(`Using ID ${firstId} for ${action.label}`);
    }
    
    // Handle compat endpoints (like /lessons/mine which is actually /lessons/mine via compat router)
    if (action.useCompat) {
      // Keep path as is, it's handled by compat router
    }
    
    // Handle class_id requirement for /timetables/me (non-students)
    if (action.requiresClassId && apiPath.includes('/timetables/me')) {
      const roles = rolesFromToken();
      if (!roles.includes('student')) {
        // Non-students need class_id
        const classes = await apiGet('/classes');
        if (Array.isArray(classes) && classes.length > 0) {
          const classId = classes[0].id;
          apiPath = `${apiPath}?class_id=${classId}`;
          console.log(`Using class_id ${classId} for ${action.label}`);
        } else {
          throw new Error('Nu există clase disponibile. Creează mai întâi o clasă.');
        }
      }
    }
    
    // Get body (call function if it's a function, otherwise use as-is)
    let body = null;
    if (action.body) {
      if (typeof action.body === 'function') {
        // Call with proper context so it can access apiGet, API_BASE, accessToken
        body = await action.body.call({ apiGet, API_BASE, accessToken });
      } else {
        body = action.body;
      }
    }
    
    let data;
    console.log(`Calling ${method} ${apiPath}`, body ? `with body: ${JSON.stringify(body)}` : '');
    
    if (method === 'GET') {
      data = await apiGet(apiPath);
    } else if (method === 'POST') {
      data = await apiPost(apiPath, body || {});
    } else if (method === 'PUT') {
      data = await apiPut(apiPath, body || {});
    } else if (method === 'PATCH') {
      data = await apiPatch(apiPath, body || {});
    } else if (method === 'DELETE') {
      data = await apiDelete(apiPath);
    } else {
      data = await apiGet(apiPath);
    }
    
    console.log('Response:', data);
    
    // Format response nicely
    if (Array.isArray(data) && data.length > 0 && data[0].class_id && data[0].timeslot_id) {
      // Timetable entries - format as table
      $('api-result').textContent = formatTimetable(data);
    } else {
      $('api-result').textContent = JSON.stringify(data, null, 2);
    }
  } catch (err){
    console.error('Action error:', err);
    const errorMsg = err.message || String(err);
    $('api-result').textContent = `❌ Eroare: ${errorMsg}\n\nEndpoint: ${action.method || 'GET'} ${action.apiPath}`;
    alert(`Eroare la executarea acțiunii "${action.label}":\n\n${errorMsg}`);
  }
}

function formatTimetable(entries) {
  if (!entries || entries.length === 0) return 'Nu există intrări în orar.';
  
  let result = `Orar (${entries.length} intrări):\n\n`;
  result += 'Clasă | Materie | Slot | Sala\n';
  result += '------|---------|------|-----\n';
  entries.slice(0, 20).forEach(e => {
    result += `${e.class_name || e.class_id} | ${e.subject_name || e.subject_id} | ${e.timeslot_name || `Zi ${e.timeslot_weekday} Ora ${e.timeslot_index}`} | ${e.room_name || '-'}\n`;
  });
  if (entries.length > 20) result += `... și ${entries.length - 20} mai multe\n`;
  return result;
}

async function apiPost(path, body) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(body)
  });
  const txt = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(txt); } catch { }
  if (!res.ok) {
    const msg = parsed ? JSON.stringify(parsed, null, 2) : txt;
    throw new Error(`API error ${res.status}\n${msg}`);
  }
  return parsed ?? txt;
}

async function apiPut(path, body) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(body)
  });
  const txt = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(txt); } catch { }
  if (!res.ok) {
    const msg = parsed ? JSON.stringify(parsed, null, 2) : txt;
    throw new Error(`API error ${res.status}\n${msg}`);
  }
  return parsed ?? txt;
}

async function apiPatch(path, body) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(body)
  });
  const txt = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(txt); } catch { }
  if (!res.ok) {
    const msg = parsed ? JSON.stringify(parsed, null, 2) : txt;
    throw new Error(`API error ${res.status}\n${msg}`);
  }
  return parsed ?? txt;
}

async function apiDelete(path) {
  if (!accessToken) throw new Error('Nu ești autentificat.');
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/json'
    }
  });
  const txt = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(txt); } catch { }
  if (!res.ok) {
    const msg = parsed ? JSON.stringify(parsed, null, 2) : txt;
    throw new Error(`API error ${res.status}\n${msg}`);
  }
  return parsed ?? { success: true };
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

  // Render all action buttons
  renderRoleActions();
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

  $('btn-fill-sysadmin').addEventListener('click', () => {
    $('username').value = 'sysadmin01';
    $('password').value = 'sysadmin01';
  });
  $('btn-fill-student').addEventListener('click', () => {
    $('username').value = 'student01';
    $('password').value = 'student01';
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
      const data = await apiGet('/me');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-rooms').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      const data = await apiGet('/rooms');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-classes').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      const data = await apiGet('/classes');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-subjects').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      const data = await apiGet('/subjects');
      $('api-result').textContent = JSON.stringify(data, null, 2);
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-timetable-me').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      const data = await apiGet('/timetables/me');
      if (Array.isArray(data) && data.length > 0) {
        $('api-result').textContent = formatTimetable(data);
      } else {
        $('api-result').textContent = JSON.stringify(data, null, 2);
      }
    } catch (err){
      $('api-result').textContent = String(err.message || err);
    }
  });

  $('btn-call-notifications').addEventListener('click', async () => {
    $('api-result').textContent = 'Loading...';
    try{
      const data = await apiGet('/notifications/me');
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
