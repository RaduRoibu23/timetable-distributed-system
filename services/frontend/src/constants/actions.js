// Helper function to generate unique names with timestamp
function getUniqueName(prefix) {
  const timestamp = Date.now();
  return `${prefix}-${timestamp}`;
}

// All available actions with required roles
export const ALL_ACTIONS = [
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
  { id: 'create-curriculum', label: 'Creează Curriculum', apiPath: '/curricula', method: 'POST', body: async function(apiGet) {
    const classes = await apiGet('/classes');
    const subjects = await apiGet('/subjects');
    if (!Array.isArray(classes) || classes.length === 0) throw new Error('Nu există clase disponibile');
    if (!Array.isArray(subjects) || subjects.length === 0) throw new Error('Nu există materii disponibile');
    const existing = await apiGet('/curricula');
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
  { id: 'modify-timetable', label: 'Modifică Orar', apiPath: '/timetables/entries/{id}', method: 'PATCH', body: async function(apiGet) {
    const subjects = await apiGet('/subjects');
    const rooms = await apiGet('/rooms/');
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
  { id: 'send-notification', label: 'Trimite Notificare', apiPath: '/notifications/send', method: 'POST', body: async function(apiGet) {
    const classes = await apiGet('/classes');
    if (!Array.isArray(classes) || classes.length === 0) throw new Error('Nu există clase disponibile');
    return { target_type: 'class', target_id: classes[0].id, message: `Test notification ${new Date().toLocaleTimeString()}` };
  }, requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  
  // Lessons
  { id: 'my-lessons', label: 'Lecțiile Mele', apiPath: '/lessons/mine', method: 'GET', requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  { id: 'list-lessons', label: 'Vezi Lecții', apiPath: '/lessons', method: 'GET', requiredRoles: ['professor', 'secretariat', 'admin', 'sysadmin'] },
  { id: 'create-lesson', label: 'Creează Lecție', apiPath: '/lessons', method: 'POST', body: async function(apiGet) {
    const subjects = await apiGet('/subjects');
    const classes = await apiGet('/classes');
    const rooms = await apiGet('/rooms/');
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

export function hasPermission(roles, requiredRoles) {
  if (!requiredRoles || requiredRoles.length === 0) return true;
  return roles.some(r => requiredRoles.includes(r));
}
